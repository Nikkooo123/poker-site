from html import escape
from social_auth_config import render_social_signin
from brand import render_brand_logo, render_site_theme, render_site_footer


def auth_shell(content: str, title: str = "Auth") -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{escape(title)} · TableRadar</title>{render_site_theme()}</head><body style="margin:0">
    <header class="tr-site-header">{render_brand_logo('/')}<a class="tr-button" href="/">← Back to tables</a></header>
    <main class="tr-auth-body"><div class="tr-auth-wrap"><div class="tr-auth-panel">{content}</div></div></main>{render_site_footer()}</body></html>"""


def back_home_logo() -> str:
    return render_brand_logo('/')


def input_block(label: str, name: str, input_type: str = "text", required: bool = True, autocomplete: str = "") -> str:
    req = "required" if required else ""
    complete = f'autocomplete="{escape(autocomplete)}"' if autocomplete else ''
    limits = 'minlength="8" maxlength="256"' if input_type == 'password' and autocomplete == 'new-password' else ''
    return f'<label for="auth-{escape(name)}">{escape(label)}</label><input id="auth-{escape(name)}" name="{escape(name)}" type="{escape(input_type)}" {req} {complete} {limits}>'


def message_block(error: str = "", success: str = "") -> str:
    if error:
        return f'<p role="alert" style="color:#f4a7a7">{escape(error)}</p>'
    if success:
        return f'<p role="status" style="color:#a8d8c4">{escape(success)}</p>'
    return ''


def render_signin_page(error: str = "") -> str:
    import player_access
    import verification_delivery
    if player_access.enabled() and not verification_delivery.ready():
        content = '<h1>Create your TableRadar account.</h1>' + message_block(error=error) + '<p class="tr-muted">Use Google or Discord with a verified email address. Email and password registration will be available after email verification is configured.</p>' + render_social_signin() + '<p class="tr-muted">Registration does not unlock table information. Player access requires an active membership or a verified 14-day trial. Phone verification and new trials are not available yet. Host has no free trial.</p><a class="tr-auth-link" href="/signin_login">Already a member? Sign in</a>'
        return auth_shell(content, 'Create account')
    content = f"""<h1>Your next table starts here.</h1><p class="tr-muted">Create your TableRadar account.</p>{message_block(error=error)}{render_social_signin()}
    <form method="post" action="/signup">{input_block('Username','username',autocomplete='username')}{input_block('Email','email','email',autocomplete='email')}{input_block('Password (at least 8 characters)','password','password',autocomplete='new-password')}{input_block('Confirm password','confirm_password','password',autocomplete='new-password')}
    <button class="tr-button tr-button-primary" type="submit">Create account →</button></form><a class="tr-auth-link" href="/signin_login">Already a member? Sign in</a>"""
    return auth_shell(content, 'Create account')


def render_signup_page(error: str = "", success: str = "") -> str:
    return render_signin_page(error) if not success else auth_shell(message_block(success=success) + '<a class="tr-button" href="/signin_login">Sign in</a>', 'Account created')


def render_signin_login_page(error: str = "") -> str:
    content = f"""<h1>Welcome back.</h1><p class="tr-muted">Sign in to your TableRadar account.</p>{message_block(error=error)}{render_social_signin()}
    <form method="post" action="/signin_login">{input_block('Email address','email','email',autocomplete='email')}{input_block('Password','password','password',autocomplete='current-password')}<button class="tr-button tr-button-primary" type="submit">Sign in →</button></form><a class="tr-auth-link" href="/signup">New to TableRadar? Create an account</a>"""
    return auth_shell(content, 'Sign in')


def render_dashboard_page(username: str, email: str) -> str:
    return auth_shell(f'<h1>Welcome, {escape(username)}</h1><p class="tr-muted">{escape(email)}</p><a class="tr-button" href="/profile">Open your profile</a>', 'Dashboard')
