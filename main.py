import secrets
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
from static_pages import render_contact_page, render_terms_page, render_faq_page
from storage import load_tables, add_table, update_players, delete_table, init_db
from views import render_public_page, render_admin_page

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
from support_chat import install_support_routes

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=session_secret(), https_only=True)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"


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
def contact_page():
    return render_contact_page()

@app.get("/faq", response_class=HTMLResponse)
def faq_page():
    return render_faq_page()

@app.get("/terms", response_class=HTMLResponse)
def terms_page():
    return render_terms_page()

@app.get("/login", response_class=HTMLResponse)
def login_page():
    from brand import render_brand_logo, render_site_theme, render_site_footer
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Staff sign in · TableRadar</title>{render_site_theme()}</head><body class="tr-auth-body"><header class="tr-site-header">{render_brand_logo('/')}</header><main class="tr-auth-wrap"><section class="tr-auth-panel"><h1>Staff sign in.</h1><p class="tr-muted">The owner login opens the manager workspace. Assigned table administrators and managers can sign in with their personal accounts.</p><form method="post" action="/login"><label for="staff-username">Username</label><input id="staff-username" name="username" autocomplete="username" required><label for="staff-password">Password</label><input id="staff-password" name="password" type="password" autocomplete="current-password" required><button class="tr-button" type="submit">Open manager workspace</button></form><a class="tr-auth-link" href="/signin_login">Sign in with a personal staff account</a></section></main>{render_site_footer()}</body></html>'''


@app.post("/login")
def login(request: Request, username: str = Form(""), password: str = Form("")):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session.clear()
        request.session["staff_role"] = "manager"
        response = RedirectResponse(url="/manager", status_code=303)
        response.delete_cookie("admin_auth")
        return response

    return HTMLResponse("""
    <html>
    <body style="background:#111;color:white;font-family:Arial;padding:20px;">
        <h1>❌ Wrong login or password</h1>
        <a href="/login" style="color:#4da3ff;">Try again</a>
    </body>
    </html>
    """)


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
    admin_html = render_admin_page(tables, manager=False, active_clubs=load_active_operator_clubs())

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
    club: str = Form(""),
    table_name: str = Form(""),
    union_name: str = Form(""),
    game: str = Form(""),
    blinds: str = Form(""),
    buyin: str = Form(""),
    players: str = Form(""),
    tags: str = Form(""),
    network: str = Form(""),
    affiliate_name: str = Form("Boom247 Official"),
    affiliate_telegram: str = Form(""),
    owner_name: str = Form(""),
    owner_telegram: str = Form("")
):
    check = require_login(request)
    if check:
        return check

    add_table(
        club,
        table_name,
        union_name,
        game,
        blinds,
        buyin,
        players,
        tags,
        network,
        affiliate_name,
        affiliate_telegram,
        owner_name,
        owner_telegram,
    )
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

    update_players(table_id, players)
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
def signup_page():
    return render_signup_page()


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
        return render_signup_page(error="Fill all fields")

    if password != confirm_password:
        return render_signup_page(error="Passwords do not match")

    ok = create_user(username, email, password)

    if not ok:
        return render_signup_page(error="User already exists")

    user = get_user_by_email(email)
    request.session.clear()
    request.session["user_email"] = user.get("email", "")
    request.session["credential_version"] = user.get("credential_version", "")
    request.session["username"] = user.get("username", "")
    request.session["plan"] = user.get("plan", "inactive")
    request.session["is_active"] = "1" if user.get("is_active", False) else "0"

    return RedirectResponse("/", status_code=303)

@app.get("/signin_login", response_class=HTMLResponse)
def signin_login_page(request: Request):
    html=render_signin_login_page()
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

    if plan_name not in ["player", "host"]:
        return RedirectResponse("/profile", status_code=303)

    return render_payment_page(user, plan_name)

@app.post("/signin_login", response_class=HTMLResponse)
def signin_login(
    request: Request,
    email: str = Form(""),
    password: str = Form("")
):
    email = email.strip().lower()
    user = authenticate_user(email, password)

    if not user:
        return render_signin_login_page(error="Wrong email or password.")

    request.session.clear()
    request.session["user_email"] = user.get("email", "")
    request.session["credential_version"] = user.get("credential_version", "")
    request.session["username"] = user.get("username", "")
    request.session["plan"] = user.get("plan", "inactive")
    request.session["is_active"] = "1" if user.get("is_active", False) else "0"

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
    return render_club_subscriptions_page(subscriptions, request.session.setdefault("account_csrf", secrets.token_urlsafe(32)))


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
        return HTMLResponse(render_club_subscriptions_page(load_club_subscriptions(), csrf, str(error)), status_code=400)

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
        return HTMLResponse(render_club_subscriptions_page(load_club_subscriptions(), csrf, str(error)), status_code=400)
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
        return HTMLResponse(render_club_subscriptions_page(load_club_subscriptions(), csrf, str(error)), status_code=400)
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
        return HTMLResponse(render_club_subscriptions_page(load_club_subscriptions(), csrf, str(error)), status_code=400)
    return RedirectResponse(url="/admin/club-subscriptions", status_code=303)


install_account_routes(app, get_current_user)
install_support_routes(app, get_current_user)


def require_manager(request: Request):
    if not is_manager(request):
        return HTMLResponse("Manager access required. Table administrators cannot view club requests or subscriptions.", status_code=403)
    return None


@app.get("/manager", response_class=HTMLResponse)
def manager_page(request: Request):
    check = require_manager(request)
    if check:
        return check
    return render_admin_page(load_tables(), manager=True, workspace="manager", active_clubs=load_active_operator_clubs(), pending_requests=pending_club_request_count())
