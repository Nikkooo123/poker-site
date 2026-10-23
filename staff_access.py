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


_activity_schema_ready = False


def _activity_schema():
    global _activity_schema_ready
    if _activity_schema_ready or not repository.enabled():
        return
    with repository.connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('tableradar_activity_schema',0))")
        conn.execute("""CREATE TABLE IF NOT EXISTS tableradar_customer_activity (
            email TEXT PRIMARY KEY REFERENCES tableradar_accounts(email) ON DELETE CASCADE,
            tracking_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_login_at TIMESTAMPTZ, last_seen_at TIMESTAMPTZ,
            login_count BIGINT NOT NULL DEFAULT 0,
            active_seconds BIGINT NOT NULL DEFAULT 0,
            last_beat_at TIMESTAMPTZ, last_beat_active BOOLEAN NOT NULL DEFAULT FALSE, last_page TEXT NOT NULL DEFAULT '')""")
    _activity_schema_ready = True


def record_customer_login(email):
    if not repository.enabled():
        return
    try:
        _activity_schema()
        with repository.connection() as conn:
            conn.execute("""INSERT INTO tableradar_customer_activity(email,last_login_at,last_seen_at,login_count)
                SELECT email,NOW(),NOW(),1 FROM tableradar_accounts WHERE email=%s
                ON CONFLICT(email) DO UPDATE SET last_login_at=NOW(),last_seen_at=NOW(),
                login_count=tableradar_customer_activity.login_count+1""",(email,))
    except Exception:
        # Analytics must never break authentication or membership access.
        pass


def activity_statistics_enabled(user):
    return isinstance(user,dict) and user.get('activity_statistics_enabled') is True


def set_activity_statistics(email, enabled):
    """Save an explicit, optional choice without changing account access."""
    from datetime import datetime,timezone
    fields=dict(activity_statistics_enabled=bool(enabled),activity_statistics_updated_at=datetime.now(timezone.utc).isoformat(),activity_statistics_version=1)
    if repository.enabled():
        _activity_schema()
        with repository.connection() as conn:
            row=conn.execute('SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE',(email,)).fetchone()
            if not row:
                raise ValueError('Account no longer exists.')
            user=dict(row[0]);user.update(fields)
            conn.execute('UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s',(Jsonb(user),email))
            # Never bridge active time across a withdrawn or newly granted choice.
            conn.execute('UPDATE tableradar_customer_activity SET last_beat_at=NULL,last_beat_active=FALSE WHERE email=%s',(email,))
        return
    if not update_user(email,**fields):
        raise ValueError('Account no longer exists.')


def record_customer_activity(email, active, section):
    if not repository.enabled():
        return
    _activity_schema()
    allowed = {'Tables','My account','Host dashboard','Membership','Support','Staff workspace','Information'}
    section = section if section in allowed else 'Information'
    with repository.connection() as conn:
        # Lock the current preference before any telemetry write. Withdrawal waits
        # for an in-flight beat; later beats cannot restart it from a stale tab.
        account=conn.execute('SELECT document FROM tableradar_accounts WHERE email=%s FOR SHARE',(email,)).fetchone()
        if not account or not activity_statistics_enabled(account[0]):
            return False
        conn.execute("""INSERT INTO tableradar_customer_activity(email)
            SELECT email FROM tableradar_accounts WHERE email=%s ON CONFLICT(email) DO NOTHING""",(email,))
        row=conn.execute('SELECT last_beat_at,last_beat_active FROM tableradar_customer_activity WHERE email=%s FOR UPDATE',(email,)).fetchone()
        if not row:
            return
        current=conn.execute('SELECT clock_timestamp()').fetchone()[0]
        elapsed=(current-row[0]).total_seconds() if row[0] else None
        if elapsed is not None and elapsed < 10:
            return
        credit=min(30,max(0,int(elapsed))) if active and row[1] and elapsed is not None and elapsed <= 75 else 0
        conn.execute("""UPDATE tableradar_customer_activity SET last_beat_at=%s,last_beat_active=%s,
            active_seconds=active_seconds+%s,
            last_seen_at=CASE WHEN %s THEN %s ELSE last_seen_at END,
            last_page=CASE WHEN %s THEN %s ELSE last_page END WHERE email=%s""",
            (current,active,credit,active,current,active,section,email))


def customer_activity_summary():
    if not repository.enabled():
        return {}
    try:
        _activity_schema()
        with repository.connection() as conn:
            cursor=conn.execute('SELECT email,tracking_started_at,last_login_at,last_seen_at,login_count,active_seconds,last_page FROM tableradar_customer_activity')
            columns=[column.name for column in cursor.description]
            return {row[0]:dict(zip(columns,row)) for row in cursor.fetchall()}
    except Exception:
        return {}


def render_activity_tracker():
    return "<script>(function(){\nif(window.top!==window.self||window.trActivityStarted)return;\nwindow.trActivityStarted=true;\nlet csrf='',lastInput=Date.now(),busy=false;\n['pointerdown','keydown','scroll','touchstart','focus'].forEach(name=>window.addEventListener(name,()=>{lastInput=Date.now();},{passive:true}));\nfunction section(){const p=location.pathname;if(p==='/')return 'Tables';if(p==='/profile'||p==='/verify-account')return 'My account';if(p.includes('host'))return 'Host dashboard';if(p.startsWith('/pay'))return 'Membership';if(p.includes('chat')||p==='/contact')return 'Support';if(p.startsWith('/manager')||p.startsWith('/admin'))return 'Staff workspace';return 'Information';}\nasync function beat(){if(!csrf||busy)return;busy=true;try{const response=await fetch('/account/activity',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({csrf:csrf,active:document.visibilityState==='visible'&&document.hasFocus()&&Date.now()-lastInput<60000?'1':'0',section:section()})});if(response.status===403){csrf='';}}catch(e){}finally{busy=false;}}\nfetch('/account/activity',{credentials:'same-origin',cache:'no-store'}).then(r=>r.ok?r.json():null).then(data=>{if(data&&data.enabled&&data.csrf){csrf=data.csrf;beat();setInterval(beat,30000);}}).catch(()=>{});\n})();</script>"
