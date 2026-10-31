from membership_plans import selectable, display_name, product, product_key
"""One-time crypto checkout, off until explicitly configured and approved.

Sandbox orders never change customer membership. Provider callback and manual
status checks both retrieve the invoice server-side before any settlement.
"""
import json
from player_access import needs_email_confirmation
import os
import secrets
from html import escape
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool
from account_membership import page
from brand import render_host_listing_notice
from staff_access import is_manager
from crypto_provider import CryptopayClient, CryptoUnavailable, callback_verified, checkout_options
import crypto_orders as orders


def configured(client):
    return client.ready() and bool(os.getenv('CRYPTOPAY_CALLBACK_SECRET',''))


def permitted_test(request,user,client):
    return not client.sandbox or bool(user.get('membership_test_enabled') or is_manager(request))


def csrf_ok(request, token):
    saved=request.session.get('account_csrf','')
    return bool(saved and secrets.compare_digest(saved.encode(),token.encode()))


def provider_data(response):
    data=response.get('data')
    if not isinstance(data,dict):
        raise ValueError('Unexpected invoice response')
    return data


def hosted_url(order):
    url=str(order.get('hosted_page_url') or '')
    parsed=urlparse(url)
    allowed={'hosted-business-sandbox.cryptopay.me'} if order.get('environment')=='sandbox' else {'hosted-business.cryptopay.me','business-hosted.cryptopay.me'}
    if parsed.scheme!='https' or parsed.netloc not in allowed or parsed.path!='/invoices/'+str(order.get('invoice_id')):
        return ''
    return url


def checkout_page(request,user,plan,error=''):
    if plan not in orders.PRICES or not selectable(plan):
        return RedirectResponse('/profile',status_code=303)
    from player_access import friends_preview_enabled
    if friends_preview_enabled():
        return RedirectResponse('/profile', status_code=303)
    if needs_email_confirmation(user):
        return RedirectResponse('/verify-account', status_code=303)
    token=request.session.setdefault('account_csrf',secrets.token_urlsafe(32))
    client=CryptopayClient()
    available=[]
    ready=configured(client) and permitted_test(request,user,client)
    if ready:
        try:
            available=checkout_options(client.request('GET','/api/coins'))
        except Exception:
            error='Crypto checkout is temporarily unavailable. Please try again later.'
    spec = product(plan)
    price=orders.PRICES[plan]
    notice=f'<p role="alert" class="tr-review-note">{escape(error)}</p>' if error else ''
    options=''.join(f'<option value="{escape(x["currency"]+":"+x["network"],quote=True)}">{escape(x["label"])}</option>' for x in available)
    form=f'''<form method="post" action="/payments/crypto/create/{plan}"><input type="hidden" name="csrf" value="{escape(token,quote=True)}"><p><label>Coin and network<select name="option" required>{options}</select></label></p><button class="tr-button" type="submit">{'Create test invoice' if client.sandbox else 'Continue to crypto payment'}</button></form>''' if options else '<p>Crypto payments are not available yet. Your account has not been charged.</p><p>Planned options: BTC · Bitcoin, ETH · Ethereum, USDT · Ethereum (ERC-20) or TRON (TRC-20), TRX · TRON, USDC · Ethereum or Solana, SOL · Solana and BNB · BNB Smart Chain. Available coins and networks will be confirmed at checkout after the payment service is approved and configured.</p><button class="tr-button" disabled>Crypto checkout unavailable</button>'
    body=f'''<p class="tr-page-intro">{escape(display_name(plan))} membership · {price} USD / 30 days</p>{notice}{render_host_listing_notice(spec["tier"]) if spec["role"] == "host" else ""}<section class="tr-info-card"><h2>Pay with crypto</h2><p>{'Private sandbox test — no real payment and no membership activation.' if ready and client.sandbox else 'A one-time payment for 30 days. Automatic renewal is off.'}</p>{form}<p>The payment page will show the exact coin amount, network, address and invoice expiry. Use only the network shown on that invoice.</p></section><p class="tr-muted">{'Sandbox test invoices do not activate paid membership.' if ready and client.sandbox else ('A verified payment opens your Host dashboard. Your service period starts when the placement is ready and the manager launches it.' if spec['role']=='host' else 'Membership activates only after a verified, completed payment.')} Bank payments are not available.</p>'''
    return HTMLResponse(page('Membership payment',body,user))


def order_page(request,user,order,error=''):
    token=request.session.setdefault('account_csrf',secrets.token_urlsafe(32))
    url=hosted_url(order)
    settled=bool(order.get('fulfilled'))
    sandbox=order.get('environment')=='sandbox'
    message=('Test completed - your membership has not changed.' if sandbox else ('Payment confirmed. Your Host access is open. See your Host dashboard for preparation progress and service dates.' if order.get('host_awaiting_launch') else 'Payment confirmed. Your 30-day membership has been activated.')) if settled else 'Waiting for confirmed payment. Returning to TableRadar does not itself confirm payment.'
    status=str(order.get('status') or 'pending')
    if status in ('unresolved','review_required'):
        message='This payment needs review. Do not send a second payment. Contact TableRadar support.'
    expired=False
    try:
        expiry=datetime.fromisoformat(str(order.get('expires_at','')).replace('Z','+00:00'))
        expired=expiry.tzinfo is not None and expiry<=datetime.now(timezone.utc)
    except (ValueError,TypeError):
        pass
    if not settled and status=='new' and expired:
        message='This invoice has expired. Do not send funds to its old address. If you already paid, check the status or contact support before creating another invoice.'
    elif not settled and status=='cancelled':
        message='This invoice was cancelled. No membership was activated. If you sent funds, contact support before paying again.'
    elif not settled and status=='refunded':
        message='The provider marked this invoice as refunded. No membership was activated. Contact support if you need payment details.'
    link=f'<a class="tr-button" href="{escape(url,quote=True)}" rel="noreferrer">Open secure payment page</a>' if url and not settled and status=='new' and not expired else ''
    refresh=f'<form method="post" action="/payments/crypto/order/{escape(order["id"],quote=True)}/refresh"><input type="hidden" name="csrf" value="{escape(token,quote=True)}"><button class="tr-button" type="submit">Check payment status</button></form>' if not settled else ''
    body=f'''<section class="tr-info-card"><h2>{escape(display_name(order.get('product') or order['plan']))} · {escape(order['price_amount'])} USD</h2><p>{'Sandbox test · ' if sandbox else ''}{escape(order['pay_currency'])} · {escape(order['network'])}</p><p>Status: <strong>{escape(status.replace('_',' ').title())}</strong></p><p>{escape(message)}</p>{'<p role="alert">'+escape(error)+'</p>' if error else ''}{link}{refresh}</section>'''
    return HTMLResponse(page('Payment status',body,user))


def refresh_order(client,order):
    environment='sandbox' if client.sandbox else 'production'
    if order.get('environment')!=environment:
        raise CryptoUnavailable('The payment environment has changed. Contact support.')
    invoice=provider_data(client.request('GET','/api/invoices/'+order['invoice_id']))
    return orders.settle(order['id'],invoice)


def install_crypto_routes(app,get_current_user):
    @app.post('/payments/crypto/create/{plan}')
    def create_payment(request:Request,plan:str,csrf:str=Form(''),option:str=Form('')):
        user=get_current_user(request)
        if not user:
            return RedirectResponse('/signin_login',status_code=303)
        if not csrf_ok(request,csrf):
            return HTMLResponse('Refresh your account page and try again.',status_code=403)
        from player_access import friends_preview_enabled
        if friends_preview_enabled():
            return HTMLResponse('Payments are paused during the friends preview. Choose Player or Host in My Account.', status_code=403)
        if needs_email_confirmation(user):
            return RedirectResponse('/verify-account', status_code=303)
        client=CryptopayClient()
        if plan not in orders.PRICES or not selectable(plan) or not configured(client) or not permitted_test(request,user,client):
            return HTMLResponse('Crypto checkout is not available.',status_code=503)
        try:
            options=checkout_options(client.request('GET','/api/coins'))
            selected=next((x for x in options if x['currency']+':'+x['network']==option),None)
            if not selected:
                return checkout_page(request,user,plan,'Select an available coin and network.')
            orders.initialize()
            order=orders.create(user['email'],plan,selected['currency'],selected['network'],'sandbox' if client.sandbox else 'production')
            response=client.request('POST','/api/invoices',dict(price_amount=order['price_amount'],price_currency='USD',pay_currency=order['pay_currency'],network=order['network'],custom_id=order['id'],description='TableRadar '+product(plan)['name']+' membership — 30 days',amount_includes_processing_fee=False))
            orders.attach_invoice(order['id'],provider_data(response))
        except Exception:
            return checkout_page(request,user,plan,'The payment invoice could not be created. No membership has been charged or activated. Please try again later.')
        return RedirectResponse('/payments/crypto/order/'+order['id'],status_code=303)

    @app.get('/payments/crypto/order/{order_id}')
    def payment_status(request:Request,order_id:str):
        user=get_current_user(request)
        if not user:
            return RedirectResponse('/signin_login',status_code=303)
        if not configured(CryptopayClient()):
            return HTMLResponse('Crypto checkout is not available.',status_code=503)
        orders.initialize()
        order=orders.get(order_id,user['email'])
        return order_page(request,user,order) if order else HTMLResponse('Payment not found.',status_code=404)

    @app.post('/payments/crypto/order/{order_id}/refresh')
    def payment_refresh(request:Request,order_id:str,csrf:str=Form('')):
        user=get_current_user(request)
        if not user:
            return RedirectResponse('/signin_login',status_code=303)
        if not csrf_ok(request,csrf):
            return HTMLResponse('Refresh your account page and try again.',status_code=403)
        client=CryptopayClient()
        if not configured(client):
            return HTMLResponse('Crypto checkout is not available.',status_code=503)
        order=orders.get(order_id,user['email'])
        if not order:
            return HTMLResponse('Payment not found.',status_code=404)
        try:
            refresh_order(client,order)
        except Exception:
            return order_page(request,user,order,'Status is temporarily unavailable. Do not pay twice; try checking again later.')
        return RedirectResponse('/payments/crypto/order/'+order_id,status_code=303)

    @app.post('/payments/crypto/callback')
    async def payment_callback(request:Request):
        client=CryptopayClient()
        if not configured(client):
            return HTMLResponse('Unavailable',status_code=503)
        body=b''
        async for chunk in request.stream():
            body+=chunk
            if len(body)>131072:
                return HTMLResponse('Too large',status_code=413)
        if not callback_verified(body,request.headers.get('x-cryptopay-signature',''),os.getenv('CRYPTOPAY_CALLBACK_SECRET','')):
            return HTMLResponse('Invalid signature',status_code=403)
        try:
            payload=json.loads(body)
            if payload.get('type')!='Invoice':
                return HTMLResponse('Ignored')
            invoice_id=payload['data']['id']
            order=await run_in_threadpool(orders.find_by_invoice,invoice_id)
            if not order:
                # A callback can race invoice attachment: let the provider retry.
                return HTMLResponse('Invoice not attached yet',status_code=503)
            await run_in_threadpool(refresh_order,client,order)
        except (KeyError,TypeError,ValueError):
            return HTMLResponse('Invalid callback',status_code=400)
        except Exception:
            return HTMLResponse('Retry later',status_code=503)
        return HTMLResponse('OK')
