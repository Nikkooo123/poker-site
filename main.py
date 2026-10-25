import secrets
import re
from html import escape
from club_subscriptions_storage import (
    load_club_subscriptions,
    load_active_operator_clubs,
    add_club_subscription,
    extend_club_subscription,
    disable_club_subscription,
    delete_club_subscription,
)
from club_subscriptions_view import render_club_subscriptions_page
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from static_pages import render_contact_page, render_terms_page, render_faq_page, render_about_page, render_privacy_page
from operator_tables import add_operator_table
from storage import load_tables, add_table, update_players, delete_table, init_db
from views import render_public_page, render_admin_page, minimum_buyin

from auth.auth_storage import create_user, authenticate_user, get_user_by_email, set_user_plan
from auth.auth_views import (
    render_signin_page,
    render_signup_page,
    render_signin_login_page,
    render_dashboard_page,
)
from auth.profile_view import render_profile_page, render_payment_page
from account_membership import membership_state, account_context, install_account_routes, pending_club_request_count
from staff_access import session_secret, staff_role, is_manager, can_edit_tables
from directory_preferences import install_preference_routes
from social_auth import install_social_routes
from account_verification import install_verification_routes
from payment_choices import membership_payment_page, install_payment_choice_routes
import player_access
import verification_delivery
from support_chat import install_support_routes
from crypto_checkout import checkout_page, install_crypto_routes

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=session_secret(), https_only=True)

@app.get('/assets/poker-lounge-v3.webp', include_in_schema=False)
def poker_lounge_illustration():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).with_name('poker-lounge-v3.webp'), media_type='image/webp',
        headers={'Cache-Control':'public, max-age=31536000, immutable'})

@app.get('/assets/poker-mascots-v7.webp', include_in_schema=False)
def poker_mascot_background():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).with_name('poker-mascots-v7.webp'), media_type='image/webp',
        headers={'Cache-Control':'public, max-age=31536000, immutable'})

@app.get('/assets/poker-mascots-v10.webp', include_in_schema=False)
def poker_mascot_background_v10():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).with_name('poker-mascots-v10.webp'), media_type='image/webp',
        headers={'Cache-Control':'public, max-age=31536000, immutable'})

@app.get('/assets/poker-mascots-v11.webp', include_in_schema=False)
def poker_mascot_background_v11():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).with_name('poker-mascots-v11.webp'), media_type='image/webp',
        headers={'Cache-Control':'public, max-age=31536000, immutable'})

@app.get('/assets/poker-mascots-v17.webp', include_in_schema=False)
def poker_mascot_background_v17():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).with_name('poker-mascots-v17.webp'), media_type='image/webp',
        headers={'Cache-Control':'public, max-age=31536000, immutable'})

@app.get('/assets/poker-mascots-v19.webp', include_in_schema=False)
def poker_mascot_background_v19():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).with_name('poker-mascots-v19.webp'), media_type='image/webp',
        headers={'Cache-Control':'public, max-age=31536000, immutable'})

@app.middleware('http')
async def browser_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault('X-Content-Type-Options','nosniff')
    # The authenticated compact inbox is embedded by our own Live Chat widget.
    embedded_chat = (request.url.path == '/staff/chat'
                     and request.query_params.get('compact','').lower() in ('1','true','on','yes')
                     and response.status_code == 200
                     and 'text/html' in response.headers.get('content-type',''))
    response.headers.setdefault('X-Frame-Options','SAMEORIGIN' if embedded_chat else 'DENY')
    ancestors = "'self'" if embedded_chat else "'none'"
    response.headers.setdefault('Content-Security-Policy',f"frame-ancestors {ancestors}; object-src 'none'; base-uri 'self'")
    response.headers.setdefault('Referrer-Policy','strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy','camera=(), microphone=(), geolocation=()')
    # Pages contain live club information and may contain personal account data.
    if 'text/html' in response.headers.get('content-type',''):
        response.headers.setdefault('Cache-Control','no-store')
    return response




@app.on_event("startup")
def startup():
    init_db()


def is_logged_in(request: Request) -> bool:
    return can_edit_tables(request)


def require_login(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


@app.get("/", response_class=HTMLResponse)
def public_site(request: Request):
    tables = load_tables()
    return render_public_page(tables, request, user=get_current_user(request))

@app.get("/contact", response_class=HTMLResponse)
def contact_page(request: Request):
    return render_contact_page(get_current_user(request))

@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return render_about_page(get_current_user(request))

@app.get("/faq", response_class=HTMLResponse)
def faq_page(request: Request):
    return render_faq_page(get_current_user(request))

@app.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return render_privacy_page(get_current_user(request))

@app.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    return render_terms_page(get_current_user(request))

@app.get("/login")
def login_page():
    return RedirectResponse('/signin_login', status_code=303)


@app.post("/login")
def login(request: Request, username: str = Form(""), password: str = Form("")):
    # Reject the retired shared login, including old bookmarked forms.
    request.session.pop('staff_role', None)
    from auth.auth_views import auth_shell
    response = HTMLResponse(auth_shell('<h1>Personal staff sign-in</h1><p class="tr-muted">Shared staff sign-in has been retired. Use your personal account with assigned staff access.</p><a class="tr-button" href="/signin_login">Sign in to your account</a>', 'Staff sign-in'), status_code=403, headers={'Cache-Control':'no-store'})
    response.delete_cookie('admin_auth')
    return response


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("admin_auth")
    return response


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    check = require_login(request)
    if check:
        return check

    tables = load_tables()
    admin_html = render_admin_page(tables, manager=False, active_clubs=load_active_operator_clubs(), csrf=request.session.setdefault("account_csrf", secrets.token_urlsafe(32)), user=get_current_user(request))

    logout_link = """
    <div style="margin-bottom:20px;">
        <a href="/logout" style="
            display:inline-block;
            background:#b71c1c;
            color:white;
            text-decoration:none;
            padding:8px 12px;
            border-radius:8px;
        ">Log out</a>
    </div>
    """

    return admin_html.replace(
        '<div style="margin-bottom:20px;color:#bbb;">Admin page</div>',
        '<div style="margin-bottom:20px;color:#bbb;">Admin page</div>' + logout_link
    )


@app.post("/add")
def add_table_route(
    request: Request,
    subscription_id: str = Form(""),
    table_name: str = Form(""), union_name: str = Form(""),
    game: str = Form(""), blinds: str = Form(""), buyin: str = Form(""),
    players: str = Form(""), tags: str = Form(""), csrf: str = Form(""),
):
    check = require_login(request)
    if check:
        return check
    if not valid_subscription_csrf(request, csrf):
        return HTMLResponse("Refresh the page and try again.", status_code=403)
    try:
        add_operator_table(subscription_id, table_name=table_name, union_name=union_name,
                           game=game, blinds=blinds, buyin=minimum_buyin(buyin), players=players, tags=tags)
    except ValueError as error:
        manager = is_manager(request)
        return HTMLResponse(render_admin_page(load_tables(), manager=manager,
            workspace="manager" if manager else "tables", active_clubs=load_active_operator_clubs(),
            pending_requests=pending_club_request_count() if manager else 0,
            csrf=csrf, error=str(error), form_data=dict(subscription_id=subscription_id,table_name=table_name,union_name=union_name,game=game,blinds=blinds,buyin=buyin,players=players,tags=tags), user=get_current_user(request)), status_code=400)
    return RedirectResponse(url="/manager" if is_manager(request) else "/admin", status_code=303)


@app.post("/update_players")
def update_players_route(
    request: Request,
    table_id: int = Form(...),
    players: str = Form("")
):
    check = require_login(request)
    if check:
        return check

    try:
        update_players(table_id, players)
    except ValueError as error:
        return HTMLResponse(escape(str(error)), status_code=400)
    return RedirectResponse(url="/manager" if is_manager(request) else "/admin", status_code=303)


@app.post("/delete")
def delete_table_route(
    request: Request,
    table_id: int = Form(...)
):
    check = require_login(request)
    if check:
        return check

    delete_table(table_id)
    return RedirectResponse(url="/manager" if is_manager(request) else "/admin", status_code=303)

def get_current_user(request: Request):
    email = request.session.get("user_email")
    username = request.session.get("username")

    if not email or not username:
        return None

    user = get_user_by_email(email)
    if user and request.session.get('credential_version','') == user.get('credential_version',''):
        return membership_state(user)

    return None


def require_user(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/signin_login", status_code=303)
    return None

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return render_signup_page(user=get_current_user(request))


@app.post("/signup", response_class=HTMLResponse)
def signup(
    request: Request,
    username: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form("")
):
    username = username.strip()
    email = email.strip().lower()

    if not username or not email or not password or not confirm_password:
        return render_signup_page(error="Fill all fields", user=get_current_user(request))

    if len(email)>254 or not re.fullmatch(r"[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+", email):
        return render_signup_page(error="Enter a valid email address.", user=get_current_user(request))
    if not 8 <= len(password) <= 256:
        return render_signup_page(error="Use a password with at least 8 characters (maximum 256).", user=get_current_user(request))

    if password != confirm_password:
        return render_signup_page(error="Passwords do not match", user=get_current_user(request))

    if player_access.enabled() and not verification_delivery.email_ready():
        return HTMLResponse(render_signup_page(error="Account verification is not configured yet. Please contact support.", user=get_current_user(request)), status_code=503)
    ok = create_user(username, email, password)

    if not ok:
        return render_signup_page(error="User already exists", user=get_current_user(request))

    user = get_user_by_email(email)
    request.session.clear()
    request.session["user_email"] = user.get("email", "")
    request.session["credential_version"] = user.get("credential_version", "")
    request.session["username"] = user.get("username", "")
    request.session["plan"] = user.get("plan", "inactive")
    request.session["is_active"] = "1" if user.get("is_active", False) else "0"

    return RedirectResponse("/verify-account" if player_access.enabled() else "/", status_code=303)

@app.get("/signin_login", response_class=HTMLResponse)
def signin_login_page(request: Request):
    html=render_signin_login_page(user=get_current_user(request))
    if request.query_params.get('password_changed') == '1':
        html=html.replace('<form method="post" action="/signin_login">','<p role="status" style="color:#b7dfc9">Password changed. Sign in with your new password.</p><form method="post" action="/signin_login">')
    return html

@app.post("/activate_plan")
def activate_plan(
    request: Request,
    plan: str = Form("")
):
    check = require_user(request)
    if check:
        return check

    email = request.session.get("user_email")
    if plan not in ["player", "host"]:
        return RedirectResponse("/profile", status_code=303)

    # Paid activation requires a verified payment; owner preview has its own protected route.
    return HTMLResponse("Payments are not enabled. Use your account preview controls if available.", status_code=403)


@app.get("/pay/{plan_name}", response_class=HTMLResponse)
def pay_page(plan_name: str, request: Request):
    check = require_user(request)
    if check:
        return check

    user = get_current_user(request)

    if plan_name not in ["player", "host", "host_starter", "host_pro"]:
        return RedirectResponse("/profile", status_code=303)

    return membership_payment_page(request, user, plan_name)

@app.post("/signin_login", response_class=HTMLResponse)
def signin_login(
    request: Request,
    email: str = Form(""),
    password: str = Form("")
):
    email = email.strip().lower()
    user = authenticate_user(email, password)

    if not user:
        return render_signin_login_page(error="Wrong email or password.", user=get_current_user(request))

    request.session.clear()
    request.session["user_email"] = user.get("email", "")
    request.session["credential_version"] = user.get("credential_version", "")
    request.session["username"] = user.get("username", "")
    request.session["plan"] = user.get("plan", "inactive")
    request.session["is_active"] = "1" if user.get("is_active", False) else "0"

    from staff_access import record_customer_login
    record_customer_login(user["email"])

    destination = "/manager" if is_manager(request) else ("/admin" if can_edit_tables(request) else "/")
    return RedirectResponse(url=destination, status_code=303)


@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    check = require_user(request)
    if check:
        return check

    user = get_current_user(request)
    return render_profile_page(account_context(request, user))


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

def valid_subscription_csrf(request, csrf):
    token = request.session.get("account_csrf", "")
    return bool(token and secrets.compare_digest(token, csrf))


@app.get("/admin/club-subscriptions", response_class=HTMLResponse)
def admin_club_subscriptions_page(request: Request):
    check = require_manager(request)
    if check:
        return check

    subscriptions = load_club_subscriptions()
    return render_club_subscriptions_page(subscriptions, request.session.setdefault("account_csrf", secrets.token_urlsafe(32)), user=get_current_user(request))


@app.post("/admin/club-subscriptions/add")
def admin_add_club_subscription(
    request: Request,
    club_name: str = Form(""),
    owner_name: str = Form(""),
    owner_telegram: str = Form(""),
    owner_email: str = Form(""),
    application: str = Form(""),
    plan: str = Form("host"),
    duration_days: int = Form(30),
    notes: str = Form(""),
    csrf: str = Form(""),
):
    check = require_manager(request)
    if check:
        return check

    if not valid_subscription_csrf(request, csrf):
        return HTMLResponse("Refresh the page and try again.", status_code=403)
    try:
        add_club_subscription(
            club_name=club_name,
            owner_name=owner_name,
            owner_telegram=owner_telegram,
            owner_email=owner_email,
            application=application,
            plan=plan,
            duration_days=duration_days,
            notes=notes,
        )
    except ValueError as error:
        return HTMLResponse(render_club_subscriptions_page(load_club_subscriptions(), csrf, str(error), user=get_current_user(request)), status_code=400)

    return RedirectResponse(url="/admin/club-subscriptions", status_code=303)


@app.post("/admin/club-subscriptions/{subscription_id}/extend")
def admin_extend_club_subscription(
    request: Request,
    subscription_id: int,
    days: int = Form(30),
    csrf: str = Form(""),
):
    check = require_manager(request)
    if check:
        return check

    if not valid_subscription_csrf(request, csrf):
        return HTMLResponse("Refresh the page and try again.", status_code=403)
    try:
        extend_club_subscription(subscription_id, days)
    except ValueError as error:
        return HTMLResponse(render_club_subscriptions_page(load_club_subscriptions(), csrf, str(error), user=get_current_user(request)), status_code=400)
    return RedirectResponse(url="/admin/club-subscriptions", status_code=303)


@app.post("/admin/club-subscriptions/{subscription_id}/disable")
def admin_disable_club_subscription(request: Request, subscription_id: int, csrf: str = Form("")):
    check = require_manager(request)
    if check:
        return check

    if not valid_subscription_csrf(request, csrf):
        return HTMLResponse("Refresh the page and try again.", status_code=403)
    try:
        disable_club_subscription(subscription_id)
    except ValueError as error:
        return HTMLResponse(render_club_subscriptions_page(load_club_subscriptions(), csrf, str(error), user=get_current_user(request)), status_code=400)
    return RedirectResponse(url="/admin/club-subscriptions", status_code=303)


@app.post("/admin/club-subscriptions/{subscription_id}/delete")
def admin_delete_club_subscription(request: Request, subscription_id: int, csrf: str = Form("")):
    check = require_manager(request)
    if check:
        return check

    if not valid_subscription_csrf(request, csrf):
        return HTMLResponse("Refresh the page and try again.", status_code=403)
    try:
        delete_club_subscription(subscription_id)
    except ValueError as error:
        return HTMLResponse(render_club_subscriptions_page(load_club_subscriptions(), csrf, str(error), user=get_current_user(request)), status_code=400)
    return RedirectResponse(url="/admin/club-subscriptions", status_code=303)


install_account_routes(app, get_current_user)
install_preference_routes(app, get_current_user)
install_social_routes(app, get_current_user)
install_verification_routes(app, get_current_user)
install_payment_choice_routes(app, get_current_user)
install_support_routes(app, get_current_user)
install_crypto_routes(app, get_current_user)


def require_manager(request: Request):
    if not is_manager(request):
        return HTMLResponse("Manager access required. Table administrators cannot view club requests or subscriptions.", status_code=403)
    return None


@app.get("/manager", response_class=HTMLResponse)
def manager_page(request: Request):
    check = require_manager(request)
    if check:
        return check
    return render_admin_page(load_tables(), manager=True, workspace="manager", active_clubs=load_active_operator_clubs(), pending_requests=pending_club_request_count(), csrf=request.session.setdefault("account_csrf", secrets.token_urlsafe(32)), user=get_current_user(request))
