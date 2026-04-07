from brand import OFFICIAL_AFFILIATE_NAME, normalize_affiliate_name
import json
import os

FILE = "tables.json"


def init_db():
    if not os.path.exists(FILE):
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def _extract_seats(players: str) -> str:
    s = str(players or "").strip()
    if "/" in s:
        parts = s.split("/")
        if len(parts) == 2:
            return parts[1].strip()
    return "6"


def _normalize_table(table: dict) -> dict:
    t = dict(table)

    club = str(t.get("club", "Club")).strip() or "Club"

    if "table_name" not in t or not str(t.get("table_name", "")).strip():
        t["table_name"] = club

    if "union_name" not in t:
        t["union_name"] = ""

    if "seats" not in t:
        t["seats"] = _extract_seats(t.get("players", ""))

    if "network" not in t:
        t["network"] = ""

    if not t.get("affiliate_name"):
        t["affiliate_name"] = OFFICIAL_AFFILIATE_NAME
    else:
        t["affiliate_name"] = normalize_affiliate_name(str(t.get("affiliate_name", "")))

    if "affiliate_telegram" not in t:
        t["affiliate_telegram"] = ""

    if not t.get("owner_name"):
        t["owner_name"] = f"{club} Official"

    if "owner_telegram" not in t:
        t["owner_telegram"] = ""

    return t


def load_tables():
    init_db()
    with open(FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [_normalize_table(t) for t in data]


def save_tables(data):
    normalized = [_normalize_table(t) for t in data]
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)


def add_table(
    club,
    table_name,
    union_name,
    game,
    blinds,
    buyin,
    players,
    tags,
    network="",
    affiliate_name=OFFICIAL_AFFILIATE_NAME,
    affiliate_telegram="",
    owner_name="",
    owner_telegram=""
):
    data = load_tables()
    new_id = max([t.get("id", 0) for t in data], default=0) + 1

    data.append({
        "id": new_id,
        "club": club,
        "table_name": table_name or club,
        "union_name": union_name,
        "game": game,
        "blinds": blinds,
        "buyin": buyin,
        "players": players,
        "tags": tags,
        "network": network,
        "affiliate_name": normalize_affiliate_name(affiliate_name),
        "affiliate_telegram": affiliate_telegram,
        "owner_name": owner_name,
        "owner_telegram": owner_telegram,
        "seats": _extract_seats(players),
    })

    save_tables(data)


def update_players(table_id, players):
    data = load_tables()
    for t in data:
        if int(t.get("id", 0)) == int(table_id):
            t["players"] = players
            t["seats"] = _extract_seats(players)
    save_tables(data)


def delete_table(table_id):
    data = load_tables()
    data = [t for t in data if int(t.get("id", 0)) != int(table_id)]
    save_tables(data)