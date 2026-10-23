"""Staff permissions are separate from customer Player/Host memberships."""
import os
import secrets

from auth.auth_storage import get_user_by_email, load_users, update_user
import account_repository as repository
from psycopg.types.json import Jsonb


def session_secret():
    configured = os.getenv("SESSION_SECRET")
    if configured:
        return configured
    if os.getenv("DATABASE_URL"):
        import psycopg
        with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=10) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS tableradar_internal_settings (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
            conn.execute("INSERT INTO tableradar_internal_settings(name,value) VALUES ('session_secret',%s) ON CONFLICT(name) DO NOTHING", (secrets.token_urlsafe(48),))
            return conn.execute("SELECT value FROM tableradar_internal_settings WHERE name='session_secret'").fetchone()[0]
    return secrets.token_urlsafe(48)


def staff_role(request):
    # Roles come only from the current account record, never a cached role claim.
    email = request.session.get("user_email")
    if not email or not request.session.get("username"):
        return None
    user = get_user_by_email(email)
    if user and request.session.get('credential_version','') != user.get('credential_version',''):
        return None
    role = (user or {}).get("staff_role")
    return role if role in ("table_admin", "manager") else None


def is_manager(request):
    return staff_role(request) == "manager"


def can_edit_tables(request):
    return staff_role(request) in ("table_admin", "manager")


def set_staff_role(email, role):
    """Serialize staff changes and prevent removal of the final manager."""
    email = str(email or '').strip().lower()
    if role not in ('', 'table_admin', 'manager'):
        raise ValueError('Invalid staff role.')
    def changed(user, managers):
        if not user:
            raise ValueError('Account no longer exists.')
        if user.get('staff_role') == 'manager' and role != 'manager' and managers <= 1:
            raise ValueError('Keep at least one manager account. Assign another manager before removing this role.')
        return dict(user, staff_role=role)
    if repository.enabled():
        with repository.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('tableradar_staff_roles',0))")
            row = conn.execute('SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE', (email,)).fetchone()
            managers = conn.execute("SELECT count(*) FROM tableradar_accounts WHERE document->>'staff_role'='manager'").fetchone()[0]
            user = changed(dict(row[0]) if row else None, managers)
            conn.execute('UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s', (Jsonb(user),email))
        return True
    users = load_users()
    user = next((user for user in users if user.get('email') == email), None)
    changed(user, sum(user.get('staff_role') == 'manager' for user in users))
    return update_user(email, staff_role=role)
