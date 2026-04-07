from auth.profile_view import render_profile_page
from html import escape


def auth_shell(content: str, title: str = "Auth") -> str:
    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>{escape(title)}</title>
    </head>
    <body style="
        margin:0;
        min-height:100vh;
        background:linear-gradient(180deg,#1c2328,#101316);
        color:#fff;
        font-family:Arial,sans-serif;">
        {content}
    </body>
    </html>
    """


def back_home_logo() -> str:
    return """
    <a href="/" style="
        position:absolute;
        top:20px;
        left:22px;
        text-decoration:none;
        font-size:46px;
        line-height:1;
        display:inline-block;">
        🔥
    </a>
    """


def input_block(label: str, name: str, input_type: str = "text", required: bool = True) -> str:
    req = "required" if required else ""
    return f"""
    <div style="font:700 16px Arial;margin-bottom:8px;color:#f3e7b1;">{escape(label)}</div>
    <input name="{escape(name)}" type="{escape(input_type)}" {req} style="
        width:100%;
        box-sizing:border-box;
        height:52px;
        border:none;
        border-radius:10px;
        background:#f5f5f5;
        color:#111;
        padding:0 14px;
        font-size:15px;
        margin-bottom:18px;">
    """


def message_block(error: str = "", success: str = "") -> str:
    if error:
        return f"""
        <div style="
            color:#ff6b6b;
            font-size:14px;
            margin-bottom:18px;">
            {escape(error)}
        </div>
        """
    if success:
        return f"""
        <div style="
            color:#7dff5a;
            font-size:14px;
            margin-bottom:18px;">
            {escape(success)}
        </div>
        """
    return ""


def render_signin_page(error: str = "") -> str:
    content = f"""
    {back_home_logo()}

    <div style="
        display:flex;
        justify-content:center;
        align-items:flex-start;
        min-height:100vh;
        padding-top:110px;
        box-sizing:border-box;">

        <div style="width:430px;max-width:92vw;">
            <div style="
                font:800 42px Arial;
                color:#fff;
                margin-bottom:24px;
                text-align:center;">
                Create your account
            </div>

            {message_block(error=error)}

            <form method="post" action="/signup">
                {input_block("Username", "username")}
                {input_block("Email", "email", "email")}
                {input_block("Password", "password", "password")}
                {input_block("Confirm password", "confirm_password", "password")}

                <button type="submit" style="
                    width:100%;
                    height:56px;
                    border:2px solid #7dff5a;
                    border-radius:4px;
                    background:transparent;
                    color:#7dff5a;
                    font:800 19px Arial;
                    cursor:pointer;">
                    Get Started
                </button>
            </form>

            <div style="text-align:center;margin-top:16px;font-size:14px;">
                <a href="/signin_login" style="color:#ffb347;text-decoration:none;">Already have account?</a>
            </div>
        </div>
    </div>
    """
    return auth_shell(content, "Create your account")


def render_signup_page(error: str = "", success: str = "") -> str:
    return render_signin_page(error)


def render_signin_login_page(error: str = "") -> str:
    content = f"""
    {back_home_logo()}

    <div style="
        display:flex;
        justify-content:center;
        align-items:flex-start;
        min-height:100vh;
        padding-top:110px;
        box-sizing:border-box;">

        <div style="width:420px;max-width:92vw;">

            <div style="
                display:flex;
                justify-content:flex-end;
                margin-bottom:16px;">
                <a href="/signup" style="
                    color:#f3e7b1;
                    text-decoration:none;
                    font:700 16px Arial;">
                    Create an Account
                </a>
            </div>

            <div style="
                font:800 38px Arial;
                color:#fff;
                margin-bottom:24px;">
                Sign In
            </div>

            {message_block(error=error)}

            <form method="post" action="/signin_login">
                {input_block("Email Address", "email", "email")}
                {input_block("Password", "password", "password")}

                <button type="submit" style="
                    width:100%;
                    height:60px;
                    border:none;
                    border-radius:10px;
                    background:#ff2a2a;
                    color:#fff;
                    font:800 20px Arial;
                    cursor:pointer;
                    margin-bottom:18px;">
                    Log In
                </button>
            </form>
        </div>
    </div>
    """
    return auth_shell(content, "Sign In")


def render_dashboard_page(username: str, email: str) -> str:
    content = f"""
    {back_home_logo()}
    <div style="
        max-width:820px;
        margin:120px auto 0 auto;
        background:rgba(255,255,255,.04);
        border-radius:20px;
        padding:34px;
        box-sizing:border-box;">
        <div style="font:800 42px Arial;color:#fff;margin-bottom:18px;">Welcome</div>
        <div style="font:700 22px Arial;color:#ffb347;margin-bottom:12px;">{escape(username)}</div>
        <div style="font-size:18px;color:#d6d6d6;">Logged in as: <b>{escape(email)}</b></div>
    </div>
    """
    return auth_shell(content, "Dashboard")

