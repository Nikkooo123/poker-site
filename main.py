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

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="change_this_secret_key_123456789")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"


@app.on_event("startup")
def startup():
    init_db()


def is_logged_in(request: Request) -> bool:
    return request.cookies.get("admin_auth") == "yes"


def require_login(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


@app.get("/", response_class=HTMLResponse)
def public_site(request: Request):
    tables = load_tables()
    return render_public_page(tables, request)

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
    return """
    <html>
    <head>
        <title>Admin Login</title>
    </head>
    <body style="background:#111;color:white;font-family:Arial;padding:20px;">
        <h1>🔐 Admin Login</h1>

        <form method="post" action="/login" style="
            background:#222;
            padding:15px;
            border-radius:10px;
            max-width:320px;
        ">
            <input name="username" placeholder="Username" style="width:100%;margin-bottom:8px;padding:8px;">
            <input name="password" type="password" placeholder="Password" style="width:100%;margin-bottom:8px;padding:8px;">
            <button type="submit" style="padding:10px 14px;">Log in</button>
        </form>
    </body>
    </html>
    """


@app.post("/login")
def login(username: str = Form(""), password: str = Form("")):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie("admin_auth", "yes", httponly=True)
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
    admin_html = render_admin_page(tables)

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
    return RedirectResponse(url="/admin", status_code=303)


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
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/delete")
def delete_table_route(
    request: Request,
    table_id: int = Form(...)
):
    check = require_login(request)
    if check:
        return check

    delete_table(table_id)
    return RedirectResponse(url="/admin", status_code=303)

def get_current_user(request: Request):
    email = request.session.get("user_email")
    username = request.session.get("username")

    if not email or not username:
        return None

    user = get_user_by_email(email)
    if user:
        return user

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
    request.session["user_email"] = user.get("email", "")
    request.session["username"] = user.get("username", "")
    request.session["plan"] = user.get("plan", "inactive")
    request.session["is_active"] = "1" if user.get("is_active", False) else "0"

    return RedirectResponse("/", status_code=303)

@app.get("/signin_login", response_class=HTMLResponse)
def signin_login_page():
    return render_signin_login_page()

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

    set_user_plan(email, plan)
    user = get_user_by_email(email)

    request.session["plan"] = user.get("plan", "inactive")
    request.session["is_active"] = "1" if user.get("is_active", False) else "0"

    return RedirectResponse("/profile", status_code=303)

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

    request.session["user_email"] = user.get("email", "")
    request.session["username"] = user.get("username", "")
    request.session["plan"] = user.get("plan", "inactive")
    request.session["is_active"] = "1" if user.get("is_active", False) else "0"

    return RedirectResponse(url="/", status_code=303)


@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    check = require_user(request)
    if check:
        return check

    user = get_current_user(request)
    return render_profile_page(user)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
