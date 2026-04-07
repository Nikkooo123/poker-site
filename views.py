from brand import BRAND_NAME, OFFICIAL_AFFILIATE_NAME, render_brand_logo, normalize_affiliate_name
from html import escape
import re


def _safe(value, default=""):
    if value is None:
        return default
    return str(value)


def _game_label(game: str) -> str:
    game = _safe(game).strip().upper()
    if game in ("PLO 4", "PLO4"):
        return "PLO4"
    if game in ("PLO 5", "PLO5"):
        return "PLO5"
    if game in ("PLO 6", "PLO6"):
        return "PLO6"
    if game == "NLH":
        return "NLH"
    return game or "NLH"


def _parse_big_blind(blinds_text: str) -> float:
    s = _safe(blinds_text).strip()
    if not s:
        return 0.0

    if "(" in s:
        s = s.split("(", 1)[0].strip()

    s = s.replace("-", "/").replace("\\\\", "/").replace("\\", "/")
    parts = [p.strip() for p in s.split("/") if p.strip()]

    if len(parts) >= 2:
        try:
            return float(parts[1])
        except:
            return 0.0

    if len(parts) == 1:
        try:
            return float(parts[0])
        except:
            return 0.0

    return 0.0
def _render_tags(tags_raw: str) -> str:
    import re

    raw = _safe(tags_raw, "").lower()
    items = []

    # VPIP badge
    if "vpip" in raw or "vipip" in raw or "vip" in raw:
        m = re.search(r"(\d+)", raw)
        percent = f" {m.group(1)}%" if m else ""
        items.append(f"""
            <span style="
                display:inline-flex;
                align-items:center;
                justify-content:center;
                height:22px;
                padding:0 8px;
                border-radius:7px;
                background:#eea11f;
                color:rgba(255,245,215,.88);
                font:700 10px Arial;
                letter-spacing:.2px;
                white-space:nowrap;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.12),
                    0 2px 6px rgba(0,0,0,.16);">
                VPIP{percent}
            </span>
        """)

    # Bomb icon
    if "bomb" in raw:
        items.append("""
            <span title="Bomb" style="
                display:inline-flex;
                align-items:center;
                justify-content:center;
                width:22px;
                height:22px;
                border-radius:6px;
                background:#df5a47;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.10),
                    0 2px 6px rgba(0,0,0,.16);">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="#ffd6df" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M15 6l3-3"></path>
                    <path d="M14 3h4v4"></path>
                    <circle cx="10" cy="14" r="6" fill="#ffd6df" stroke="none"></circle>
                </svg>
            </span>
        """)

    # Clock icon
    if "clock" in raw:
        items.append("""
            <span title="Clock" style="
                display:inline-flex;
                align-items:center;
                justify-content:center;
                width:22px;
                height:22px;
                border-radius:6px;
                background:#73c95a;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.10),
                    0 2px 6px rgba(0,0,0,.16);">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="#ecffd8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="8"></circle>
                    <path d="M12 8v5"></path>
                    <path d="M12 12l3 2"></path>
                </svg>
            </span>
        """)

    if not items:
        return ""

    return f"""
    <div style="
        margin-top:6px;
        display:flex;
        align-items:center;
        justify-content:flex-end;
        gap:4px;
        flex-wrap:nowrap;
        white-space:nowrap;">
        {"".join(items)}
    </div>
    """

# =========================
# HELPERS
# =========================

def game_label(game: str) -> str:
    game = (game or "").strip().upper()
    if game == "PLO":
        return "PLO4"
    return game


def game_color(game: str) -> str:
    return {
        "NLH": "#2f7d32",   # darker green
        "PLO4": "#1f4fa8",  # darker blue
        "PLO5": "#1aa7b8",  # darker cyan
        "PLO6": "#6f42c1",  # darker purple
    }.get(game_label(game), "#666666")


def to_number(value: str) -> float:
    value = (value or "").replace(",", ".")
    cleaned = "".join(ch for ch in value if ch.isdigit() or ch == ".")
    try:
        return float(cleaned)
    except Exception:
        return 0.0


def big_blind_value(blinds: str) -> float:
    s = (blinds or "").strip()

    # "2/4 (1.20)" -> use only "2/4"
    if "(" in s:
        s = s.split("(", 1)[0].strip()

    s = s.replace("-", "/").replace("\\", "/")
    parts = [p.strip() for p in s.split("/") if p.strip()]

    if len(parts) >= 2:
        return to_number(parts[1])
    if len(parts) == 1:
        return to_number(parts[0])
    return 0.0


def players_value(players: str) -> int:
    try:
        return int((players or "0").split("/")[0])
    except Exception:
        return 0


def small_badge(text: str, bg: str, fg: str = "#fff") -> str:
    return (
        f'<span style="display:inline-block;'
        f'background:{bg};color:{fg};'
        f'font:700 8px Arial;line-height:1;'
        f'padding:3px 6px;border-radius:7px;'
        f'margin-left:3px;white-space:nowrap;">'
        f'{escape(text)}</span>'
    )


def render_tags(tags: str) -> str:
    result = []
    for tag in [x.strip() for x in (tags or "").split(",") if x.strip()]:
        low = tag.lower()
        if "vpip" in low:
            result.append(small_badge(tag.upper(), "#f4b62a", "#1b1b1b"))
        elif "bomb" in low:
            result.append(small_badge("BOMB", "#ff6b4a"))
        elif "clock" in low or "time" in low:
            result.append(small_badge("⏰", "#66d36e"))
        else:
            result.append(small_badge(tag, "#777777"))
    return "".join(result)


def input_style() -> str:
    return (
        "width:100%;padding:12px;margin-bottom:10px;"
        "border-radius:8px;border:none;box-sizing:border-box;"
    )


# =========================
# PUBLIC SMALL BLOCKS
# =========================

def game_button(game: str) -> str:
    return f"""
    <button
        type="button"
        class="game-filter-btn"
        data-game="{escape(game)}"
        data-bg="#4a515b"
        data-color="#eef2f5"
        data-active-bg="#636d78"
        data-active-color="#ffffff"
        style="
            width:74px;
            height:34px;
            border:none;
            border-radius:12px;
            background:#4a515b;
            color:#eef2f5;
            font:700 13px Arial;
            cursor:pointer;
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,.05),
                0 6px 14px rgba(0,0,0,.12);">
        {escape(game)}
    </button>
    """

def club_filter_button(label: str, key: str) -> str:
    presets = {
        "pppoker": {
            "bg": "rgba(15,25,16,.96)",
            "border": "rgba(85,196,104,.42)",
            "color": "#72d48a",
            "active_bg": "rgba(34,68,42,.98)",
            "active_border": "rgba(119,226,140,.82)",
            "active_color": "#f0fff3",
        },
        "pokerbros": {
            "bg": "rgba(34,24,16,.96)",
            "border": "rgba(237,162,86,.42)",
            "color": "#efb06a",
            "active_bg": "rgba(88,56,28,.98)",
            "active_border": "rgba(255,191,119,.82)",
            "active_color": "#fff6eb",
        },
        "clubgg": {
            "bg": "rgba(38,16,18,.96)",
            "border": "rgba(224,94,104,.42)",
            "color": "#e47b85",
            "active_bg": "rgba(101,34,40,.98)",
            "active_border": "rgba(255,126,137,.82)",
            "active_color": "#fff0f2",
        },
        "xpoker": {
            "bg": "rgba(18,28,44,.96)",
            "border": "rgba(118,177,236,.42)",
            "color": "#8dc6ff",
            "active_bg": "rgba(42,68,103,.98)",
            "active_border": "rgba(153,205,255,.82)",
            "active_color": "#eef8ff",
        },
    }

    p = presets.get(key, {
        "bg": "rgba(40,40,45,.96)",
        "border": "rgba(255,255,255,.18)",
        "color": "#f3f3f3",
        "active_bg": "rgba(80,80,86,.98)",
        "active_border": "rgba(255,255,255,.55)",
        "active_color": "#ffffff",
    })

    return f"""
    <button
        type="button"
        class="club-filter-btn"
        data-network="{escape(key)}"
        data-bg="{p['bg']}"
        data-border="{p['border']}"
        data-color="{p['color']}"
        data-active-bg="{p['active_bg']}"
        data-active-border="{p['active_border']}"
        data-active-color="{p['active_color']}"
        style="
            width:116px;
            height:32px;
            border:1px solid {p['border']};
            border-radius:11px;
            background:{p['bg']};
            color:{p['color']};
            font:700 12px Arial;
            cursor:pointer;
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,.03),
                0 6px 14px rgba(0,0,0,.12);">
        {escape(label)}
    </button>
    """

def blinds_select(select_id: str, label: str) -> str:
    values = ["", "0.5", "1", "2", "4", "5", "6", "8", "10", "15", "20", "25", "30", "50", "100", "200"]
    options = []
    for v in values:
        if v == "":
            options.append(f'<option value="">{label}</option>')
        else:
            options.append(f'<option value="{v}">{v}</option>')

    return f"""
    <select id="{escape(select_id)}" style="
        width:96px;
        height:38px;
        padding:0 12px;
        border:none;
        border-radius:12px;
        background:#4a515b;
        color:#eef2f5;
        font:700 13px Arial;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,.05),
            0 6px 14px rgba(0,0,0,.12);
        cursor:pointer;">
        {''.join(options)}
    </select>
    """


# =========================
# PUBLIC TABLE CARD
# =========================

def _network_from_table(table: dict) -> str:
    network = _safe(table.get("network", table.get("platform", ""))).strip().lower()
    raw_tags = _safe(table.get("tags", "")).lower()

    if not network:
        if "pppoker" in raw_tags or "pp poker" in raw_tags:
            network = "pppoker"
        elif "pokerbros" in raw_tags or "poker bros" in raw_tags:
            network = "pokerbros"
        elif "clubgg" in raw_tags or "club gg" in raw_tags:
            network = "clubgg"
        elif "xpoker" in raw_tags or "x-poker" in raw_tags or "x poker" in raw_tags:
            network = "xpoker"
        else:
            network = "unknown"

    return network


def _network_label(network: str) -> str:
    labels = {
        "pppoker": "PP Poker",
        "pokerbros": "Poker Bros",
        "clubgg": "Club GG",
        "xpoker": "X Poker",
    }
    return labels.get(network, "")


def _network_overlay_color(network: str) -> str:
    colors = {
        "pppoker": "rgba(111, 206, 135, .18)",
        "pokerbros": "rgba(239, 176, 106, .18)",
        "clubgg": "rgba(228, 123, 133, .18)",
        "xpoker": "rgba(141, 198, 255, .18)",
    }
    return colors.get(network, "rgba(255,255,255,.10)")

def render_public_card(table: dict) -> str:
    table_id = int(table.get("id", 0))
    game = _game_label(table.get("game", "NLH"))

    club_name = escape(_safe(table.get("club", "")))
    table_name = escape(_safe(table.get("table_name", table.get("club", ""))))
    union_name_raw = _safe(table.get("union_name", "")).strip()
    union_name = escape(union_name_raw if union_name_raw else "—")

    blinds = escape(_safe(table.get("blinds", "")))
    buyin = escape(_safe(table.get("buyin", "")))
    players_raw = _safe(table.get("players", "-")).strip()
    seats_raw = _safe(table.get("seats", "6")).strip()
    tags_raw = _safe(table.get("tags", ""))

    network = _network_from_table(table)
    network_label = _network_label(network)
    overlay_color = _network_overlay_color(network)

    affiliate_name = escape(normalize_affiliate_name(_safe(table.get("affiliate_name", OFFICIAL_AFFILIATE_NAME))))
    affiliate_telegram = escape(_safe(table.get("affiliate_telegram", "")))
    owner_name = escape(_safe(table.get("owner_name", f"{_safe(table.get('club', 'Club'))} Official")))
    owner_telegram = escape(_safe(table.get("owner_telegram", "")))

    if "/" in players_raw:
        players_badge = players_raw
    else:
        players_badge = f"{players_raw}/{seats_raw}"

    big_blind = _parse_big_blind(blinds)

    game_colors = {
        "NLH": "#57b84f",
        "PLO4": "#56739a",
        "PLO5": "#58c1d2",
        "PLO6": "#7b65c4",
    }
    game_color = game_colors.get(game, "#58c1d2")

    return f"""
    <div class="table-row"
         data-id="{table_id}"
         data-game="{escape(game)}"
         data-club="{club_name.lower()}"
         data-network="{escape(network)}"
         data-players="{escape(players_badge)}"
         data-blind="{big_blind}"
         style="
            display:grid;
            grid-template-columns:28px 758px 160px 96px;
            gap:8px;
            align-items:center;
            width:1066px;
            min-width:1066px;
            max-width:1066px;
            margin:0 0 12px 0;">

        <div style="
            width:28px;
            display:flex;
            justify-content:center;
            align-items:center;">
            <button class="fav-btn" data-table="{table_id}" style="
                width:20px;
                height:20px;
                background:none;
                border:none;
                color:#d8d8d8;
                font-size:20px;
                cursor:pointer;
                padding:0;
                line-height:1;">
                ☆
            </button>
        </div>

        <div class="glass-bar" style="
            height:78px;
            width:758px;
            min-width:758px;
            border-radius:18px;
            overflow:hidden;
            display:grid;
            grid-template-columns:42px 74px 1fr 124px;
            align-items:center;
            box-sizing:border-box;">

            <div style="
                height:100%;
                background:{game_color};
                color:#fff;
                display:flex;
                align-items:center;
                justify-content:center;
                writing-mode:vertical-rl;
                transform:rotate(180deg);
                font:700 13px Arial;
                letter-spacing:.4px;
                box-shadow:inset -1px 0 0 rgba(255,255,255,.08);">
                {escape(game)}
            </div>

            <div style="
                display:flex;
                align-items:center;
                justify-content:center;">
                <div style="
                    width:50px;
                    height:50px;
                    border-radius:50%;
                    border:4px solid {game_color};
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    color:#fff;
                    font:700 18px Arial;
                    box-shadow:0 8px 18px rgba(0,0,0,.12);">
                    {escape(players_badge)}
                </div>
            </div>

            <div style="
                position:relative;
                display:flex;
                flex-direction:column;
                justify-content:center;
                min-width:0;
                height:100%;
                padding-left:2px;">

                <div style="
                    position:absolute;
                    inset:0;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    pointer-events:none;
                    font:700 24px Arial;
                    letter-spacing:1px;
                    color:{overlay_color};
                    text-transform:uppercase;
                    user-select:none;">
                    {escape(network_label)}
                </div>

                <div style="position:relative;z-index:2;">
                    <div style="
                        font:500 13px Arial;
                        color:#f2f4f7;
                        line-height:1.05;
                        margin-bottom:5px;
                        letter-spacing:.2px;">
                        {table_name}
                    </div>
                    <div style="
                        font:600 17px Arial;
                        color:#ffffff;
                        line-height:1;">
                        {blinds}
                    </div>
                </div>
            </div>

            <div style="
                display:flex;
                flex-direction:column;
                justify-content:center;
                align-items:flex-end;
                padding-right:12px;
                box-sizing:border-box;">
                <div style="
                    font:700 10px Arial;
                    color:#f0f0f0;
                    opacity:.9;">
                    Buy-in
                </div>
                <div style="
                    font:700 16px Arial;
                    color:#fff;
                    line-height:1.05;">
                    {buyin}
                </div>
                {_render_tags(tags_raw)}
            </div>
        </div>

        <div class="glass-bar" style="
            width:160px;
            height:78px;
            border-radius:18px;
            padding:10px 12px;
            box-sizing:border-box;
            display:flex;
            flex-direction:column;
            justify-content:center;">
            <div style="
                font:700 10px Arial;
                color:#bfc5cd;
                margin-bottom:2px;">
                Club
            </div>
            <div style="
                font:700 15px 'Trebuchet MS', Arial;
                font-style:italic;
                letter-spacing:.3px;
                color:#fff;
                margin-bottom:8px;
                line-height:1.05;">
                {club_name}
            </div>

            <div style="
                font:700 10px Arial;
                color:#bfc5cd;
                margin-bottom:2px;">
                Union
            </div>
            <div style="
                font:700 15px 'Trebuchet MS', Arial;
                font-style:italic;
                letter-spacing:.3px;
                color:#fff;
                line-height:1.05;">
                {union_name}
            </div>
        </div>

        <div style="
            width:96px;
            height:78px;
            border-radius:18px;
            background:rgba(255,255,255,.08);
            border:1px solid rgba(255,255,255,.06);
            display:flex;
            align-items:center;
            justify-content:center;
            box-shadow:0 16px 32px rgba(0,0,0,.18);
            backdrop-filter:blur(8px);">
            <button
                type="button"
                class="join-open-btn join-btn-3d"
                data-club="{club_name}"
                data-table-name="{table_name}"
                data-affiliate-name="{affiliate_name}"
                data-affiliate-url="{affiliate_telegram}"
                data-owner-name="{owner_name}"
                data-owner-url="{owner_telegram}"
                style="
                    width:72px;
                    height:46px;
                    border:none;
                    border-radius:16px;
                    background:linear-gradient(180deg,#f1e1b7,#e3c77e);
                    color:#7a6340;
                    font:700 16px Arial;
                    cursor:pointer;
                    box-shadow:
                        inset 0 1px 0 rgba(255,255,255,.65),
                        0 8px 18px rgba(0,0,0,.15);">
                Join
            </button>
        </div>
    </div>
    """

# =========================
# PUBLIC PAGE SCRIPT
# =========================

def render_public_script():
    return """
    <script>
    const $ = (s) => document.querySelector(s);
    const $$ = (s) => Array.from(document.querySelectorAll(s));

    const CURRENT_USER = document.body.dataset.username || "guest";

    function userKey(base) {
        return base + "_" + CURRENT_USER;
    }

    const STORAGE_KEYS = {
        favorites: userKey("favorite_tables"),
        activeGames: userKey("active_games"),
        activeNetworks: userKey("active_networks"),
        search: userKey("club_search"),
        minBlind: userKey("blind_min_value"),
        maxBlind: userKey("blind_max_value"),
        sortPlayersDir: userKey("sort_players_dir"),
        sortBlindsDir: userKey("sort_blinds_dir"),
        sortPriority: userKey("sort_priority"),
        onlyFav: userKey("only_favorites")
    };

    let sortPlayersDir = localStorage.getItem(STORAGE_KEYS.sortPlayersDir) || "";
    let sortBlindsDir = localStorage.getItem(STORAGE_KEYS.sortBlindsDir) || "";
    let sortPriority = ["players", "blinds"];

    try {
        const savedPriority = JSON.parse(localStorage.getItem(STORAGE_KEYS.sortPriority) || "[]");
        if (Array.isArray(savedPriority) && savedPriority.length) {
            sortPriority = savedPriority;
        }
    } catch (e) {}

    let visibleCount = 15;
    const LOAD_MORE_STEP = 10;
    let showOnlyFavorites = localStorage.getItem(STORAGE_KEYS.onlyFav) === "1";

    function getRows() {
        return $$(".table-row");
    }

    function getFavorites() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEYS.favorites) || "[]");
        } catch (e) {
            return [];
        }
    }

    function setFavorites(arr) {
        localStorage.setItem(STORAGE_KEYS.favorites, JSON.stringify(arr));
    }

    function getActiveGames() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEYS.activeGames) || "[]");
        } catch (e) {
            return [];
        }
    }

    function setActiveGames(arr) {
        localStorage.setItem(STORAGE_KEYS.activeGames, JSON.stringify(arr));
    }

    function getActiveNetworks() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEYS.activeNetworks) || "[]");
        } catch (e) {
            return [];
        }
    }

    function setActiveNetworks(arr) {
        localStorage.setItem(STORAGE_KEYS.activeNetworks, JSON.stringify(arr));
    }

    function parsePlayersValue(text) {
        const s = String(text || "").trim();
        const m = s.match(/(\\d+)\\s*\\//);
        return m ? parseInt(m[1], 10) : 0;
    }

    function parseBlindValue(text) {
        const n = parseFloat(String(text || "").replace(",", "."));
        return Number.isFinite(n) ? n : 0;
    }

    function paintFavoriteStars() {
        const favs = getFavorites();

        $$(".fav-btn").forEach(btn => {
            const tableId = Number(btn.dataset.table);
            const active = favs.includes(tableId);
            btn.textContent = active ? "★" : "☆";
            btn.style.color = active ? "#efb300" : "#d8d8d8";
        });

        const topBtn = $("#favorite-only-btn");
        if (topBtn) {
            topBtn.textContent = showOnlyFavorites ? "★" : "☆";
            topBtn.style.color = showOnlyFavorites ? "#efb300" : "#d8d8d8";
        }
    }

    function paintGameButtons() {
        const activeGames = getActiveGames();

        $$(".game-filter-btn").forEach(btn => {
            const active = activeGames.includes(btn.dataset.game);
            btn.style.background = active ? btn.dataset.activeBg : btn.dataset.bg;
            btn.style.color = active ? btn.dataset.activeColor : btn.dataset.color;
            btn.style.boxShadow = active
                ? "inset 0 1px 0 rgba(255,255,255,.08), 0 10px 18px rgba(0,0,0,.16)"
                : "inset 0 1px 0 rgba(255,255,255,.05), 0 6px 14px rgba(0,0,0,.12)";
        });
    }

    function paintClubButtons() {
        const activeNetworks = getActiveNetworks();

        $$(".club-filter-btn").forEach(btn => {
            const active = activeNetworks.includes(btn.dataset.network);
            btn.style.background = active ? btn.dataset.activeBg : btn.dataset.bg;
            btn.style.color = active ? btn.dataset.activeColor : btn.dataset.color;
            btn.style.borderColor = active ? btn.dataset.activeBorder : btn.dataset.border;
            btn.style.boxShadow = active
                ? "inset 0 1px 0 rgba(255,255,255,.08), 0 10px 18px rgba(0,0,0,.18)"
                : "inset 0 1px 0 rgba(255,255,255,.03), 0 6px 14px rgba(0,0,0,.12)";
        });
    }

    function cycleDir(dir) {
        if (!dir) return "desc";
        if (dir === "desc") return "asc";
        return "";
    }

    function touchPriority(key) {
        sortPriority = [key].concat(sortPriority.filter(k => k !== key));
    }

    function restoreInputs() {
        const searchEl = $("#club-search");
        const minEl = $("#blinds-min");
        const maxEl = $("#blinds-max");

        if (searchEl) searchEl.value = localStorage.getItem(STORAGE_KEYS.search) || "";
        if (minEl) minEl.value = localStorage.getItem(STORAGE_KEYS.minBlind) || "";
        if (maxEl) maxEl.value = localStorage.getItem(STORAGE_KEYS.maxBlind) || "";
    }

    function saveInputs() {
        const searchEl = $("#club-search");
        const minEl = $("#blinds-min");
        const maxEl = $("#blinds-max");

        if (searchEl) localStorage.setItem(STORAGE_KEYS.search, searchEl.value || "");
        if (minEl) localStorage.setItem(STORAGE_KEYS.minBlind, minEl.value || "");
        if (maxEl) localStorage.setItem(STORAGE_KEYS.maxBlind, maxEl.value || "");

        localStorage.setItem(STORAGE_KEYS.onlyFav, showOnlyFavorites ? "1" : "0");
        localStorage.setItem(STORAGE_KEYS.sortPlayersDir, sortPlayersDir);
        localStorage.setItem(STORAGE_KEYS.sortBlindsDir, sortBlindsDir);
        localStorage.setItem(STORAGE_KEYS.sortPriority, JSON.stringify(sortPriority));
    }

    function sortRows(rows) {
        const activeSorts = sortPriority.filter(key => {
            if (key === "players") return !!sortPlayersDir;
            if (key === "blinds") return !!sortBlindsDir;
            return false;
        });

        if (!activeSorts.length) return rows;

        rows.sort((a, b) => {
            for (const key of activeSorts) {
                let cmp = 0;

                if (key === "players" && sortPlayersDir) {
                    const ap = parsePlayersValue(a.dataset.players);
                    const bp = parsePlayersValue(b.dataset.players);
                    cmp = sortPlayersDir === "asc" ? ap - bp : bp - ap;
                }

                if (key === "blinds" && sortBlindsDir) {
                    const ab = parseBlindValue(a.dataset.blind);
                    const bb = parseBlindValue(b.dataset.blind);
                    cmp = sortBlindsDir === "asc" ? ab - bb : bb - ab;
                }

                if (cmp !== 0) return cmp;
            }
            return 0;
        });

        return rows;
    }

    function applyAll() {
        saveInputs();

        const rows = getRows();
        const search = ($("#club-search")?.value || "").trim().toLowerCase();
        const minBlindRaw = $("#blinds-min")?.value || "";
        const maxBlindRaw = $("#blinds-max")?.value || "";
        const minBlind = parseBlindValue(minBlindRaw);
        const maxBlind = parseBlindValue(maxBlindRaw);
        const activeGames = getActiveGames();
        const activeNetworks = getActiveNetworks();
        const favorites = getFavorites();

        rows.forEach(row => {
            const club = row.dataset.club || "";
            const game = row.dataset.game || "";
            const network = row.dataset.network || "";
            const bigBlind = parseBlindValue(row.dataset.blind);
            const tableId = Number(row.dataset.id);

            let visible = true;

            if (search && !club.includes(search)) visible = false;
            if (activeGames.length && !activeGames.includes(game)) visible = false;
            if (activeNetworks.length && !activeNetworks.includes(network)) visible = false;
            if (minBlindRaw !== "" && bigBlind < minBlind) visible = false;
            if (maxBlindRaw !== "" && bigBlind > maxBlind) visible = false;
            if (showOnlyFavorites && !favorites.includes(tableId)) visible = false;

            row.dataset.visible = visible ? "1" : "0";
            row.style.display = "none";
        });

        let filtered = rows.filter(r => r.dataset.visible === "1");
        filtered = sortRows(filtered);

        const wrap = $("#tables-wrap");
        filtered.forEach(r => wrap.appendChild(r));

        filtered.slice(0, visibleCount).forEach(r => {
            r.style.display = "grid";
        });

        const loadWrap = $("#load-more-wrap");
        if (loadWrap) {
            loadWrap.style.display = filtered.length > visibleCount ? "flex" : "none";
        }
    }

    function setJoinLink(el, url) {
        if (!el) return;
        if (url && url.trim() && url.trim() !== "#") {
            el.href = url;
            el.style.pointerEvents = "auto";
            el.style.opacity = "1";
        } else {
            el.href = "#";
            el.style.pointerEvents = "none";
            el.style.opacity = ".45";
        }
    }

    function openJoinModal(btn) {
        const overlay = $("#join-modal-overlay");
        if (!overlay) return;

        const club = btn.dataset.club || "";
        const tableName = btn.dataset.tableName || "";
        const affiliateName = btn.dataset.affiliateName || "TableRadar Official";
        const affiliateUrl = btn.dataset.affiliateUrl || "";
        const ownerName = btn.dataset.ownerName || (club ? club + " Official" : "Club Official");
        const ownerUrl = btn.dataset.ownerUrl || "";

        $("#join-club-title").textContent = tableName ? (tableName + " · " + club) : club;
        $("#join-affiliate-name").textContent = affiliateName;
        $("#join-owner-name").textContent = ownerName;

        $("#join-affiliate-tip").textContent =
            affiliateName + " is responsible for deposits, payouts and winnings.";

        $("#join-owner-tip").textContent =
            ownerName + ": you deal directly with the club owner. We are not responsible for deposits, payouts or winnings.";

        setJoinLink($("#join-affiliate-link"), affiliateUrl);
        setJoinLink($("#join-owner-link"), ownerUrl);

        overlay.style.display = "flex";
    }

    function closeJoinModal() {
        const overlay = $("#join-modal-overlay");
        if (overlay) overlay.style.display = "none";
    }

    document.addEventListener("click", function(e) {
        const joinBtn = e.target.closest(".join-open-btn");
        if (joinBtn) {
            openJoinModal(joinBtn);
            return;
        }

        const favBtn = e.target.closest(".fav-btn");
        if (favBtn) {
            const tableId = Number(favBtn.dataset.table);
            let favs = getFavorites();

            if (favs.includes(tableId)) {
                favs = favs.filter(x => x !== tableId);
            } else {
                favs.push(tableId);
            }

            setFavorites(favs);
            paintFavoriteStars();
            applyAll();
            return;
        }

        const gameBtn = e.target.closest(".game-filter-btn");
        if (gameBtn) {
            const game = gameBtn.dataset.game;
            let activeGames = getActiveGames();

            if (activeGames.includes(game)) {
                activeGames = activeGames.filter(x => x !== game);
            } else {
                activeGames.push(game);
            }

            setActiveGames(activeGames);
            visibleCount = 15;
            paintGameButtons();
            applyAll();
            return;
        }

        const clubBtn = e.target.closest(".club-filter-btn");
        if (clubBtn) {
            const network = clubBtn.dataset.network;
            let activeNetworks = getActiveNetworks();

            if (activeNetworks.includes(network)) {
                activeNetworks = activeNetworks.filter(x => x !== network);
            } else {
                activeNetworks.push(network);
            }

            setActiveNetworks(activeNetworks);
            visibleCount = 15;
            paintClubButtons();
            applyAll();
            return;
        }

        if (e.target.id === "join-modal-overlay" || e.target.id === "join-modal-close") {
            closeJoinModal();
        }
    });

    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape") {
            closeJoinModal();
        }
    });

    $("#favorite-only-btn")?.addEventListener("click", function() {
        showOnlyFavorites = !showOnlyFavorites;
        visibleCount = 15;
        paintFavoriteStars();
        applyAll();
    });

    $("#club-search")?.addEventListener("input", function() {
        visibleCount = 15;
        applyAll();
    });

    $("#blinds-min")?.addEventListener("change", function() {
        visibleCount = 15;
        applyAll();
    });

    $("#blinds-max")?.addEventListener("change", function() {
        visibleCount = 15;
        applyAll();
    });

    $("#sort-players")?.addEventListener("click", function() {
        sortPlayersDir = cycleDir(sortPlayersDir);
        touchPriority("players");
        visibleCount = 15;
        applyAll();
    });

    $("#sort-blinds")?.addEventListener("click", function() {
        sortBlindsDir = cycleDir(sortBlindsDir);
        touchPriority("blinds");
        visibleCount = 15;
        applyAll();
    });

    $("#load-more-btn")?.addEventListener("click", function() {
        visibleCount += LOAD_MORE_STEP;
        applyAll();
    });

    restoreInputs();
    paintFavoriteStars();
    paintGameButtons();
    paintClubButtons();
    applyAll();
    </script>
    """


# =========================
# PUBLIC PAGE
# =========================

def render_public_page(tables, request=None):
    username = None
    user_email = None
    plan = "inactive"
    is_active = False

    if request:
        try:
            username = request.session.get("username")
            user_email = request.session.get("user_email")
            plan = str(request.session.get("plan", "inactive")).lower()
            is_active = str(request.session.get("is_active", "0")) in ("1", "true", "True")
        except:
            username = None
            user_email = None
            plan = "inactive"
            is_active = False

    display_name = user_email or username or ""

    cards = "".join(render_public_card(t) for t in tables)

    if not cards:
        cards = """
        <div style="
            background:rgba(255,255,255,.10);
            border-radius:18px;
            padding:18px;
            color:#ddd;
            width:1066px;
            min-width:1066px;
            box-sizing:border-box;
            backdrop-filter:blur(10px);
            border:1px solid rgba(255,255,255,.08);
            box-shadow:0 18px 40px rgba(0,0,0,.22);">
            No tables available
        </div>
        """

    if username:
        if plan == "host" and is_active:
            plan_button = """
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
                Host
            </span>
            """
        elif plan == "player" and is_active:
            plan_button = """
            <a href="/profile" style="
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
                text-decoration:none;
                font:700 14px Arial;
                box-sizing:border-box;
                box-shadow:0 8px 18px rgba(0,0,0,.16);">
                Player
            </a>
            """
        else:
            plan_button = """
            <a href="/profile" style="
                display:inline-flex;
                align-items:center;
                justify-content:center;
                min-width:118px;
                height:38px;
                padding:0 16px;
                border:1.5px solid #3fae5a;
                border-radius:999px;
                color:#6fce87;
                background:rgba(14,33,18,.82);
                text-decoration:none;
                font:700 14px Arial;
                box-sizing:border-box;
                box-shadow:0 8px 18px rgba(0,0,0,.16);">
                Upgrade
            </a>
            """

        right_top_html = f"""
        <div style="display:flex;align-items:center;gap:12px;">
            {plan_button}

            <div id="profile-menu-wrap" style="position:relative;">
                <div id="profile-menu-btn" style="
                    background:rgba(255,255,255,.08);
                    border:1px solid rgba(255,255,255,.08);
                    border-radius:16px;
                    padding:10px 16px;
                    color:#fff;
                    font:700 15px Arial;
                    cursor:pointer;
                    display:flex;
                    align-items:center;
                    gap:10px;
                    min-width:220px;
                    justify-content:flex-start;
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
                        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="#fff1f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M20 21a8 8 0 0 0-16 0"></path>
                            <circle cx="12" cy="7" r="4"></circle>
                        </svg>
                    </span>

                    <span>{escape(display_name)}</span>
                </div>

                <div id="profile-dropdown" style="
                    display:none;
                    position:absolute;
                    right:0;
                    top:44px;
                    width:230px;
                    background:rgba(23,26,31,.96);
                    border:1px solid rgba(255,255,255,.08);
                    border-radius:16px;
                    padding:8px 0;
                    box-shadow:0 16px 34px rgba(0,0,0,.35);
                    z-index:999;
                    backdrop-filter:blur(10px);">
                    <a href="/profile" style="
                        display:block;
                        padding:12px 16px;
                        color:#fff;
                        text-decoration:none;
                        font:700 14px Arial;">
                        Profile
                    </a>
                    <a href="/faq" style="
                        display:block;
                        padding:12px 16px;
                        color:#fff;
                        text-decoration:none;
                        font:700 14px Arial;">
                        FAQ
                    </a>
                    <a href="/contact" style="
                        display:block;
                        padding:12px 16px;
                        color:#fff;
                        text-decoration:none;
                        font:700 14px Arial;">
                        Contact us
                    </a>
                    <a href="/terms" style="
                        display:block;
                        padding:12px 16px;
                        color:#fff;
                        text-decoration:none;
                        font:700 14px Arial;">
                        Terms & Conditions
                    </a>
                    <a href="/logout" style="
                        display:block;
                        padding:12px 16px;
                        color:#fff;
                        text-decoration:none;
                        font:700 14px Arial;">
                        Logout
                    </a>
                </div>
            </div>
        </div>
        """
    else:
        right_top_html = """
        <a href="/signin_login" style="
            display:inline-flex;
            align-items:center;
            justify-content:center;
            min-width:120px;
            height:54px;
            padding:0 22px;
            border:2px solid #ff7a2f;
            border-radius:4px;
            color:#ff7a2f;
            background:rgba(0,0,0,.18);
            text-decoration:none;
            font:700 18px Arial;
            box-sizing:border-box;
            box-shadow:0 10px 24px rgba(0,0,0,.18);">
            Sign In
        </a>
        """          

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>TableRadar</title>
        <meta http-equiv="refresh" content="30">
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

            .orb-a {{
                width: 420px;
                height: 420px;
                top: 70px;
                left: -80px;
                background: #5ac8fa;
            }}

            .orb-b {{
                width: 360px;
                height: 360px;
                top: 180px;
                right: 120px;
                background: #7b65c4;
            }}

            .orb-c {{
                width: 420px;
                height: 420px;
                bottom: -120px;
                left: 30%;
                background: #57b84f;
            }}

            .page-shell {{
                position: relative;
                z-index: 2;
            }}

            .glass-bar {{
                background: linear-gradient(180deg, rgba(255,255,255,.12), rgba(255,255,255,.06));
                border: 1px solid rgba(255,255,255,.08);
                box-shadow: 0 18px 42px rgba(0,0,0,.22);
                backdrop-filter: blur(12px);
            }}

            .table-row {{
                transition: transform .16s ease, box-shadow .16s ease;
            }}

            .table-row:hover {{
                transform: translateY(-2px);
            }}

            .game-filter-btn:hover,
            .club-filter-btn:hover {{
                transform: translateY(-1px);
            }}

            .fav-btn {{
                transition: transform .12s ease;
            }}

            .fav-btn:hover {{
                transform: scale(1.12);
            }}

            .join-btn-3d {{
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.75),
                    0 8px 18px rgba(0,0,0,.15);
                transition: transform .12s ease, box-shadow .12s ease;
            }}

            .join-btn-3d:hover {{
                transform: translateY(-1px);
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.75),
                    0 12px 22px rgba(0,0,0,.18);
            }}

            #profile-dropdown a:hover {{
                background: rgba(255,255,255,.05);
            }}

            .join-help-wrap {{
                position:relative;
                display:inline-flex;
                align-items:center;
            }}

            .join-help-tip {{
                display:none;
                position:absolute;
                top:24px;
                left:0;
                width:260px;
                padding:10px 12px;
                border-radius:12px;
                background:rgba(18,20,24,.98);
                color:#f0f0f0;
                font:600 12px Arial;
                line-height:1.45;
                box-shadow:0 14px 28px rgba(0,0,0,.24);
                border:1px solid rgba(255,255,255,.08);
                z-index:30;
            }}

            .join-help-wrap:hover .join-help-tip {{
                display:block;
            }}
        </style>
    </head>
    <body data-username="{escape(display_name if display_name else 'guest')}" style="
        margin:0;
        background:
            radial-gradient(circle at 14% 18%, rgba(91,199,255,.20), transparent 26%),
            radial-gradient(circle at 86% 20%, rgba(123,101,196,.16), transparent 24%),
            radial-gradient(circle at 50% 100%, rgba(87,184,79,.16), transparent 28%),
            linear-gradient(135deg,#12171b 0%, #0f1217 38%, #131922 100%);
        color:#fff;
        font-family:Arial,sans-serif;
        min-height:100vh;
        padding:24px;
        box-sizing:border-box;">

        <div class="bg-orb orb-a"></div>
        <div class="bg-orb orb-b"></div>
        <div class="bg-orb orb-c"></div>

        <div class="page-shell">

            <div style="
    width:100%;
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    margin-bottom:18px;">

    {render_brand_logo("/")}

    {right_top_html}
</div>

            <div style="
                width:1066px;
                min-width:1066px;
                max-width:1066px;
                margin:0 auto;">

                <div style="
                    display:grid;
                    grid-template-columns:28px 1030px;
                    gap:8px;
                    align-items:center;
                    margin-bottom:12px;
                    width:1066px;
                    min-width:1066px;">

                    <div style="
                        width:28px;
                        display:flex;
                        justify-content:center;">
                        <button id="favorite-only-btn" type="button" title="Favorite" style="
                            width:20px;
                            height:20px;
                            background:none;
                            border:none;
                            color:#d7d7d7;
                            cursor:pointer;
                            font-size:20px;
                            padding:0;
                            display:flex;
                            align-items:center;
                            justify-content:center;">
                            ☆
                        </button>
                    </div>

                    <div class="glass-bar" style="
                        width:1030px;
                        min-width:1030px;
                        border-radius:20px;
                        padding:12px 14px;
                        display:grid;
                        grid-template-columns:170px 250px 96px;
                        justify-content:space-between;
                        align-items:center;
                        box-sizing:border-box;">

                        <div style="
                            width:170px;
                            display:grid;
                            grid-template-columns:repeat(2, 74px);
                            gap:8px 8px;
                            justify-content:start;">
                            {game_button("NLH")}
                            {game_button("PLO4")}
                            {game_button("PLO5")}
                            {game_button("PLO6")}
                        </div>

                        <div style="
                            width:250px;
                            display:grid;
                            grid-template-columns:repeat(2, 116px);
                            gap:8px 10px;
                            justify-content:center;">
                            {club_filter_button("PP Poker", "pppoker")}
                            {club_filter_button("Poker Bros", "pokerbros")}
                            {club_filter_button("Club GG", "clubgg")}
                            {club_filter_button("X Poker", "xpoker")}
                        </div>

                        <div style="
                            width:96px;
                            display:grid;
                            grid-template-columns:1fr;
                            gap:8px;
                            justify-items:end;">
                            {blinds_select("blinds-min", "MIN")}
                            {blinds_select("blinds-max", "MAX")}
                        </div>
                    </div>
                </div>

                <div style="
                    display:grid;
                    grid-template-columns:28px 1030px;
                    gap:8px;
                    align-items:center;
                    margin-bottom:14px;
                    width:1066px;
                    min-width:1066px;">

                    <div></div>

                    <div style="
                        width:1030px;
                        min-width:1030px;
                        box-sizing:border-box;">
                        <input id="club-search" type="text" placeholder="Search club" style="
                            width:100%;
                            padding:12px 14px;
                            border:none;
                            border-radius:12px;
                            box-sizing:border-box;
                            background:rgba(243,238,230,.96);
                            color:#111;
                            font-size:14px;
                            box-shadow:0 10px 26px rgba(0,0,0,.18);">
                    </div>
                </div>

                <div style="
                    display:grid;
                    grid-template-columns:28px 112px 850px 96px;
                    gap:8px;
                    align-items:end;
                    margin:0 0 6px 0;
                    color:#f4efe9;
                    font-size:12px;
                    font-weight:700;
                    width:1066px;
                    min-width:1066px;">
                    <div></div>
                    <div id="sort-players" style="
                        cursor:pointer;
                        text-align:left;
                        padding-left:28px;">
                        Players ↕
                    </div>
                    <div id="sort-blinds" style="
                        cursor:pointer;
                        text-align:left;">
                        Blinds ↕
                    </div>
                    <div></div>
                </div>

                <div id="tables-wrap" style="
                    width:1066px;
                    min-width:1066px;">
                    {cards}
                </div>

                <div id="load-more-wrap" style="
                    display:none;
                    justify-content:center;
                    margin:18px 0 8px 0;
                    width:1066px;">
                    <button id="load-more-btn" class="glass-bar" style="
                        min-width:190px;
                        height:42px;
                        border:none;
                        border-radius:14px;
                        color:#fff;
                        font:700 14px Arial;
                        cursor:pointer;">
                        Load more tables
                    </button>
                </div>
            </div>
        </div>

        <div id="join-modal-overlay" style="
    display:none;
    position:fixed;
    inset:0;
    background:rgba(0,0,0,.46);
    align-items:center;
    justify-content:center;
    z-index:1200;
    backdrop-filter:blur(4px);">

    <div class="glass-bar" id="join-modal-card" style="
        width:760px;
        max-width:calc(100vw - 60px);
        border-radius:22px;
        padding:26px;
        box-sizing:border-box;">

        <div style="
            display:flex;
            justify-content:space-between;
            align-items:flex-start;
            gap:16px;
            margin-bottom:18px;">
            <div>
                <div id="join-club-title" style="
                    font:700 32px Arial;
                    color:#fff;
                    line-height:1.1;
                    margin-bottom:8px;"></div>
                <div style="
                    font:600 14px Arial;
                    color:#d9d9d9;">
                    Choose your way to join the club
                </div>
            </div>

            <button id="join-modal-close" type="button" style="
                width:38px;
                height:38px;
                border:none;
                border-radius:10px;
                background:rgba(255,255,255,.08);
                color:#fff;
                font:700 20px Arial;
                cursor:pointer;">
                ×
            </button>
        </div>

        <div style="
            display:grid;
            grid-template-columns:1fr 1fr;
            gap:18px;">

            <div style="
                background:rgba(43,31,12,.42);
                border:1px solid rgba(223,181,86,.32);
                border-radius:18px;
                padding:22px;
                box-sizing:border-box;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <div id="join-affiliate-name" style="font:700 23px Arial;color:#d7b258;">TableRadar Official</div>

                    <div class="join-help-wrap">
                        <span style="
                            width:22px;
                            height:22px;
                            border-radius:50%;
                            background:rgba(215,178,88,.20);
                            border:1px solid rgba(215,178,88,.35);
                            color:#f0d186;
                            display:inline-flex;
                            align-items:center;
                            justify-content:center;
                            font:700 13px Arial;
                            cursor:default;">?</span>

                        <div class="join-help-tip" id="join-affiliate-tip">
                            Boom247 Official is responsible for deposits, payouts and winnings.
                        </div>
                    </div>
                </div>

                <div style="font:600 15px Arial;color:#ece2c7;line-height:1.5;margin-bottom:20px;">
                    Official affiliate of the website.
                </div>

                <a id="join-affiliate-link" href="#" target="_blank" style="
                    display:inline-flex;
                    align-items:center;
                    justify-content:center;
                    width:100%;
                    height:48px;
                    border-radius:12px;
                    background:linear-gradient(180deg,#d7b258,#ac8530);
                    color:#1e1708;
                    text-decoration:none;
                    font:700 17px Arial;
                    box-shadow:0 12px 24px rgba(0,0,0,.18);">
                    Join
                </a>
            </div>

            <div style="
                background:rgba(54,20,24,.42);
                border:1px solid rgba(207,92,106,.32);
                border-radius:18px;
                padding:22px;
                box-sizing:border-box;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <div id="join-owner-name" style="font:700 23px Arial;color:#d8757d;">Club Official</div>

                    <div class="join-help-wrap">
                        <span style="
                            width:22px;
                            height:22px;
                            border-radius:50%;
                            background:rgba(216,117,125,.18);
                            border:1px solid rgba(216,117,125,.35);
                            color:#f0c3c7;
                            display:inline-flex;
                            align-items:center;
                            justify-content:center;
                            font:700 13px Arial;
                            cursor:default;">?</span>

                        <div class="join-help-tip" id="join-owner-tip">
                            You deal directly with the club owner. We are not responsible for deposits, payouts or winnings.
                        </div>
                    </div>
                </div>

                <div style="font:600 15px Arial;color:#f1d9db;line-height:1.5;margin-bottom:20px;">
                    Direct club contact.
                </div>

                <a id="join-owner-link" href="#" target="_blank" style="
                    display:inline-flex;
                    align-items:center;
                    justify-content:center;
                    width:100%;
                    height:48px;
                    border-radius:12px;
                    background:linear-gradient(180deg,#d97a84,#b44757);
                    color:#fff3f4;
                    text-decoration:none;
                    font:700 17px Arial;
                    box-shadow:0 12px 24px rgba(0,0,0,.18);">
                    Join
                </a>
            </div>
        </div>
    </div>
</div>

        <script>
            const wrap = document.getElementById("profile-menu-wrap");
            const drop = document.getElementById("profile-dropdown");

            if (wrap && drop) {{
                wrap.addEventListener("mouseenter", function() {{
                    drop.style.display = "block";
                }});

                wrap.addEventListener("mouseleave", function() {{
                    drop.style.display = "none";
                }});
            }}
        </script>

        {render_public_script()}
    </body>
    </html>
    """

# =========================
# ADMIN PAGE
# =========================

def render_admin_card(table: dict) -> str:
    table_id = int(table.get("id", 0))
    game = _game_label(table.get("game", "NLH"))

    club_name = escape(_safe(table.get("club", "")))
    table_name = escape(_safe(table.get("table_name", table.get("club", ""))))
    union_name_raw = _safe(table.get("union_name", "")).strip()
    union_name = escape(union_name_raw if union_name_raw else "—")

    blinds = escape(_safe(table.get("blinds", "")))
    buyin = escape(_safe(table.get("buyin", "")))
    players_raw = _safe(table.get("players", "-")).strip()
    seats_raw = _safe(table.get("seats", "6")).strip()

    network = _network_from_table(table)
    network_label = _network_label(network)
    overlay_color = _network_overlay_color(network)

    affiliate_name = escape(_safe(table.get("affiliate_name", "Boom247 Official")))
    affiliate_telegram = escape(_safe(table.get("affiliate_telegram", "")))
    owner_name = escape(_safe(table.get("owner_name", f"{_safe(table.get('club', 'Club'))} Official")))
    owner_telegram = escape(_safe(table.get("owner_telegram", "")))

    if "/" in players_raw:
        players_badge = players_raw
    else:
        players_badge = f"{players_raw}/{seats_raw}"

    game_colors = {
        "NLH": "#57b84f",
        "PLO4": "#56739a",
        "PLO5": "#58c1d2",
        "PLO6": "#7b65c4",
    }
    game_color = game_colors.get(game, "#58c1d2")

    return f"""
    <div class="admin-table-card" data-club="{club_name.lower()}" style="width:760px;margin:0 0 8px 0;">

        <div class="glass-bar" style="
            border-radius:10px;
            overflow:hidden;">

            <div style="
                min-height:42px;
                display:grid;
                grid-template-columns:18px 40px 1fr 138px;
                align-items:center;">

                <div style="
                    height:100%;
                    background:{game_color};
                    color:#fff;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    writing-mode:vertical-rl;
                    transform:rotate(180deg);
                    font:700 8px Arial;
                    letter-spacing:.2px;">
                    {escape(game)}
                </div>

                <div style="
                    display:flex;
                    align-items:center;
                    justify-content:center;">
                    <div style="
                        width:30px;
                        height:30px;
                        border-radius:50%;
                        border:2px solid {game_color};
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        color:#fff;
                        font:700 10px Arial;">
                        {escape(players_badge)}
                    </div>
                </div>

                <div style="
                    position:relative;
                    display:flex;
                    flex-direction:column;
                    justify-content:center;
                    min-width:0;
                    height:100%;
                    padding:4px 0;">

                    <div style="
                        position:absolute;
                        inset:0;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        pointer-events:none;
                        font:700 12px Arial;
                        letter-spacing:1px;
                        color:{overlay_color};
                        text-transform:uppercase;
                        user-select:none;">
                        {escape(network_label)}
                    </div>

                    <div style="position:relative;z-index:2;">
                        <div style="
                            font:700 11px Arial;
                            color:#fff;
                            line-height:1;
                            margin-bottom:2px;">
                            {table_name}
                        </div>
                        <div style="
                            font:700 9px Arial;
                            color:#f2f2f2;
                            line-height:1;">
                            {club_name} · {union_name}
                        </div>
                        <div style="
                            font:700 9px Arial;
                            color:#f2f2f2;
                            line-height:1;
                            margin-top:2px;">
                            {blinds} · {buyin}
                        </div>
                    </div>
                </div>

                <div style="
                    padding:4px 6px;
                    box-sizing:border-box;
                    display:flex;
                    align-items:center;
                    justify-content:flex-end;
                    gap:4px;">

                    <form method="post" action="/update_players" style="display:flex;gap:4px;align-items:center;">
                        <input type="hidden" name="table_id" value="{table_id}">
                        <input name="players" value="{escape(players_raw)}" style="
                            width:54px;
                            padding:5px 6px;
                            border:none;
                            border-radius:7px;
                            font:600 10px Arial;">
                        <button type="submit" style="
                            padding:5px 8px;
                            border:none;
                            border-radius:7px;
                            background:#3498db;
                            color:#fff;
                            font:700 9px Arial;
                            cursor:pointer;">
                            Update
                        </button>
                    </form>

                    <form method="post" action="/delete" onsubmit="return confirm('Delete this table?')">
                        <input type="hidden" name="table_id" value="{table_id}">
                        <button type="submit" style="
                            padding:5px 10px;
                            border:none;
                            border-radius:7px;
                            background:#c0392b;
                            color:#fff;
                            font:700 9px Arial;
                            cursor:pointer;">
                            Delete
                        </button>
                    </form>
                </div>
            </div>

            <div style="
                border-top:1px solid rgba(255,255,255,.06);
                padding:4px 8px 5px 58px;
                box-sizing:border-box;">

                <div style="
                    display:grid;
                    grid-template-columns:1fr 1fr;
                    gap:4px 10px;">

                    <div style="
                        min-width:0;
                        color:#d7b258;
                        font:600 8.5px Arial;
                        line-height:1.2;
                        overflow:hidden;
                        text-overflow:ellipsis;
                        white-space:nowrap;">
                        <b>Affiliate:</b> {affiliate_name} · <b>TG:</b> {affiliate_telegram if affiliate_telegram else "—"}
                    </div>

                    <div style="
                        min-width:0;
                        color:#d97a84;
                        font:600 8.5px Arial;
                        line-height:1.2;
                        overflow:hidden;
                        text-overflow:ellipsis;
                        white-space:nowrap;">
                        <b>Club official:</b> {owner_name} · <b>TG:</b> {owner_telegram if owner_telegram else "—"}
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

def render_admin_page(tables):
    cards = "".join(render_admin_card(t) for t in tables)

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Admin</title>
        <style>
            .admin-pick-btn {{
                min-width:84px;
                height:28px;
                border:none;
                border-radius:9px;
                background:#4a515b;
                color:#eef2f5;
                font:700 12px Arial;
                cursor:pointer;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.05),
                    0 6px 14px rgba(0,0,0,.12);
                transition:all .12s ease;
            }}

            .admin-pick-btn:hover {{
                transform:translateY(-1px);
            }}

            .admin-pick-btn.active {{
                background:#636d78;
                color:#fff;
            }}

            .admin-network-btn.network-pppoker.active {{
                background:rgba(34,68,42,.98);
                color:#f0fff3;
                border:1px solid rgba(119,226,140,.82);
            }}

            .admin-network-btn.network-pokerbros.active {{
                background:rgba(88,56,28,.98);
                color:#fff6eb;
                border:1px solid rgba(255,191,119,.82);
            }}

            .admin-network-btn.network-clubgg.active {{
                background:rgba(101,34,40,.98);
                color:#fff0f2;
                border:1px solid rgba(255,126,137,.82);
            }}

            .admin-network-btn.network-xpoker.active {{
                background:rgba(42,68,103,.98);
                color:#eef8ff;
                border:1px solid rgba(153,205,255,.82);
            }}

            .admin-tag-btn.active {{
                background:#2f8f46;
                color:#eef8f0;
            }}

            .glass-bar {{
                background: linear-gradient(180deg, rgba(255,255,255,.12), rgba(255,255,255,.06));
                border: 1px solid rgba(255,255,255,.08);
                box-shadow: 0 18px 42px rgba(0,0,0,.22);
                backdrop-filter: blur(12px);
            }}
        </style>
    </head>
    <body style="
        margin:0;
        background:#111;
        color:#fff;
        font-family:Arial,sans-serif;
        padding:12px;">

<div style="
    max-width:1300px;
    margin:0 auto 14px auto;
    display:flex;
    justify-content:flex-start;
    align-items:center;">
    {render_brand_logo("/")}
</div>

        <div style="
            max-width:1300px;
            margin:0 auto;
            display:grid;
            grid-template-columns:480px 760px;
            gap:14px;
            align-items:start;">

            <div class="glass-bar" style="
                border-radius:14px;
                padding:12px;">

                <div style="
                    font-size:18px;
                    font-weight:800;
                    margin-bottom:3px;">
                    Add new table
                </div>

                <div style="
                    color:#c9ced6;
                    font:600 12px Arial;
                    margin-bottom:10px;">
                    Quick add form
                </div>

                <form method="post" action="/add" id="admin-add-form">
                    <input type="hidden" name="game" id="admin-game-input">
                    <input type="hidden" name="network" id="admin-network-input">
                    <input type="hidden" name="tags" id="admin-tags-input">

                    <div style="
                        display:grid;
                        grid-template-columns:1fr 1fr;
                        gap:12px;">

                        <div>
                            <div style="font:700 12px Arial;margin-bottom:4px;">Club name</div>
                            <input id="admin-club-input" name="club" placeholder="Club name" style="
                                width:100%;
                                box-sizing:border-box;
                                padding:8px 10px;
                                border:none;
                                border-radius:8px;
                                font:600 12px Arial;
                                margin-bottom:8px;">

                            <div style="font:700 12px Arial;margin-bottom:4px;">Table name</div>
                            <input name="table_name" placeholder="Table name" style="
                                width:100%;
                                box-sizing:border-box;
                                padding:8px 10px;
                                border:none;
                                border-radius:8px;
                                font:600 12px Arial;
                                margin-bottom:8px;">

                            <div style="font:700 12px Arial;margin-bottom:4px;">Union name</div>
                            <input name="union_name" placeholder="Union name" style="
                                width:100%;
                                box-sizing:border-box;
                                padding:8px 10px;
                                border:none;
                                border-radius:8px;
                                font:600 12px Arial;
                                margin-bottom:8px;">

                            <div style="font:700 12px Arial;margin-bottom:4px;">Blinds</div>
                            <input name="blinds" placeholder="Blinds" style="
                                width:100%;
                                box-sizing:border-box;
                                padding:8px 10px;
                                border:none;
                                border-radius:8px;
                                font:600 12px Arial;
                                margin-bottom:8px;">

                            <div style="font:700 12px Arial;margin-bottom:4px;">Buy-in</div>
                            <input name="buyin" placeholder="Buy-in" style="
                                width:100%;
                                box-sizing:border-box;
                                padding:8px 10px;
                                border:none;
                                border-radius:8px;
                                font:600 12px Arial;
                                margin-bottom:8px;">

                            <div style="font:700 12px Arial;margin-bottom:4px;">Players</div>
                            <input name="players" placeholder="Players (ex. 4/6)" style="
                                width:100%;
                                box-sizing:border-box;
                                padding:8px 10px;
                                border:none;
                                border-radius:8px;
                                font:600 12px Arial;">
                        </div>

                        <div>
                            <div style="font:700 12px Arial;margin-bottom:4px;">Affiliate name</div>
                            <input name="affiliate_name" value="TableRadar Official" placeholder="Affiliate name" style="
                                width:100%;
                                box-sizing:border-box;
                                padding:8px 10px;
                                border:none;
                                border-radius:8px;
                                font:600 12px Arial;
                                margin-bottom:8px;">

                            <div style="font:700 12px Arial;margin-bottom:4px;">Affiliate Telegram URL</div>
                            <input name="affiliate_telegram" placeholder="https://t.me/boom247official" style="
                                width:100%;
                                box-sizing:border-box;
                                padding:8px 10px;
                                border:none;
                                border-radius:8px;
                                font:600 12px Arial;
                                margin-bottom:8px;">

                            <div style="font:700 12px Arial;margin-bottom:4px;">Club official name</div>
                            <input id="admin-owner-input" name="owner_name" placeholder="Club owner name" style="
                                width:100%;
                                box-sizing:border-box;
                                padding:8px 10px;
                                border:none;
                                border-radius:8px;
                                font:600 12px Arial;
                                margin-bottom:8px;">

                            <div style="font:700 12px Arial;margin-bottom:4px;">Club Telegram URL</div>
                            <input name="owner_telegram" placeholder="https://t.me/playaofficial" style="
                                width:100%;
                                box-sizing:border-box;
                                padding:8px 10px;
                                border:none;
                                border-radius:8px;
                                font:600 12px Arial;">
                        </div>
                    </div>

                    <div style="margin-top:10px;">
                        <div style="font:700 12px Arial;margin-bottom:4px;">Application</div>
                        <div style="display:grid;grid-template-columns:repeat(2,84px);gap:6px 6px;margin-bottom:8px;">
                            <button type="button" class="admin-pick-btn admin-network-btn network-pppoker" data-value="pppoker">PP Poker</button>
                            <button type="button" class="admin-pick-btn admin-network-btn network-pokerbros" data-value="pokerbros">Poker Bros</button>
                            <button type="button" class="admin-pick-btn admin-network-btn network-clubgg" data-value="clubgg">Club GG</button>
                            <button type="button" class="admin-pick-btn admin-network-btn network-xpoker" data-value="xpoker">X Poker</button>
                        </div>

                       <div style="font:700 12px Arial;margin-bottom:4px;">Tags</div>
<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;">
    <button type="button" class="admin-pick-btn admin-tag-btn" data-value="vpip 30%">VPIP 30%</button>
    <button type="button" class="admin-pick-btn admin-tag-btn" data-value="vpip 35%">VPIP 35%</button>
    <button type="button" class="admin-pick-btn admin-tag-btn" data-value="vpip 40%">VPIP 40%</button>
    <button type="button" class="admin-pick-btn admin-tag-btn" data-value="vpip 45%">VPIP 45%</button>
    <button type="button" class="admin-pick-btn admin-tag-btn" data-value="vpip 50%">VPIP 50%</button>
    <button type="button" class="admin-pick-btn admin-tag-btn" data-value="vpip 55%">VPIP 55%</button>
    <button type="button" class="admin-pick-btn admin-tag-btn" data-value="vpip 60%">VPIP 60%</button>

    <button type="button" class="admin-pick-btn admin-tag-btn" data-value="bomb">💣</button>
    <button type="button" class="admin-pick-btn admin-tag-btn" data-value="clock">⏱</button>
</div>

                        <div style="font:700 12px Arial;margin-bottom:4px;">Game format</div>
                        <div style="display:grid;grid-template-columns:repeat(2,84px);gap:6px 6px;">
                            <button type="button" class="admin-pick-btn admin-game-btn" data-value="NLH">NLH</button>
                            <button type="button" class="admin-pick-btn admin-game-btn" data-value="PLO4">PLO4</button>
                            <button type="button" class="admin-pick-btn admin-game-btn" data-value="PLO5">PLO5</button>
                            <button type="button" class="admin-pick-btn admin-game-btn" data-value="PLO6">PLO6</button>
                        </div>
                    </div>

                    <div style="
                        margin-top:10px;
                        display:flex;
                        justify-content:space-between;
                        align-items:flex-end;
                        gap:10px;">

                        <button type="submit" style="
                            padding:8px 14px;
                            border:none;
                            border-radius:8px;
                            background:#2ecc71;
                            color:#fff;
                            font:700 12px Arial;
                            cursor:pointer;">
                            Add table
                        </button>

                        <div style="
                            color:#c9ced6;
                            font:600 10px Arial;
                            line-height:1.35;
                            text-align:right;
                            max-width:220px;">
                            Your Telegram channel goes into <b>Affiliate Telegram URL</b>.<br>
                            Club owner's Telegram goes into <b>Club Telegram URL</b>.
                        </div>
                    </div>
                </form>
            </div>

            <div>
                <div class="glass-bar" style="
                    border-radius:12px;
                    padding:10px 12px;
                    margin-bottom:10px;">

                    <div style="
                        display:flex;
                        justify-content:flex-end;
                        align-items:center;
                        gap:8px;">
                        <div style="
                            font:700 11px Arial;
                            color:#d6dde4;">
                            Search club
                        </div>
                        <input id="admin-club-search" placeholder="Type club name" style="
                            width:220px;
                            box-sizing:border-box;
                            padding:8px 10px;
                            border:none;
                            border-radius:8px;
                            font:600 11px Arial;">
                    </div>
                </div>

                {cards}
            </div>
        </div>

        <script>
            (function() {{
                const gameInput = document.getElementById("admin-game-input");
                const networkInput = document.getElementById("admin-network-input");
                const tagsInput = document.getElementById("admin-tags-input");
                const clubInput = document.getElementById("admin-club-input");
                const ownerInput = document.getElementById("admin-owner-input");
                const clubSearch = document.getElementById("admin-club-search");

                let selectedTags = [];

                function syncTags() {{
                    tagsInput.value = selectedTags.join(",");
                }}

                document.querySelectorAll(".admin-game-btn").forEach(btn => {{
                    btn.addEventListener("click", function() {{
                        document.querySelectorAll(".admin-game-btn").forEach(b => b.classList.remove("active"));
                        btn.classList.add("active");
                        gameInput.value = btn.dataset.value;
                    }});
                }});

                document.querySelectorAll(".admin-network-btn").forEach(btn => {{
                    btn.addEventListener("click", function() {{
                        document.querySelectorAll(".admin-network-btn").forEach(b => b.classList.remove("active"));
                        btn.classList.add("active");
                        networkInput.value = btn.dataset.value;
                    }});
                }});

                document.querySelectorAll(".admin-tag-btn").forEach(btn => {{
                    btn.addEventListener("click", function() {{
                        const value = btn.dataset.value;
                        if (selectedTags.includes(value)) {{
                            selectedTags = selectedTags.filter(v => v !== value);
                            btn.classList.remove("active");
                        }} else {{
                            selectedTags.push(value);
                            btn.classList.add("active");
                        }}
                        syncTags();
                    }});
                }});

                clubInput?.addEventListener("input", function() {{
                    if (!ownerInput.dataset.touched) {{
                        const v = clubInput.value.trim();
                        ownerInput.value = v ? v + " Official" : "";
                    }}
                }});

                ownerInput?.addEventListener("input", function() {{
                    ownerInput.dataset.touched = "1";
                }});

                clubSearch?.addEventListener("input", function() {{
                    const q = clubSearch.value.trim().toLowerCase();
                    document.querySelectorAll(".admin-table-card").forEach(card => {{
                        const club = card.dataset.club || "";
                        card.style.display = (!q || club.includes(q)) ? "" : "none";
                    }});
                }});
            }})();
        </script>
    </body>
    </html>
    """