"""Social sign-in stays hidden and disabled until explicitly configured."""
import os
from html import escape
from urllib.parse import urlsplit

PROVIDERS = {'google': 'Google', 'discord': 'Discord'}


def configured_providers():
    if os.getenv('SOCIAL_LOGIN_ENABLED', '').lower() != 'true':
        return ()
    origin = os.getenv('SOCIAL_LOGIN_ORIGIN', 'https://tableradar.net').rstrip('/')
    parsed = urlsplit(origin)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        return ()
    return tuple(key for key in PROVIDERS if os.getenv(key.upper()+'_CLIENT_ID') and os.getenv(key.upper()+'_CLIENT_SECRET'))


def callback_url(provider):
    if provider not in configured_providers():
        raise ValueError('Social sign-in is not configured.')
    return os.getenv('SOCIAL_LOGIN_ORIGIN', 'https://tableradar.net').rstrip('/')+'/auth/'+provider+'/callback'


def render_social_signin():
    providers = configured_providers()
    if not providers:
        return ''
    buttons = ''.join(f'<a class="tr-button" href="/auth/{key}" style="justify-content:center">Continue with {PROVIDERS[key]}</a>' for key in providers)
    return '<div class="tr-social-signin" style="display:grid;gap:8px;margin:18px 0">'+buttons+'</div><p class="tr-muted" style="font-size:12px">Use the same sign-in method each time. Existing accounts can connect another method from My Account.</p>'


def render_social_connections(user):
    providers = configured_providers()
    if not providers:
        return ''
    from social_auth_storage import linked_providers
    try:
        linked = linked_providers(user['email'])
    except Exception:
        return '<p class="note">Sign-in options are temporarily unavailable.</p>'
    forms = []
    for key in providers:
        if key in linked:
            forms.append(f'<p class="note">{PROVIDERS[key]} connected</p>')
            continue
        password = '<label class="tr-muted">Current password<input type="password" name="current_password" required autocomplete="current-password" maxlength="256" style="width:100%;padding:9px;margin:7px 0"></label>' if user.get('password_login_enabled', True) else '<p class="note">Sign in with your connected provider again if your last sign-in was over five minutes ago.</p>'
        forms.append(f'<form method="post" action="/auth/{key}/connect" style="margin-top:12px"><input type="hidden" name="csrf" value="{escape(str(user.get("_csrf", "")),quote=True)}">{password}<button class="tr-button" type="submit">Connect {PROVIDERS[key]}</button></form>')
    return '<details style="margin-top:18px"><summary style="cursor:pointer;font-size:13px">Sign-in options</summary><p class="note">Connect an account with the same verified email address. Your TableRadar email and membership stay the same.</p>'+''.join(forms)+'</details>'
