from html import escape
from brand import render_brand_logo


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

    if plan == "host" and is_active:
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
    username = _safe(user.get("username", user.get("email", "User")))
    email = _safe(user.get("email", ""))
    registered_at = _safe(user.get("registered_at", user.get("registered", "-")))
    days_left = int(user.get("days_left", 0))
    is_active = bool(user.get("is_active", False))
    status_text = f"Active ({days_left} days)" if is_active else "Inactive"
    status_color = "#2f8f46" if is_active else "#666666"

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Profile</title>
        <style>
            body {{
                overflow-x: hidden;
            }}

            .bg-orb {{
                position: fixed;
                border-radius: 999px;
                filter: blur(90px);
                opacity: .28;
                pointer-events: none;
                z-index: 0;
            }}

            .orb-a {{ width: 420px; height: 420px; top: 70px; left: -80px; background: #5ac8fa; }}
            .orb-b {{ width: 360px; height: 360px; top: 180px; right: 120px; background: #7b65c4; }}
            .orb-c {{ width: 420px; height: 420px; bottom: -120px; left: 30%; background: #57b84f; }}

            .glass {{
                background: linear-gradient(180deg, rgba(255,255,255,.12), rgba(255,255,255,.06));
                border: 1px solid rgba(255,255,255,.08);
                box-shadow: 0 18px 42px rgba(0,0,0,.22);
                backdrop-filter: blur(12px);
            }}

            .mini-card {{
                background: rgba(255,255,255,.08);
                border: 1px solid rgba(255,255,255,.05);
                border-radius: 14px;
                padding: 16px;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.03);
            }}
        </style>
    </head>
    <body style="
        margin:0;
        background:
            radial-gradient(circle at 14% 18%, rgba(91,199,255,.20), transparent 26%),
            radial-gradient(circle at 86% 20%, rgba(123,101,196,.16), transparent 24%),
            radial-gradient(circle at 50% 100%, rgba(87,184,79,.16), transparent 28%),
            linear-gradient(135deg,#12171b 0%, #0f1217 38%, #131922 100%);
        color:white;
        font-family:Arial,sans-serif;
        min-height:100vh;
        box-sizing:border-box;
        padding:24px;">

        <div class="bg-orb orb-a"></div>
        <div class="bg-orb orb-b"></div>
        <div class="bg-orb orb-c"></div>

        <div style="position:relative;z-index:2;">

            <div style="
                width:100%;
                display:flex;
                justify-content:space-between;
                align-items:flex-start;
                margin-bottom:18px;">

                {render_brand_logo("/")}

                <div style="display:flex;align-items:center;gap:12px;">
                    {_top_plan_badge(user)}

                    <div style="
                        background:rgba(255,255,255,.08);
                        border:1px solid rgba(255,255,255,.08);
                        border-radius:16px;
                        padding:10px 16px;
                        color:#fff;
                        font:700 15px Arial;
                        display:flex;
                        align-items:center;
                        gap:10px;
                        min-width:220px;
                        box-sizing:border-box;
                        box-shadow:0 10px 24px rgba(0,0,0,.22);
                        backdrop-filter:blur(8px);">

                        <span style="
                            width:30px;
                            height:30px;
                            border-radius:50%;
                            background:linear-gradient(180deg,#9c3c48,#702430);
                            display:inline-flex;
                            align-items:center;
                            justify-content:center;
                            box-shadow:0 4px 10px rgba(0,0,0,.2);">
                            {_person_icon(15)}
                        </span>

                        <span>{escape(email)}</span>
                    </div>
                </div>
            </div>

            <div style="width:980px;margin:22px auto 0 auto;">

                <div class="glass" style="
                    border-radius:22px;
                    padding:28px;
                    box-sizing:border-box;">

                    <div style="
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        gap:20px;
                        margin-bottom:22px;">

                        <div style="
                            display:flex;
                            align-items:center;
                            gap:18px;">

                            <div style="
                                width:68px;
                                height:68px;
                                border-radius:50%;
                                background:linear-gradient(180deg,#9c3c48,#702430);
                                display:flex;
                                align-items:center;
                                justify-content:center;
                                box-shadow:0 12px 24px rgba(0,0,0,.18);">
                                {_person_icon(28)}
                            </div>

                            <div style="
                                font:700 22px Arial;
                                color:#f1c40f;
                                line-height:1.2;">
                                {escape(email)}
                            </div>
                        </div>

                        <div style="
                            background:{status_color};
                            padding:9px 14px;
                            border-radius:20px;
                            font:700 13px Arial;
                            box-shadow:0 10px 20px rgba(0,0,0,.16);">
                            {escape(status_text)}
                        </div>
                    </div>

                    <div style="
                        display:grid;
                        grid-template-columns:1fr 1fr;
                        gap:18px;">

                        <div class="mini-card">
                            <div style="color:#b9c0c9;font-size:13px;margin-bottom:8px;">Username</div>
                            <div style="font:700 18px Arial;color:#fff;">{escape(username)}</div>
                        </div>

                        <div class="mini-card">
                            <div style="color:#b9c0c9;font-size:13px;margin-bottom:8px;">Email</div>
                            <div style="font:700 18px Arial;color:#fff;">{escape(email)}</div>
                        </div>

                        <div class="mini-card">
                            <div style="color:#b9c0c9;font-size:13px;margin-bottom:8px;">Registered</div>
                            <div style="font:700 18px Arial;color:#fff;">{escape(registered_at)}</div>
                        </div>

                        <div class="mini-card">
                            <div style="color:#b9c0c9;font-size:13px;margin-bottom:8px;">Current plan</div>
                            <div>{_current_plan_badge(user)}</div>
                        </div>
                    </div>

                    {_plans_html(user)}

                    <div style="margin-top:22px;">
                        <a href="/" style="
                            display:inline-flex;
                            align-items:center;
                            justify-content:center;
                            min-width:160px;
                            height:46px;
                            border:none;
                            border-radius:14px;
                            background:linear-gradient(180deg,#9c3c48,#702430);
                            color:#fff1f1;
                            text-decoration:none;
                            font:700 16px Arial;
                            box-shadow:
                                inset 0 1px 0 rgba(255,255,255,.12),
                                0 12px 24px rgba(0,0,0,.18);">
                            Back to home
                        </a>
                    </div>

                </div>
            </div>
        </div>
    </body>
    </html>
    """


def render_payment_page(*args, **kwargs) -> str:
    user = None
    username = kwargs.get("username", "")
    title = kwargs.get("title", "Payment")
    desc = kwargs.get("desc", "Complete payment to activate your selected plan.")
    action_href = kwargs.get("action_href", "#")
    button_text = kwargs.get("button_text", "Proceed to payment")
    back_href = kwargs.get("back_href", "/profile")

    remaining = list(args)

    if remaining and isinstance(remaining[0], dict):
        user = remaining.pop(0)
        username = _safe(user.get("email", user.get("username", username)))

    elif remaining:
        username = _safe(remaining.pop(0))

    if remaining and "title" not in kwargs:
        title = _safe(remaining.pop(0))

    if remaining and "desc" not in kwargs:
        desc = _safe(remaining.pop(0))

    if remaining and "action_href" not in kwargs:
        action_href = _safe(remaining.pop(0))

    if remaining and "button_text" not in kwargs:
        button_text = _safe(remaining.pop(0))

    plan_badge_html = _top_plan_badge(user or {"plan": "inactive", "is_active": False})

    pay_button_html = f"""
    <a href="{escape(action_href)}" style="
        display:inline-flex;
        align-items:center;
        justify-content:center;
        min-width:240px;
        height:50px;
        border:none;
        border-radius:12px;
        background:linear-gradient(180deg,#2f8f46,#236b34);
        color:#eef8f0;
        text-decoration:none;
        font:700 17px Arial;
        box-shadow:0 12px 24px rgba(0,0,0,.18);">
        {escape(button_text)}
    </a>
    """ if action_href and action_href != "#" else """
    <div style="
        display:inline-flex;
        align-items:center;
        justify-content:center;
        min-width:240px;
        height:50px;
        border-radius:12px;
        background:rgba(255,255,255,.08);
        color:#fff;
        font:700 17px Arial;">
        Payment setup pending
    </div>
    """

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Payment</title>
        <style>
            .bg-orb {{
                position: fixed;
                border-radius: 999px;
                filter: blur(90px);
                opacity: .28;
                pointer-events: none;
                z-index: 0;
            }}

            .orb-a {{ width: 420px; height: 420px; top: 70px; left: -80px; background: #5ac8fa; }}
            .orb-b {{ width: 360px; height: 360px; top: 180px; right: 120px; background: #7b65c4; }}
            .orb-c {{ width: 420px; height: 420px; bottom: -120px; left: 30%; background: #57b84f; }}
        </style>
    </head>
    <body style="
        margin:0;
        background:
            radial-gradient(circle at 14% 18%, rgba(91,199,255,.20), transparent 26%),
            radial-gradient(circle at 86% 20%, rgba(123,101,196,.16), transparent 24%),
            radial-gradient(circle at 50% 100%, rgba(87,184,79,.16), transparent 28%),
            linear-gradient(135deg,#12171b 0%, #0f1217 38%, #131922 100%);
        color:white;
        font-family:Arial,sans-serif;
        min-height:100vh;
        box-sizing:border-box;
        padding:24px;">

        <div class="bg-orb orb-a"></div>
        <div class="bg-orb orb-b"></div>
        <div class="bg-orb orb-c"></div>

        <div style="position:relative;z-index:2;">

            <div style="
                width:100%;
                display:flex;
                justify-content:space-between;
                align-items:flex-start;
                margin-bottom:18px;">

                {render_brand_logo("/")}

                <div style="display:flex;align-items:center;gap:12px;">
                    {plan_badge_html}

                    <div style="
                        background:rgba(255,255,255,.08);
                        border:1px solid rgba(255,255,255,.08);
                        border-radius:16px;
                        padding:10px 16px;
                        color:#fff;
                        font:700 15px Arial;
                        display:flex;
                        align-items:center;
                        gap:10px;
                        min-width:220px;
                        box-sizing:border-box;
                        box-shadow:0 10px 24px rgba(0,0,0,.22);
                        backdrop-filter:blur(8px);">

                        <span style="
                            width:30px;
                            height:30px;
                            border-radius:50%;
                            background:linear-gradient(180deg,#9c3c48,#702430);
                            display:inline-flex;
                            align-items:center;
                            justify-content:center;
                            box-shadow:0 4px 10px rgba(0,0,0,.2);">
                            {_person_icon(15)}
                        </span>

                        <span>{escape(username)}</span>
                    </div>
                </div>
            </div>

            <div style="
                width:760px;
                margin:40px auto 0 auto;
                background:linear-gradient(180deg, rgba(255,255,255,.12), rgba(255,255,255,.06));
                border:1px solid rgba(255,255,255,.08);
                box-shadow:0 18px 42px rgba(0,0,0,.22);
                backdrop-filter:blur(12px);
                border-radius:22px;
                padding:30px;
                box-sizing:border-box;">

                <div style="font:700 34px Arial;color:#fff;margin-bottom:10px;">Payment</div>
                <div style="font:700 18px Arial;color:#6fce87;margin-bottom:22px;">{escape(username)}</div>

                <div style="
                    background:rgba(255,255,255,.08);
                    border:1px solid rgba(63,174,90,.32);
                    border-radius:18px;
                    padding:24px;
                    box-sizing:border-box;
                    margin-bottom:24px;">

                    <div style="font:700 28px Arial;color:#6fce87;margin-bottom:8px;">{escape(title)}</div>
                    <div style="font:600 17px Arial;color:#fff;line-height:1.55;">{escape(desc)}</div>
                </div>

                <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap;">
                    {pay_button_html}

                    <a href="{escape(back_href)}" style="
                        display:inline-flex;
                        align-items:center;
                        justify-content:center;
                        min-width:180px;
                        height:50px;
                        border:none;
                        border-radius:12px;
                        background:linear-gradient(180deg,#9c3c48,#702430);
                        color:#fff1f1;
                        text-decoration:none;
                        font:700 16px Arial;
                        box-shadow:0 12px 24px rgba(0,0,0,.18);">
                        Back to profile
                    </a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """