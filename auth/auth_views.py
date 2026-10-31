from html import escape
from social_auth_config import render_social_signin
from brand import render_brand_logo, render_site_theme, render_site_footer


def auth_shell(content: str, title: str = "Auth", user=None) -> str:
    from auth.profile_view import render_account_menu
    account = render_account_menu(user) if user else '<a class="tr-button" href="/">← Back to tables</a>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{escape(title)} · TableRadar</title>{render_site_theme()}</head><body style="margin:0">
    <header class="tr-site-header">{render_brand_logo('/')}{account}</header>
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


def render_signin_page(error: str = "", user=None) -> str:
    import player_access
    import verification_delivery
    preview = player_access.friends_preview_enabled()
    email_pending = player_access.enabled() and not preview and not verification_delivery.email_ready()
    availability = '<p role="status" class="tr-muted">Email registration requires an email confirmation code. Email delivery is being configured; this form will become available when it is ready. You can use Google or Discord now.</p>' if email_pending else '<p class="tr-muted">Create your account, then confirm your email with a six-digit code before accessing membership features.</p>'
    disabled = ' disabled' if email_pending else ''
    if preview:
        availability = '<p class="tr-muted">Create an account with your email and password. Email confirmation is not required during the friends preview.</p>'
    access_note = 'Email confirmation is not required during the friends preview.' if preview else 'Registration alone does not unlock tables. Email confirmation is required; SMS verification will be added later.'
    content = f"""<h1>Your next table starts here.</h1>{availability}{message_block(error=error)}{render_social_signin()}
    <form method="post" action="/signup"><fieldset{disabled} style="border:0;padding:0;margin:0">{input_block('Username','username',autocomplete='username')}{input_block('Email','email','email',autocomplete='email')}{input_block('Password (at least 8 characters)','password','password',autocomplete='new-password')}{input_block('Confirm password','confirm_password','password',autocomplete='new-password')}
    <button class="tr-button tr-button-primary" type="submit">Create account →</button></fieldset></form><p class="tr-muted">{access_note}</p><a class="tr-auth-link" href="/signin_login">Already a member? Sign in</a>"""
    return auth_shell(content, 'Create account', user=user)


def render_signup_page(error: str = "", success: str = "", user=None) -> str:
    return render_signin_page(error, user=user) if not success else auth_shell(message_block(success=success) + '<a class="tr-button" href="/signin_login">Sign in</a>', 'Account created', user=user)


def render_signin_login_page(error: str = "", user=None) -> str:
    content = f"""<h1>Welcome back.</h1><p class="tr-muted">Sign in to your TableRadar account.</p>{message_block(error=error)}{render_social_signin()}
    <form method="post" action="/signin_login">{input_block('Email address','email','email',autocomplete='email')}{input_block('Password','password','password',autocomplete='current-password')}<button class="tr-button tr-button-primary" type="submit">Sign in →</button></form><a class="tr-auth-link" href="/signup">New to TableRadar? Create an account</a>"""
    return auth_shell(content, 'Sign in', user=user)


def render_dashboard_page(username: str, email: str, user=None) -> str:
    return auth_shell(f'<h1>Welcome, {escape(username)}</h1><p class="tr-muted">{escape(email)}</p><a class="tr-button" href="/profile">Open your profile</a>', 'Dashboard', user=user)
