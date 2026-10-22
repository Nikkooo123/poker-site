import os
from datetime import date, datetime, timedelta, timezone
from psycopg.types.json import Jsonb

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

            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS access_expires_at TIMESTAMPTZ;")
        conn.commit()

    _DB_READY = True


def load_club_subscriptions():
    init_club_subscriptions_db()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    *,
                    CASE WHEN access_expires_at IS NOT NULL THEN GREATEST(0, CEIL(EXTRACT(EPOCH FROM (access_expires_at - clock_timestamp())) / 86400))::int ELSE GREATEST(0, expires_at - CURRENT_DATE) END AS days_left
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


def load_active_operator_clubs():
    """Limited read-only worklist; no owner emails, notes or account documents leave storage."""
    init_club_subscriptions_db()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT c.club_name,c.application,c.expires_at,c.access_expires_at,
                a.document->'club_application'->>'club_name' AS submitted_club,
                a.document->'club_application'->>'application' AS submitted_application,
                a.document->'club_application'->>'club_code' AS submitted_code
                FROM club_subscriptions c LEFT JOIN tableradar_accounts a ON a.email=lower(trim(c.owner_email))
                WHERE c.plan='host' AND c.status='active'
                AND COALESCE(c.access_expires_at,c.expires_at::timestamptz)>clock_timestamp()
                ORDER BY c.expires_at,c.club_name,c.id""")
            rows=cur.fetchall()
    result=[]
    normalize=lambda value: ''.join(ch for ch in str(value or '').casefold() if ch.isalnum())
    for row in rows:
        same_club=normalize(row['club_name'])==normalize(row['submitted_club']) and normalize(row['application'])==normalize(row['submitted_application'])
        result.append(dict(club_name=row['club_name'],application=row['application'],
                           expires_at_display=_date_display(row['expires_at']),
                           club_code=row['submitted_code'] if same_club else ''))
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

    email = owner_email.strip().lower()
    if plan != "host" or not email or "@" not in email or not club_name.strip():
        raise ValueError("Enter the registered owner's email and club name. This form activates Host access.")
    if int(duration_days) != 30:
        raise ValueError("New Host memberships start with 30 days. Use Extend for renewals.")
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=30)
    with _connect() as conn:
        with conn.cursor() as cur:
            # Lock the account first: simultaneous submissions cannot create duplicate grants.
            cur.execute("SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE", (email,))
            account = cur.fetchone()
            if not account:
                raise ValueError("No registered account matches this email. Ask the owner to create an account first.")
            user = dict(account["document"])
            cur.execute("SELECT id FROM club_subscriptions WHERE lower(owner_email)=%s AND plan='host' AND status='active' AND COALESCE(access_expires_at, expires_at::timestamptz)>NOW()", (email,))
            if cur.fetchone():
                raise ValueError("This owner already has an active club subscription. Use Extend on the existing entry.")
            cur.execute("""INSERT INTO club_subscriptions
                (club_name,owner_name,owner_telegram,owner_email,application,plan,status,started_at,expires_at,notes,access_expires_at)
                VALUES (%s,%s,%s,%s,%s,'host','active',%s,%s,%s,%s) RETURNING id""",
                (club_name.strip(),owner_name.strip(),owner_telegram.strip(),email,application.strip(),now.date(),expiry.date(),notes.strip(),expiry))
            new_id = cur.fetchone()["id"]
            user.update(plan="host",role="host",is_active=True,days_left=30,auto_renew=False,
                        membership_test_enabled=False,membership_source="manager",manual_subscription_id=new_id,
                        membership_expires_at=expiry.isoformat(),plan_started_at=now.strftime("%d/%m/%Y"),
                        plan_expires_at=expiry.strftime("%d/%m/%Y"))
            # Staff permissions, passwords, favourites and the owner's application are preserved.
            cur.execute("UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s", (Jsonb(user),email))
    return new_id


def _sync_linked_account(cur, sub, expiry=None, inactive=False):
    email = (sub.get("owner_email") or "").strip().lower()
    cur.execute("SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE", (email,))
    account = cur.fetchone()
    if not account:
        return
    user = dict(account["document"])
    if user.get("manual_subscription_id") != sub["id"] or user.get("membership_source") != "manager":
        return
    if inactive:
        user.update(is_active=False,days_left=0,auto_renew=False)
    else:
        user.update(plan="host",role="host",is_active=True,auto_renew=False,membership_test_enabled=False,
                    membership_expires_at=expiry.isoformat(),plan_expires_at=expiry.strftime("%d/%m/%Y"))
    cur.execute("UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s", (Jsonb(user),email))


def _change_subscription(subscription_id, action, days=30):
    init_club_subscriptions_db()
    if not 1 <= int(days) <= 366:
        raise ValueError("Extension must be between 1 and 366 days.")
    with _connect() as conn:
        with conn.cursor() as cur:
            # Same lock order as activation avoids an account/subscription deadlock.
            cur.execute("SELECT * FROM club_subscriptions WHERE id=%s", (int(subscription_id),))
            sub = cur.fetchone()
            if not sub:
                raise ValueError("Subscription no longer exists. Refresh this page.")
            cur.execute("SELECT email FROM tableradar_accounts WHERE email=%s FOR UPDATE", ((sub.get("owner_email") or "").strip().lower(),))
            cur.execute("SELECT * FROM club_subscriptions WHERE id=%s FOR UPDATE", (int(subscription_id),))
            sub = cur.fetchone()
            if not sub:
                raise ValueError("Subscription no longer exists. Refresh this page.")
            if action == "extend":
                now = datetime.now(timezone.utc)
                old = sub.get("access_expires_at") or datetime.combine(sub["expires_at"], datetime.min.time(), timezone.utc)
                expiry = max(old, now) + timedelta(days=int(days))
                cur.execute("UPDATE club_subscriptions SET expires_at=%s,access_expires_at=%s,status='active',updated_at=NOW() WHERE id=%s", (expiry.date(),expiry,int(subscription_id)))
                _sync_linked_account(cur,sub,expiry=expiry)
            elif action == "delete":
                _sync_linked_account(cur,sub,inactive=True)
                cur.execute("DELETE FROM club_subscriptions WHERE id=%s", (int(subscription_id),))
            elif action == "disable":
                _sync_linked_account(cur,sub,inactive=True)
                cur.execute("UPDATE club_subscriptions SET status='inactive',updated_at=NOW() WHERE id=%s", (int(subscription_id),))


def extend_club_subscription(subscription_id: int, days: int = 30):
    _change_subscription(subscription_id, "extend", days)


def disable_club_subscription(subscription_id: int):
    _change_subscription(subscription_id, "disable")


def delete_club_subscription(subscription_id: int):
    _change_subscription(subscription_id, "delete")

