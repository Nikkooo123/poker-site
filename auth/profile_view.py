from player_access import render_trial_notice, enabled as trial_enabled, remaining as trial_remaining, entitled as trial_entitled
from host_lifecycle import has_host_access, awaiting_launch
from html import escape
from social_auth_config import render_social_connections
from brand import render_brand_logo, render_site_theme, render_site_footer, render_host_listing_notice


def _safe(value, default=""):
    if value is None:
        return default
    return str(value)


def _person_icon(size=16):
    return f"""
    <svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="#fff1f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 21a8 8 0 0 0-16 0"></path>
        <circle cx="12" cy="7" r="4"></circle>
    </svg>
    """


def _plan_label(user: dict) -> str:
    plan = _safe(user.get("plan", "inactive")).strip().lower()
    is_active = bool(user.get("is_active", False))

    if has_host_access(user):
        return "Host"
    if plan == "player" and is_active:
        return "Player"
    return "Inactive"


def _top_plan_badge(user: dict) -> str:
    label = _plan_label(user)

    if label == "Inactive":
        return """
        <span style="
            display:inline-flex;
            align-items:center;
            justify-content:center;
            min-width:110px;
            height:38px;
            padding:0 16px;
            border:1.5px solid #7c7c7c;
            border-radius:999px;
            color:#d5d5d5;
            background:rgba(70,70,70,.55);
            font:700 14px Arial;
            box-sizing:border-box;">
            Inactive
        </span>
        """

    return f"""
    <span style="
        display:inline-flex;
        align-items:center;
        justify-content:center;
        min-width:110px;
        height:38px;
        padding:0 16px;
        border:1.5px solid #3fae5a;
        border-radius:999px;
        color:#6fce87;
        background:rgba(14,33,18,.82);
        font:700 14px Arial;
        box-sizing:border-box;
        box-shadow:0 8px 18px rgba(0,0,0,.16);">
        {escape(label)}
    </span>
    """


def _current_plan_badge(user: dict) -> str:
    label = _plan_label(user)

    if label == "Inactive":
        return """
        <span style="
            display:inline-flex;
            align-items:center;
            justify-content:center;
            min-width:110px;
            height:38px;
            padding:0 16px;
            border:1.5px solid #7c7c7c;
            border-radius:999px;
            color:#d5d5d5;
            background:rgba(70,70,70,.55);
            font:700 14px Arial;
            box-sizing:border-box;">
            Inactive
        </span>
        """

    return f"""
    <span style="
        display:inline-flex;
        align-items:center;
        justify-content:center;
        min-width:110px;
        height:38px;
        padding:0 16px;
        border:1.5px solid #3fae5a;
        border-radius:999px;
        color:#6fce87;
        background:rgba(14,33,18,.82);
        font:700 14px Arial;
        box-sizing:border-box;
        box-shadow:0 8px 18px rgba(0,0,0,.16);">
        {escape(label)}
    </span>
    """


def _plans_html(user: dict) -> str:
    label = _plan_label(user)

    player_button = """
    <a href="/pay/player" style="
        display:inline-flex;
        align-items:center;
        justify-content:center;
        width:100%;
        height:48px;
        border:none;
        border-radius:10px;
        background:linear-gradient(180deg,#2f8f46,#236b34);
        color:#eef8f0;
        text-decoration:none;
        font:700 16px Arial;
        box-shadow:0 10px 20px rgba(0,0,0,.16);">
        Choose Player
    </a>
    """

    host_button = """
    <a href="/pay/host" style="
        display:inline-flex;
        align-items:center;
        justify-content:center;
        width:100%;
        height:48px;
        border:none;
        border-radius:10px;
        background:linear-gradient(180deg,#2f8f46,#236b34);
        color:#eef8f0;
        text-decoration:none;
        font:700 16px Arial;
        box-shadow:0 10px 20px rgba(0,0,0,.16);">
        Upgrade to Host
    </a>
    """

    if label == "Player":
        player_button = """
        <div style="
            display:inline-flex;
            align-items:center;
            justify-content:center;
            width:100%;
            height:48px;
            border-radius:10px;
            background:rgba(255,255,255,.08);
            color:#fff;
            font:700 16px Arial;">
            Current plan
        </div>
        """

    if label == "Host":
        host_button = """
        <div style="
            display:inline-flex;
            align-items:center;
            justify-content:center;
            width:100%;
            height:48px;
            border-radius:10px;
            background:rgba(255,255,255,.08);
            color:#fff;
            font:700 16px Arial;">
            Current plan
        </div>
        """

    return f"""
    <div style="margin-top:24px;">
        <div style="
            font:700 30px 'Trebuchet MS', Arial;
            color:#fff;
            margin-bottom:16px;
            font-style:italic;
            letter-spacing:.4px;">
            Choose your plan
        </div>

        <div style="
            display:grid;
            grid-template-columns:1fr 1fr;
            gap:22px;">

            <div style="
                background:rgba(255,255,255,.06);
                border:1px solid rgba(63,174,90,.28);
                border-radius:18px;
                padding:22px;
                box-sizing:border-box;
                box-shadow:0 18px 42px rgba(0,0,0,.22);">
                <div style="font:700 30px Arial;color:#6fce87;margin-bottom:8px;">Player</div>
                <div style="font:600 18px Arial;color:#fff;margin-bottom:14px;">See all website information</div>
                <div style="font:600 16px Arial;color:#dce4db;line-height:1.55;margin-bottom:20px;">
                    Full access to tables, filters, favorites and your personal profile.
                </div>
                {player_button}
            </div>

            <div style="
                background:rgba(255,255,255,.06);
                border:1px solid rgba(63,174,90,.38);
                border-radius:18px;
                padding:22px;
                box-sizing:border-box;
                box-shadow:0 18px 42px rgba(0,0,0,.22);">
                <div style="font:700 30px Arial;color:#6fce87;margin-bottom:8px;">Host</div>
                <div style="font:600 18px Arial;color:#fff;margin-bottom:14px;">Add one of your own clubs</div>
                <div style="font:600 16px Arial;color:#dce4db;line-height:1.55;margin-bottom:20px;">
                    Everything in Player plus the ability to add one of your own club listings to the website.
                </div>
                {host_button}
            </div>
        </div>
    </div>
    """


def render_profile_page(user: dict) -> str:
    return render_profile(user)


def render_payment_page(*args, **kwargs) -> str:
    user = args[0] if args and isinstance(args[0], dict) else {}
    candidate = str(args[1] if len(args)>1 else kwargs.get('title', 'player')).lower()
    plan = 'host' if candidate == 'host' else 'player'
    price = '$600' if plan == 'host' else '$29.99'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{plan.title()} membership · TableRadar</title>{render_site_theme()}</head>
    <body style="margin:0"><header class="tr-site-header">{render_brand_logo('/')}{render_account_menu(user)}</header><main class="tr-site-main"><h1 class="tr-page-title">{plan.title()} membership.</h1><p class="tr-page-intro">{price} USD for 30 days. {'Listing and manual monitoring of one club, plus Player access.' if plan=='host' else 'Table information, filters, favorites and your profile.'}</p><span class="tr-status-pill">Payment setup in progress</span>
    <div class="tr-payment-grid" style="margin:24px 0"><section class="tr-payment-choice"><h2>Crypto payment</h2><p>Choose your currency and network when crypto checkout becomes available.</p><ul><li>Bitcoin · Bitcoin</li><li>ETH · Ethereum</li><li>USDT · Ethereum (ERC-20)</li><li>USDT · TRON (TRC-20)</li><li>TRX · TRON</li></ul><button class="tr-button" disabled>Crypto checkout coming soon</button></section><section class="tr-payment-choice"><h2>Bank payment</h2><p>Bank payment details and available methods will appear here after the payment service is connected.</p><p>No bank or wallet details are collected on this page.</p><button class="tr-button" disabled>Bank payment coming soon</button></section></div>
    <p class="tr-page-intro">Payments and automatic renewal are not enabled yet. Selecting a plan does not activate or charge a subscription.</p><a class="tr-button" href="/profile">← Back to membership</a></main>{render_site_footer()}</body></html>"""


def render_account_menu(user):
    host_link = '<a href="/host">Host dashboard</a>' if has_host_access(user) else ''
    staff_links = ('<a href="/manager">Manager workspace</a>' if user.get("_is_manager") or user.get("staff_role") == "manager" else ('<a href="/admin">Table administration</a>' if user.get("staff_role") == "table_admin" else ''))
    email = escape(str(user.get("email") or user.get("username") or "Account"))
    return f'''<style>
    .tr-account{{position:relative;font:13px/1.5 'Segoe UI',Arial,sans-serif;z-index:10;max-width:100%}}
    .tr-account summary{{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;padding:11px 15px;border:1px solid #ffffff20;border-radius:12px;background:#203035;color:#edf3f2}}
    .tr-account summary::-webkit-details-marker{{display:none}}.tr-account summary:focus-visible{{outline:2px solid #a8d8c4;outline-offset:4px}}
    .tr-account summary span{{max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
    .tr-account-menu{{position:absolute;right:0;top:calc(100% + 9px);min-width:210px;padding:7px;background:#1e2a30;border:1px solid #ffffff20;border-radius:14px;box-shadow:0 15px 35px #0005}}
    .tr-account-menu a{{display:block;padding:10px 12px;color:#e3efeb;text-decoration:none;border-radius:8px}}.tr-account-menu a:hover,.tr-account-menu a:focus-visible{{background:#ffffff0d}}
    </style><details class="tr-account"><summary aria-label="Account menu"><span>{email}</span>⌄</summary><nav class="tr-account-menu" aria-label="Account"><a href="/profile">My account</a>{staff_links}{host_link}<a href="/">Explore tables</a><a href="/about">About Us</a><a href="/faq">FAQ</a><a href="/terms">Terms &amp; Conditions</a><a href="/contact">Contact</a><a href="/logout">Sign out</a></nav></details>'''


"""Responsive account page, with the existing plan and payment routes."""
from html import escape
from brand import render_brand_logo, render_site_theme, render_site_footer, render_host_listing_notice



def render_profile(user):
    def safe(value):
        return escape(str(value if value is not None else ""))

    email = safe(user.get("email", ""))
    username = safe(user.get("username") or user.get("email") or "Player")
    registered = safe(user.get("registered_at", user.get("registered", "—")))
    active = bool(user.get("is_active", False))
    plan = str(user.get("plan", "inactive")).lower()
    current = plan.title() if (active or awaiting_launch(user)) and plan in ("player", "host") else "No membership"
    days = safe(user.get("days_left", 0))
    status = f"Active · {current} · {days} days remaining" if active else "No active membership — choose a plan below"
    if awaiting_launch(user):
        status = "Host payment confirmed - preparing your listing - service clock not started"
    if trial_enabled() and trial_remaining(user) and trial_entitled(user) and not active:
        current = "Player trial"
        days = str(trial_remaining(user))
        status = "Player free trial · " + days + " days remaining — full table and club access, including Join"
    initial = username[:1].upper() if username else "P"

    testing = bool(user.get("membership_test_enabled"))
    can_test = bool(user.get("_can_test") or user.get("_can_enable_test"))
    csrf = safe(user.get("_csrf", ""))
    def test_form(plan, label):
        return f'<form method="post" action="/account/test-membership"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="plan" value="{plan}"><button class="button secondary" style="width:100%;cursor:pointer;color:inherit" type="submit">{label}</button></form>'
    test_controls = ""
    if testing and can_test:
        test_controls = '<p class="note">Private test mode. No payment, no automatic renewal. Switching starts a fresh 30-day test period; your club request stays saved.</p>' + test_form("reset", "Reset my test membership")
    elif user.get("_can_enable_test"):
        test_controls = '<p class="note">Manager-only preview. Test either membership free on your own account. No payment or renewal.</p>' + test_form("host", "Try Host free") + test_form("player", "Try Player free")
    dashboard = '<a class="button secondary" href="/host">Open Host dashboard →</a>' if has_host_access(user) else ""
    security_error = f'<p role="alert" class="tr-security-error">{safe(user.get("_security_error"))}</p>' if user.get('_security_error') else ''
    password_login = user.get("password_login_enabled", True)
    password_control = '<button type="button" id="open-password-dialog" aria-haspopup="dialog">Change Password</button>' if password_login else '<span class="tr-muted" style="font-size:12px">Provider sign-in</span>'
    social_connections = render_social_connections(user)
    open_on_error = "<script>document.getElementById('password-dialog').showModal();</script>" if security_error else ""
    security = f'''<dialog id="password-dialog" class="tr-password-dialog" aria-labelledby="password-title"><div class="tr-password-heading"><h2 id="password-title">Change password</h2><form method="dialog"><button class="tr-button" aria-label="Close password window" type="submit">×</button></form></div><p class="tr-muted">Your email stays the same: <strong>{email}</strong></p>{security_error}<form method="post" action="/account/security/password"><input type="hidden" name="csrf" value="{csrf}"><div class="tr-security-fields"><label>Current password<input type="password" name="current_password" autocomplete="current-password" maxlength="256" autofocus required></label><label>New password<input type="password" name="new_password" autocomplete="new-password" minlength="10" maxlength="256" required></label><label>Confirm new password<input type="password" name="confirm_password" autocomplete="new-password" minlength="10" maxlength="256" required></label></div><p class="note">Use at least 10 characters. After changing your password, sign in again on your devices.</p><button class="tr-button" type="submit">Save new password</button></form></dialog>{open_on_error}<script>document.getElementById('open-password-dialog').addEventListener('click',()=>document.getElementById('password-dialog').showModal());</script>'''
    if not password_login:
        security = ''


    privacy = f'''<details style="margin-top:16px;border-top:1px solid var(--line);padding-top:12px"><summary style="cursor:pointer;font-size:13px;color:var(--accent)">Privacy preferences</summary><form method="post" action="/account/privacy/activity" style="margin-top:12px"><input type="hidden" name="csrf" value="{csrf}"><label style="display:flex;gap:9px;align-items:flex-start;font-size:12px"><input type="checkbox" name="activity_statistics" value="1" {'checked' if user.get('activity_statistics_enabled') is True else ''} style="width:16px;height:16px;flex:none;margin:3px 0 0"><span>Share my approximate activity statistics with TableRadar managers.</span></label><p style="font-size:11px;color:var(--muted);margin:8px 0 12px;line-height:1.5">Optional and off by default. Includes approximate active time and the last general site section. Your choice does not affect membership. You can switch it off here at any time. Sign-in security records are kept separately.</p><button class="tr-button" type="submit" style="font-size:12px;padding:7px 12px">Save privacy preference</button> <a href="/privacy" style="font-size:12px;color:var(--accent)">Privacy Policy</a></form></details>'''

    def plan_card(name, caption, features, href):
        selected = current.lower() == name.lower()
        action = '<span class="button current">Current plan <span>✓</span></span>' if selected else f'<a class="button {"primary" if name == "Host" else "secondary"}" href="{href}">Choose {name} <span>↗</span></a>'
        if can_test and not selected:
            action = test_form(name.lower(), f"Try {name} free" if not active else f"Switch to {name} — free test")
        price = "$29.99" if name == "Player" else "$600"
        price_html = (f'<div style="font-size:26px;margin-bottom:8px">Free test<span style="display:block;font-size:12px;color:var(--muted)">No charge · Standard price {price} / 30 days when payments launch</span></div>' if testing else f'<div style="font-size:26px;margin-bottom:8px">{price}<span style="font-size:12px;color:var(--muted)"> / 30 days</span></div>')
        return f'''<article class="plan {'selected' if selected else ''}">
          <div class="plan-top"><span class="eyebrow">{name} membership</span>{'<span class="pill">Your plan</span>' if selected else ''}</div>
          <h3>{name}</h3>{price_html}<p>{caption}</p>
          <ul>{''.join(f'<li><span>✓</span>{item}</li>' for item in features)}</ul>{render_host_listing_notice() if name == "Host" else ""}{action}</article>'''

    player = plan_card("Player", "Your place at the right table.", ["Access to all table information", "Filters and favorites", "Your personal profile"], "/pay/player")
    host = plan_card("Host", "Bring your club to the radar.", ["Everything included in Player", "Add one of your own club listings", "Showcase your club to players"], "/pay/host")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1"><title>Profile · TableRadar</title>
    <style>
    :root{{--bg:#10171b;--panel:#192329;--text:#edf3f2;--muted:#a5b4b6;--line:rgba(200,223,221,.12);--accent:#a8d8c4}}
    *{{box-sizing:border-box}}body{{margin:0;color:var(--text);font:15px/1.6 'Segoe UI',Arial,sans-serif;background:radial-gradient(ellipse at 12% 0%,#203d3c80,transparent 52%),radial-gradient(ellipse at 95% 60%,#332c3b60,transparent 50%),var(--bg);min-height:100vh}}
    a{{color:inherit;text-decoration:none}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:5px}}header{{max-width:1200px;margin:auto;padding:25px 36px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);gap:20px}}.nav{{display:flex;gap:24px;align-items:center;color:var(--muted);font-size:13px}}.nav a:hover{{color:white}}.avatar{{width:44px;height:44px;border-radius:14px;background:#334b47;color:#d6f5e8;display:grid;place-items:center;font-weight:600;flex-shrink:0}}
    main{{max-width:1120px;margin:auto;padding:46px 36px 64px}}.eyebrow{{font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}}h1,h2,h3,p{{margin:0}}h1{{font-size:clamp(30px,4vw,42px);font-weight:600;letter-spacing:-.04em;margin:6px 0 8px}}.intro{{color:var(--muted);max-width:530px}}.layout{{display:grid;grid-template-columns:1fr;gap:32px;margin-top:18px;align-items:start}}.account dl{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px}}.account .identity{{margin-bottom:16px}}.panel,.plan{{border:1px solid var(--line);background:linear-gradient(145deg,#202d32e8,#172126e8);border-radius:22px;box-shadow:0 16px 40px #00000015}}
    .account{{padding:26px}}.account-email-heading{{display:flex;align-items:baseline;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:4px}}.account-email-heading dt{{margin:0}}#open-password-dialog{{appearance:none;background:none;border:0;box-shadow:none;padding:0;border-radius:0;font:inherit;font-size:12px;font-weight:400;color:var(--muted);cursor:pointer}}#open-password-dialog:hover{{color:var(--text);text-decoration:underline}}#open-password-dialog:focus-visible{{outline:2px solid var(--accent);outline-offset:4px}}.identity{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px;align-items:center;margin-bottom:24px}}.identity-person{{grid-column:1/4;display:flex;align-items:center;gap:14px;min-width:0}}.identity-person>div:last-child{{min-width:0}}.identity #open-password-dialog{{grid-column:4;justify-self:start}}.identity strong{{display:block;overflow-wrap:anywhere;font-size:16px;font-weight:600}}.identity small{{color:var(--muted)}}.pill{{display:inline-flex;align-items:center;border:1px solid #a8d8c435;background:#a8d8c40c;border-radius:100px;padding:4px 10px;color:var(--accent);font-size:11px;white-space:nowrap}}.status{{padding-bottom:22px;border-bottom:1px solid var(--line);color:{'#a8d8c4' if active else '#b7bcc0'};font-size:12px}}dl{{margin:0}}dl>div{{padding-top:20px}}dt{{color:var(--muted);font-size:12px;margin-bottom:4px}}dd{{margin:0;font-size:14px;overflow-wrap:anywhere}}.back{{margin-top:26px;padding-top:20px;border-top:1px solid var(--line);display:block;font-size:13px;color:var(--accent)}}.section-head{{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:18px}}h2{{font-size:22px;font-weight:600;letter-spacing:-.025em}}.section-head p{{color:var(--muted);font-size:13px;margin-top:3px}}.plans{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.plan{{padding:24px;display:flex;flex-direction:column;min-width:0}}.plan.selected{{border:2px solid #8db6c4;background:linear-gradient(145deg,#27404ae8,#1b2c34e8);box-shadow:0 0 0 4px #8db6c412}}.plan.selected .pill{{background:#8db6c426;border-color:#8db6c477;color:#d4e7ee;font-weight:700}}.plan-top{{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:29px}}.plan-top .eyebrow{{font-size:10px;letter-spacing:.08em}}h3{{font-size:28px;font-weight:500;letter-spacing:-.03em;margin:20px 0 5px}}.plan p{{color:var(--muted);font-size:13px;min-height:42px}}ul{{list-style:none;padding:24px 0;margin:0;flex:1}}li{{display:flex;gap:9px;font-size:12px;margin-bottom:13px}}li span{{color:var(--accent)}}.button{{display:flex;justify-content:space-between;align-items:center;padding:12px 15px;border-radius:11px;font-size:13px;font-weight:600;border:1px solid var(--line);gap:10px}}.primary{{background:var(--accent);color:#152720;border-color:var(--accent)}}.primary:hover{{background:#bee9d8}}.secondary:hover{{background:#ffffff09}}.current{{color:#d4e7ee;background:#8db6c424;border-color:#8db6c477;font-weight:700}}.note{{color:var(--muted);font-size:12px;margin-top:20px}}footer{{margin-top:42px;padding-top:20px;border-top:1px solid var(--line);display:flex;justify-content:space-between;color:#86999c;font-size:11px;gap:16px}}
    @media(max-width:1000px){{.identity{{grid-template-columns:minmax(0,1fr) auto}}.identity-person{{grid-column:1}}.identity #open-password-dialog{{grid-column:2}}.account dl{{grid-template-columns:repeat(2,minmax(0,1fr))}}.plan p{{min-height:0}}}}@media(max-width:680px){{.identity{{grid-template-columns:minmax(0,1fr);gap:12px}}.identity-person{{grid-column:1}}.identity #open-password-dialog{{grid-column:1;justify-self:end}}header{{padding:20px;flex-wrap:wrap}}main{{padding:30px 20px}}.layout{{grid-template-columns:1fr;gap:28px}}.nav .nav-label{{display:none}}.plans{{grid-template-columns:1fr}}.account{{padding:22px}}.account dl{{grid-template-columns:1fr}}footer{{flex-wrap:wrap}}}}
    </style>{render_site_theme()}</head><body><header>{render_brand_logo("/")}<div class="nav">{render_account_menu(user)}</div></header>
    <main><div class="eyebrow">Your TableRadar</div><h1>A place for your game.</h1><p class="intro">Your account details and membership settings, clearly separated.</p>
    <div class="section-head" style="margin-top:34px"><div><h2>My profile</h2><p>Your personal account and current access.</p></div></div><div class="layout"><aside class="panel account" aria-label="Account details"><div class="identity"><div class="identity-person"><div class="avatar" aria-hidden="true">{initial}</div><div><strong>{username}</strong><small>TableRadar account</small></div></div>{password_control}</div><div class="status">● {status}</div><dl><div><dt>Email address</dt><dd>{email}</dd></div><div><dt>Member since</dt><dd>{registered}</dd></div><div><dt>Current membership</dt><dd>{current}{" · Free test" if testing and active else ""}</dd></div><div><dt>Valid until</dt><dd>{safe(user.get("plan_expires_at") or "Not recorded") if active else ("Starts when your listing is ready" if awaiting_launch(user) else "No active subscription")}</dd></div></dl>{social_connections}{privacy}<a class="back" href="/">← Back to tables</a></aside>
    <section aria-labelledby="membership"><div class="section-head"><div><h2 id="membership">Manage membership</h2><p>{"Private preview: try either membership free. No payment or renewal." if testing else "Player access or a Host membership for your club."}</p></div></div><div class="plans">{player}{host}</div>{render_trial_notice(user)}{test_controls}{dashboard}</section></div><p class="note">Membership details are linked to your TableRadar account.</p>{security}{render_site_footer()}</main></body></html>'''

