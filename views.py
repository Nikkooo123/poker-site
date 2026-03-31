def build_tags_html(tags: str) -> str:
    tags_html = ""

    if tags.strip():
        for tag in tags.split(","):
            tag = tag.strip()
            lower_tag = tag.lower()

            color = "#ff8c00"
            display_text = tag

            if "bomb" in lower_tag:
                color = "#e53935"
                display_text = "BOMB"

            elif "clock" in lower_tag or "time" in lower_tag:
                color = "#43a047"
                display_text = "⏱"

            elif "vpip" in lower_tag:
                color = "#fb8c00"
                if "30" in lower_tag:
                    display_text = "VPIP 30%"
                elif "40" in lower_tag:
                    display_text = "VPIP 40%"
                elif "50" in lower_tag:
                    display_text = "VPIP 50%"
                elif "60" in lower_tag:
                    display_text = "VPIP 60%"
                else:
                    display_text = "VPIP"

            elif "red" in lower_tag:
                color = "#b71c1c"
                display_text = "RED"

            if display_text:
                tags_html += f"""
                <span style="
                    display:inline-block;
                    background:{color};
                    color:white;
                    padding:4px 8px;
                    border-radius:8px;
                    margin-right:6px;
                    font-size:12px;
                    font-weight:bold;
                ">{display_text}</span>
                """

    return tags_html


def build_public_cards(tables) -> str:
    html_tables = ""

    for t in tables:
        tags_html = build_tags_html(t["tags"])

        html_tables += f"""
        <div style="
            background:#2a2a2a;
            padding:14px;
            margin-top:12px;
            border-radius:10px;
        ">
            <div style="font-size:22px;font-weight:bold;">{t['club']}</div>
            <div style="font-size:18px;margin-top:6px;">{t['game']}</div>
            <div>Blinds: {t['blinds']}</div>
            <div>Buy-in: {t['buyin']}</div>
            <div>Players: {t['players']}</div>
            <div style="margin-top:10px;">{tags_html}</div>
        </div>
        """

    if not html_tables:
        html_tables = """
        <div style="
            background:#2a2a2a;
            padding:14px;
            margin-top:12px;
            border-radius:10px;
            color:#bbb;
        ">
            Пока нет добавленных столов
        </div>
        """

    return html_tables


def render_public_page(tables) -> str:
    html_tables = build_public_cards(tables)

    return f"""
    <html>
    <head>
        <title>Poker Tables</title>
        <meta http-equiv="refresh" content="30">
    </head>
    <body style="background:#111;color:white;font-family:Arial;padding:20px;">
        <h1>🔥 Poker Tables</h1>
        <div style="margin-bottom:20px;color:#bbb;">Public page</div>

        <div style="margin-top:20px;">
            {html_tables}
        </div>
    </body>
    </html>
    """


def render_admin_page(tables) -> str:
    html_tables = ""

    for t in tables:
        tags_html = build_tags_html(t["tags"])

        html_tables += f"""
        <div style="
            background:#2a2a2a;
            padding:14px;
            margin-top:12px;
            border-radius:10px;
        ">
            <div style="font-size:22px;font-weight:bold;">{t['club']}</div>
            <div style="font-size:18px;margin-top:6px;">{t['game']}</div>
            <div>Blinds: {t['blinds']}</div>
            <div>Buy-in: {t['buyin']}</div>
            <div>Players: {t['players']}</div>
            <div style="margin-top:10px;">{tags_html}</div>

            <div style="margin-top:14px;">
                <form method="post" action="/update_players" style="display:inline-block; margin-right:10px;">
                    <input type="hidden" name="table_id" value="{t['id']}">
                    <input name="players" placeholder="New players (4/6)" style="padding:6px; width:140px;">
                    <button type="submit" style="padding:6px 10px;">Save players</button>
                </form>

                <form method="post" action="/delete" style="display:inline-block;">
                    <input type="hidden" name="table_id" value="{t['id']}">
                    <button type="submit" style="
                        padding:6px 10px;
                        background:#b71c1c;
                        color:white;
                        border:none;
                        border-radius:6px;
                    ">Delete</button>
                </form>
            </div>
        </div>
        """

    if not html_tables:
        html_tables = """
        <div style="
            background:#2a2a2a;
            padding:14px;
            margin-top:12px;
            border-radius:10px;
            color:#bbb;
        ">
            Пока нет добавленных столов
        </div>
        """

    return f"""
    <html>
    <head>
        <title>Poker Tables Admin</title>
    </head>
    <body style="background:#111;color:white;font-family:Arial;padding:20px;">
        <h1>🔥 Poker Tables Admin</h1>
        <div style="margin-bottom:20px;color:#bbb;">Admin page</div>

        <form method="post" action="/add" style="
            background:#222;
            padding:15px;
            border-radius:10px;
            max-width:320px;
        ">
            <input name="club" placeholder="Club name" style="width:100%;margin-bottom:8px;padding:8px;">
            <input name="game" placeholder="Game (PLO5)" style="width:100%;margin-bottom:8px;padding:8px;">
            <input name="blinds" placeholder="Blinds (2/4 or 10/20)" style="width:100%;margin-bottom:8px;padding:8px;">
            <input name="buyin" placeholder="Buy-in (600)" style="width:100%;margin-bottom:8px;padding:8px;">
            <input name="players" placeholder="Players (6/6)" style="width:100%;margin-bottom:8px;padding:8px;">
            <input name="tags" placeholder="Tags: VPIP 40%, Bomb, Clock" style="width:100%;margin-bottom:8px;padding:8px;">
            <button type="submit" style="padding:10px 14px;">Add Table</button>
        </form>

        <div style="margin-top:20px;">
            {html_tables}
        </div>
    </body>
    </html>
    """