"""Authenticated verification UI. Delivery is inactive until the owner configures it."""
import re
import secrets
from html import escape
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool
import player_access
import verification_storage as store
import verification_delivery as delivery


def render_verification(request, user, message='', error=False):
    from account_membership import page
    csrf = escape(request.session.setdefault('account_csrf', secrets.token_urlsafe(32)), quote=True)
    token = '<input type="hidden" name="csrf" value="' + csrf + '">'
    alert = '<p role="alert" style="color:' + ('#ffb4b4' if error else '#c5eddf') + '">' + escape(message) + '</p>' if message else ''
    active = player_access.enabled() and delivery.ready()
    email_verified = bool(user.get('email_verified_at'))
    email_step = '<p>Email confirmed.</p>' if email_verified else ('<p>We will send a six-digit code to <strong>' + escape(user['email']) + '</strong>.</p><form method="post" action="/verify-account/email/send">' + token + '<button class="tr-button" type="submit">Send email code</button></form><form method="post" action="/verify-account/email/check">' + token + '<label>Email code<input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" minlength="6" maxlength="6" required></label><button class="tr-button" type="submit">Confirm email</button></form>')
    if user.get('player_trial_expires_at'):
        phone_step = '<p>Your one-time Player trial has already been used on this account. A new phone or email does not restart it.</p>'
    elif not email_verified:
        phone_step = '<p>Confirm your email first to continue.</p>'
    else:
        phone_step = '<p>Start one 14-day Player trial per verified phone number. Enter an international phone number without spaces. SMS delivery and eligibility vary by country.</p><form method="post" action="/verify-account/phone/send">' + token + '<label>Phone number<input name="phone" type="tel" autocomplete="tel" pattern="[+][1-9][0-9]{7,14}" maxlength="16" placeholder="+447700900123" required></label><label style="display:flex;gap:8px;align-items:flex-start;margin:12px 0"><input type="checkbox" name="phone_consent" value="accepted" required style="width:18px;min-height:18px;margin:3px 0"><span>I request an SMS verification code for my number and agree that a protected identifier of this number is kept to prevent repeat trials. This is not marketing consent. See our <a href="/privacy">Privacy Policy</a>.</span></label><button class="tr-button" type="submit">Send SMS code</button></form><form method="post" action="/verify-account/phone/check">' + token + '<label>SMS code<input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{4,10}" minlength="4" maxlength="10" required></label><button class="tr-button" type="submit">Confirm phone and start 14-day Player trial</button></form>'
    if not active:
        email_step = '<p>Email confirmed.</p>' if email_verified else '<p>Email verification is not available yet. You can connect Google or Discord with a matching verified email in My Account &rarr; Sign-in options.</p>'
        phone_step = '<p>Phone verification and new trials are not available yet. No SMS has been sent and no trial has started.</p>'
    body = '<p class="tr-page-intro">Registration alone does not unlock full table information. A verified trial includes the same table access as paid Player membership for exactly 14 days. After expiry, a paid membership is needed. Host has no free trial.</p>' + alert + player_access.render_trial_notice(user) + '<section class="tr-info-card"><h2>1. Confirm your email</h2>' + email_step + '</section><section class="tr-info-card"><h2>2. Confirm your phone and start Player trial</h2>' + phone_step + '</section><p class="tr-muted">One phone number can receive one Player trial across all accounts. A phone number is not proof of a unique person. Recycled or shared numbers may need help from support. Existing paid memberships and staff access are separate.</p>'
    return HTMLResponse(page('Verify your account', body, user), headers={'Cache-Control': 'no-store'})


def install_verification_routes(app, get_current_user):
    def checked(request, csrf):
        if not player_access.enabled() or not delivery.ready():
            return None, HTMLResponse('Verification is not available yet.', status_code=503)
        user = get_current_user(request)
        saved = request.session.get('account_csrf', '')
        if not user or not saved or not secrets.compare_digest(saved, csrf):
            return None, HTMLResponse('Sign in and reopen account verification.', status_code=403)
        return user, None

    def ip(request):
        # Never trust a client-supplied forwarded header as identity.
        return str(getattr(getattr(request, 'client', None), 'host', '') or '')

    @app.get('/verify-account', response_class=HTMLResponse)
    def verify_page(request: Request):
        user = get_current_user(request)
        if not user:
            return RedirectResponse('/signin_login', status_code=303)
        return render_verification(request, user)

    @app.post('/verify-account/email/send')
    async def send_email(request: Request, csrf: str = Form('')):
        user, denied = checked(request, csrf)
        if denied is not None:
            return denied
        challenge = None
        try:
            challenge = await run_in_threadpool(store.create, user['email'], 'email', user['email'], user.get('credential_version', ''), ip(request))
            await run_in_threadpool(delivery.send_email, user['email'], challenge['code'], challenge['id'])
            await run_in_threadpool(store.delivered, user['email'], challenge['id'])
            return render_verification(request, user, 'Email code sent. It expires in ten minutes.')
        except Exception:
            if challenge:
                await run_in_threadpool(store.failed, user['email'], challenge['id'])
            return render_verification(request, user, 'Could not send a code. Wait before retrying, or contact support.', True)

    @app.post('/verify-account/email/check')
    async def check_email(request: Request, csrf: str = Form(''), code: str = Form('')):
        user, denied = checked(request, csrf)
        if denied is not None:
            return denied
        if not re.fullmatch(r'[0-9]{6}', code):
            return render_verification(request, user, 'Enter the six-digit email code.', True)
        try:
            verified = await run_in_threadpool(store.verify_email, user['email'], code, user.get('credential_version', ''))
        except Exception:
            verified = False
        return render_verification(request, get_current_user(request) or user,
            'Email confirmed. Continue with phone verification.' if verified else 'Code incorrect, expired or already used. Request a new code if needed.', not verified)

    @app.post('/verify-account/phone/send')
    async def send_phone(request: Request, csrf: str = Form(''), phone: str = Form(''), phone_consent: str = Form('')):
        user, denied = checked(request, csrf)
        if denied is not None:
            return denied
        if not user.get('email_verified_at') or phone_consent != 'accepted':
            return render_verification(request, user, 'Confirm your email and request the verification SMS using the checkbox.', True)
        challenge = None
        try:
            phone = delivery.phone_number(phone)
            challenge = await run_in_threadpool(store.create, user['email'], 'phone', phone, user.get('credential_version', ''), ip(request))
            sid = await run_in_threadpool(delivery.send_phone, phone)
            await run_in_threadpool(store.delivered, user['email'], challenge['id'], sid)
            return render_verification(request, user, 'SMS code sent. Enter it within ten minutes to start your Player trial.')
        except Exception:
            if challenge:
                await run_in_threadpool(store.failed, user['email'], challenge['id'])
            return render_verification(request, user, 'Could not send an SMS. Check the international number, wait before retrying, or contact support.', True)

    @app.post('/verify-account/phone/check')
    async def check_phone(request: Request, csrf: str = Form(''), code: str = Form('')):
        user, denied = checked(request, csrf)
        if denied is not None:
            return denied
        if not re.fullmatch(r'[0-9]{4,10}', code):
            return render_verification(request, user, 'Enter the SMS verification code.', True)
        try:
            challenge = await run_in_threadpool(store.phone_attempt, user['email'], user.get('credential_version', ''))
            approved = challenge and await run_in_threadpool(delivery.check_phone, challenge['phone'], challenge['sid'], code)
            granted = approved and await run_in_threadpool(store.claim_trial, user['email'], challenge['id'], user.get('credential_version', ''))
        except Exception:
            granted = False
        if granted:
            return RedirectResponse('/profile', status_code=303)
        return render_verification(request, get_current_user(request) or user, 'Code incorrect, expired, already used, or this account/phone is not eligible for another trial. Contact support if needed.', True)
