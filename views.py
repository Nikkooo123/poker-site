from player_access import directory_access, render_trial_notice, enabled as trial_enabled, remaining as trial_remaining
from directory_preferences import saved_filters
import json
import secrets
from currency_codes import normalize_currency, currency_badge
from table_features import FEATURES, PRIMARY_FEATURES, render_feature_icon, feature_buttons, render_vpip_badge
from brand import BRAND_NAME, OFFICIAL_AFFILIATE_NAME, TELEGRAM_URL, render_brand_logo, normalize_affiliate_name, render_site_theme, render_site_footer
from html import escape
from auth.profile_view import render_account_menu
import re


def _safe(value, default=""):
    if value is None:
        return default
    return str(value)


def minimum_buyin(value):
    text = _safe(value).strip()
    match = re.fullmatch(r"([£$€]?\s*\d[\d,]*(?:\.\d+)?)\s*(?:[-–—]|to)\s*[£$€]?\s*\d[\d,]*(?:\.\d+)?", text, re.IGNORECASE)
    return match.group(1).strip() if match else text


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
    raw = _safe(tags_raw).lower()
    selected = {token.strip() for token in raw.split(',')}
    items = []
    if 'demo' in selected:
        items.append('<span class="tr-demo-label" style="display:inline-flex;align-items:center;height:22px;padding:0 5px;border:1px solid #b9d8c855;border-radius:5px;background:#426257;color:#e5f8ed;font-size:9px;font-weight:600">Demo</span>')
    if 'vpip' in raw or 'vipip' in raw or 'vip' in raw:
        match = re.search(r'(?:vpip|vipip|vip)\s*(\d+)', raw)
        items.append(render_vpip_badge(match.group(1) if match else ''))
    items.extend(render_feature_icon(key) for key in ('bomb', 'clock') if key in raw)
    items.extend(render_feature_icon(key) for key in FEATURES if key in selected)
    if not items:
        return ''
    return '<div class="tr-feature-tags" style="width:100%;max-width:208px;margin-top:6px;display:flex;align-items:center;justify-content:flex-end;gap:4px;flex-wrap:nowrap;white-space:nowrap">'+''.join(items)+'</div>'

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
        if low in FEATURES:
            result.append(render_feature_icon(low))
        elif "vpip" in low:
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
        data-bg="#24343b"
        data-color="#eef2f5"
        data-active-bg="#3c6055"
        data-active-color="#ffffff"
        style="
            width:74px;
            height:34px;
            border:none;
            border-radius:12px;
            background:#24343b;
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
        background:#24343b;
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

def render_public_card(table: dict, show_club=False) -> str:
    if not show_club:
        # Whitelist public game metadata before rendering any HTML or data-* fields.
        table = {key: table.get(key, "") for key in ("id", "game", "blinds", "players", "seats", "tags", "network", "platform", "buyin", "currency")}
        table.update(club="***", table_name="***", union_name="", owner_name="", owner_telegram="", affiliate_name="", affiliate_telegram="")
    name_help_attrs = 'data-name-help="Register or sign in, then choose a membership or Free Trial to view table and club names." tabindex="0" aria-describedby="tr-name-tooltip" aria-label="Hidden name. Register or sign in, then choose a membership or Free Trial to view table and club names."' if not show_club else ''
    table_id = int(table.get("id", 0))
    game = _game_label(table.get("game", "NLH"))

    club_name = escape(_safe(table.get("club", "")))
    table_name = escape(_safe(table.get("table_name", table.get("club", ""))))
    union_name_raw = _safe(table.get("union_name", "")).strip()
    union_name = escape(union_name_raw if union_name_raw else "—")

    blinds = escape(_safe(table.get("blinds", "")))
    buyin = escape(minimum_buyin(table.get("buyin", "")))
    players_raw = _safe(table.get("players", "-")).strip()
    seats_raw = _safe(table.get("seats", "6")).strip()
    tags_raw = _safe(table.get("tags", ""))

    network = _network_from_table(table)
    network_label = _network_label(network)
    overlay_color = _network_overlay_color(network)

    affiliate_name = escape(normalize_affiliate_name(_safe(table.get("affiliate_name", OFFICIAL_AFFILIATE_NAME))))
    affiliate_telegram = escape(TELEGRAM_URL if affiliate_name == OFFICIAL_AFFILIATE_NAME and show_club else _safe(table.get("affiliate_telegram", "")))
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

    card = f"""
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

        <div class="tr-favorite-cell" style="
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

        <div class="glass-bar tr-game-cell" style="
            min-height:78px;
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

            <div class="tr-table-identity" style="
                position:relative;
                display:flex;
                flex-direction:column;
                justify-content:center;
                min-width:0;
                height:100%;
                padding-left:2px;">

                <div class="tr-network-label" style="
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

                <div class="tr-table-copy" style="position:relative;z-index:2;">
                    <div {name_help_attrs} style="
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
                        {blinds}{currency_badge(table.get("currency"))}
                    </div>
                </div>
            </div>

            <div style="
                display:flex;
                flex-direction:column;
                justify-content:center;
                align-items:flex-end;
                padding:5px 12px 5px 0;
                box-sizing:border-box;">
                {f'<div style="font:700 10px Arial;color:#f0f0f0;opacity:.9;">Min. buy-in</div><div style="font:700 16px Arial;color:#fff;line-height:1.05;">{buyin}</div>' if buyin else ''}
                {_render_tags(tags_raw)}
            </div>
        </div>

        <div class="glass-bar tr-club-cell" style="
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
            <div class="tr-club-name" {name_help_attrs} style="
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
            <div class="tr-union-name" style="
                font:700 15px 'Trebuchet MS', Arial;
                font-style:italic;
                letter-spacing:.3px;
                color:#fff;
                line-height:1.05;">
                {union_name}
            </div>
        </div>

        <div class="tr-join-cell" style="
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
    if not show_club:
        card = card.replace("                Join\n", "                Join 🔒\n")
        card = card.replace('class="join-open-btn join-btn-3d"', 'class="join-locked-btn" popovertarget="guest-access" title="Activate Player access to view club details and join." aria-label="Join locked — activate Player access"')
    return card

# PUBLIC PAGE SCRIPT
# =========================

def render_public_script():
    return """
    <script>
    const $ = (s) => document.querySelector(s);
    const $$ = (s) => Array.from(document.querySelectorAll(s));

    // Masked-name hints appear synchronously, outside cards to avoid clipping.
    const nameHint = document.getElementById('tr-name-tooltip');
    let nameHintTarget = null;
    function hideNameHint() { if (nameHint) nameHint.hidden = true; nameHintTarget = null; }
    function showNameHint(target) {
        if (!nameHint || !target) return;
        nameHintTarget = target;
        nameHint.textContent = target.dataset.nameHelp;
        nameHint.hidden = false;
        const box = target.getBoundingClientRect();
        const width = nameHint.offsetWidth, height = nameHint.offsetHeight;
        const left = Math.max(12, Math.min(innerWidth - width - 12, box.left + box.width / 2 - width / 2));
        const below = box.bottom + 8;
        const top = below + height <= innerHeight - 12 ? below : Math.max(12, box.top - height - 8);
        nameHint.style.left = left + 'px';
        nameHint.style.top = top + 'px';
    }
    document.addEventListener('pointerover', event => {
        const target = event.target.closest?.('[data-name-help]');
        if (target && target !== nameHintTarget) showNameHint(target);
    });
    document.addEventListener('pointerout', event => {
        const target = event.target.closest?.('[data-name-help]');
        if (target && !target.contains(event.relatedTarget)) hideNameHint();
    });
    document.addEventListener('focusin', event => {
        const target = event.target.closest?.('[data-name-help]');
        if (target) showNameHint(target);
    });
    document.addEventListener('focusout', event => { if (event.target === nameHintTarget) hideNameHint(); });
    document.addEventListener('keydown', event => { if (event.key === 'Escape') hideNameHint(); });
    window.addEventListener('scroll', hideNameHint, true);
    window.addEventListener('resize', hideNameHint);

    const CURRENT_USER = document.body.dataset.username || "guest";
    const memoryStorage = new Map();
    const filterStorage = {
        getItem(key) { try { return localStorage.getItem(key); } catch(e) { return memoryStorage.get(key) || null; } },
        setItem(key,value) { memoryStorage.set(key,String(value)); try { localStorage.setItem(key,String(value)); } catch(e) {} }
    };

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
        onlyFav: userKey("only_favorites"),
        pending: userKey("table_filters_pending"),
        visibleCount: userKey("table_visible_count")
    };

    const FILTER_CSRF = document.body.dataset.filterCsrf || "";
    let serverFilters = null;
    try { serverFilters = JSON.parse(document.body.dataset.filters || "null"); } catch(e) {}
    if (serverFilters && filterStorage.getItem(STORAGE_KEYS.pending) !== "1") {
        for (const key of ["activeGames","activeNetworks","sortPriority"]) filterStorage.setItem(STORAGE_KEYS[key],JSON.stringify(serverFilters[key]));
        for (const key of ["search","minBlind","maxBlind","sortPlayersDir","sortBlindsDir"]) filterStorage.setItem(STORAGE_KEYS[key],serverFilters[key]);
        filterStorage.setItem(STORAGE_KEYS.onlyFav,serverFilters.onlyFav ? "1" : "0");
    }
    let filtersReady = false, filterSaveTimer = null, filterSaveBusy = false;
    let lastFilterPayload = "", pendingFilterPayload = null;

    function currentFilters() {
        return {activeGames:getActiveGames(),activeNetworks:getActiveNetworks(),search:$("#club-search")?.value || "",minBlind:$("#blinds-min")?.value || "",maxBlind:$("#blinds-max")?.value || "",onlyFav:showOnlyFavorites,sortPlayersDir,sortBlindsDir,sortPriority};
    }

    async function flushFilterSave() {
        if (!FILTER_CSRF || filterSaveBusy || !pendingFilterPayload) return;
        filterSaveBusy = true;
        const payload = pendingFilterPayload;
        try {
            const response = await fetch("/account/table-filters",{method:"POST",credentials:"same-origin",keepalive:true,headers:{"Content-Type":"application/json","X-CSRF-Token":FILTER_CSRF},body:payload});
            if (!response.ok) throw new Error("Filters could not sync");
            if (pendingFilterPayload === payload) {
                pendingFilterPayload = null;
                filterStorage.setItem(STORAGE_KEYS.pending,"0");
            }
        } catch(e) {
            // Keep the browser copy and retry on the next change, visit or reconnection.
        } finally {
            filterSaveBusy = false;
            if (pendingFilterPayload && pendingFilterPayload !== payload) flushFilterSave();
        }
    }

    function queueFilterSave(force=false) {
        if (!FILTER_CSRF || !filtersReady) return;
        const payload = JSON.stringify(currentFilters());
        if (!force && payload === lastFilterPayload) return;
        lastFilterPayload = payload;
        pendingFilterPayload = payload;
        filterStorage.setItem(STORAGE_KEYS.pending,"1");
        clearTimeout(filterSaveTimer);
        filterSaveTimer = setTimeout(flushFilterSave,250);
    }
    window.addEventListener("online",flushFilterSave);
    window.addEventListener("pagehide",flushFilterSave);

    let sortPlayersDir = filterStorage.getItem(STORAGE_KEYS.sortPlayersDir) || "";
    let sortBlindsDir = filterStorage.getItem(STORAGE_KEYS.sortBlindsDir) || "";
    let sortPriority = ["players", "blinds"];

    try {
        const savedPriority = JSON.parse(filterStorage.getItem(STORAGE_KEYS.sortPriority) || "[]");
        if (Array.isArray(savedPriority) && savedPriority.length) {
            sortPriority = savedPriority;
        }
    } catch (e) {}

    const savedVisibleCount = Number(filterStorage.getItem(STORAGE_KEYS.visibleCount));
    let visibleCount = Number.isSafeInteger(savedVisibleCount) && savedVisibleCount >= 15 && savedVisibleCount <= 100000 ? savedVisibleCount : 15;
    const LOAD_MORE_STEP = 10;
    let showOnlyFavorites = filterStorage.getItem(STORAGE_KEYS.onlyFav) === "1";

    function getRows() {
        return $$(".table-row");
    }

    const defaultOrder = new Map(getRows().map((row, index) => [row, index]));

    function getFavorites() {
        try {
            return JSON.parse(filterStorage.getItem(STORAGE_KEYS.favorites) || "[]");
        } catch (e) {
            return [];
        }
    }

    function setFavorites(arr) {
        filterStorage.setItem(STORAGE_KEYS.favorites, JSON.stringify(arr));
    }

    function getActiveGames() {
        try {
            return JSON.parse(filterStorage.getItem(STORAGE_KEYS.activeGames) || "[]");
        } catch (e) {
            return [];
        }
    }

    function setActiveGames(arr) {
        filterStorage.setItem(STORAGE_KEYS.activeGames, JSON.stringify(arr));
    }

    function getActiveNetworks() {
        try {
            return JSON.parse(filterStorage.getItem(STORAGE_KEYS.activeNetworks) || "[]");
        } catch (e) {
            return [];
        }
    }

    function setActiveNetworks(arr) {
        filterStorage.setItem(STORAGE_KEYS.activeNetworks, JSON.stringify(arr));
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
            btn.setAttribute("aria-pressed", String(active));
            btn.setAttribute("aria-label", active ? "Remove table from favorites" : "Add table to favorites");
            btn.style.color = active ? "#efb300" : "#d8d8d8";
        });

        const topBtn = $("#favorite-only-btn");
        if (topBtn) {
            topBtn.textContent = showOnlyFavorites ? "★" : "☆";
            topBtn.setAttribute("aria-pressed", String(showOnlyFavorites));
            topBtn.setAttribute("aria-label", "Show favorites only");
            topBtn.style.color = showOnlyFavorites ? "#efb300" : "#d8d8d8";
        }
    }

    function paintGameButtons() {
        const activeGames = getActiveGames();

        $$(".game-filter-btn").forEach(btn => {
            const active = activeGames.includes(btn.dataset.game);
            btn.setAttribute("aria-pressed", String(active));
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
            btn.setAttribute("aria-pressed", String(active));
            btn.style.background = active ? btn.dataset.activeBg : btn.dataset.bg;
            btn.style.color = active ? btn.dataset.activeColor : btn.dataset.color;
            btn.style.borderColor = active ? btn.dataset.activeBorder : btn.dataset.border;
            btn.style.boxShadow = active
                ? "inset 0 1px 0 rgba(255,255,255,.08), 0 10px 18px rgba(0,0,0,.18)"
                : "inset 0 1px 0 rgba(255,255,255,.03), 0 6px 14px rgba(0,0,0,.12)";
        });
    }

    function cycleDir(dir) {
        return dir === "desc" ? "asc" : "desc";
    }

    function touchPriority(key) {
        sortPriority = [key].concat(sortPriority.filter(k => k !== key));
    }

    function restoreInputs() {
        const searchEl = $("#club-search");
        const minEl = $("#blinds-min");
        const maxEl = $("#blinds-max");

        if (searchEl) searchEl.value = filterStorage.getItem(STORAGE_KEYS.search) || "";
        if (minEl) minEl.value = filterStorage.getItem(STORAGE_KEYS.minBlind) || "";
        if (maxEl) maxEl.value = filterStorage.getItem(STORAGE_KEYS.maxBlind) || "";
    }

    function saveInputs() {
        const searchEl = $("#club-search");
        const minEl = $("#blinds-min");
        const maxEl = $("#blinds-max");

        if (searchEl) filterStorage.setItem(STORAGE_KEYS.search, searchEl.value || "");
        if (minEl) filterStorage.setItem(STORAGE_KEYS.minBlind, minEl.value || "");
        if (maxEl) filterStorage.setItem(STORAGE_KEYS.maxBlind, maxEl.value || "");

        filterStorage.setItem(STORAGE_KEYS.onlyFav, showOnlyFavorites ? "1" : "0");
        filterStorage.setItem(STORAGE_KEYS.sortPlayersDir, sortPlayersDir);
        filterStorage.setItem(STORAGE_KEYS.sortBlindsDir, sortBlindsDir);
        filterStorage.setItem(STORAGE_KEYS.sortPriority, JSON.stringify(sortPriority));
        queueFilterSave();
    }

    function sortRows(rows) {
        const activeSorts = sortPriority.filter(key => {
            if (key === "players") return !!sortPlayersDir;
            if (key === "blinds") return !!sortBlindsDir;
            return false;
        });

        if (!activeSorts.length) return rows.sort((a, b) => defaultOrder.get(a) - defaultOrder.get(b));

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
            return defaultOrder.get(a) - defaultOrder.get(b);
        });

        return rows;
    }

    function applyAll() {
        // Keep the expanded page size across the automatic 30-second refresh.
        filterStorage.setItem(STORAGE_KEYS.visibleCount, String(visibleCount));
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

        const count = $("#table-count");
        if (count) count.textContent = filtered.length + (filtered.length === 1 ? " table" : " tables") + (filtered.length > visibleCount ? " · showing " + visibleCount : "");
        const empty = $("#table-empty");
        if (empty) empty.hidden = rows.length === 0 || filtered.length > 0;
        const reset = $("#clear-filters");
        if (reset) reset.disabled = !(search || minBlindRaw || maxBlindRaw || activeGames.length || activeNetworks.length || showOnlyFavorites);
        for (const [id,label,dir] of [["sort-players","Players",sortPlayersDir],["sort-blinds","Blinds",sortBlindsDir]]) {
            const button=$("#"+id);
            if(button){button.dataset.sort=dir;button.setAttribute("aria-label",label+" sort: "+(dir==="asc"?"ascending":dir==="desc"?"descending":"not sorted")+". Activate to change direction.");}
        }

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
        $("#join-affiliate-contact").textContent = affiliateUrl.startsWith("https://t.me/") ? "Telegram · @" + affiliateUrl.slice(13) : "Contact via Telegram";
        $("#join-owner-name").textContent = ownerName;

        $("#join-affiliate-tip").textContent =
            "TableRadar is responsible for the security of its service and for the official support we provide. When you join through TableRadar Official, our team is your point of contact for information and assistance.";

        $("#join-owner-tip").textContent =
            "When you contact a club directly, you deal with the independent club owner. TableRadar is not responsible for the owner's actions, game arrangements or further interactions.";

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

    $("#clear-filters")?.addEventListener("click", function() {
        setActiveGames([]);
        setActiveNetworks([]);
        showOnlyFavorites = false;
        visibleCount = 15;
        ["#club-search", "#blinds-min", "#blinds-max"].forEach(selector => {
            const input = $(selector);
            if (input) input.value = "";
        });
        paintFavoriteStars();
        paintGameButtons();
        paintClubButtons();
        applyAll();
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
    filtersReady = true;
    lastFilterPayload = JSON.stringify(currentFilters());
    if (FILTER_CSRF && (filterStorage.getItem(STORAGE_KEYS.pending) === "1" || !serverFilters)) queueFilterSave(true);
    </script>
    """


# =========================
# PUBLIC PAGE
# =========================

def render_public_page(tables, request=None, user=None):
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

    # A real account loaded server-side is required; session display strings are not access rights.
    if not user:
        username = user_email = None
        plan, is_active = "inactive", False
    else:
        username, user_email = user.get("username"), user.get("email")
        plan, is_active = user.get("plan", "inactive"), bool(user.get("is_active"))
    display_name = user_email or username or ""

    filter_csrf = request.session.setdefault("account_csrf", secrets.token_urlsafe(32)) if user and request else ""
    filters_json = escape(json.dumps(saved_filters(user),ensure_ascii=True),quote=True)

    cards = "".join(render_public_card(t, show_club=directory_access(user)) for t in tables if players_value(t.get("players", "")) > 0)

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
        label = plan.title() if is_active and plan in ('player', 'host') else 'Membership'
        if trial_enabled() and trial_remaining(user) and directory_access(user) and not is_active:
            label = 'Player trial · ' + str(trial_remaining(user)) + ' days'
        menu_user = dict(user or {}, email=display_name, plan=plan, is_active=is_active)
        right_top_html = f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap"><a href="/profile" class="tr-status-pill" style="text-decoration:none">{escape(label)}</a>{render_account_menu(menu_user)}</div>'
    else:
        right_top_html = '<a class="tr-button" href="/signin_login">Sign in →</a>'

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
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

            .admin-tag-btn.tr-vpip-pick {{padding:2px;min-width:70px;background:transparent;border:1px solid transparent;box-shadow:none}}
            .admin-tag-btn.tr-vpip-pick.active {{border-color:#f3dba5;background:#65522c;box-shadow:0 0 0 1px #f3dba555}}
            .admin-tag-btn.tr-feature-pick {{min-width:28px!important;width:28px;height:28px!important;padding:2px;background:transparent;border:1px solid transparent;box-shadow:none}}
            .admin-tag-btn.tr-feature-pick.active {{border-color:#c7f2dd;background:#3c6152;box-shadow:0 0 0 1px #c7f2dd55}}
            .tr-feature-pick .tr-feature-icon {{pointer-events:none}}
            .admin-tag-btn.tr-feature-with-label {{width:auto!important;padding:2px 6px;gap:5px;display:inline-flex;align-items:center;font-size:11px}}
            .tr-extra-features summary {{cursor:pointer;color:#c5ded5;font:600 11px Arial}}
            .tr-extra-features small {{display:block;font-size:10px;color:#abc1bb;margin-top:6px}}
            .tr-feature-tags>span {{flex-shrink:0}}
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

            .join-help-wrap:hover .join-help-tip, .join-help-wrap:focus-within .join-help-tip {{
                display:block;
            }}
        </style>
        {render_site_theme()}
    </head>
    <body class="tr-directory" data-username="{escape(display_name if display_name else 'guest')}" data-filter-csrf="{escape(filter_csrf,quote=True)}" data-filters="{filters_json}" style="
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

            <header class="tr-site-header" style="margin-bottom:24px">
    {render_brand_logo("/")}
    {right_top_html}
</header>

<p class="tr-scroll-hint">Swipe across to see all table details.</p><div class="tr-table-scroll" aria-label="Table directory">
            <div style="
                width:1066px;
                min-width:1066px;
                max-width:1066px;
                margin:0 auto;">

                <div class="tr-filter-row" style="
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

                    <div class="glass-bar tr-filter-panel" style="
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

                <div class="tr-search-row" style="
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
                        <input id="club-search" maxlength="120" aria-label="Search club" type="text" placeholder="Search club" style="
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

                <div class="tr-filter-summary"><span id="table-count" role="status" aria-live="polite"></span><button id="clear-filters" type="button" class="tr-button">Clear filters</button></div>
                <div class="tr-sort-row" style="
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
                    <button id="sort-players" type="button" class="tr-sort-button" title="Sort by players; click again to reverse" style="
                        cursor:pointer;
                        text-align:left;
                        padding-left:28px;">
                        Players <span class="tr-sort-arrows" aria-hidden="true"><svg viewBox="0 0 18 18" width="16" height="16" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path class="sort-up" d="M5 14V3M2 6l3-3 3 3"/><path class="sort-down" d="M13 4v11m-3-3l3 3 3-3"/></svg></span>
                    </button>
                    <button id="sort-blinds" type="button" class="tr-sort-button" title="Sort by blinds; click again to reverse" style="
                        cursor:pointer;
                        text-align:left;">
                        Blinds <span class="tr-sort-arrows" aria-hidden="true"><svg viewBox="0 0 18 18" width="16" height="16" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path class="sort-up" d="M5 14V3M2 6l3-3 3 3"/><path class="sort-down" d="M13 4v11m-3-3l3 3 3-3"/></svg></span>
                    </button>
                    <div></div>
                </div>

                <div id="tables-wrap" style="
                    width:1066px;
                    min-width:1066px;">
                    {render_trial_notice(user) if user else ""}
                    {cards}
                </div>

                <div id="table-empty" hidden class="glass-bar" style="padding:24px;border-radius:16px;margin:12px 0"><strong>No tables match your filters.</strong><p style="margin:8px 0 0;color:#a5b4b6">Try another club, game or blind range, or clear the filters above.</p></div>
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

        </div>
        <div id="tr-name-tooltip" role="tooltip" hidden></div>
        <div popover id="guest-access" class="tr-guest-popover"><h2>Unlock club details</h2><p>To see full game information, register and purchase a membership or select Free Trial.</p><div><a class="tr-button tr-button-primary" href="{'/profile' if user else '/signup'}">{'Player access' if user else 'Create account'}</a> <a class="tr-button" href="/signin_login">Sign in</a> <a class="tr-button" href="{'/verify-account' if user else '/signup'}">Free Trial</a> <button class="tr-button" popovertarget="guest-access" popovertargetaction="hide">Close</button></div></div>
        <div id="join-modal-overlay" style="
    display:none;
    position:fixed;
    inset:0;
    background:rgba(0,0,0,.46);
    align-items:center;
    justify-content:center;
    z-index:1200;
    backdrop-filter:blur(4px);">

    <div class="glass-bar" id="join-modal-card" role="dialog" aria-modal="true" aria-labelledby="join-club-title" style="
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

            <button id="join-modal-close" type="button" aria-label="Close join options" style="
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
            gap:18px;" class="tr-join-options">

            <div class="tr-join-option tr-join-affiliate" style="
                background:rgba(43,31,12,.42);
                border:1px solid rgba(223,181,86,.32);
                border-radius:18px;
                padding:22px;
                box-sizing:border-box;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <div id="join-affiliate-name" style="font:700 23px Arial;color:#d7b258;">TableRadar Official</div>

                    <div class="join-help-wrap" tabindex="0" aria-label="Joining information">
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
                            TableRadar is responsible for the security of its service and for the official support we provide. When you join through TableRadar Official, our team is your point of contact for information and assistance.
                        </div>
                    </div>
                </div>

                <div style="font:600 15px Arial;color:#ece2c7;line-height:1.5;margin-bottom:20px;">
                    Official affiliate of the website.
                    <div id="join-affiliate-contact" style="margin-top:7px;font-size:13px;overflow-wrap:anywhere">Telegram · @tableradar</div>
                </div>

                <a id="join-affiliate-link" href="#" target="_blank" rel="noopener noreferrer" style="
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

            <div class="tr-join-option tr-join-owner" style="
                background:rgba(54,20,24,.42);
                border:1px solid rgba(207,92,106,.32);
                border-radius:18px;
                padding:22px;
                box-sizing:border-box;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <div id="join-owner-name" style="font:700 23px Arial;color:#d8757d;">Club Official</div>

                    <div class="join-help-wrap" tabindex="0" aria-label="Joining information">
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
                            When you contact a club directly, you deal with the independent club owner. TableRadar is not responsible for the owner's actions, game arrangements or further interactions.
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

        {render_site_footer()}
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
    buyin = escape(minimum_buyin(table.get("buyin", "")))
    players_raw = _safe(table.get("players", "-")).strip()
    seats_raw = _safe(table.get("seats", "6")).strip()

    network = _network_from_table(table)
    network_label = _network_label(network)
    overlay_color = _network_overlay_color(network)

    affiliate_name = escape(normalize_affiliate_name(_safe(table.get("affiliate_name", OFFICIAL_AFFILIATE_NAME))))
    affiliate_telegram = escape(TELEGRAM_URL if affiliate_name == OFFICIAL_AFFILIATE_NAME else _safe(table.get("affiliate_telegram", "")))
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
                            {blinds} · {buyin}{currency_badge(table.get("currency"))}
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

                    <form method="post" action="/delete">
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

        </div>
    </div>
    """

def render_operator_clubs(clubs):
    if clubs is None:
        return ''
    items=[]
    for club in clubs:
        name=escape(str(club.get('club_name') or 'Unnamed club'))
        application=escape(str(club.get('application') or 'Application not recorded'))
        expiry=escape(str(club.get('expires_at_display') or 'Not recorded'))
        code=escape(str(club.get('club_code') or ''))
        items.append(f'<li><strong>{name}</strong><span>{application}{" · "+escape(normalize_currency(club.get("currency"),required=False)) if club.get("currency") else ""}{" · ID: "+code if code else ""}</span><small>Active until {expiry}</small></li>')
    body='<ul>'+''.join(items)+'</ul>' if items else '<p>No active club placements. Ask the manager before adding tables.</p>'
    return f'<aside class="tr-operator-clubs" aria-label="Active clubs to monitor"><h2>Clubs to monitor <span>{len(items)}</span></h2><p>Check and add tables only for these active club placements. The manager controls activation and renewal.</p>{body}<small>Active placement does not by itself confirm payment.</small></aside>'


def render_admin_page(tables, manager=False, workspace="tables", active_clubs=None, pending_requests=0, csrf="", error="", form_data=None):
    form_values = dict(form_data or {})
    fields = [
        ('Table name','table_name','Table name'),
        ('Union name','union_name','Union name'),
        ('Blinds','blinds','Blinds'),
        ('Minimum buy-in','buyin','Minimum amount'),
        ('Players','players','Players (ex. 4/6)'),
    ]
    options=''.join(f'<option value="{int(c["subscription_id"])}"{" selected" if str(c["subscription_id"]) == str(form_values.get("subscription_id", "")) else ""}>{escape(str(c["club_name"]))} · {escape(str(c["application"]))}</option>' for c in (active_clubs or []) if c.get('subscription_id'))
    entry_fields='<label class="tr-entry-field">Club name *<select name="subscription_id" required style="width:100%;min-width:0;box-sizing:border-box;padding:9px;border-radius:8px;background:#20323a;color:#e6eeeb;border:1px solid #a6cdbb38;font:600 12px Arial"><option value="">Select an active club</option>'+options+'</select></label>'
    entry_fields+=''.join(f'<label class="tr-entry-field">{escape(label)} *<input name="{name}" placeholder="{escape(placeholder,quote=True)}" value="{escape(str(form_values.get(name, "")),quote=True)}" required maxlength="160"></label>' for label,name,placeholder in fields)
    error_html=f'<p role="alert" style="color:#ffc1c7">{escape(error)}</p>' if error else ''
    cards = "".join(render_admin_card(t) for t in tables)
    title = "Manager workspace" if workspace == "manager" else "Table administration"
    request_count = max(0, int(pending_requests)) if manager else 0
    request_badge = (f'<span class="tr-request-count" aria-label="{request_count} pending club requests" style="display:inline-flex;align-items:center;justify-content:center;min-width:21px;height:21px;padding:0 6px;margin-left:7px;border-radius:999px;background:#b44f55;color:#fff0f0;font-size:12px;font-weight:700;line-height:1">{request_count}</span>' if request_count else '')
    staff_nav = (f'<a class="tr-button" href="/manager">Manager workspace</a><a class="tr-button" href="/manager/team">Staff access</a><a class="tr-button" href="/manager/membership-test">Test Host / Player</a><a class="tr-button" href="/admin/club-requests">Club requests{request_badge}</a><a class="tr-button" href="/admin/club-subscriptions">Club subscriptions</a>' if manager else '')
    staff_nav += '<a class="tr-button" href="/admin">Tables</a><a class="tr-button" href="/staff/chat">Live chat inbox<span class="tr-support-count" data-support-count hidden></span></a><a class="tr-button" href="/">View website</a><a class="tr-button" href="/logout">Sign out</a>' 

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{title} · TableRadar</title>
        <style>
            .admin-pick-btn {{
                min-width:84px;
                height:28px;
                border:none;
                border-radius:9px;
                background:#24343b;
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

            .admin-tag-btn.tr-vpip-pick {{padding:2px;min-width:70px;background:transparent;border:1px solid transparent;box-shadow:none}}
            .admin-tag-btn.tr-vpip-pick.active {{border-color:#f3dba5;background:#65522c;box-shadow:0 0 0 1px #f3dba555}}
            .admin-tag-btn.tr-feature-pick {{min-width:28px!important;width:28px;height:28px!important;padding:2px;background:transparent;border:1px solid transparent;box-shadow:none}}
            .admin-tag-btn.tr-feature-pick.active {{border-color:#c7f2dd;background:#3c6152;box-shadow:0 0 0 1px #c7f2dd55}}
            .tr-feature-pick .tr-feature-icon {{pointer-events:none}}
            .admin-tag-btn.tr-feature-with-label {{width:auto!important;padding:2px 6px;gap:5px;display:inline-flex;align-items:center;font-size:11px}}
            .tr-extra-features summary {{cursor:pointer;color:#c5ded5;font:600 11px Arial}}
            .tr-extra-features small {{display:block;font-size:10px;color:#abc1bb;margin-top:6px}}
            .tr-feature-tags>span {{flex-shrink:0}}
            .glass-bar {{
                background: linear-gradient(180deg, rgba(255,255,255,.12), rgba(255,255,255,.06));
                border: 1px solid rgba(255,255,255,.08);
                box-shadow: 0 18px 42px rgba(0,0,0,.22);
                backdrop-filter: blur(12px);
            }}
        </style>
        {render_site_theme()}
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
    gap:16px;flex-wrap:wrap;
    display:flex;
    justify-content:flex-start;
    align-items:center;">
    {render_brand_logo("/")}
    <nav aria-label="Administration" style="display:flex;gap:12px;flex-wrap:wrap;margin-left:auto">{staff_nav}</nav>
</div>

        <h1 style="max-width:1300px;margin:20px auto;font-size:28px">{title}</h1><div class="tr-staff-grid" style="
            max-width:1300px;
            margin:0 auto;
            display:grid;
            grid-template-columns:320px minmax(0,1fr);
            gap:14px;
            align-items:start;">

            <div class="glass-bar tr-add-table-panel" style="
                border-radius:14px;
                padding:12px;">


                <div style="
                    font-size:18px;
                    font-weight:800;
                    margin-bottom:3px;">
                    Add new table
                </div>

                {error_html}<form method="post" action="/add" id="admin-add-form">
                    <input type="hidden" name="csrf" value="{escape(csrf,quote=True)}">
                    <input type="hidden" name="game" id="admin-game-input" value="{escape(str(form_values.get("game", "")),quote=True)}">
                    <input type="hidden" name="tags" id="admin-tags-input" value="{escape(str(form_values.get("tags", "")),quote=True)}">

                    <div class="tr-entry-fields">{entry_fields}</div>

                    <div class="tr-entry-options">
                        <section><div style="font:700 12px Arial;margin-bottom:4px;">Tags</div>
<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;">
    <button type="button" class="admin-pick-btn admin-tag-btn tr-vpip-pick" data-value="vpip 30%" aria-label="VPIP 30%">{render_vpip_badge("30")}</button>
    <button type="button" class="admin-pick-btn admin-tag-btn tr-vpip-pick" data-value="vpip 35%" aria-label="VPIP 35%">{render_vpip_badge("35")}</button>
    <button type="button" class="admin-pick-btn admin-tag-btn tr-vpip-pick" data-value="vpip 40%" aria-label="VPIP 40%">{render_vpip_badge("40")}</button>
    <button type="button" class="admin-pick-btn admin-tag-btn tr-vpip-pick" data-value="vpip 45%" aria-label="VPIP 45%">{render_vpip_badge("45")}</button>
    <button type="button" class="admin-pick-btn admin-tag-btn tr-vpip-pick" data-value="vpip 50%" aria-label="VPIP 50%">{render_vpip_badge("50")}</button>
    <button type="button" class="admin-pick-btn admin-tag-btn tr-vpip-pick" data-value="vpip 55%" aria-label="VPIP 55%">{render_vpip_badge("55")}</button>
    <button type="button" class="admin-pick-btn admin-tag-btn tr-vpip-pick" data-value="vpip 60%" aria-label="VPIP 60%">{render_vpip_badge("60")}</button>

    {feature_buttons(('bomb', 'clock'))}
    {feature_buttons(PRIMARY_FEATURES)}
</div>
<details class="tr-extra-features"><summary>More table features</summary><div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:7px">{feature_buttons((key for key in FEATURES if key not in PRIMARY_FEATURES), labels=True)}</div><small>Select only features enabled on this table. Availability varies by application.</small></details>

                        </section><section><div style="font:700 12px Arial;margin-bottom:4px;">Game format</div>
                        <div style="display:grid;grid-template-columns:repeat(2,84px);gap:6px 6px;">
                            <button type="button" class="admin-pick-btn admin-game-btn" data-value="NLH">NLH</button>
                            <button type="button" class="admin-pick-btn admin-game-btn" data-value="PLO4">PLO4</button>
                            <button type="button" class="admin-pick-btn admin-game-btn" data-value="PLO5">PLO5</button>
                            <button type="button" class="admin-pick-btn admin-game-btn" data-value="PLO6">PLO6</button>
                        </div></section>
                    </div>

                    <p id="admin-form-feedback" role="status" aria-live="polite" style="margin:6px 0 0;color:#d7c7a1;font-size:11px"></p>
                    <div class="tr-entry-submit" style="
                        margin-top:10px;
                        display:flex;
                        justify-content:space-between;
                        align-items:flex-end;
                        gap:10px;">

                        <button id="admin-add-submit" type="submit" style="
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
                            Choose a club from Clubs to monitor.<br>Currency, application and joining contacts are filled automatically.
                        </div>
                    </div>
                </form>
            </div>

            <div class="tr-club-worklist-column">{render_operator_clubs(active_clubs)}</div>
            <div class="tr-table-list-column">
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
                const tagsInput = document.getElementById("admin-tags-input");

                const clubSearch = document.getElementById("admin-club-search");

                const entryForm = document.getElementById("admin-add-form");
                const entrySubmit = document.getElementById("admin-add-submit");
                const feedback = document.getElementById("admin-form-feedback");
                const fieldLabels = {{subscription_id:"Club name",table_name:"Table name",union_name:"Union name",blinds:"Blinds",buyin:"Minimum buy-in",players:"Players"}};
                function validateEntry() {{
                    const missing = Object.entries(fieldLabels).filter(([name])=>!entryForm.elements[name].value.trim()).map(([,label])=>label);
                    if (!gameInput.value) missing.push("Game format");
                    let invalid = "";
                    const buyin = entryForm.elements.buyin.value.trim();
                    const players = entryForm.elements.players.value.trim();
                    if (buyin && (!/^[0-9]{{1,10}}(?:[.,][0-9]{{1,2}})?$/.test(buyin) || Number(buyin.replace(',','.'))<=0)) invalid="Minimum buy-in: enter a positive amount.";
                    const seats = /^(\\d{{1,2}})\\s*\\/\\s*(\\d{{1,2}})$/.exec(players);
                    if (players && (!seats || +seats[1]>+seats[2] || +seats[2]<2 || +seats[2]>10)) invalid="Players: use occupied / total seats, for example 4/6.";
                    const tooLong = Object.keys(fieldLabels).find(name=>name!=="subscription_id" && entryForm.elements[name].value.length>160);
                    if (tooLong) invalid=fieldLabels[tooLong]+": use up to 160 characters.";
                    entrySubmit.disabled=!!(missing.length || invalid);
                    feedback.textContent=missing.length ? "Please complete: "+missing.join(", ")+"." : invalid || "Ready to add this table.";
                    return !entrySubmit.disabled;
                }}
                entryForm.addEventListener("input",validateEntry);
                entryForm.addEventListener("change",validateEntry);
                entryForm.addEventListener("submit",event=>{{if(!validateEntry()) event.preventDefault();}});
                let selectedTags = tagsInput.value.split(",").filter(Boolean);
                document.querySelectorAll(".admin-game-btn").forEach(btn=>btn.classList.toggle("active",btn.dataset.value===gameInput.value));
                document.querySelectorAll(".admin-tag-btn").forEach(btn=>{{const on=selectedTags.includes(btn.dataset.value);btn.classList.toggle("active",on);btn.setAttribute("aria-pressed",String(on));}});
                validateEntry();

                function syncTags() {{
                    tagsInput.value = selectedTags.join(",");
                }}

                document.querySelectorAll(".admin-game-btn").forEach(btn => {{
                    btn.addEventListener("click", function() {{
                        document.querySelectorAll(".admin-game-btn").forEach(b => b.classList.remove("active"));
                        btn.classList.add("active");
                        gameInput.value = btn.dataset.value;
                        validateEntry();
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
                        btn.setAttribute("aria-pressed", String(btn.classList.contains("active")));
                        syncTags();
                    }});
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
