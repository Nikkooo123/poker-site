"""Reset a manager's own Host test; identity and staff access are never changed."""
import uuid
from datetime import datetime, timezone
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
import account_repository as repository


def reset_own_host(email):
    email = str(email).strip().lower()
    with repository.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE', (email,))
            row = cur.fetchone()
            if not row or row['document'].get('staff_role') != 'manager':
                raise ValueError('A personal manager account is required.')
            original = row['document']
            cur.execute('SELECT * FROM club_subscriptions WHERE lower(trim(owner_email))=%s ORDER BY id FOR UPDATE', (email,))
            subscriptions = cur.fetchall()
            ids = [s['id'] for s in subscriptions]
            cur.execute('SELECT * FROM poker_tables WHERE club_subscription_id=ANY(%s) ORDER BY id FOR UPDATE', (ids,))
            tables = cur.fetchall()
            backup = dict(account=original, subscriptions=subscriptions, tables=tables)
            # A database-local snapshot is committed atomically with the reset.
            import json
            backup = json.loads(json.dumps(backup, default=str))
            cur.execute('CREATE TABLE IF NOT EXISTS tableradar_host_reset_backups (id TEXT PRIMARY KEY, email TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), document JSONB NOT NULL)')
            backup_id = str(uuid.uuid4())
            cur.execute('INSERT INTO tableradar_host_reset_backups(id,email,document) VALUES(%s,%s,%s)', (backup_id,email,Jsonb(backup)))
            cur.execute('DELETE FROM poker_tables WHERE club_subscription_id=ANY(%s)', (ids,))
            cur.execute('DELETE FROM club_subscriptions WHERE id=ANY(%s) AND lower(trim(owner_email))=%s', (ids,email))
            updated = dict(original)
            for key in ('club_application','manual_subscription_id','host_tier','host_service_state','host_paid_days','host_paid_at','host_launched_at','host_approved_submission','host_notification','membership_source','membership_before_test'):
                updated.pop(key,None)
            updated.update(plan='inactive',role='member',is_active=False,days_left=0,auto_renew=False,
                           membership_test_enabled=False,test_expires_at='',membership_expires_at='',
                           plan_started_at='',plan_expires_at='',host_test_reset_at=datetime.now(timezone.utc).isoformat())
            assert updated['staff_role'] == original['staff_role'] == 'manager'
            cur.execute('UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s', (Jsonb(updated),email))
    return dict(backup_id=backup_id, subscriptions=len(subscriptions), tables=len(tables))
