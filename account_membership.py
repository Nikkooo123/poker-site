from membership_plans import PLANS, product_key, host_tier, table_limit, host_name
"""Owner-only membership preview and private club application workflow."""
from datetime import datetime, timedelta, timezone
from html import escape
from currency_codes import normalize_currency, currency_input
from club_request_changes import updated_request, field_html, changes_html, current_request
import account_repository as account_db
import secrets
import re
from staff_access import is_manager, set_staff_role
from host_lifecycle import awaiting_launch, has_host_access, launch_host, review_host_request, delete_club_request

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from auth.auth_storage import update_user, load_users, get_user_by_email
from brand import render_brand_logo, render_site_theme, render_site_footer, render_host_listing_notice


def membership_state(user):
    result = dict(user)
    if result.get("membership_test_enabled") or result.get("membership_source") in ("manager", "crypto"):
        try:
            expiry = datetime.fromisoformat(result.get("test_expires_at", "") if result.get("membership_test_enabled") else result.get("membership_expires_at", ""))
            remaining = max(0, int((expiry - datetime.now(timezone.utc)).total_seconds() + 86399) // 86400)
        except (ValueError, TypeError):
            remaining = 0
        result["days_left"] = remaining
        result["is_active"] = remaining > 0 and result.get("plan") in ("player", "host") and (result.get("membership_test_enabled") or result.get("is_active", False))
        result["auto_renew"] = False
    return result


def customer_activity_card(user, activity):
    safe = lambda value: escape(str(value or ""), quote=True)
    def stamp(value):
        if not value:
            return 'Not recorded yet'
        try:
            dt = value if isinstance(value,datetime) else datetime.fromisoformat(str(value).replace('Z','+00:00'))
            if dt.tzinfo is None:
                return safe(value)
            return dt.astimezone(timezone.utc).strftime('%d %b %Y, %H:%M UTC')
        except (ValueError,TypeError):
            return safe(value)
    from staff_access import activity_statistics_enabled
    shared=activity_statistics_enabled(user)
    seconds=max(0,int(activity.get('active_seconds',0)))
    duration=(str(seconds//3600)+'h '+str(seconds//60%60)+'m') if seconds>=3600 else (str(seconds//60)+'m '+str(seconds%60)+'s')
    state=membership_state(user)
    plan=str(state.get('plan','inactive')).lower()
    label=plan.title() if plan in ('player','host') else 'No membership'
    fields=[('Membership',label+' · '+('Active' if state.get('is_active') else 'Inactive')),
        ('Registered',stamp(user.get('registered_at') or user.get('registered'))),
        ('Last sign-in',stamp(activity.get('last_login_at'))),('Last active',stamp(activity.get('last_seen_at')) if shared else 'Not shared'),
        ('Sign-ins recorded',str(activity.get('login_count',0))),('Active time (approx.)',(duration if activity else 'Not recorded yet') if shared else 'Not shared'),
        ('Last section',safe(activity.get('last_page') or 'Not recorded yet') if shared else 'Not shared'),('Activity sharing','Enabled' if shared else 'Off')]
    return '<dl class="tr-team-metrics">'+''.join('<div><dt style="font-size:11px;color:var(--tr-muted)">'+title+'</dt><dd style="margin:3px 0 0;font-size:12px;overflow-wrap:anywhere">'+value+'</dd></div>' for title,value in fields)+'</dl>'


def pending_club_request_count():
    return sum(1 for user in load_users()
               if user.get("club_application")
               and not user["club_application"].get("deleted_at")
               and user["club_application"].get("status", "pending") == "pending")


def account_context(request, user):
    result = membership_state(user)
    result["_is_manager"] = is_manager(request)
    result["_can_test"] = is_manager(request) and bool(user.get("membership_test_enabled"))
    result["_can_enable_test"] = is_manager(request)
    result["_csrf"] = request.session.setdefault("account_csrf", secrets.token_urlsafe(32))
    return result


ACCOUNT_CSS = """<style>
.tr-club-request .tr-request-changed{color:#ff999f;font-weight:650;overflow-wrap:anywhere;white-space:pre-wrap}.tr-request-diff{margin:10px 0;padding:10px 12px;border-left:2px solid #e47780;background:#be43510c;border-radius:0 8px 8px 0}.tr-club-request .tr-request-update-note{font-size:11px;color:#eeb0b5;margin:0 0 7px}.tr-request-diff dl{margin:0;display:grid;gap:8px}.tr-request-diff-row{display:grid;grid-template-columns:125px minmax(0,1fr);gap:8px;font-size:12px}.tr-request-diff-row dt{color:#c3cdce}.tr-request-diff-row dd{margin:0;min-width:0}.tr-request-before{display:block;color:#9baaad;font-size:11px;overflow-wrap:anywhere;white-space:pre-wrap;margin-bottom:2px}@media(max-width:600px){.tr-request-diff-row{grid-template-columns:1fr;gap:2px}}

.tr-info-card{border:1px solid rgba(200,223,221,.12);border-radius:22px;padding:28px;margin:24px 0;background:linear-gradient(145deg,#202d32e8,#172126e8)}
.tr-status-changes{color:#edaaa5;background:#9e434326;border:1px solid #d98a8555;border-radius:8px;padding:4px 8px;display:inline-block}.tr-review-note{border-left:3px solid #d98a85;padding:10px 14px;background:#9e434310}.tr-info-card h2{font-size:22px;margin:0 0 14px}.tr-info-card p{color:#a5b4b6;line-height:1.6}.tr-info-card form{max-width:620px;margin-top:26px}.tr-info-card label{display:block;font-size:13px;color:#dbe6e4}.tr-info-card input,.tr-info-card select,.tr-info-card textarea{display:block;width:100%;box-sizing:border-box;padding:12px 14px;margin-top:8px;border-radius:11px;border:1px solid #a8d8c430;background:#101b21;color:#edf3f2;font:inherit;min-height:46px}.tr-info-card textarea{min-height:110px;resize:vertical}.tr-info-card input:focus-visible,.tr-info-card select:focus-visible,.tr-info-card textarea:focus-visible{outline:2px solid #a8d8c4;outline-offset:2px}@media(max-width:600px){.tr-info-card{padding:22px}}
.tr-host-club.tr-info-card{padding:18px 22px;margin:16px 0}.tr-host-club h2{font-size:19px;margin-bottom:8px}.tr-host-club p{margin:8px 0;font-size:13px}.tr-host-edit summary{cursor:pointer;color:#b9dfd0;font-size:13px;padding:8px 0}.tr-host-club form{margin-top:12px;max-width:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.tr-host-club form p{margin:0}.tr-host-club textarea{min-height:72px}.tr-host-progress.tr-info-card{padding:22px;margin:18px 0}.tr-host-progress>p{margin:9px 0}.tr-host-steps{list-style:none;padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:20px 0 0}.tr-host-steps li{border-top:2px solid #8cbba45c;padding-top:12px;font-size:13px}.tr-host-steps span{display:block;font-size:12px;color:#a5b4b6;margin-top:6px;line-height:1.5}.tr-host-notification{border:1px solid #a8d8c455;background:#a8d8c414;border-radius:12px;padding:14px;color:#c4e9d9}@media(max-width:680px){.tr-host-steps{grid-template-columns:repeat(2,minmax(0,1fr))}.tr-host-club form{grid-template-columns:1fr}.tr-host-progress.tr-info-card,.tr-host-club.tr-info-card{padding:18px}}
</style>"""


def page(title, body, user, manager=False):
    from auth.profile_view import render_account_menu
    header_account = render_account_menu(user)
    workspace_nav = '<nav style="display:flex;gap:10px;flex-wrap:wrap;margin:0 0 24px"><a class="tr-button" href="/manager">← Back to manager</a><a class="tr-button" href="/admin">Table administration</a><a class="tr-button" href="/admin/club-subscriptions">Club subscriptions</a></nav>' if manager else ""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} · TableRadar</title>{render_site_theme()}{ACCOUNT_CSS}</head><body style="margin:0"><header class="tr-site-header">{render_brand_logo('/')}{header_account}</header><main class="tr-site-main">{workspace_nav}<h1 class="tr-page-title">{escape(title)}</h1>{body}<p><a class="tr-button" href="/profile">← My account</a></p></main>{render_site_footer()}</body></html>'''


def install_account_routes(app, get_current_user):
    @app.get('/manager/club-requests/count')
    def club_request_count(request: Request):
        if not is_manager(request):
            return JSONResponse({'error':'Manager access required.'},status_code=403,headers={'Cache-Control':'no-store'})
        return JSONResponse({'pending_count':pending_club_request_count()},headers={'Cache-Control':'no-store'})

    @app.post('/account/security/password')
    def update_password(request: Request, csrf: str = Form(''), current_password: str = Form(''), new_password: str = Form(''), confirm_password: str = Form('')):
        from auth.auth_storage import change_password
        from auth.profile_view import render_profile_page
        user=get_current_user(request)
        token=request.session.get('account_csrf','')
        if not user:
            return RedirectResponse('/signin_login',status_code=303)
        if not token or not secrets.compare_digest(token,csrf):
            return HTMLResponse('Refresh your account page and try again.',status_code=403)
        error=''
        if not 10 <= len(new_password) <= 256:
            error='Use a new password between 10 and 256 characters.'
        elif new_password != confirm_password:
            error='The new passwords do not match.'
        elif new_password == current_password:
            error='Choose a password different from your current password.'
        elif not change_password(user['email'],current_password,new_password):
            error='Your current password is incorrect. Please try again.'
        if error:
            context=account_context(request,user)
            context['_security_error']=error
            return HTMLResponse(render_profile_page(context),status_code=400)
        request.session.clear()
        response=RedirectResponse('/signin_login?password_changed=1',status_code=303)
        response.delete_cookie('admin_auth')
        return response

    @app.get('/manager/membership-test', response_class=HTMLResponse)
    def manager_membership_test(request: Request):
        if not is_manager(request):
            return HTMLResponse('Manager access required.',status_code=403)
        csrf=escape(request.session.setdefault('account_csrf',secrets.token_urlsafe(32)),quote=True)
        user=get_current_user(request)
        if not user:
            return RedirectResponse('/signin_login',status_code=303)
        forms=''.join(f'<form method="post" action="/account/test-membership"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="plan" value="{plan}"><button class="tr-button" type="submit">Try {PLANS[plan]["name"]} free</button></form>' for plan in ('player','host_starter','host_pro'))
        body=f'<p class="tr-page-intro">Manager-only test tools for {escape(user["email"])}. No payment or automatic renewal.</p><section class="tr-info-card"><h2>Test the customer experience</h2><p>Host opens your dashboard so you can submit your own club request, approve it in Club requests and check the resulting subscription and monitoring lists. Player lets you check the player account.</p>{forms}<p>Only your current account changes. Staff permissions stay the same. Existing membership details are backed up when you first enter test mode.</p><a class="tr-button" href="/profile">My account</a></section>'
        if request.query_params.get('host_reset') == 'done':
            body = '<p role="status" class="tr-host-notification">Your Host status, club request and placement have been reset. Your account, connected sign-in methods and manager access are preserved. Choose a Host plan below to start again.</p>' + body
        body += f'<section class="tr-info-card"><h2>Start your Host test again</h2><p>Reset only your own Host status, club request, club subscriptions and tables linked to those subscriptions. A backup is saved. Your account, sign-in methods, chat history and manager access stay intact.</p><form method="post" action="/manager/membership-test/reset-host"><input type="hidden" name="csrf" value="{csrf}"><button class="tr-button" type="submit">Reset my Host and club</button></form></section>'
        return page('Manager membership test',body,user or {},manager=True)

    @app.post('/manager/membership-test/reset-host')
    def reset_manager_host(request: Request, csrf: str = Form('')):
        user = get_current_user(request)
        token = request.session.get('account_csrf','')
        if not user or not is_manager(request) or not token or not secrets.compare_digest(token,csrf):
            return HTMLResponse('Manager access required.',status_code=403)
        from host_test_reset import reset_own_host
        reset_own_host(user['email'])
        request.session['plan'] = 'inactive'
        request.session['is_active'] = '0'
        return RedirectResponse('/manager/membership-test?host_reset=done',status_code=303)

    @app.post('/manager/membership-test/account')
    def bind_manager_test_account(request: Request, csrf: str = Form(''), email: str = Form(''), password: str = Form('')):
        token=request.session.get('account_csrf','')
        if not is_manager(request) or not token or not secrets.compare_digest(token,csrf):
            return HTMLResponse('Manager access required.',status_code=403)
        # Personal managers already have a bound account; never mint role claims.
        return RedirectResponse('/manager/membership-test',status_code=303)

    def permitted(request, csrf, allow_bootstrap=False):
        user = get_current_user(request)
        token = request.session.get('account_csrf','')
        if not user or not is_manager(request) or not token or not secrets.compare_digest(token,csrf):
            return None
        return user

    @app.post("/account/test-membership")
    def test_membership(request: Request, plan: str = Form(""), csrf: str = Form("")):
        user = permitted(request, csrf, allow_bootstrap=plan == "reset")
        if not user or plan not in ("reset", "player", "host", "host_starter", "host_pro"):
            return HTMLResponse("Membership preview is not available for this account.", status_code=403)
        selected_product = product_key(plan)
        base_plan = PLANS[selected_product]["role"] if plan != "reset" else "inactive"
        # The manager explicitly chooses a free preview for their signed-in account only.
        now = datetime.now(timezone.utc)
        previous = {key: user.get(key) for key in ("plan", "role", "is_active", "days_left", "auto_renew", "plan_started_at", "plan_expires_at", "membership_source", "membership_expires_at", "manual_subscription_id", "host_service_state", "host_paid_days", "host_approved_submission", "host_tier")}
        fields = dict(membership_test_enabled=True, plan="inactive" if plan == "reset" else base_plan,
                      role="member" if plan == "reset" else base_plan, is_active=plan != "reset",
                      days_left=0 if plan == "reset" else 30, auto_renew=False,
                      test_expires_at="" if plan == "reset" else (now + timedelta(days=30)).isoformat(),
                      plan_started_at="" if plan == "reset" else now.strftime("%d/%m/%Y"),
                      plan_expires_at="" if plan == "reset" else (now + timedelta(days=30)).strftime("%d/%m/%Y"))
        if base_plan == "host":
            fields["host_tier"] = PLANS[selected_product]["tier"]
        if not user.get("membership_test_enabled"):
            fields["membership_before_test"] = previous
        update_user(user["email"], **fields)
        request.session["plan"] = fields["plan"]
        request.session["is_active"] = "1" if fields["is_active"] else "0"
        return RedirectResponse("/host" if base_plan == "host" else "/profile", status_code=303)

    @app.get("/host", response_class=HTMLResponse)
    def host_account(request: Request):
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/signin_login", status_code=303)
        user = account_context(request, user)
        if not has_host_access(user):
            return RedirectResponse("/profile", status_code=303)
        club = current_request(user.get("club_application"))
        safe = lambda value: escape(str(value or ""), quote=True)
        csrf = safe(user["_csrf"])
        status_labels = {"pending": "Awaiting operator review", "approved": "Approved — operator manages table updates", "needs_changes": "Changes requested by the operator", "archived": "Request removed - submit updated details to request a new review"}
        club_status = status_labels.get(club.get("status"), "Awaiting operator review") if club else "No club submitted"
        review_note = f'<p class="tr-review-note">Operator note: {safe(club.get("review_note"))}</p>' if club.get("review_note") else ""
        status_class = "tr-status-changes" if club.get("status") == "needs_changes" else ""
        preparing = awaiting_launch(user)
        stage = ('Changes requested' if club.get('status')=='needs_changes' else 'Preparing your listing' if club.get('status')=='approved' else 'Request received - under review' if club else 'Your club details are needed')
        if preparing:
            period = f"{int(user.get('host_paid_days') or 30)} paid service days reserved. The countdown has not started."
            next_step = ('Please update the details below using the operator note.' if club.get('status')=='needs_changes' else 'We are checking your club and preparing its placement. When it is ready, approval will start the service period and a confirmation will appear here.' if club else 'Submit your club name, application and code below so our team can begin the review.')
        else:
            stage = 'Placement active' if club.get('status')=='approved' else stage
            period = f"{int(user.get('days_left') or 0)} days remaining. Service started: {safe(user.get('plan_started_at') or 'Not recorded')}. Valid until {safe(user.get('plan_expires_at') or 'Not recorded')}."
            if club.get('status') == 'approved' and user.get('is_active') and not club.get('deleted_at'):
                days = max(0, int(user.get('days_left') or 0))
                period = f'<span class="tr-host-remaining" role="status" aria-label="{days} days remaining" style="display:inline-flex;align-items:center;gap:10px;padding:12px 18px;margin:4px 0 12px;border:1px solid #77c5a480;border-radius:12px;background:linear-gradient(135deg,#294c40,#203c38);color:#d3f5e3"><strong style="font-size:28px;line-height:1">{days}</strong><span style="font-weight:600">days remaining</span></span><br>Service started: {safe(user.get("plan_started_at") or "Not recorded")}. Valid until {safe(user.get("plan_expires_at") or "Not recorded")}.'
            next_step = 'Your existing service dates are shown above. The operator reviews your request and maintains table information manually.'
        if user.get('membership_test_enabled') and club.get('status') != 'approved':
            period = 'Host test access is available. Your club placement period has not started.'
            next_step = 'Submit your club details below to start a new review.' if not club else 'Your request is being reviewed. Approval will start the club placement period.'
        if club.get('deleted_at'):
            stage = 'Request removed'
            next_step = 'Your previous request was removed from the review queue. You can update the details below and submit a new request. Any existing club placement keeps its current service dates.'
        timeline = ''.join(f'<li><strong>{title}</strong><span>{detail}</span></li>' for title,detail in (
            ('1. Host access confirmed', 'Your payment opens this private dashboard.' if preparing else 'Your Host access is available.'),
            ('2. Club review', 'Request received.' if club else 'Submit your club details.'),
            ('3. Preparation', 'Our team checks the details and prepares the placement.'),
            ('4. Placement starts', 'Approval activates your placement and starts the service countdown. Confirmation appears here.')))
        progress = f'<section class="tr-info-card tr-host-progress"><h2>{stage}</h2><p>{period}</p><p>{next_step}</p><ol class="tr-host-steps">{timeline}</ol></section>'
        current_approval = (club.get('status') == 'approved' and not club.get('deleted_at')
                            and club.get('submitted_at')
                            and user.get('host_approved_submission') == club.get('submitted_at'))
        notification = f'<p class="tr-host-notification" role="status">{safe(user.get("host_notification"))}</p>' if current_approval and user.get('host_notification') else ''
        test_notice = '<p class="tr-muted">Private free test - no payment was taken. Test dates are separate from paid club placement.</p>' if user.get("membership_test_enabled") else ""
        body = f'''<p class="tr-page-intro">Your club, listing request and membership in one place.</p>{test_notice}{notification}{progress}<section class="tr-info-card tr-host-club"><h2>Your club</h2><p>{host_name(user)} · up to {table_limit(user)} active tables</p>{"<p><strong>"+safe(club.get("club_name"))+"</strong> · "+safe(club.get("application"))+(" · "+safe(club.get("currency")) if club.get("currency") else "")+" · Code: "+safe(club.get("club_code"))+"</p>" if club else ""}<p>Status: <strong class="{status_class}">{club_status}</strong></p>{review_note}<p>One club per Host account. Submitting details does not publish tables or join a poker club. The operator reviews the request and updates table information manually.</p>{render_host_listing_notice(host_tier(user))}<details class="tr-host-edit" {"" if club else "open"}><summary>{"Edit club details" if club else "Submit club details"}</summary><form method="post" action="/host/club"><input type="hidden" name="csrf" value="{csrf}"><p><label>Your name or screen name *<br><input name="owner_name" required maxlength="100" autocomplete="nickname" value="{safe(club.get('owner_name'))}"></label></p><p><label>Telegram *<br><input name="telegram" required maxlength="80" placeholder="@yourname" value="{safe(club.get('telegram'))}"></label></p><p><label>Club name *<br><input name="club_name" required maxlength="120" value="{safe(club.get('club_name'))}"></label></p><p><label>Application<br><select name="application">{''.join(f'<option{chr(32)+"selected" if club.get("application")==name else ""}>{name}</option>' for name in ('ClubGG','X Poker','PPPoker','Other'))}</select></label></p><p><label>Game currency *<br>{currency_input(club.get("currency"))}</label></p><p><label>Club ID *<br><input name="club_code" required maxlength="80" value="{safe(club.get('club_code'))}"></label></p><p><label>Notes for the operator *<br><textarea name="notes" required maxlength="1000" aria-describedby="club-notes-help" placeholder="Describe club terms, rules and rakeback. If no rakeback is offered, please say so.">{safe(club.get('notes'))}</textarea></label><small id="club-notes-help" class="tr-muted">Include your club terms, rules and rakeback. If no rakeback is offered, please say so.</small></p><label style="display:flex;align-items:flex-start;gap:10px;margin:18px 0"><input type="checkbox" name="listing_conditions" value="accepted" required {"checked" if club.get("listing_policy_version")=="2026-10-23" and club.get("listing_policy_tier", "pro")==host_tier(user) else ""} style="width:18px;min-height:18px;margin:3px 0 0;flex-shrink:0"><span>* I agree to the Host listing conditions above: up to {table_limit(user)} eligible tables, $0.50/$1 minimum blinds and no heads-up tables.</span></label><button class="tr-button" type="submit">{'Update club request' if club else 'Submit club for review'}</button><p class="tr-muted">* Required fields</p></form></details></section>'''
        return page("Host dashboard", body, user)

    @app.post("/host/club")
    def submit_club(request: Request, csrf: str = Form(""), club_name: str = Form(""), application: str = Form(""), club_code: str = Form(""), notes: str = Form(""), owner_name: str = Form(""), telegram: str = Form(""), currency: str = Form(""), listing_conditions: str = Form("")):
        user = get_current_user(request)
        token = request.session.get("account_csrf", "")
        if not user or not token or not secrets.compare_digest(token, csrf) or not has_host_access(membership_state(user)):
            return HTMLResponse("Host access required.", status_code=403)
        telegram = telegram.strip()
        telegram = re.sub(r'^https?://(?:www\.)?t\.me/', '', telegram, flags=re.I).rstrip('/')
        if telegram and not telegram.startswith('@'):
            telegram = '@' + telegram
        if not owner_name.strip() or len(owner_name.strip()) > 100 or not re.fullmatch(r'@[A-Za-z0-9_]{3,64}', telegram):
            return HTMLResponse('Enter your name or screen name and a Telegram username such as @yourname. Telegram is required to submit your club.', status_code=400)
        if not club_name.strip() or not club_code.strip() or len(club_name) > 120 or len(club_code) > 80 or len(notes) > 1000 or application not in ("ClubGG", "X Poker", "PPPoker", "Other"):
            return HTMLResponse("Check the club name, application and code.", status_code=400)
        if not notes.strip():
            return HTMLResponse('Describe the club terms, rules and rakeback in Notes for the operator. If no rakeback is offered, please say so.',status_code=400)
        try:
            currency = normalize_currency(currency)
        except ValueError as error:
            return HTMLResponse(escape(str(error)), status_code=400)
        if listing_conditions != "accepted":
            return HTMLResponse(f'Please agree to the Host listing conditions: up to {table_limit(user)} eligible tables per club, blinds of $0.50/$1 or higher, and no heads-up tables. Return to the form to confirm.', status_code=400)
        details = dict(listing_policy_tier=host_tier(user), host_tier=host_tier(user), table_limit=table_limit(user), listing_policy_version="2026-10-23", listing_policy_accepted_at=datetime.now(timezone.utc).isoformat(), currency=currency, owner_name=owner_name.strip(), telegram=telegram, club_name=club_name.strip(), application=application, club_code=club_code.strip(), notes=notes.strip(), status="pending", submitted_at=datetime.now(timezone.utc).isoformat())
        if account_db.enabled():
            def apply_request(current):
                current['club_application'] = updated_request(details, current.get('club_application'))
                return current
            saved = account_db.mutate(user['email'], apply_request)
        else:
            current = get_user_by_email(user['email']) or {}
            saved = update_user(user['email'], club_application=updated_request(details, current.get('club_application')))
        if not saved:
            return HTMLResponse("Account no longer exists.", status_code=400)
        return RedirectResponse("/host", status_code=303)

    @app.get("/admin/club-requests", response_class=HTMLResponse)
    def club_requests(request: Request):
        if not is_manager(request):
            return RedirectResponse("/login", status_code=303)
        safe = lambda value: escape(str(value or ""), quote=True)
        csrf = safe(request.session.setdefault("account_csrf", secrets.token_urlsafe(32)))
        cards = []
        for user in load_users():
            club = user.get("club_application")
            if club and not club.get("deleted_at"):
                state = membership_state(user)
                review_options = ''.join(f'<option value="{value}"{" selected" if club.get("status", "pending") == value else ""}>{label}</option>' for value, label in (("pending", "Pending review"), ("approved", "Approve listing request"), ("needs_changes", "Request changes")))
                launch = f'<form method="post" action="/admin/club-requests/delete" onsubmit="return confirm(\'Delete this request? Existing club subscriptions and monitoring will stay unchanged.\')"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="email" value="{safe(user.get("email"))}"><input type="hidden" name="submitted_at" value="{safe(club.get("submitted_at"))}"><button class="tr-button" type="submit">Delete request</button></form>' 
                cards.append(f'<section class="tr-info-card tr-club-request"><h2>{field_html(club,"club_name")}</h2><p>{field_html(club,"owner_name","Owner name not provided")} · {field_html(club,"telegram","Telegram not provided")}</p><p>{safe(user.get("email"))} · {field_html(club,"application")}{(" · "+field_html(club,"currency")) if club.get("currency") else ""} · Club code: {field_html(club,"club_code")}</p><p>{safe(club.get("status", "pending"))} · Host access: {"paid - awaiting launch" if awaiting_launch(state) else "active" if state.get("is_active") and state.get("plan")=="host" else "inactive"}</p>{changes_html(club)}<details class="tr-request-review"><summary>Review request</summary><p>{field_html(club,"notes")}</p><form method="post" action="/admin/club-requests/review"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="email" value="{safe(user.get("email"))}"><input type="hidden" name="submitted_at" value="{safe(club.get("submitted_at"))}"><p><label>Review status<select name="status">{review_options}</select></label></p><p><label>Note to the owner<textarea name="review_note" maxlength="1000">{safe(club.get("review_note"))}</textarea></label></p><button class="tr-button" type="submit">Save review</button> <button class="tr-button" type="submit" formaction="/admin/club-requests/approve">Approve listing request</button><p class="tr-muted" style="grid-column:1/-1">Approving starts the service period, activates Club subscriptions and adds the club to Clubs to monitor. Approve only when the placement is ready.</p></form>{launch}</details></section>')
        return page("Club requests", ''.join(cards) or '<p>No club requests yet.</p>', get_current_user(request) or {}, manager=True)

    @app.post("/admin/club-requests/review")
    def review_club(request: Request, csrf: str = Form(""), email: str = Form(""), submitted_at: str = Form(""), status: str = Form(""), review_note: str = Form("")):
        token = request.session.get("account_csrf", "")
        if not is_manager(request) or not token or not secrets.compare_digest(token, csrf):
            return HTMLResponse("Operator access required.", status_code=403)
        if status not in ("pending", "approved", "needs_changes") or len(review_note) > 1000:
            return HTMLResponse("Invalid review.", status_code=400)
        try:
            from club_subscriptions_storage import init_club_subscriptions_db
            init_club_subscriptions_db()
            review_host_request(email, submitted_at, status, review_note)
        except ValueError as error:
            return HTMLResponse(escape(str(error)),status_code=409)
        return RedirectResponse("/admin/club-requests", status_code=303)

    @app.post('/admin/club-requests/delete')
    def remove_club_request(request: Request, csrf: str = Form(''), email: str = Form(''), submitted_at: str = Form('')):
        token=request.session.get('account_csrf','')
        if not is_manager(request) or not token or not secrets.compare_digest(token,csrf):
            return HTMLResponse('Manager access required.',status_code=403)
        try:
            delete_club_request(email,submitted_at)
        except ValueError as error:
            return HTMLResponse(escape(str(error)),status_code=409)
        return RedirectResponse('/admin/club-requests',status_code=303)

    @app.post('/admin/club-requests/approve')
    def approve_club(request: Request, csrf: str = Form(''), email: str = Form(''), submitted_at: str = Form(''), review_note: str = Form('')):
        return review_club(request,csrf,email,submitted_at,'approved',review_note)

    @app.post('/admin/club-requests/start')
    def start_club(request: Request, csrf: str = Form(''), email: str = Form(''), submitted_at: str = Form('')):
        token=request.session.get('account_csrf','')
        if not is_manager(request) or not token or not secrets.compare_digest(token,csrf):
            return HTMLResponse('Manager access required.',status_code=403)
        try:
            from club_subscriptions_storage import init_club_subscriptions_db
            init_club_subscriptions_db()
            launch_host(email, submitted_at)
        except ValueError as error:
            return HTMLResponse(escape(str(error)),status_code=409)
        return RedirectResponse('/admin/club-requests',status_code=303)

    @app.post('/account/privacy/activity')
    def activity_preference(request: Request, csrf: str = Form(''), activity_statistics: str = Form('')):
        user=get_current_user(request)
        token=request.session.get('account_csrf','')
        if not user or not token or not secrets.compare_digest(token,csrf):
            return HTMLResponse('Sign in and refresh your account page.',status_code=403)
        if activity_statistics not in ('','1'):
            return HTMLResponse('Choose whether to share optional activity statistics.',status_code=400)
        from staff_access import set_activity_statistics
        try:
            set_activity_statistics(user['email'],activity_statistics=='1')
        except ValueError as error:
            return HTMLResponse(escape(str(error)),status_code=409)
        return RedirectResponse('/profile',status_code=303)

    @app.get("/account/activity")
    def activity_token(request: Request):
        user = get_current_user(request)
        if not user:
            return JSONResponse({}, status_code=401, headers={'Cache-Control':'no-store'})
        from staff_access import activity_statistics_enabled
        if not activity_statistics_enabled(user):
            return JSONResponse({'enabled':False},headers={'Cache-Control':'no-store'})
        return JSONResponse({'enabled':True,'csrf':request.session.setdefault('account_csrf',secrets.token_urlsafe(32))}, headers={'Cache-Control':'no-store'})

    @app.post("/account/activity")
    def activity_heartbeat(request: Request, csrf: str = Form(""), active: str = Form("0"), section: str = Form("Information")):
        user = get_current_user(request)
        token = request.session.get('account_csrf','')
        if not user or not token or not secrets.compare_digest(token,csrf):
            return JSONResponse({}, status_code=403, headers={'Cache-Control':'no-store'})
        from staff_access import record_customer_activity,activity_statistics_enabled
        if not activity_statistics_enabled(user):
            return JSONResponse({'enabled':False},status_code=403,headers={'Cache-Control':'no-store'})
        try:
            if record_customer_activity(user['email'],active=='1',section) is False:
                return JSONResponse({'enabled':False},status_code=403,headers={'Cache-Control':'no-store'})
        except Exception:
            return JSONResponse({}, status_code=503, headers={'Cache-Control':'no-store'})
        return JSONResponse({'ok':True},headers={'Cache-Control':'no-store'})

    @app.get("/manager/team", response_class=HTMLResponse)
    def team_page(request: Request):
        if not is_manager(request):
            return HTMLResponse("Manager access required.", status_code=403)
        safe = lambda value: escape(str(value or ""), quote=True)
        csrf = safe(request.session.setdefault("account_csrf", secrets.token_urlsafe(32)))
        query = str(getattr(request, "query_params", {}).get("q", "")).strip()[:254]
        users = load_users()
        matches = [user for user in users if not query or query.casefold() in str(user.get("username") or "").casefold() or query.casefold() in str(user.get("email") or "").casefold()]
        search = f'<section class="tr-info-card tr-team-search"><form method="get" action="/manager/team" role="search"><label class="tr-team-search-label" for="team-search">Find a customer by nickname or email</label><input id="team-search" name="q" type="search" maxlength="254" autocomplete="off" placeholder="Nickname or email" value="{safe(query)}"><button class="tr-button" type="submit">Search</button>{"<a class=tr-button href=/manager/team>Clear</a>" if query else ""}<span class="tr-muted" role="status">{len(matches)} of {len(users)} customers</span></form></section>'

        from staff_access import customer_activity_summary
        activity = customer_activity_summary()
        cards = []
        for user in matches:
            role = user.get("staff_role", "")
            options = ''.join(f'<option value="{value}"{" selected" if role == value else ""}>{label}</option>' for value, label in (("", "Customer only — no staff access"), ("table_admin", "Table administrator — tables only"), ("manager", "Manager — tables, requests and subscriptions")))
            identity = f'<div class="tr-team-identity"><h2>{safe(user.get("username") or user.get("email"))}</h2>' + (f'<p>{safe(user.get("email"))}</p>' if user.get('username') and user.get('username') != user.get('email') else '') + '</div>'
            cards.append(f'<section class="tr-info-card tr-team-member">{identity}<form method="post" action="/manager/team"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="email" value="{safe(user.get("email"))}"><label>Staff access<select name="role">{options}</select></label><button class="tr-button" type="submit">Save access</button></form>{customer_activity_card(user, activity.get(user.get("email"), {}))}</section>')

        compact_css = """<style>
        .tr-team-page .tr-team-search{padding:10px 12px!important;margin:10px 0!important;border-radius:12px}
        .tr-team-page .tr-team-search form{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0!important;max-width:none!important}
        .tr-team-page .tr-team-search input{flex:1;min-width:160px;max-width:460px;width:auto;height:34px;min-height:34px;margin:0;padding:6px 10px;font-size:12px}
        .tr-team-page .tr-team-search .tr-button{height:34px;min-height:34px;padding:6px 12px;font-size:12px}
        .tr-team-page .tr-team-search [role=status]{font-size:11px;margin-left:auto;white-space:nowrap}
        .tr-team-search-label{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
        .tr-team-page .tr-team-member{padding:12px 14px!important;margin:8px 0!important;border-radius:12px;grid-template-columns:minmax(0,1fr) auto;align-items:start;gap:8px 16px}
        .tr-team-page .tr-team-identity{min-width:0;align-self:center}.tr-team-page .tr-team-member h2{font-size:14px!important;line-height:1.3;margin:0!important;overflow-wrap:anywhere}.tr-team-page .tr-team-member p{font-size:11px;margin:3px 0 0!important}
        .tr-team-page .tr-team-member form{gap:8px}.tr-team-page .tr-team-member form label{font-size:10px;min-width:0}.tr-team-page .tr-team-member select{height:32px;min-height:32px;margin:2px 0 0;padding:4px 8px;font-size:11px;max-width:290px}.tr-team-page .tr-team-member button{height:32px;min-height:32px;font-size:11px;padding:5px 10px}
        .tr-team-page .tr-team-metrics{grid-column:1/-1;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px 18px;margin:0!important;padding-top:7px;border-top:1px solid var(--tr-line)}
        .tr-team-page .tr-team-metrics dt{font-size:10px!important;line-height:1.3}.tr-team-page .tr-team-metrics dd{font-size:11px!important;line-height:1.3;margin-top:2px!important}
        .tr-team-page .tr-team-note{font-size:11px;line-height:1.5;margin:8px 0}
        @media(max-width:680px){.tr-team-page .tr-team-member{grid-template-columns:minmax(0,1fr);gap:8px}.tr-team-page .tr-team-member form{display:flex;flex-wrap:nowrap}.tr-team-page .tr-team-member form label{flex:1}.tr-team-page .tr-team-member select{max-width:none;width:100%}.tr-team-page .tr-team-metrics{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 12px}.tr-team-page .tr-team-search input{max-width:none}.tr-team-page .tr-team-search [role=status]{margin-left:0}}
        </style>"""
        return page("Staff access", compact_css + '<div class="tr-team-page"><p class="tr-muted tr-team-note">Personal accounts only. Keep at least one manager. Activity is approximate, excludes idle/background time and starts from this update. Dates: UTC.</p>' + search + (''.join(cards) or '<p class="tr-muted">No customers found. Try another nickname or email.</p>') + '</div>', get_current_user(request) or {}, manager=True)


    @app.post("/manager/team")
    def update_staff(request: Request, csrf: str = Form(""), email: str = Form(""), role: str = Form("")):
        token = request.session.get("account_csrf", "")
        if not is_manager(request) or not token or not secrets.compare_digest(token, csrf):
            return HTMLResponse("Manager access required.", status_code=403)
        if role not in ("", "table_admin", "manager") or not get_user_by_email(email):
            return HTMLResponse("Invalid account or staff role.", status_code=400)
        try:
            set_staff_role(email, role)
        except ValueError as error:
            return HTMLResponse(escape(str(error)), status_code=400)
        return RedirectResponse("/manager/team", status_code=303)
