from membership_plans import host_name, table_limit
from currency_codes import normalize_currency
import os
from datetime import date, datetime, timedelta, timezone
from psycopg.types.json import Jsonb
from club_table_lifecycle import init_archive, remove_linked_tables

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
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT '';")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS manager_created BOOLEAN NOT NULL DEFAULT FALSE;")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS owner_contact_email TEXT;")
            cur.execute("ALTER TABLE club_subscriptions ADD COLUMN IF NOT EXISTS club_code TEXT;")
        conn.commit()

    _DB_READY = True


def load_club_subscriptions():
    init_club_subscriptions_db()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    c.*,
                    (SELECT a.document->'club_application'->>'club_code' FROM tableradar_accounts a
                     WHERE a.email=lower(trim(c.owner_email))
                     AND a.document->>'manual_subscription_id'=c.id::text) AS request_club_code,
                    CASE WHEN access_expires_at IS NOT NULL THEN GREATEST(0, CEIL(EXTRACT(EPOCH FROM (access_expires_at - clock_timestamp())) / 86400))::int ELSE GREATEST(0, expires_at - CURRENT_DATE) END AS days_left
                FROM club_subscriptions c
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
        if item.get("status") == "preparing":
            item.update(days_left=0, started_at_display="Not started", expires_at_display="After launch")

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
            cur.execute("""SELECT c.id,c.club_name,c.application,c.currency,c.club_code,c.expires_at,c.access_expires_at,
                a.document->>'host_tier' AS host_tier,
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
        result.append(dict(host_plan=host_name(row),table_limit=table_limit(row),subscription_id=row['id'],club_name=row['club_name'],application=row['application'],currency=normalize_currency(row.get('currency'),required=False),
                           expires_at_display=_date_display(row['expires_at']),
                           club_code=row.get('club_code') if row.get('club_code') is not None else (row['submitted_code'] if same_club else '')))
    return result


def add_club_subscription(
    club_name: str = "",
    owner_name: str = "",
    owner_telegram: str = "",
    owner_email: str = "",
    application: str = "",
    plan: str = "host",
    duration_days: int = 30,
    notes: str = "",
    currency: str = "",
    club_code: str = "",
):
    init_club_subscriptions_db()

    # A manager-created placement is independent of customer registration/payment.
    # Missing contacts must never cause an account to be created or granted access.
    email = _safe(owner_email).strip().lower()
    currency = normalize_currency(currency) if _safe(currency).strip() else ""
    plan = _safe(plan).strip().lower() or "host"
    if plan != "host":
        raise ValueError("Choose the Host plan or leave it blank.")
    try:
        days = int(_safe(duration_days).strip() or "30")
    except ValueError:
        raise ValueError("Days must be a whole number, or leave it blank for 30 days.") from None
    if not 1 <= days <= 3660:
        raise ValueError("Days must be between 1 and 3660, or leave it blank for 30 days.")
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=days)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO club_subscriptions
                (club_name,owner_name,owner_telegram,owner_email,application,plan,status,started_at,expires_at,notes,access_expires_at,manager_created,currency,club_code)
                VALUES (%s,%s,%s,%s,%s,'host','active',%s,%s,%s,%s,TRUE,%s,%s) RETURNING id""",
                (_safe(club_name).strip(),_safe(owner_name).strip(),_safe(owner_telegram).strip(),email,_safe(application).strip(),now.date(),expiry.date(),_safe(notes).strip(),expiry,currency,_safe(club_code).strip()))
            new_id = cur.fetchone()["id"]
    return new_id


def edit_club_subscription(subscription_id, *, club_name="", owner_name="", owner_telegram="",
                           owner_email="", application="", currency="", club_code="", notes=""):
    """Edit listing metadata only; contact email never transfers an owner's account/access."""
    init_club_subscriptions_db()
    values = {key: _safe(value).strip() for key, value in dict(club_name=club_name,
        owner_name=owner_name,owner_telegram=owner_telegram,owner_email=owner_email,
        application=application,currency=currency,club_code=club_code,notes=notes).items()}
    for key, value in values.items():
        if len(value) > (4000 if key == 'notes' else 320):
            raise ValueError("Club details are too long.")
    values['currency'] = normalize_currency(currency) if values['currency'] else ''
    from storage import _normalize_network
    network = _normalize_network(application) if values['application'] else ''
    if network and network not in ('clubgg', 'xpoker', 'pppoker', 'pokerbros'):
        raise ValueError("Choose a supported application or leave it blank.")
    import re
    telegram = values['owner_telegram']
    if re.fullmatch(r'@[A-Za-z0-9_]{3,64}', telegram):
        telegram = 'https://t.me/' + telegram[1:]
    if telegram and not re.fullmatch(r'https://t\.me/[A-Za-z0-9_]{3,64}/?', telegram):
        raise ValueError("Use a Telegram @username or https://t.me/ link, or leave it blank.")
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM club_subscriptions WHERE id=%s FOR UPDATE", (int(subscription_id),))
            if not cur.fetchone():
                raise ValueError("This club no longer exists. Refresh the page.")
            cur.execute("""UPDATE club_subscriptions SET club_name=%s,owner_name=%s,owner_telegram=%s,
                owner_contact_email=%s,application=%s,currency=%s,club_code=%s,notes=%s,updated_at=NOW()
                WHERE id=%s""", tuple(values[key] for key in ('club_name','owner_name','owner_telegram',
                    'owner_email','application','currency','club_code','notes')) + (int(subscription_id),))
            cur.execute("""UPDATE poker_tables SET club=%s,owner_name=%s,owner_telegram=%s,
                network=%s,platform=%s,currency=%s,updated_at=NOW() WHERE club_subscription_id=%s""",
                (values['club_name'],values['owner_name'],telegram,network,network,values['currency'],int(subscription_id)))


def _request_matches_placement(user, club, sub):
    """An owner's newer request may describe a different club; do not remove it by email alone."""
    if not club:
        return False
    for state in (user, user.get("friends_preview_host") or {}):
        if (str(state.get("manual_subscription_id", "")) == str(sub["id"])
                and state.get("host_approved_submission")
                and state.get("host_approved_submission") == club.get("submitted_at")):
            return True
    normalize = lambda value: "".join(char for char in _safe(value).casefold() if char.isalnum())
    name = normalize(club.get("club_name"))
    application = normalize(sub.get("application"))
    return bool(name and name == normalize(sub.get("club_name"))
                and (application == normalize(club.get("application"))
                     or (not application and sub.get("status") == "preparing")))


def _unlink_deleted_club(cur, sub):
    """Remove only the request explicitly linked to this placement, never other owners/clubs."""
    email = _safe(sub.get("owner_email")).strip().lower()
    if not email:
        return
    cur.execute("SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE", (email,))
    row = cur.fetchone()
    if not row or not isinstance(row.get("document"), dict):
        return
    user = dict(row["document"])
    linked = str(user.get("manual_subscription_id", "")) == str(sub["id"])
    preview = dict(user.get("friends_preview_host") or {})
    linked_preview = str(preview.get("manual_subscription_id", "")) == str(sub["id"])
    if not linked and not linked_preview:
        return
    if _request_matches_placement(user, user.get("club_application") or {}, sub):
        user.pop("club_application", None)
    if linked:
        user.pop("manual_subscription_id", None)
        user.pop("host_approved_submission", None)
        if user.get("plan") == "host":
            user.update(is_active=False, days_left=0, auto_renew=False, host_service_state="disabled", host_paid_days=0)
            if user.get("membership_test_enabled"):
                user["test_expires_at"] = ""
        else:
            # A former Host can now have a different paid membership. Remove stale
            # club linkage without disabling that unrelated current entitlement.
            user.pop("host_service_state", None)
            user.pop("host_paid_days", None)
    if linked_preview:
        user.pop("friends_preview_host", None)
    cur.execute("UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s", (Jsonb(user), email))


def _delete_placement(cur, sub):
    _unlink_deleted_club(cur, sub)
    init_archive(cur)
    remove_linked_tables(cur, [int(sub["id"])], "Club permanently removed by manager")
    cur.execute("DELETE FROM club_subscriptions WHERE id=%s", (int(sub["id"]),))


def _sync_linked_account(cur, sub, expiry=None, inactive=False):
    email = (sub.get("owner_email") or "").strip().lower()
    cur.execute("SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE", (email,))
    account = cur.fetchone()
    if not account:
        return
    user = dict(account["document"])
    if user.get("manual_subscription_id") != sub["id"] or user.get("membership_source") not in ("manager", "crypto"):
        return
    if inactive:
        user.update(is_active=False,days_left=0,auto_renew=False,host_service_state="disabled",host_paid_days=0)
        if user.get("membership_test_enabled"):
            user["test_expires_at"] = ""
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
                if sub.get("status") == "preparing":
                    raise ValueError("Start this listing from Club requests before extending its service period.")
                now = datetime.now(timezone.utc)
                old = sub.get("access_expires_at") or datetime.combine(sub["expires_at"], datetime.min.time(), timezone.utc)
                expiry = max(old, now) + timedelta(days=int(days))
                cur.execute("UPDATE club_subscriptions SET expires_at=%s,access_expires_at=%s,status='active',updated_at=NOW() WHERE id=%s", (expiry.date(),expiry,int(subscription_id)))
                _sync_linked_account(cur,sub,expiry=expiry)
            elif action == "delete":
                _delete_placement(cur, sub)
            elif action == "disable":
                _sync_linked_account(cur,sub,inactive=True)
                init_archive(cur)
                remove_linked_tables(cur,[int(subscription_id)],'Club placement disabled')
                cur.execute("UPDATE club_subscriptions SET status='inactive',updated_at=NOW() WHERE id=%s", (int(subscription_id),))


def extend_club_subscription(subscription_id: int, days: int = 30):
    _change_subscription(subscription_id, "extend", days)


def disable_club_subscription(subscription_id: int):
    _change_subscription(subscription_id, "disable")


def delete_club_subscription(subscription_id: int):
    _change_subscription(subscription_id, "delete")


def delete_club_request_and_subscription(email: str, submitted_at: str):
    """Manager-only entry point: request and its explicitly linked placement are one transaction."""
    init_club_subscriptions_db()
    email = _safe(email).strip().lower()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE", (email,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Account no longer exists. Refresh Club requests.")
            user = dict(row["document"])
            club = user.get("club_application") or {}
            if not club or club.get("submitted_at", "") != submitted_at:
                raise ValueError("The request changed. Reload Club requests before deleting it.")
            preview = user.get("friends_preview_host") or {}
            linked_ids = []
            for value in (user.get("manual_subscription_id"), preview.get("manual_subscription_id")):
                try:
                    selected = int(value)
                    if selected not in linked_ids:
                        linked_ids.append(selected)
                except (ValueError, TypeError):
                    pass
            placements = []
            if linked_ids:
                cur.execute("SELECT * FROM club_subscriptions WHERE id=ANY(%s) AND lower(trim(owner_email))=%s ORDER BY id FOR UPDATE", (linked_ids, email))
                placements = cur.fetchall()
            for sub in placements:
                if _request_matches_placement(user, club, sub):
                    _delete_placement(cur, sub)
            # Pending requests can exist without a placement. Re-read after linked cleanup.
            cur.execute("SELECT document FROM tableradar_accounts WHERE email=%s", (email,))
            latest = dict(cur.fetchone()["document"])
            current = latest.get("club_application") or {}
            if current and current.get("submitted_at", "") == submitted_at:
                latest.pop("club_application", None)
                cur.execute("UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s", (Jsonb(latest), email))

