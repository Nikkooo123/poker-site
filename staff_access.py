"""Staff permissions are separate from customer Player/Host memberships."""
import os
import secrets

from auth.auth_storage import get_user_by_email


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
    # The signed session is set only by successful staff login. The old unsigned
    # admin_auth cookie is deliberately ignored for every permission decision.
    if request.session.get("staff_role") == "manager":
        return "manager"
    email = request.session.get("user_email")
    user = get_user_by_email(email) if email else None
    if user and request.session.get('credential_version','') != user.get('credential_version',''):
        return None
    role = (user or {}).get("staff_role")
    return role if role in ("table_admin", "manager") else None


def is_manager(request):
    return staff_role(request) == "manager"


def can_edit_tables(request):
    return staff_role(request) in ("table_admin", "manager")
