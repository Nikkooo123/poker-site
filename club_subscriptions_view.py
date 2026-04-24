from html import escape
from brand import render_brand_logo


def _safe(value, default=""):
    if value is None:
        return default
    return str(value)


def _status_badge(status: str, days_left: int) -> str:
    status = _safe(status).lower()

    if status == "expired":
        bg = "rgba(160,60,60,.35)"
        color = "#ff9b9b"
        text = "Expired"
    elif status == "inactive":
        bg = "rgba(120,120,120,.28)"
        color = "#d5d5d5"
        text = "Inactive"
    elif days_left <= 2:
        bg = "rgba(210,140,40,.32)"
        color = "#ffd28a"
        text = "Ending soon"
    else:
        bg = "rgba(35,100,52,.45)"
        color = "#7fdc97"
        text = "Active"

    return f"""
    <span style="
        display:inline-flex;
        align-items:center;
        justify-content:center;
        min-width:92px;
        height:28px;
        border-radius:999px;
        background:{bg};
        color:{color};
        font:700 12px Arial;">
        {escape(text)}
    </span>
    """


def render_club_subscriptions_page(subscriptions: list) -> str:
    rows = ""

    for sub in subscriptions:
        sub_id = int(sub.get("id", 0))
        club_name = escape(_safe(sub.get("club_name", "")))
        owner_name = escape(_safe(sub.get("owner_name", "")))
        owner_telegram = escape(_safe(sub.get("owner_telegram", "")))
        owner_email = escape(_safe(sub.get("owner_email", "")))
        application = escape(_safe(sub.get("application", "")))
        plan = escape(_safe(sub.get("plan", "")))
        started = escape(_safe(sub.get("started_at_display", "-")))
        expires = escape(_safe(sub.get("expires_at_display", "-")))
        days_left = int(sub.get("days_left", 0) or 0)
        display_status = _safe(sub.get("display_status", sub.get("status", "active")))

        rows += f"""
        <div style="
            display:grid;
            grid-template-columns:1.1fr 1fr .8fr .7fr .7fr .55fr .7fr 1.5fr;
            gap:10px;
            align-items:center;
            min-height:58px;
            padding:10px 12px;
            border-radius:14px;
            background:rgba(255,255,255,.055);
            border:1px solid rgba(255,255,255,.06);
            box-sizing:border-box;
            margin-bottom:8px;">

            <div>
                <div style="font:800 15px Arial;color:#fff;">{club_name}</div>
                <div style="font:700 11px Arial;color:#b9c0c9;">{application}</div>
            </div>

            <div>
                <div style="font:700 13px Arial;color:#fff;">{owner_name or "-"}</div>
                <div style="font:700 11px Arial;color:#b9c0c9;">Owner</div>
            </div>

            <div style="font:700 12px Arial;color:#dce4db;word-break:break-all;">
                {owner_telegram or "-"}
            </div>

            <div style="font:700 12px Arial;color:#dce4db;word-break:break-all;">
                {owner_email or "-"}
            </div>

            <div style="font:700 13px Arial;color:#fff;">
                {plan}
            </div>

            <div>
                <div style="font:800 18px Arial;color:#fff;">{days_left}</div>
                <div style="font:700 10px Arial;color:#b9c0c9;">days</div>
            </div>

            <div>
                {_status_badge(display_status, days_left)}
                <div style="font:700 10px Arial;color:#b9c0c9;margin-top:4px;">
                    {started} → {expires}
                </div>
            </div>

            <div style="display:flex;gap:6px;align-items:center;justify-content:flex-end;flex-wrap:wrap;">
                <form method="post" action="/admin/club-subscriptions/{sub_id}/extend" style="display:flex;gap:4px;margin:0;">
                    <input name="days" value="30" style="
                        width:46px;
                        height:28px;
                        border:none;
                        border-radius:8px;
                        padding:0 8px;
                        font:700 12px Arial;">
                    <button type="submit" style="
                        height:28px;
                        border:none;
                        border-radius:8px;
                        background:#236b34;
                        color:#eef8f0;
                        font:700 12px Arial;
                        padding:0 9px;
                        cursor:pointer;">
                        Extend
                    </button>
                </form>

                <form method="post" action="/admin/club-subscriptions/{sub_id}/disable" style="margin:0;">
                    <button type="submit" style="
                        height:28px;
                        border:none;
                        border-radius:8px;
                        background:#6d5b37;
                        color:#fff0cf;
                        font:700 12px Arial;
                        padding:0 9px;
                        cursor:pointer;">
                        Disable
                    </button>
                </form>

                <form method="post" action="/admin/club-subscriptions/{sub_id}/delete" style="margin:0;">
                    <button type="submit" style="
                        height:28px;
                        border:none;
                        border-radius:8px;
                        background:#8f2e36;
                        color:#fff1f1;
                        font:700 12px Arial;
                        padding:0 9px;
                        cursor:pointer;">
                        Delete
                    </button>
                </form>
            </div>
        </div>
        """

    if not rows:
        rows = """
        <div style="
            padding:18px;
            border-radius:14px;
            background:rgba(255,255,255,.06);
            color:#dce4db;
            font:700 15px Arial;">
            No club subscriptions yet.
        </div>
        """

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Club Subscriptions · TableRadar</title>
        <style>
            body {{
                overflow-x:hidden;
            }}

            .bg-orb {{
                position: fixed;
                border-radius: 999px;
                filter: blur(90px);
                opacity: .28;
                pointer-events: none;
                z-index: 0;
            }}

            .orb-a {{ width:420px;height:420px;top:70px;left:-80px;background:#5ac8fa; }}
            .orb-b {{ width:360px;height:360px;top:180px;right:120px;background:#7b65c4; }}
            .orb-c {{ width:420px;height:420px;bottom:-120px;left:30%;background:#57b84f; }}

            .glass {{
                background:linear-gradient(180deg, rgba(255,255,255,.12), rgba(255,255,255,.06));
                border:1px solid rgba(255,255,255,.08);
                box-shadow:0 18px 42px rgba(0,0,0,.22);
                backdrop-filter:blur(12px);
            }}

            input, select, textarea {{
                box-sizing:border-box;
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
        padding:24px;">

        <div class="bg-orb orb-a"></div>
        <div class="bg-orb orb-b"></div>
        <div class="bg-orb orb-c"></div>

        <div style="position:relative;z-index:2;">

            <div style="
                display:flex;
                justify-content:space-between;
                align-items:center;
                margin-bottom:18px;">
                {render_brand_logo("/")}

                <div style="display:flex;gap:10px;">
                    <a href="/admin" style="
                        display:inline-flex;
                        align-items:center;
                        justify-content:center;
                        height:38px;
                        padding:0 16px;
                        border-radius:999px;
                        background:rgba(255,255,255,.08);
                        color:#fff;
                        text-decoration:none;
                        font:700 13px Arial;">
                        Admin
                    </a>

                    <a href="/" style="
                        display:inline-flex;
                        align-items:center;
                        justify-content:center;
                        height:38px;
                        padding:0 16px;
                        border-radius:999px;
                        background:rgba(35,107,52,.85);
                        color:#eef8f0;
                        text-decoration:none;
                        font:700 13px Arial;">
                        Home
                    </a>
                </div>
            </div>

            <div style="max-width:1280px;margin:0 auto;">

                <div class="glass" style="
                    border-radius:22px;
                    padding:22px;
                    box-sizing:border-box;
                    margin-bottom:18px;">

                    <div style="font:800 32px Arial;color:#fff;margin-bottom:4px;">
                        Club Subscriptions
                    </div>

                    <div style="font:600 15px Arial;color:#c9d1d9;margin-bottom:20px;">
                        Track club owners, subscription expiry dates and contact details.
                    </div>

                    <form method="post" action="/admin/club-subscriptions/add" style="
                        display:grid;
                        grid-template-columns:1fr 1fr 1fr 1fr;
                        gap:12px;
                        align-items:end;">

                        <div>
                            <label style="font:700 12px Arial;color:#dce4db;">Club name</label>
                            <input name="club_name" placeholder="Club name" required style="
                                width:100%;
                                height:40px;
                                border:none;
                                border-radius:10px;
                                padding:0 12px;">
                        </div>

                        <div>
                            <label style="font:700 12px Arial;color:#dce4db;">Owner name</label>
                            <input name="owner_name" placeholder="Owner name" style="
                                width:100%;
                                height:40px;
                                border:none;
                                border-radius:10px;
                                padding:0 12px;">
                        </div>

                        <div>
                            <label style="font:700 12px Arial;color:#dce4db;">Owner Telegram</label>
                            <input name="owner_telegram" placeholder="@username or https://t.me/..." style="
                                width:100%;
                                height:40px;
                                border:none;
                                border-radius:10px;
                                padding:0 12px;">
                        </div>

                        <div>
                            <label style="font:700 12px Arial;color:#dce4db;">Owner email</label>
                            <input name="owner_email" placeholder="email" style="
                                width:100%;
                                height:40px;
                                border:none;
                                border-radius:10px;
                                padding:0 12px;">
                        </div>

                        <div>
                            <label style="font:700 12px Arial;color:#dce4db;">Application</label>
                            <select name="application" style="
                                width:100%;
                                height:40px;
                                border:none;
                                border-radius:10px;
                                padding:0 12px;">
                                <option value="PP Poker">PP Poker</option>
                                <option value="Poker Bros">Poker Bros</option>
                                <option value="Club GG">Club GG</option>
                                <option value="X Poker">X Poker</option>
                            </select>
                        </div>

                        <div>
                            <label style="font:700 12px Arial;color:#dce4db;">Plan</label>
                            <select name="plan" style="
                                width:100%;
                                height:40px;
                                border:none;
                                border-radius:10px;
                                padding:0 12px;">
                                <option value="host">Host</option>
                                <option value="player">Player</option>
                                <option value="custom">Custom</option>
                            </select>
                        </div>

                        <div>
                            <label style="font:700 12px Arial;color:#dce4db;">Days</label>
                            <input name="duration_days" value="30" style="
                                width:100%;
                                height:40px;
                                border:none;
                                border-radius:10px;
                                padding:0 12px;">
                        </div>

                        <div>
                            <button type="submit" style="
                                width:100%;
                                height:40px;
                                border:none;
                                border-radius:10px;
                                background:#236b34;
                                color:#eef8f0;
                                font:800 14px Arial;
                                cursor:pointer;">
                                Add subscription
                            </button>
                        </div>

                        <div style="grid-column:1 / span 4;">
                            <textarea name="notes" placeholder="Notes" style="
                                width:100%;
                                height:68px;
                                border:none;
                                border-radius:10px;
                                padding:12px;
                                resize:vertical;"></textarea>
                        </div>
                    </form>
                </div>

                <div class="glass" style="
                    border-radius:22px;
                    padding:16px;
                    box-sizing:border-box;">

                    <div style="
                        display:grid;
                        grid-template-columns:1.1fr 1fr .8fr .7fr .7fr .55fr .7fr 1.5fr;
                        gap:10px;
                        padding:0 12px 10px 12px;
                        color:#b9c0c9;
                        font:800 11px Arial;
                        text-transform:uppercase;">
                        <div>Club</div>
                        <div>Owner</div>
                        <div>Telegram</div>
                        <div>Email</div>
                        <div>Plan</div>
                        <div>Left</div>
                        <div>Status</div>
                        <div style="text-align:right;">Actions</div>
                    </div>

                    {rows}
                </div>
            </div>
        </div>
    </body>
    </html>
    """