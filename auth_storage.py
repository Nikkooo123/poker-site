import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Optional

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
USERS_JSON = Path("users.json")


def _connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing. Check .env locally or Render Environment.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def _safe(value, default=""):
    if value is None:
        return default
    return str(value)


def _normalize_email(email: str) -> str:
    return _safe(email).strip().lower()


def _hash_password(password: str) -> str:
    password = _safe(password)
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _today() -> date:
    return datetime.now().date()


def _date_to_string(value) -> str:
    if not value:
        return "-"

    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    s = str(value)

    # если уже dd/mm/yyyy
    if "/" in s:
        return s

    # если ISO date
    try:
        return datetime.fromisoformat(s).strftime("%d/%m/%Y")
    except Exception:
        return s


def init_auth_db():
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT DEFAULT '',
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT DEFAULT '',
                    registered_at DATE DEFAULT CURRENT_DATE,
                    role TEXT DEFAULT 'player',
                    plan TEXT DEFAULT 'inactive',
                    is_active BOOLEAN DEFAULT FALSE,
                    days_left INTEGER DEFAULT 0,
                    auto_renew BOOLEAN DEFAULT TRUE,
                    plan_started_at DATE,
                    plan_expires_at DATE,
                    country TEXT DEFAULT 'United Kingdom',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)

            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT DEFAULT '';")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT DEFAULT '';")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS registered_at DATE DEFAULT CURRENT_DATE;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'player';")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan TEXT DEFAULT 'inactive';")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT FALSE;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS days_left INTEGER DEFAULT 0;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS auto_renew BOOLEAN DEFAULT TRUE;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_started_at DATE;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_expires_at DATE;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS country TEXT DEFAULT 'United Kingdom';")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();")

        conn.commit()

    migrate_users_json_to_db_once()


def _row_to_user(row: dict) -> dict:
    if not row:
        return None

    return {
        "id": row.get("id"),
        "username": _safe(row.get("username")) or _safe(row.get("email")),
        "email": _safe(row.get("email")),
        "password_hash": _safe(row.get("password_hash")),
        "registered_at": _date_to_string(row.get("registered_at")),
        "role": _safe(row.get("role", "player")).lower(),
        "plan": _safe(row.get("plan", "inactive")).lower(),
        "is_active": bool(row.get("is_active")),
        "days_left": int(row.get("days_left") or 0),
        "auto_renew": bool(row.get("auto_renew")),
        "plan_started_at": _date_to_string(row.get("plan_started_at")),
        "plan_expires_at": _date_to_string(row.get("plan_expires_at")),
        "country": _safe(row.get("country", "United Kingdom")),
        "created_at": _safe(row.get("created_at", "")),
        "updated_at": _safe(row.get("updated_at", "")),
    }


def migrate_users_json_to_db_once():
    if not USERS_JSON.exists():
        return

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS count FROM users;")
            count = cur.fetchone()["count"]

            if count > 0:
                return

            try:
                users = json.loads(USERS_JSON.read_text(encoding="utf-8"))
            except Exception:
                return

            if not isinstance(users, list):
                return

            for user in users:
                if not isinstance(user, dict):
                    continue

                email = _normalize_email(user.get("email", ""))
                if not email:
                    continue

                username = _safe(user.get("username", email)).strip() or email

                password_hash = _safe(user.get("password_hash", ""))
                if not password_hash and user.get("password"):
                    password_hash = _hash_password(user.get("password"))

                registered_at = _safe(
                    user.get("registered_at", user.get("registered", user.get("created_at", "")))
                )

                try:
                    if registered_at and "/" in registered_at:
                        registered_date = datetime.strptime(registered_at, "%d/%m/%Y").date()
                    elif registered_at:
                        registered_date = datetime.fromisoformat(registered_at).date()
                    else:
                        registered_date = _today()
                except Exception:
                    registered_date = _today()

                role = _safe(user.get("role", "player")).lower()
                plan = _safe(user.get("plan", "inactive")).lower()
                is_active = bool(user.get("is_active", user.get("active", False)))
                days_left = int(user.get("days_left", user.get("days", 0)) or 0)
                auto_renew = bool(user.get("auto_renew", True))
                country = _safe(user.get("country", "United Kingdom"))

                cur.execute("""
                    INSERT INTO users (
                        username,
                        email,
                        password_hash,
                        registered_at,
                        role,
                        plan,
                        is_active,
                        days_left,
                        auto_renew,
                        country
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (email) DO NOTHING;
                """, (
                    username,
                    email,
                    password_hash,
                    registered_date,
                    role,
                    plan,
                    is_active,
                    days_left,
                    auto_renew,
                    country,
                ))

        conn.commit()


def load_users() -> list:
    init_auth_db()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM users
                ORDER BY id ASC;
            """)
            rows = cur.fetchall()

    return [_row_to_user(dict(row)) for row in rows]


def save_users(users: list) -> None:
    """
    Оставлено для совместимости со старым кодом.
    Теперь пользователи хранятся в Postgres.
    """
    init_auth_db()

    if not isinstance(users, list):
        return

    with _connect() as conn:
        with conn.cursor() as cur:
            for user in users:
                if not isinstance(user, dict):
                    continue

                email = _normalize_email(user.get("email", ""))
                if not email:
                    continue

                username = _safe(user.get("username", email)).strip() or email
                password_hash = _safe(user.get("password_hash", ""))
                role = _safe(user.get("role", "player")).lower()
                plan = _safe(user.get("plan", "inactive")).lower()
                is_active = bool(user.get("is_active", False))
                days_left = int(user.get("days_left", 0) or 0)
                auto_renew = bool(user.get("auto_renew", True))
                country = _safe(user.get("country", "United Kingdom"))

                cur.execute("""
                    INSERT INTO users (
                        username,
                        email,
                        password_hash,
                        role,
                        plan,
                        is_active,
                        days_left,
                        auto_renew,
                        country
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (email)
                    DO UPDATE SET
                        username = EXCLUDED.username,
                        password_hash = EXCLUDED.password_hash,
                        role = EXCLUDED.role,
                        plan = EXCLUDED.plan,
                        is_active = EXCLUDED.is_active,
                        days_left = EXCLUDED.days_left,
                        auto_renew = EXCLUDED.auto_renew,
                        country = EXCLUDED.country,
                        updated_at = NOW();
                """, (
                    username,
                    email,
                    password_hash,
                    role,
                    plan,
                    is_active,
                    days_left,
                    auto_renew,
                    country,
                ))

        conn.commit()


def get_user_by_email(email: str) -> Optional[dict]:
    init_auth_db()

    email = _normalize_email(email)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM users
                WHERE LOWER(email) = %s
                LIMIT 1;
            """, (email,))
            row = cur.fetchone()

    return _row_to_user(dict(row)) if row else None


def get_user_by_username(username: str) -> Optional[dict]:
    init_auth_db()

    username = _safe(username).strip().lower()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM users
                WHERE LOWER(username) = %s
                LIMIT 1;
            """, (username,))
            row = cur.fetchone()

    return _row_to_user(dict(row)) if row else None


def create_user(*args, **kwargs):
    """
    Поддерживает старые и новые вызовы:

    create_user(email, password)
    create_user(username, email, password)
    create_user(email="...", password="...", username="...")
    """

    init_auth_db()

    username = kwargs.get("username", "")
    email = kwargs.get("email", "")
    password = kwargs.get("password", "")

    if len(args) == 2:
        email = args[0]
        password = args[1]

    elif len(args) >= 3:
        username = args[0]
        email = args[1]
        password = args[2]

    email = _normalize_email(email)
    username = _safe(username).strip() or email
    password = _safe(password)

    if not email or not password:
        return False

    password_hash = _hash_password(password)

    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (
                        username,
                        email,
                        password_hash,
                        registered_at,
                        role,
                        plan,
                        is_active,
                        days_left,
                        auto_renew,
                        country
                    )
                    VALUES (%s,%s,%s,CURRENT_DATE,'player','inactive',FALSE,0,TRUE,'United Kingdom')
                    ON CONFLICT (email) DO NOTHING
                    RETURNING id;
                """, (
                    username,
                    email,
                    password_hash,
                ))

                row = cur.fetchone()

            conn.commit()

        return bool(row)

    except Exception:
        return False


def authenticate_user(email: str, password: str) -> Optional[dict]:
    init_auth_db()

    email = _normalize_email(email)
    password = _safe(password)
    password_hash = _hash_password(password)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM users
                WHERE LOWER(email) = %s
                LIMIT 1;
            """, (email,))
            row = cur.fetchone()

    if not row:
        return None

    user = dict(row)
    stored_hash = _safe(user.get("password_hash", ""))

    if stored_hash == password_hash:
        return _row_to_user(user)

    return None


def set_user_plan(email: str, plan: str, days: int = 30, active: bool = True):
    init_auth_db()

    email = _normalize_email(email)
    plan = _safe(plan, "inactive").lower()

    plan_started = _today()
    plan_expires = plan_started + timedelta(days=int(days))

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET plan = %s,
                    is_active = %s,
                    days_left = %s,
                    plan_started_at = %s,
                    plan_expires_at = %s,
                    updated_at = NOW()
                WHERE LOWER(email) = %s;
            """, (
                plan,
                bool(active),
                int(days),
                plan_started,
                plan_expires,
                email,
            ))

            changed = cur.rowcount

        conn.commit()

    return changed > 0


def set_user_role(email: str, role: str):
    init_auth_db()

    email = _normalize_email(email)
    role = _safe(role, "player").lower()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET role = %s,
                    updated_at = NOW()
                WHERE LOWER(email) = %s;
            """, (role, email))

            changed = cur.rowcount

        conn.commit()

    return changed > 0


def set_user_auto_renew(email: str, enabled: bool):
    init_auth_db()

    email = _normalize_email(email)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET auto_renew = %s,
                    updated_at = NOW()
                WHERE LOWER(email) = %s;
            """, (bool(enabled), email))

            changed = cur.rowcount

        conn.commit()

    return changed > 0


def deactivate_user_plan(email: str):
    init_auth_db()

    email = _normalize_email(email)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET plan = 'inactive',
                    is_active = FALSE,
                    days_left = 0,
                    auto_renew = FALSE,
                    plan_expires_at = NULL,
                    updated_at = NOW()
                WHERE LOWER(email) = %s;
            """, (email,))

            changed = cur.rowcount

        conn.commit()

    return changed > 0


def update_user(email: str, **fields):
    init_auth_db()

    email = _normalize_email(email)

    allowed = {
        "username",
        "role",
        "plan",
        "is_active",
        "days_left",
        "auto_renew",
        "country",
    }

    updates = []
    values = []

    for key, value in fields.items():
        if key == "password":
            updates.append("password_hash = %s")
            values.append(_hash_password(value))
            continue

        if key in allowed:
            updates.append(f"{key} = %s")
            values.append(value)

    if not updates:
        return False

    updates.append("updated_at = NOW()")
    values.append(email)

    sql = f"""
        UPDATE users
        SET {", ".join(updates)}
        WHERE LOWER(email) = %s;
    """

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, values)
            changed = cur.rowcount

        conn.commit()

    return changed > 0