from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from storage import load_tables, save_tables
from views import render_public_page, render_admin_page

app = FastAPI()

tables = load_tables()

if tables:
    next_id = max(table["id"] for table in tables) + 1
else:
    next_id = 1

ADMIN_USERNAME = "admin1234"
ADMIN_PASSWORD = "12341234"


def is_logged_in(request: Request) -> bool:
    return request.cookies.get("admin_auth") == "yes"


def require_login(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


@app.get("/", response_class=HTMLResponse)
def public_site():
    return render_public_page(tables)


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
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("admin_auth")
    return response


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    check = require_login(request)
    if check:
        return check

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
def add_table(
    request: Request,
    club: str = Form(""),
    game: str = Form(""),
    blinds: str = Form(""),
    buyin: str = Form(""),
    players: str = Form(""),
    tags: str = Form("")
):
    check = require_login(request)
    if check:
        return check

    global next_id

    tables.append({
        "id": next_id,
        "club": club,
        "game": game,
        "blinds": blinds,
        "buyin": buyin,
        "players": players,
        "tags": tags
    })

    next_id += 1
    save_tables(tables)
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/update_players")
def update_players(
    request: Request,
    table_id: int = Form(...),
    players: str = Form("")
):
    check = require_login(request)
    if check:
        return check

    for table in tables:
        if table["id"] == table_id:
            table["players"] = players
            break

    save_tables(tables)
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/delete")
def delete_table(
    request: Request,
    table_id: int = Form(...)
):
    check = require_login(request)
    if check:
        return check

    global tables
    tables = [table for table in tables if table["id"] != table_id]
    save_tables(tables)

    return RedirectResponse(url="/admin", status_code=303)