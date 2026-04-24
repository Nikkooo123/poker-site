import os
import json
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

try:
    from brand import OFFICIAL_AFFILIATE_NAME, normalize_affiliate_name
except Exception:
    OFFICIAL_AFFILIATE_NAME = "TableRadar Official"

    def normalize_affiliate_name(value: str) -> str:
        value = str(value or "").strip()
        if not value:
            return OFFICIAL_AFFILIATE_NAME
        if value.lower() in {"boom247", "boom247 official", "tableradar", "tableradar official"}:
            return OFFICIAL_AFFILIATE_NAME
        return value


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
TABLES_JSON = Path("tables.json")
_DB_READY = False

def _connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing. Check .env locally or Render Environment.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def _safe(value, default=""):
    if value is None:
        return default
    return str(value)


def _extract_seats(players: str) -> str:
    s = _safe(players).strip()
    if "/" in s:
        try:
            return s.split("/", 1)[1].strip() or "6"
        except Exception:
            return "6"
    return "6"


def _normalize_game(game: str) -> str:
    g = _safe(game, "NLH").strip().upper()

    if g in {"PLO 4", "PLO4", "PL4"}:
        return "PLO4"
    if g in {"PLO 5", "PLO5", "PL5"}:
        return "PLO5"
    if g in {"PLO 6", "PLO6", "PL6"}:
        return "PLO6"
    if g == "NLH":
        return "NLH"

    return g or "NLH"


def _normalize_network(value: str) -> str:
    s = _safe(value).strip().lower()

    if s in {"pp poker", "pppoker", "pp"}:
        return "pppoker"
    if s in {"poker bros", "pokerbros", "bros"}:
        return "pokerbros"
    if s in {"club gg", "clubgg", "gg"}:
        return "clubgg"
    if s in {"x poker", "x-poker", "xpoker", "x"}:
        return "xpoker"

    return s


def _normalize_tags(tags: str) -> str:
    raw = _safe(tags).lower()
    out = []

    if "vpip" in raw or "vip" in raw or "vipip" in raw:
        import re
        m = re.search(r"(\d+)", raw)
        if m:
            out.append(f"vpip {m.group(1)}%")
        else:
            out.append("vpip")

    if "bomb" in raw:
        out.append("bomb")

    if "clock" in raw:
        out.append("clock")

    return ",".join(out) if out else _safe(tags)


def init_db():
    global _DB_READY

    if _DB_READY:
        return

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS poker_tables (
                    id SERIAL PRIMARY KEY,
                    club TEXT DEFAULT '',
                    table_name TEXT DEFAULT '',
                    union_name TEXT DEFAULT '',
                    game TEXT DEFAULT 'NLH',
                    network TEXT DEFAULT '',
                    platform TEXT DEFAULT '',
                    blinds TEXT DEFAULT '',
                    buyin TEXT DEFAULT '',
                    players TEXT DEFAULT '',
                    seats TEXT DEFAULT '6',
                    tags TEXT DEFAULT '',
                    affiliate_name TEXT DEFAULT 'TableRadar Official',
                    affiliate_telegram TEXT DEFAULT '',
                    owner_name TEXT DEFAULT '',
                    owner_telegram TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)

            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS club TEXT DEFAULT '';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS table_name TEXT DEFAULT '';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS union_name TEXT DEFAULT '';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS game TEXT DEFAULT 'NLH';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS network TEXT DEFAULT '';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS platform TEXT DEFAULT '';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS blinds TEXT DEFAULT '';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS buyin TEXT DEFAULT '';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS players TEXT DEFAULT '';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS seats TEXT DEFAULT '6';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS tags TEXT DEFAULT '';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS affiliate_name TEXT DEFAULT 'TableRadar Official';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS affiliate_telegram TEXT DEFAULT '';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS owner_name TEXT DEFAULT '';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS owner_telegram TEXT DEFAULT '';")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();")
            cur.execute("ALTER TABLE poker_tables ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();")

        conn.commit()

    migrate_json_to_db_once()
    _DB_READY = True


def migrate_json_to_db_once():
    if not TABLES_JSON.exists():
        return

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS count FROM poker_tables;")
            count = cur.fetchone()["count"]

            if count > 0:
                return

            try:
                data = json.loads(TABLES_JSON.read_text(encoding="utf-8"))
            except Exception:
                return

            if not isinstance(data, list):
                return

            for table in data:
                if not isinstance(table, dict):
                    continue

                _insert_table(cur, table)

        conn.commit()


def _table_dict_from_args(*args, **kwargs) -> dict:
    if args and isinstance(args[0], dict):
        table = dict(args[0])
        table.update(kwargs)
        return table

    # старая версия: add_table(club, game, blinds, buyin, players, tags)
    if len(args) == 6:
        return {
            "club": args[0],
            "table_name": args[0],
            "game": args[1],
            "blinds": args[2],
            "buyin": args[3],
            "players": args[4],
            "tags": args[5],
        }

    # твоя текущая версия:
    # add_table(club, table_name, union_name, game, blinds, buyin, players, tags, network, affiliate_name, affiliate_telegram, owner_name, owner_telegram)
    if len(args) >= 13:
        return {
            "club": args[0],
            "table_name": args[1],
            "union_name": args[2],
            "game": args[3],
            "blinds": args[4],
            "buyin": args[5],
            "players": args[6],
            "tags": args[7],
            "network": args[8],
            "affiliate_name": args[9],
            "affiliate_telegram": args[10],
            "owner_name": args[11],
            "owner_telegram": args[12],
        }

    table = dict(kwargs)
    names = [
        "club",
        "table_name",
        "union_name",
        "game",
        "blinds",
        "buyin",
        "players",
        "tags",
        "network",
        "affiliate_name",
        "affiliate_telegram",
        "owner_name",
        "owner_telegram",
    ]

    for i, value in enumerate(args):
        if i < len(names):
            table[names[i]] = value

    return table


def _normalize_table(table: dict) -> dict:
    club = _safe(table.get("club", "")).strip()
    table_name = _safe(table.get("table_name") or table.get("name") or club).strip()
    union_name = _safe(table.get("union_name", "")).strip()

    game = _normalize_game(table.get("game", "NLH"))

    network = _normalize_network(table.get("network") or table.get("platform") or "")
    platform = network

    blinds = _safe(table.get("blinds", "")).strip()
    buyin = _safe(table.get("buyin", "")).strip()
    players = _safe(table.get("players", "")).strip()
    seats = _safe(table.get("seats") or _extract_seats(players)).strip() or "6"
    tags = _normalize_tags(table.get("tags", ""))

    affiliate_name = normalize_affiliate_name(table.get("affiliate_name") or OFFICIAL_AFFILIATE_NAME)
    affiliate_telegram = _safe(table.get("affiliate_telegram", "")).strip()

    owner_name = _safe(
        table.get("owner_name")
        or table.get("club_official_name")
        or table.get("owner")
        or ""
    ).strip()

    owner_telegram = _safe(
        table.get("owner_telegram")
        or table.get("club_telegram")
        or ""
    ).strip()

    return {
        "club": club,
        "table_name": table_name,
        "union_name": union_name,
        "game": game,
        "network": network,
        "platform": platform,
        "blinds": blinds,
        "buyin": buyin,
        "players": players,
        "seats": seats,
        "tags": tags,
        "affiliate_name": affiliate_name,
        "affiliate_telegram": affiliate_telegram,
        "owner_name": owner_name,
        "owner_telegram": owner_telegram,
    }


def _insert_table(cur, table: dict):
    t = _normalize_table(table)

    cur.execute("""
        INSERT INTO poker_tables (
            club, table_name, union_name, game, network, platform,
            blinds, buyin, players, seats, tags,
            affiliate_name, affiliate_telegram,
            owner_name, owner_telegram
        )
        VALUES (
            %(club)s, %(table_name)s, %(union_name)s, %(game)s, %(network)s, %(platform)s,
            %(blinds)s, %(buyin)s, %(players)s, %(seats)s, %(tags)s,
            %(affiliate_name)s, %(affiliate_telegram)s,
            %(owner_name)s, %(owner_telegram)s
        )
        RETURNING id;
    """, t)

    return cur.fetchone()["id"]


def load_tables():
    init_db()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    club,
                    table_name,
                    union_name,
                    game,
                    network,
                    platform,
                    blinds,
                    buyin,
                    players,
                    seats,
                    tags,
                    affiliate_name,
                    affiliate_telegram,
                    owner_name,
                    owner_telegram,
                    created_at,
                    updated_at
                FROM poker_tables
                ORDER BY id DESC;
            """)
            rows = cur.fetchall()

    return [dict(row) for row in rows]


def add_table(*args, **kwargs):
    init_db()

    table = _table_dict_from_args(*args, **kwargs)

    with _connect() as conn:
        with conn.cursor() as cur:
            new_id = _insert_table(cur, table)
        conn.commit()

    return new_id


def update_players(table_id: int, players: str):
    init_db()

    players = _safe(players).strip()
    seats = _extract_seats(players)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE poker_tables
                SET players = %s,
                    seats = %s,
                    updated_at = NOW()
                WHERE id = %s;
            """, (players, seats, int(table_id)))

        conn.commit()


def delete_table(table_id: int):
    init_db()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM poker_tables WHERE id = %s;", (int(table_id),))
        conn.commit()


def save_tables(tables):
    # совместимость со старым кодом
    # живые данные теперь хранятся в Postgres
    return