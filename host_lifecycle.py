"""Host payment entitlement is separate from the listing's service clock."""
from datetime import datetime, timedelta, timezone
from psycopg.types.json import Jsonb
import account_repository as repository


def awaiting_launch(user):
    return (user.get('plan') == 'host' and not user.get('membership_test_enabled')
            and user.get('membership_source') in ('manager', 'crypto')
            and user.get('host_service_state') == 'preparing'
            and int(user.get('host_paid_days') or 0) > 0)


def has_host_access(user):
    return user.get('plan') == 'host' and (awaiting_launch(user) or user.get('is_active') is True)


def prepare_paid_host(user, now):
    """Only called inside the confirmed-payment/manual-confirmation transaction."""
    user.update(plan='host', role='host', is_active=False, days_left=0, auto_renew=False,
                membership_test_enabled=False, host_service_state='preparing',
                host_paid_days=int(user.get('host_paid_days') or 0) + 30,
                host_paid_at=now.isoformat(), host_notification='', membership_expires_at='',
                plan_started_at='', plan_expires_at='')


def launch_host(email, submitted_at):
    """Manager-only caller; lock account then subscription. Repeated launch is a no-op."""
    email=email.strip().lower()
    with repository.connection() as conn:
        row=conn.execute('SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE',(email,)).fetchone()
        user=dict(row[0]) if row else {}
        club=user.get('club_application') or {}
        if club.get('submitted_at','') != submitted_at or club.get('status') != 'approved':
            raise ValueError('Approve the current request before starting the listing. Refresh if the request changed.')
        if user.get('host_service_state') == 'live':
            return False
        if not awaiting_launch(user):
            raise ValueError('A confirmed Host payment awaiting launch is required. Existing active periods stay unchanged.')
        if not club.get('owner_name', '').strip() or not club.get('telegram', '').strip():
            raise ValueError('The owner must provide their name or screen name and Telegram before launch.')
        now=datetime.now(timezone.utc)
        expiry=now+timedelta(days=int(user['host_paid_days']))
        sub_id=user.get('manual_subscription_id')
        sub=conn.execute('SELECT id,status FROM club_subscriptions WHERE id=%s AND lower(owner_email)=%s FOR UPDATE', (sub_id,email)).fetchone() if sub_id else None
        if sub and sub[1] != 'preparing':
            raise ValueError('The linked placement changed. Review Club subscriptions first.')
        if sub:
            conn.execute("UPDATE club_subscriptions SET club_name=%s,application=%s,status='active',started_at=%s,expires_at=%s,access_expires_at=%s,updated_at=NOW() WHERE id=%s",(club['club_name'],club['application'],now.date(),expiry.date(),expiry,sub_id))
        else:
            sub_id=conn.execute("""INSERT INTO club_subscriptions(club_name,owner_email,application,plan,status,started_at,expires_at,access_expires_at)
                VALUES(%s,%s,%s,'host','active',%s,%s,%s) RETURNING id""",(club['club_name'],email,club['application'],now.date(),expiry.date(),expiry)).fetchone()[0]
        user.update(host_service_state='live',host_paid_days=0,host_launched_at=now.isoformat(),
                    manual_subscription_id=sub_id,is_active=True,days_left=int((expiry-now).total_seconds()/86400),
                    membership_expires_at=expiry.isoformat(),plan_started_at=now.strftime('%d/%m/%Y'),plan_expires_at=expiry.strftime('%d/%m/%Y'),
                    host_notification=f"Your club placement is ready. Your service period started on {now.strftime('%d/%m/%Y')}.")
        conn.execute('UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s',(Jsonb(user),email))
        return True
