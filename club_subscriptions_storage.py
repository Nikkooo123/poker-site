import os
from datetime import date, datetime, timedelta

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
_DB_READY = False


def _connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing. Check .env locally or Render Environment.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def _safe(value, default=""):
    if value is None:
        return default
    return str(value)


def _parse_date(value):
    value = _safe(value).strip()

    if not value:
        return date.today()

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        pass

    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except Exception:
        pass

    return date.today()


def _date_display(value):
    if not value:
        return "-"

    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    try:
        return datetime.fromisoformat(str(value)).strftime("%d/%m/%Y")
    except Exception:
        return str(value)


def init_club_subscriptions_db():
    global _DB_READY

    if _DB_READY:
        return

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS club_subscriptions (
                    id SERIAL PRIMARY KEY,
                    club_name TEXT DEFAULT '',
                    owner_name TEXT DEFAULT '',
                    owner_telegram TEXT DEFAULT '',
                    owner_email TEXT DEFAULT '',
                    application TEXT DEFAULT '',
                    plan TEXT DEFAULT 'host',
                    status TEXT DEFAULT 'active',
                    started_at DATE DEFAULT CURRENT_DATE,
                    expires_at DATE DEFAULT CURRENT_DATE + INTERVAL '30 days',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)

            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS club_name TEXT DEFAULT '';")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS owner_name TEXT DEFAULT '';")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS owner_telegram TEXT DEFAULT '';")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS owner_email TEXT DEFAULT '';")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS application TEXT DEFAULT '';")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS plan TEXT DEFAULT 'host';")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS started_at DATE DEFAULT CURRENT_DATE;")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS expires_at DATE DEFAULT CURRENT_DATE + INTERVAL '30 days';")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS notes TEXT DEFAULT '';")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();")

        conn.commit()

    _DB_READY = True


def load_club_subscriptions():
    init_club_subscriptions_db()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    *,
                    GREATEST(0, expires_at - CURRENT_DATE) AS days_left
                FROM club_subscriptions
                ORDER BY
                    CASE
                        WHEN status = 'active' THEN 0
                        ELSE 1
                    END,
                    expires_at ASC,
                    id DESC;
            """)
            rows = cur.fetchall()

    result = []

    for row in rows:
        item = dict(row)
        item["started_at_display"] = _date_display(item.get("started_at"))
        item["expires_at_display"] = _date_display(item.get("expires_at"))
        item["days_left"] = int(item.get("days_left") or 0)

        if item.get("status") == "active" and item["days_left"] <= 0:
            item["display_status"] = "expired"
        else:
            item["display_status"] = item.get("status", "active")

        result.append(item)

    return result


def add_club_subscription(
    club_name: str,
    owner_name: str = "",
    owner_telegram: str = "",
    owner_email: str = "",
    application: str = "",
    plan: str = "host",
    duration_days: int = 30,
    notes: str = "",
):
    init_club_subscriptions_db()

    started_at = date.today()
    expires_at = started_at + timedelta(days=int(duration_days or 30))

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO club_subscriptions (
                    club_name,
                    owner_name,
                    owner_telegram,
                    owner_email,
                    application,
                    plan,
                    status,
                    started_at,
                    expires_at,
                    notes
                )
                VALUES (%s,%s,%s,%s,%s,%s,'active',%s,%s,%s)
                RETURNING id;
            """, (
                _safe(club_name).strip(),
                _safe(owner_name).strip(),
                _safe(owner_telegram).strip(),
                _safe(owner_email).strip(),
                _safe(application).strip(),
                _safe(plan, "host").strip() or "host",
                started_at,
                expires_at,
                _safe(notes).strip(),
            ))

            new_id = cur.fetchone()["id"]

        conn.commit()

    return new_id


def extend_club_subscription(subscription_id: int, days: int = 30):
    init_club_subscriptions_db()

    days = int(days or 30)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE club_subscriptions
                SET
                    expires_at =
                        CASE
                            WHEN expires_at < CURRENT_DATE THEN CURRENT_DATE + (%s || ' days')::interval
                            ELSE expires_at + (%s || ' days')::interval
                        END,
                    status = 'active',
                    updated_at = NOW()
                WHERE id = %s;
            """, (days, days, int(subscription_id)))

        conn.commit()


def disable_club_subscription(subscription_id: int):
    init_club_subscriptions_db()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE club_subscriptions
                SET status = 'inactive',
                    updated_at = NOW()
                WHERE id = %s;
            """, (int(subscription_id),))

        conn.commit()


def enable_club_subscription(subscription_id: int):
    init_club_subscriptions_db()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE club_subscriptions
                SET status = 'active',
                    updated_at = NOW()
                WHERE id = %s;
            """, (int(subscription_id),))

        conn.commit()


def delete_club_subscription(subscription_id: int):
    init_club_subscriptions_db()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM club_subscriptions
                WHERE id = %s;
            """, (int(subscription_id),))

        conn.commit()