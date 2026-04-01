from html import escape


# =========================
# HELPERS
# =========================

def game_label(game: str) -> str:
    game = (game or "").strip().upper()
    return "PLO4" if game == "PLO" else game


def game_color(game: str) -> str:
    return {
        "NLH": "#35c84a",
        "PLO4": "#45c7ea",
        "PLO5": "#37b9df",
        "PLO6": "#2e9fc6",
    }.get(game_label(game), "#666666")


def to_number(value: str) -> float:
    value = (value or "").replace(",", ".")
    value = "".join(ch for ch in value if ch.isdigit() or ch == ".")
    try:
        return float(value)
    except Exception:
        return 0.0


def big_blind_value(blinds: str) -> float:
    s = (blinds or "").strip()

    # если есть скобки, например "2/4 (1.20)", берём только часть до скобок
    if "(" in s:
        s = s.split("(", 1)[0].strip()

    # нормализуем возможные тире
    s = s.replace("-", "/").replace("\\", "/")

    parts = [p.strip() for p in s.split("/") if p.strip()]

    if len(parts) >= 2:
        return to_number(parts[1])   # большой блайнд
    if len(parts) == 1:
        return to_number(parts[0])
    return 0.0


def players_value(players: str) -> int:
    try:
        return int((players or "0").split("/")[0])
    except Exception:
        return 0


def small_badge(text: str, bg: str) -> str:
    return (
        f'<span style="display:inline-block;background:{bg};color:#fff;'
        f'font:700 8px Arial;padding:2px 5px;border-radius:7px;'
        f'margin-left:3px;white-space:nowrap;">{escape(text)}</span>'
    )


def render_tags(tags: str) -> str:
    result = []
    for tag in [x.strip() for x in (tags or "").split(",") if x.strip()]:
        low = tag.lower()
        if "vpip" in low:
            result.append(small_badge(tag.upper(), "#d49a17"))
        elif "bomb" in low:
            result.append(small_badge("BOMB", "#d85d4a"))
        elif "clock" in low or "time" in low:
            result.append(small_badge("⏰", "#6abb5d"))
        else:
            result.append(small_badge(tag, "#777"))
    return "".join(result)


def input_style() -> str:
    return (
        "width:100%;padding:12px;margin-bottom:10px;"
        "border-radius:8px;border:none;box-sizing:border-box;"
    )


# =========================
# PUBLIC SMALL BLOCKS
# =========================

def game_button(name: str) -> str:
    return f"""
    <button class="game-filter" data-game="{name}" style="
        background:#2a2d33;
        color:#fff;
        border:1px solid rgba(255,255,255,.08);
        border-radius:16px;
        padding:8px 18px;
        cursor:pointer;
        font:700 12px Arial;">
        {name}
    </button>
    """


def blinds_select(select_id: str, first_label: str) -> str:
    options = ["0.5", "1", "2", "4", "6", "8", "10", "15", "20", "25", "30", "50", "100", "200"]
    opts = [f'<option value="">{first_label}</option>'] + [
        f'<option value="{v}">{v}</option>' for v in options
    ]
    return f"""
    <select id="{select_id}" style="
        width:86px;
        padding:8px 10px;
        border-radius:10px;
        border:none;
        background:#f3f3f3;
        color:#111;
        font-size:13px;
        box-sizing:border-box;">
        {''.join(opts)}
    </select>
    """


# =========================
# PUBLIC TABLE CARD
# =========================

def render_public_card(table: dict) -> str:
    table_id = int(table.get("id", 0))
    club_raw = str(table.get("club", ""))
    club = escape(club_raw)
    game = game_label(str(table.get("game", "")))
    blinds = str(table.get("blinds", ""))
    buyin = str(table.get("buyin", ""))
    players = str(table.get("players", ""))
    tags = render_tags(str(table.get("tags", "")))

    return f"""
    <div class="table-row"
         data-table-id="{table_id}"
         data-game="{escape(game)}"
         data-club="{escape(club_raw.lower())}"
         data-blinds="{big_blind_value(blinds)}"
         data-buyin="{to_number(buyin)}"
         data-players="{players_value(players)}"
         style="
            display:flex;
            align-items:center;
            gap:8px;
            margin-bottom:8px;
            width:970px;">

        <div style="
            width:28px;
            flex:0 0 28px;
            display:flex;
            justify-content:center;
            align-items:center;">
            <button class="favorite-btn"
                    data-table-id="{table_id}"
                    title="Favorite"
                    style="
                        background:none;
                        border:none;
                        color:#bdbdbd;
                        font-size:20px;
                        cursor:pointer;
                        padding:0;
                        width:20px;
                        height:20px;
                        display:flex;
                        align-items:center;
                        justify-content:center;">
                ☆
            </button>
        </div>

        <div style="
            width:866px;
            background:#43464c;
            border-radius:12px;
            overflow:hidden;
            height:58px;
            box-shadow:0 2px 6px rgba(0,0,0,.18);
            display:flex;
            box-sizing:border-box;">

            <div style="
                width:30px;
                background:{game_color(game)};
                color:#fff;
                font:800 12px Arial;
                letter-spacing:.3px;
                display:flex;
                align-items:center;
                justify-content:center;
                writing-mode:vertical-rl;
                transform:rotate(180deg);
                flex:0 0 30px;">
                {escape(game)}
            </div>

            <div style="
                padding:5px 8px;
                display:flex;
                align-items:center;
                gap:8px;
                width:100%;
                box-sizing:border-box;">

                <div style="
                    width:40px;
                    height:40px;
                    border-radius:50%;
                    border:4px solid #5ad3ef;
                    box-sizing:border-box;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font:500 15px Arial;
                    color:#fff;
                    background:#555;
                    flex:0 0 40px;">
                    {escape(players or "-")}
                </div>

                <div style="
                    flex:1;
                    min-width:0;
                    padding-left:32px;
                    display:flex;
                    flex-direction:column;
                    justify-content:center;">
                    <div style="
                        font:400 13px Arial;
                        color:#fff;
                        white-space:nowrap;
                        overflow:hidden;
                        text-overflow:ellipsis;
                        line-height:1.1;
                        margin:0 0 3px 0;">
                        {club}
                    </div>

                    <div style="
                        font:700 12px Arial;
                        color:#fff;
                        line-height:1.1;
                        margin:0;">
                        {escape(blinds)}
                    </div>
                </div>

                <div style="
                    width:158px;
                    min-width:158px;
                    text-align:right;
                    display:flex;
                    flex-direction:column;
                    justify-content:center;
                    align-items:flex-end;
                    overflow:hidden;">

                    <div style="
                        font:700 8px Arial;
                        color:#e6e6e6;
                        margin-bottom:2px;">
                        Buy-in
                    </div>

                    <div style="
                        font:400 15px Arial;
                        color:#fff;
                        line-height:1;
                        margin-bottom:4px;
                        white-space:nowrap;">
                        {escape(buyin)}
                    </div>

                    <div style="
                        display:flex;
                        justify-content:flex-end;
                        align-items:center;
                        gap:0;
                        flex-wrap:nowrap;
                        width:100%;
                        overflow:hidden;">
                        {tags}
                    </div>
                </div>
            </div>
        </div>

        <div style="
            width:96px;
            height:58px;
            background:#43464c;
            border-radius:12px;
            display:flex;
            align-items:center;
            justify-content:center;
            box-shadow:0 2px 6px rgba(0,0,0,.18);">
            <button style="
                min-width:62px;
                height:30px;
                border:none;
                border-radius:16px;
                background:#f3f3f3;
                color:#111;
                font:700 12px Arial;
                cursor:pointer;">
                Join
            </button>
        </div>
    </div>
    """


# =========================
# PUBLIC PAGE SCRIPT
# =========================

def render_public_script() -> str:
    return """
    <script>
        const K = {
          fav: "favorite_tables_ids_v1",
          games: "filter_games_v7",
          min: "filter_blinds_min_v7",
          max: "filter_blinds_max_v7",
          favOnly: "filter_favorite_only_v7",
          sortField: "sort_field_v7",
          sortPlayers: "sort_players_direction_v7",
          sortBlinds: "sort_blinds_direction_v7",
          search: "filter_search_v7"
        };

        const FIRST_LOAD_COUNT = 15;
        const LOAD_MORE_STEP = 10;

        let selectedGames = [];
        try { selectedGames = JSON.parse(localStorage.getItem(K.games) || "[]"); } catch { selectedGames = []; }

        let favoriteOnly = localStorage.getItem(K.favOnly) === "true";
        let currentSort = localStorage.getItem(K.sortField) || "";
        let sortPlayersDirection = localStorage.getItem(K.sortPlayers) || "desc";
        let sortBlindsDirection = localStorage.getItem(K.sortBlinds) || "desc";
        let visibleCount = FIRST_LOAD_COUNT;

        const $ = s => document.querySelector(s);
        const $$ = s => Array.from(document.querySelectorAll(s));

        function getFavs() {
            try { return JSON.parse(localStorage.getItem(K.fav) || "[]"); }
            catch { return []; }
        }

        function setFavs(v) {
            localStorage.setItem(K.fav, JSON.stringify(v));
        }

        function paintFavs() {
            const ids = getFavs();

            $$(".favorite-btn").forEach(btn => {
                const on = ids.includes(Number(btn.dataset.tableId));
                btn.textContent = on ? "★" : "☆";
                btn.style.color = on ? "#d0ac45" : "#bdbdbd";
            });

            const topBtn = $("#favorite-only-btn");
            topBtn.textContent = favoriteOnly ? "★" : "☆";
            topBtn.style.color = favoriteOnly ? "#d0ac45" : "#bdbdbd";
        }

        function paintGames() {
            $$(".game-filter").forEach(btn => {
                const on = selectedGames.includes(btn.dataset.game);
                btn.style.background = on ? "#50545b" : "#2a2d33";
                btn.style.border = on ? "none" : "1px solid rgba(255,255,255,.08)";
            });
        }

        function paintSort() {
            const playersBtn = $("#sort-players");
            const blindsBtn = $("#sort-blinds");

            if (playersBtn) {
                playersBtn.textContent =
                    currentSort === "players"
                        ? (sortPlayersDirection === "desc" ? "Players ↓" : "Players ↑")
                        : "Players ↕";
            }

            if (blindsBtn) {
                blindsBtn.textContent =
                    currentSort === "blinds"
                        ? (sortBlindsDirection === "desc" ? "Blinds ↓" : "Blinds ↑")
                        : "Blinds ↕";
            }
        }

        function isRowMatching(row) {
            const minRaw = $("#blinds-min").value;
            const maxRaw = $("#blinds-max").value;
            const minVal = minRaw === "" ? NaN : parseFloat(minRaw);
            const maxVal = maxRaw === "" ? NaN : parseFloat(maxRaw);
            const search = ($("#club-search").value || "").trim().toLowerCase();
            const favs = getFavs();

            const game = row.dataset.game || "";
            const club = (row.dataset.club || "").toLowerCase();
            const bigBlind = parseFloat(row.dataset.blinds || "0");
            const id = Number(row.dataset.tableId);

            if (selectedGames.length && !selectedGames.includes(game)) return false;
            if (!Number.isNaN(minVal) && bigBlind < minVal) return false;
            if (!Number.isNaN(maxVal) && bigBlind > maxVal) return false;
            if (favoriteOnly && !favs.includes(id)) return false;
            if (search && !club.includes(search)) return false;

            return true;
        }

        function updateLoadMoreButton(totalShownRows) {
            const wrap = $("#load-more-wrap");
            const btn = $("#load-more-btn");

            if (!wrap || !btn) return;

            if (totalShownRows > visibleCount) {
                wrap.style.display = "flex";
            } else {
                wrap.style.display = "none";
            }
        }

        function applyAll(mode = "reset") {
            const wrap = $("#tables-wrap");
            const rows = $$(".table-row");

            if (mode !== "loadmore") {
                visibleCount = FIRST_LOAD_COUNT;
            }

            const shown = rows.filter(isRowMatching);

            if (currentSort) {
                const dir = currentSort === "players" ? sortPlayersDirection : sortBlindsDirection;

                shown.sort((a, b) => {
                    const av = parseFloat(a.dataset[currentSort] || "0");
                    const bv = parseFloat(b.dataset[currentSort] || "0");
                    return dir === "desc" ? bv - av : av - bv;
                });
            }

            shown.forEach(row => wrap.appendChild(row));
            rows.forEach(row => row.style.display = "none");
            shown.slice(0, visibleCount).forEach(row => row.style.display = "flex");

            updateLoadMoreButton(shown.length);

            localStorage.setItem(K.games, JSON.stringify(selectedGames));
            localStorage.setItem(K.favOnly, favoriteOnly ? "true" : "false");
            localStorage.setItem(K.sortField, currentSort);
            localStorage.setItem(K.sortPlayers, sortPlayersDirection);
            localStorage.setItem(K.sortBlinds, sortBlindsDirection);
            localStorage.setItem(K.search, $("#club-search").value || "");
            localStorage.setItem(K.min, $("#blinds-min").value || "");
            localStorage.setItem(K.max, $("#blinds-max").value || "");
        }

        $$(".favorite-btn").forEach(btn => {
            btn.onclick = () => {
                let ids = getFavs();
                const id = Number(btn.dataset.tableId);
                ids = ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id];
                setFavs(ids);
                paintFavs();
                applyAll();
            };
        });

        $("#favorite-only-btn").onclick = () => {
            favoriteOnly = !favoriteOnly;
            localStorage.setItem(K.favOnly, favoriteOnly ? "true" : "false");
            paintFavs();
            applyAll();
        };

        $$(".game-filter").forEach(btn => {
            btn.onclick = () => {
                const g = btn.dataset.game;
                selectedGames = selectedGames.includes(g)
                    ? selectedGames.filter(x => x !== g)
                    : [...selectedGames, g];
                localStorage.setItem(K.games, JSON.stringify(selectedGames));
                paintGames();
                applyAll();
            };
        });

        $("#club-search").addEventListener("input", e => {
            localStorage.setItem(K.search, e.target.value);
            applyAll();
        });

        $("#blinds-min").addEventListener("change", e => {
            localStorage.setItem(K.min, e.target.value);
            applyAll();
        });

        $("#blinds-max").addEventListener("change", e => {
            localStorage.setItem(K.max, e.target.value);
            applyAll();
        });

        $("#sort-players").onclick = () => {
            currentSort = "players";
            sortPlayersDirection = sortPlayersDirection === "desc" ? "asc" : "desc";
            localStorage.setItem(K.sortField, currentSort);
            localStorage.setItem(K.sortPlayers, sortPlayersDirection);
            paintSort();
            applyAll();
        };

        $("#sort-blinds").onclick = () => {
            currentSort = "blinds";
            sortBlindsDirection = sortBlindsDirection === "desc" ? "asc" : "desc";
            localStorage.setItem(K.sortField, currentSort);
            localStorage.setItem(K.sortBlinds, sortBlindsDirection);
            paintSort();
            applyAll();
        };

        $("#load-more-btn").onclick = () => {
            visibleCount += LOAD_MORE_STEP;
            applyAll("loadmore");
        };

        $("#club-search").value = localStorage.getItem(K.search) || "";
        $("#blinds-min").value = localStorage.getItem(K.min) || "";
        $("#blinds-max").value = localStorage.getItem(K.max) || "";

        paintFavs();
        paintGames();
        paintSort();
        applyAll();
    </script>
    """

# =========================
# PUBLIC PAGE
# =========================

def render_public_page(tables):
    cards = "".join(render_public_card(t) for t in tables) or """
    <div style="
        background:rgba(255,255,255,.1);
        border-radius:14px;
        padding:16px;
        color:#ddd;
        width:970px;">
        Пока нет добавленных столов
    </div>
    """

    return f"""
    <html>
    <head>
        <title>Poker Tables</title>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="30">
    </head>
    <body style="
        margin:0;
        background:linear-gradient(180deg,#17181c,#0e0f12);
        color:#fff;
        font-family:Arial,sans-serif;
        padding:24px;">

        <div style="max-width:1320px;margin:0 auto;">

            <div style="
                display:flex;
                justify-content:space-between;
                align-items:flex-start;
                margin-bottom:18px;">

                <div style="font-size:58px;line-height:1;margin-left:8px;">🔥</div>

                <div style="
                    color:#d8d8d8;
                    font-size:16px;
                    padding-top:6px;
                    margin-right:8px;">
                    Sign In
                </div>
            </div>

            <div style="
                width:970px;
                margin:0 auto 0 190px;">

                <div style="
                    display:flex;
                    align-items:center;
                    gap:8px;
                    margin-bottom:12px;">

                    <div style="
                        width:28px;
                        flex:0 0 28px;
                        display:flex;
                        justify-content:center;">
                        <button id="favorite-only-btn" type="button" title="Favorite"
                            style="
                                width:20px;
                                height:20px;
                                background:none;
                                border:none;
                                color:#bdbdbd;
                                cursor:pointer;
                                font-size:20px;
                                padding:0;
                                display:flex;
                                align-items:center;
                                justify-content:center;">
                            ☆
                        </button>
                    </div>

                    <div style="
                        width:934px;
                        background:#43464c;
                        border:1px solid rgba(255,255,255,.06);
                        border-radius:18px;
                        padding:10px 14px;
                        display:flex;
                        align-items:center;
                        justify-content:space-between;
                        gap:16px;
                        box-sizing:border-box;">

                        <div style="
                            display:flex;
                            align-items:center;
                            gap:10px;
                            flex-wrap:wrap;">
                            {game_button("NLH")}
                            {game_button("PLO4")}
                            {game_button("PLO5")}
                            {game_button("PLO6")}
                        </div>

                        <div style="
                            display:flex;
                            align-items:center;
                            gap:10px;">
                            {blinds_select("blinds-min", "MIN")}
                            {blinds_select("blinds-max", "MAX")}
                        </div>
                    </div>
                </div>

                <div style="
                    display:flex;
                    align-items:center;
                    gap:8px;
                    margin-bottom:14px;">

                    <div style="width:28px;flex:0 0 28px;"></div>

                    <div style="
                        width:934px;
                        box-sizing:border-box;">
                        <input id="club-search" type="text" placeholder="Search club"
                               style="
                                   width:100%;
                                   padding:11px 14px;
                                   border:none;
                                   border-radius:10px;
                                   box-sizing:border-box;
                                   background:#f3f3f3;
                                   color:#111;
                                   font-size:14px;">
                    </div>
                </div>

                <div style="
                    display:grid;
                    grid-template-columns:28px 112px 1fr 96px;
                    align-items:end;
                    gap:8px;
                    margin:0 0 6px 0;
                    color:#d0d0d0;
                    font-size:12px;
                    font-weight:700;
                    width:970px;">
                    <div></div>
                    <div id="sort-players" style="cursor:pointer;text-align:left;padding-left:28px;">Players ↕</div>
                    <div id="sort-blinds" style="cursor:pointer;text-align:left;padding-left:0;">Blinds ↕</div>
                    <div></div>
                </div>

                <div id="tables-wrap">
                    {cards}
                </div>

                <div id="load-more-wrap" style="
                    display:none;
                    justify-content:center;
                    margin:18px 0 8px 0;
                    width:970px;">
                    <button id="load-more-btn" style="
                        min-width:190px;
                        height:42px;
                        border:none;
                        border-radius:14px;
                        background:#43464c;
                        color:#fff;
                        font:700 14px Arial;
                        cursor:pointer;
                        box-shadow:0 2px 6px rgba(0,0,0,.18);">
                        Load more tables
                    </button>
                </div>
            </div>
        </div>

        {render_public_script()}
    </body>
    </html>
    """

# =========================
# ADMIN PAGE
# =========================

def render_admin_card(table: dict) -> str:
    table_id = int(table.get("id", 0))
    club = escape(str(table.get("club", "")))
    game = escape(game_label(str(table.get("game", ""))))
    blinds = escape(str(table.get("blinds", "")))
    buyin = escape(str(table.get("buyin", "")))
    players = escape(str(table.get("players", "")))
    tags = render_tags(str(table.get("tags", "")))

    return f"""
    <div style="
        background:rgba(255,255,255,.12);
        border-radius:18px;
        padding:18px;
        margin-bottom:18px;">

        <div style="font-size:22px;font-weight:bold;margin-bottom:6px;">{club}</div>
        <div style="font-size:18px;font-weight:bold;">{game}</div>
        <div style="font-size:18px;">Blinds: {blinds}</div>
        <div style="font-size:18px;">Buy-in: {buyin}</div>
        <div style="font-size:18px;">Players: {players}</div>
        <div style="margin-top:8px;">{tags}</div>

        <div style="margin-top:14px;">
            <form method="post" action="/update_players" style="display:inline-block;margin-right:8px;">
                <input type="hidden" name="table_id" value="{table_id}">
                <input name="players" value="{players}" placeholder="New players (4/6)"
                       style="padding:8px;border-radius:8px;border:none;margin-right:8px;width:140px;">
                <button type="submit" style="padding:8px 14px;border:none;border-radius:8px;cursor:pointer;">
                    Save players
                </button>
            </form>

            <form method="post" action="/delete" style="display:inline-block;">
                <input type="hidden" name="table_id" value="{table_id}">
                <button type="submit" style="
                    padding:8px 14px;
                    border:none;
                    border-radius:8px;
                    cursor:pointer;
                    background:#9f4740;
                    color:white;
                    font-weight:bold;">
                    Delete
                </button>
            </form>
        </div>
    </div>
    """


def render_admin_page(tables):
    cards = "".join(render_admin_card(t) for t in tables) or """
    <div style="
        background:rgba(255,255,255,.12);
        border-radius:18px;
        padding:18px;
        margin-bottom:18px;
        font-size:18px;
        color:#ddd;">
        Пока нет добавленных столов
    </div>
    """

    return f"""
    <html>
    <head>
        <title>Poker Tables Admin</title>
        <meta charset="utf-8">
    </head>
    <body style="
        margin:0;
        background:linear-gradient(90deg,#171717,#0d0d0d);
        color:white;
        font-family:Arial,sans-serif;
        padding:40px;">

        <div style="max-width:1100px;margin:0 auto;">
            <h1 style="font-size:64px;margin:0 0 20px;">🔥 Poker Tables Admin</h1>
            <div style="margin-bottom:20px;color:#bbb;">Admin page</div>

            <div style="
                background:rgba(255,255,255,.10);
                border-radius:18px;
                padding:18px;
                margin-bottom:28px;
                max-width:520px;">

                <form method="post" action="/add">
                    <input name="club" placeholder="Club name" style="{input_style()}">

                    <select name="game" style="{input_style()}">
                        <option value="NLH">NLH</option>
                        <option value="PLO4">PLO4</option>
                        <option value="PLO5">PLO5</option>
                        <option value="PLO6">PLO6</option>
                    </select>

                    <input name="blinds" placeholder="Blinds (2/4 or 10/20)" style="{input_style()}">
                    <input name="buyin" placeholder="Buy-in (600)" style="{input_style()}">
                    <input name="players" placeholder="Players (6/6)" style="{input_style()}">
                    <input name="tags" placeholder="Tags: VPIP 40%, Bomb, Clock" style="{input_style()}">

                    <button type="submit" style="
                        padding:12px 18px;
                        border:none;
                        border-radius:8px;
                        cursor:pointer;
                        font-size:16px;">
                        Add Table
                    </button>
                </form>
            </div>

            {cards}
        </div>
    </body>
    </html>
    """
