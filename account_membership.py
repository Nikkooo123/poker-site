"""Owner-only membership preview and private club application workflow."""
from datetime import datetime, timedelta, timezone
from html import escape
from currency_codes import normalize_currency, currency_options
import secrets
import re
from staff_access import is_manager
from host_lifecycle import awaiting_launch, has_host_access, launch_host, review_host_request, delete_club_request

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from auth.auth_storage import update_user, load_users, get_user_by_email
from brand import render_brand_logo, render_site_theme, render_site_footer


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
.tr-info-card{border:1px solid rgba(200,223,221,.12);border-radius:22px;padding:28px;margin:24px 0;background:linear-gradient(145deg,#202d32e8,#172126e8)}
.tr-status-changes{color:#edaaa5;background:#9e434326;border:1px solid #d98a8555;border-radius:8px;padding:4px 8px;display:inline-block}.tr-review-note{border-left:3px solid #d98a85;padding:10px 14px;background:#9e434310}.tr-info-card h2{font-size:22px;margin:0 0 14px}.tr-info-card p{color:#a5b4b6;line-height:1.6}.tr-info-card form{max-width:620px;margin-top:26px}.tr-info-card label{display:block;font-size:13px;color:#dbe6e4}.tr-info-card input,.tr-info-card select,.tr-info-card textarea{display:block;width:100%;box-sizing:border-box;padding:12px 14px;margin-top:8px;border-radius:11px;border:1px solid #a8d8c430;background:#101b21;color:#edf3f2;font:inherit;min-height:46px}.tr-info-card textarea{min-height:110px;resize:vertical}.tr-info-card input:focus-visible,.tr-info-card select:focus-visible,.tr-info-card textarea:focus-visible{outline:2px solid #a8d8c4;outline-offset:2px}@media(max-width:600px){.tr-info-card{padding:22px}}
.tr-host-club.tr-info-card{padding:18px 22px;margin:16px 0}.tr-host-club h2{font-size:19px;margin-bottom:8px}.tr-host-club p{margin:8px 0;font-size:13px}.tr-host-edit summary{cursor:pointer;color:#b9dfd0;font-size:13px;padding:8px 0}.tr-host-club form{margin-top:12px;max-width:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.tr-host-club form p{margin:0}.tr-host-club textarea{min-height:72px}.tr-host-progress.tr-info-card{padding:22px;margin:18px 0}.tr-host-progress>p{margin:9px 0}.tr-host-steps{list-style:none;padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:20px 0 0}.tr-host-steps li{border-top:2px solid #8cbba45c;padding-top:12px;font-size:13px}.tr-host-steps span{display:block;font-size:12px;color:#a5b4b6;margin-top:6px;line-height:1.5}.tr-host-notification{border:1px solid #a8d8c455;background:#a8d8c414;border-radius:12px;padding:14px;color:#c4e9d9}@media(max-width:680px){.tr-host-steps{grid-template-columns:repeat(2,minmax(0,1fr))}.tr-host-club form{grid-template-columns:1fr}.tr-host-progress.tr-info-card,.tr-host-club.tr-info-card{padding:18px}}
</style>"""


def page(title, body, user, manager=False):
    from auth.profile_view import render_account_menu
    header_account = '<a class="tr-button" href="/logout">Staff sign out</a>' if manager else render_account_menu(user)
    workspace_nav = '<nav style="display:flex;gap:10px;flex-wrap:wrap;margin:0 0 24px"><a class="tr-button" href="/manager">← Back to manager</a><a class="tr-button" href="/admin">Table administration</a><a class="tr-button" href="/admin/club-subscriptions">Club subscriptions</a></nav>' if manager else ""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} · TableRadar</title>{render_site_theme()}{ACCOUNT_CSS}</head><body style="margin:0"><header class="tr-site-header">{render_brand_logo('/')}{header_account}</header><main class="tr-site-main">{workspace_nav}<h1 class="tr-page-title">{escape(title)}</h1>{body}<p><a class="tr-button" href="/profile">← My account</a></p></main>{render_site_footer()}</body></html>'''


def install_account_routes(app, get_current_user):
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
            body=f'<p class="tr-page-intro">Sign in to your own existing customer account to test Host and Player. Your manager workspace stays available in this session.</p><section class="tr-info-card"><form method="post" action="/manager/membership-test/account"><input type="hidden" name="csrf" value="{csrf}"><p><label>Your account email<input name="email" type="email" autocomplete="username" required></label></p><p><label>Your account password<input name="password" type="password" autocomplete="current-password" required></label></p><button class="tr-button" type="submit">Use my account for testing</button></form></section>'
        else:
            forms=''.join(f'<form method="post" action="/account/test-membership"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="plan" value="{plan}"><button class="tr-button" type="submit">Try {plan.title()} free</button></form>' for plan in ('host','player'))
            body=f'<p class="tr-page-intro">Manager-only test tools for {escape(user["email"])}. No payment or automatic renewal.</p><section class="tr-info-card"><h2>Test the customer experience</h2><p>Host opens your dashboard so you can submit your own club request, approve it in Club requests and check the resulting subscription and monitoring lists. Player lets you check the player account.</p>{forms}<p>Only your current account changes. Staff permissions stay the same. Existing membership details are backed up when you first enter test mode.</p><a class="tr-button" href="/profile">My account</a></section>'
        return page('Manager membership test',body,user or {},manager=True)

    @app.post('/manager/membership-test/account')
    def bind_manager_test_account(request: Request, csrf: str = Form(''), email: str = Form(''), password: str = Form('')):
        token=request.session.get('account_csrf','')
        if not is_manager(request) or not token or not secrets.compare_digest(token,csrf):
            return HTMLResponse('Manager access required.',status_code=403)
        if get_current_user(request):
            return RedirectResponse('/manager/membership-test',status_code=303)
        # Only the already-authenticated owner manager session can lack a personal account.
        if request.session.get('staff_role') != 'manager':
            return HTMLResponse('Sign in with your personal manager account.',status_code=403)
        from auth.auth_storage import authenticate_user
        user=authenticate_user(email.strip().lower(),password)
        if not user:
            return HTMLResponse('Account email or password is incorrect. Return to the manager test page and try again.',status_code=400)
        request.session.clear()
        request.session.update(staff_role='manager',user_email=user['email'],username=user.get('username') or user['email'],credential_version=user.get('credential_version',''))
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
        if not user or plan not in ("reset", "player", "host"):
            return HTMLResponse("Membership preview is not available for this account.", status_code=403)
        # The manager explicitly chooses a free preview for their signed-in account only.
        now = datetime.now(timezone.utc)
        previous = {key: user.get(key) for key in ("plan", "role", "is_active", "days_left", "auto_renew", "plan_started_at", "plan_expires_at", "membership_source", "membership_expires_at", "manual_subscription_id", "host_service_state", "host_paid_days", "host_approved_submission")}
        fields = dict(membership_test_enabled=True, plan="inactive" if plan == "reset" else plan,
                      role="member" if plan == "reset" else plan, is_active=plan != "reset",
                      days_left=0 if plan == "reset" else 30, auto_renew=False,
                      test_expires_at="" if plan == "reset" else (now + timedelta(days=30)).isoformat(),
                      plan_started_at="" if plan == "reset" else now.strftime("%d/%m/%Y"),
                      plan_expires_at="" if plan == "reset" else (now + timedelta(days=30)).strftime("%d/%m/%Y"))
        if not user.get("membership_test_enabled"):
            fields["membership_before_test"] = previous
        update_user(user["email"], **fields)
        request.session["plan"] = fields["plan"]
        request.session["is_active"] = "1" if fields["is_active"] else "0"
        return RedirectResponse("/host" if plan == "host" else "/profile", status_code=303)

    @app.get("/host", response_class=HTMLResponse)
    def host_account(request: Request):
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/signin_login", status_code=303)
        user = account_context(request, user)
        if not has_host_access(user):
            return RedirectResponse("/profile", status_code=303)
        club = user.get("club_application") or {}
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
        if club.get('deleted_at'):
            stage = 'Request removed'
            next_step = 'Your previous request was removed from the review queue. You can update the details below and submit a new request. Any existing club placement keeps its current service dates.'
        timeline = ''.join(f'<li><strong>{title}</strong><span>{detail}</span></li>' for title,detail in (
            ('1. Host access confirmed', 'Your payment opens this private dashboard.' if preparing else 'Your Host access is available.'),
            ('2. Club review', 'Request received.' if club else 'Submit your club details.'),
            ('3. Preparation', 'Our team checks the details and prepares the placement.'),
            ('4. Placement starts', 'Approval activates your placement and starts the service countdown. Confirmation appears here.')))
        progress = f'<section class="tr-info-card tr-host-progress"><h2>{stage}</h2><p>{period}</p><p>{next_step}</p><ol class="tr-host-steps">{timeline}</ol></section>'
        notification = f'<p class="tr-host-notification" role="status">{safe(user.get("host_notification"))}</p>' if user.get('host_notification') else ''
        test_notice = '<p class="tr-muted">Private free test - no payment was taken. Test dates are separate from paid club placement.</p>' if user.get("membership_test_enabled") else ""
        body = f'''<p class="tr-page-intro">Your club, listing request and membership in one place.</p>{test_notice}{notification}{progress}<section class="tr-info-card tr-host-club"><h2>Your club</h2>{"<p><strong>"+safe(club.get("club_name"))+"</strong> · "+safe(club.get("application"))+(" · "+safe(club.get("currency")) if club.get("currency") else "")+" · Code: "+safe(club.get("club_code"))+"</p>" if club else ""}<p>Status: <strong class="{status_class}">{club_status}</strong></p>{review_note}<p>One club per Host account. Submitting details does not publish tables or join a poker club. The operator reviews the request and updates table information manually.</p><details class="tr-host-edit" {"" if club else "open"}><summary>{"Edit club details" if club else "Submit club details"}</summary><form method="post" action="/host/club"><input type="hidden" name="csrf" value="{csrf}"><p><label>Your name or screen name *<br><input name="owner_name" required maxlength="100" autocomplete="nickname" value="{safe(club.get('owner_name'))}"></label></p><p><label>Telegram *<br><input name="telegram" required maxlength="80" placeholder="@yourname" value="{safe(club.get('telegram'))}"></label></p><p><label>Club name *<br><input name="club_name" required maxlength="120" value="{safe(club.get('club_name'))}"></label></p><p><label>Application<br><select name="application">{''.join(f'<option{chr(32)+"selected" if club.get("application")==name else ""}>{name}</option>' for name in ('ClubGG','X Poker','PPPoker','Other'))}</select></label></p><p><label>Game currency *<br><select name="currency" required>{currency_options(club.get("currency"))}</select></label></p><p><label>Club ID *<br><input name="club_code" required maxlength="80" value="{safe(club.get('club_code'))}"></label></p><p><label>Notes for the operator<br><textarea name="notes" maxlength="1000">{safe(club.get('notes'))}</textarea></label></p><button class="tr-button" type="submit">{'Update club request' if club else 'Submit club for review'}</button><p class="tr-muted">* Required fields</p></form></details></section>'''
        return page("Host dashboard", body, user)

    @app.post("/host/club")
    def submit_club(request: Request, csrf: str = Form(""), club_name: str = Form(""), application: str = Form(""), club_code: str = Form(""), notes: str = Form(""), owner_name: str = Form(""), telegram: str = Form(""), currency: str = Form("")):
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
        try:
            currency = normalize_currency(currency)
        except ValueError as error:
            return HTMLResponse(escape(str(error)), status_code=400)
        update_user(user["email"], club_application=dict(currency=currency, owner_name=owner_name.strip(), telegram=telegram, club_name=club_name.strip(), application=application, club_code=club_code.strip(), notes=notes.strip(), status="pending", submitted_at=datetime.now(timezone.utc).isoformat()))
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
                cards.append(f'<section class="tr-info-card tr-club-request"><h2>{safe(club.get("club_name"))}</h2><p>{safe(club.get("owner_name") or "Owner name not provided")} · {safe(club.get("telegram") or "Telegram not provided")}</p><p>{safe(user.get("email"))} · {safe(club.get("application"))}{(" · "+safe(club.get("currency"))) if club.get("currency") else ""} · Club code: {safe(club.get("club_code"))}</p><p>{safe(club.get("status", "pending"))} · Host access: {"paid - awaiting launch" if awaiting_launch(state) else "active" if state.get("is_active") and state.get("plan")=="host" else "inactive"}</p><details class="tr-request-review"><summary>Review request</summary><p>{safe(club.get("notes"))}</p><form method="post" action="/admin/club-requests/review"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="email" value="{safe(user.get("email"))}"><input type="hidden" name="submitted_at" value="{safe(club.get("submitted_at"))}"><p><label>Review status<select name="status">{review_options}</select></label></p><p><label>Note to the owner<textarea name="review_note" maxlength="1000">{safe(club.get("review_note"))}</textarea></label></p><button class="tr-button" type="submit">Save review</button> <button class="tr-button" type="submit" formaction="/admin/club-requests/approve">Approve listing request</button><p class="tr-muted" style="grid-column:1/-1">Approving starts the service period, activates Club subscriptions and adds the club to Clubs to monitor. Approve only when the placement is ready.</p></form>{launch}</details></section>')
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

    @app.get("/manager/team", response_class=HTMLResponse)
    def team_page(request: Request):
        if not is_manager(request):
            return HTMLResponse("Manager access required.", status_code=403)
        safe = lambda value: escape(str(value or ""), quote=True)
        csrf = safe(request.session.setdefault("account_csrf", secrets.token_urlsafe(32)))
        cards = []
        for user in load_users():
            role = user.get("staff_role", "")
            options = ''.join(f'<option value="{value}"{" selected" if role == value else ""}>{label}</option>' for value, label in (("", "Customer only — no staff access"), ("table_admin", "Table administrator — tables only"), ("manager", "Manager — tables, requests and subscriptions")))
            cards.append(f'<section class="tr-info-card tr-team-member"><div class="tr-team-identity"><h2>{safe(user.get("username") or user.get("email"))}</h2><p>{safe(user.get("email"))}</p></div><form method="post" action="/manager/team"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="email" value="{safe(user.get("email"))}"><label>Staff access<select name="role">{options}</select></label><button class="tr-button" type="submit">Save access</button></form></section>')
        return page("Staff access", '<p class="tr-page-intro">Assign staff access only to trusted operators with existing accounts. Table administrators use the Tables screen; managers can also review clubs and subscriptions.</p>' + ''.join(cards), get_current_user(request) or {}, manager=True)

    @app.post("/manager/team")
    def update_staff(request: Request, csrf: str = Form(""), email: str = Form(""), role: str = Form("")):
        token = request.session.get("account_csrf", "")
        if not is_manager(request) or not token or not secrets.compare_digest(token, csrf):
            return HTMLResponse("Manager access required.", status_code=403)
        if role not in ("", "table_admin", "manager") or not get_user_by_email(email):
            return HTMLResponse("Invalid account or staff role.", status_code=400)
        update_user(email, staff_role=role)
        return RedirectResponse("/manager/team", status_code=303)
