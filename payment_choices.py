from membership_plans import selectable, display_name, PLANS, product, product_key
"""Honest method chooser. Card and PayPal never collect or simulate payment."""
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from account_membership import page
from brand import render_host_listing_notice
import player_access


def membership_payment_page(request, user, plan):
    if not selectable(plan):
        return RedirectResponse('/profile', status_code=303)
    plan = product_key(plan)
    if player_access.friends_preview_enabled():
        return RedirectResponse('/profile', status_code=303)
    spec = product(plan)
    if player_access.needs_email_confirmation(user):
        return RedirectResponse('/verify-account', status_code=303)
    crypto = '<section class="tr-info-card"><h2>Cryptocurrency</h2><p>A one-time payment for 30 days, without automatic renewal. Availability depends on the configured payment service.</p><a class="tr-button" href="/pay/' + plan + '/crypto">View crypto payment options</a></section>'
    other = ''
    if plan == 'player':
        other = '<section class="tr-info-card"><h2>Bank card</h2><p>Coming soon. A payment provider has not been connected. No card details are collected and no payment is made here.</p><button class="tr-button" disabled>Card payment unavailable</button></section><section class="tr-info-card"><h2>PayPal</h2><p>Coming soon. A payment provider has not been connected. No PayPal payment can be started here.</p><button class="tr-button" disabled>PayPal unavailable</button></section>'
        trial = '<section class="tr-info-card"><h2>14-day Player Free Trial</h2><p>Verify your email and phone number, then start your 14-day Player Free Trial for full club and table details, including Join. After the trial ends, a paid membership is required.</p><a class="tr-button" href="/verify-account">Verify and start Free Trial</a>'
        other = trial + '</section>' + other
    intro = (f"{display_name(plan)} membership: {spec['price']} USD for 30 days. " + ('Planned methods: bank card, PayPal and cryptocurrency.' if spec['role'] == 'player' else f"Up to {spec['table_limit']} active tables for one club. Cryptocurrency only. Host has no free trial. The listing service period starts when the placement is ready and approved."))
    body = '<p class="tr-page-intro">' + intro + '</p>' + (render_host_listing_notice(spec['tier']) if spec['role'] == 'host' else '') + crypto + other
    return HTMLResponse(page('Choose ' + display_name(plan) + ' access', body, user), headers={'Cache-Control': 'no-store'})


def install_payment_choice_routes(app, get_current_user):
    @app.get('/pay/{plan}/crypto', response_class=HTMLResponse)
    def crypto(request: Request, plan: str):
        from crypto_checkout import checkout_page
        user = get_current_user(request)
        if not user:
            return RedirectResponse('/signin_login', status_code=303)
        return checkout_page(request, user, plan)
