"""Host payment entitlement is separate from the listing's service clock."""
from currency_codes import normalize_currency
from club_request_changes import reviewed_request
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
    if not awaiting_launch(user):
        user.pop('manual_subscription_id', None)
        user.pop('host_approved_submission', None)
    user.update(plan='host', role='host', is_active=False, days_left=0, auto_renew=False,
                membership_test_enabled=False, host_service_state='preparing',
                host_paid_days=int(user.get('host_paid_days') or 0) + 30,
                host_paid_at=now.isoformat(), host_notification='', membership_expires_at='',
                plan_started_at='', plan_expires_at='')


def review_host_request(email, submitted_at, status, review_note):
    """Approval and placement activation share one account/subscription transaction."""
    if status == 'approved':
        return launch_host(email, submitted_at, approve=True, review_note=review_note)
    if status not in ('pending', 'needs_changes') or len(review_note)>1000:
        raise ValueError('Invalid review.')
    def transform(user):
        club=user.get('club_application') or {}
        if not club or club.get('deleted_at') or club.get('submitted_at','') != submitted_at:
            raise ValueError('The request changed. Reload the review page.')
        user['club_application']=reviewed_request(club,status=status,review_note=review_note.strip(),reviewed_at=datetime.now(timezone.utc).isoformat())
        return user
    if not repository.mutate(email.strip().lower(),transform):
        raise ValueError('Account no longer exists.')


def launch_host(email, submitted_at, approve=False, review_note=''):
    """Manager-only caller; approval version is idempotent, not a renewal button."""
    email=email.strip().lower()
    if len(review_note)>1000:
        raise ValueError('The operator note is too long.')
    with repository.connection() as conn:
        row=conn.execute('SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE',(email,)).fetchone()
        user=dict(row[0]) if row else {}
        club=user.get('club_application') or {}
        if not club or club.get('deleted_at') or club.get('submitted_at','') != submitted_at or (not approve and club.get('status') != 'approved'):
            raise ValueError('The request changed. Reload the review page.')
        now=datetime.now(timezone.utc)
        if approve:
            club=reviewed_request(club,status='approved',review_note=review_note.strip(),reviewed_at=now.isoformat())
            user['club_application']=club
        if user.get('host_approved_submission') == submitted_at or (not approve and user.get('host_service_state') == 'live'):
            if approve:
                conn.execute('UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s',(Jsonb(user),email))
            return False
        preparing=awaiting_launch(user)
        active=False
        try:
            expiry=datetime.fromisoformat(user.get('test_expires_at','') if user.get('membership_test_enabled') else user.get('membership_expires_at',''))
            active=(user.get('plan')=='host' and user.get('is_active') is True and expiry>now)
        except (ValueError,TypeError):
            pass
        if not preparing and not (approve and active):
            raise ValueError('Confirmed Host access is required before approving a listing.')
        if not all(str(club.get(key) or '').strip() for key in ('owner_name','telegram','club_name','club_code','application')):
            raise ValueError('The owner must provide their name or screen name, Telegram, club name and Club ID before approval.')
        currency = normalize_currency(club.get('currency'))
        days=int(user['host_paid_days']) if preparing else 30
        expiry=now+timedelta(days=days)
        sub_id=user.get('manual_subscription_id')
        sub=conn.execute("SELECT id FROM club_subscriptions WHERE id=%s AND lower(trim(owner_email))=%s AND plan='host' FOR UPDATE",(sub_id,email)).fetchone() if sub_id else None
        if not sub:
            matches=conn.execute("SELECT id FROM club_subscriptions WHERE lower(trim(owner_email))=%s AND plan='host' AND status IN ('active','preparing') ORDER BY id DESC FOR UPDATE",(email,)).fetchall()
            if len(matches)>1:
                raise ValueError('Multiple placements exist for this owner. Review Club subscriptions first.')
            sub=matches[0] if matches else None
        if sub:
            sub_id=sub[0]
            conn.execute("UPDATE club_subscriptions SET club_name=%s,owner_name=%s,owner_telegram=%s,owner_email=%s,application=%s,currency=%s,status='active',started_at=%s,expires_at=%s,access_expires_at=%s,updated_at=NOW() WHERE id=%s",(club['club_name'],club['owner_name'],club['telegram'],email,club['application'],currency,now.date(),expiry.date(),expiry,sub_id))
        else:
            sub_id=conn.execute("""INSERT INTO club_subscriptions(club_name,owner_name,owner_telegram,owner_email,application,currency,plan,status,started_at,expires_at,access_expires_at,notes)
                VALUES(%s,%s,%s,%s,%s,%s,'host','active',%s,%s,%s,%s) RETURNING id""",(club['club_name'],club['owner_name'],club['telegram'],email,club['application'],currency,now.date(),expiry.date(),expiry,'Private owner preview - no payment' if user.get('membership_test_enabled') else '')).fetchone()[0]
        user.update(host_service_state='live',host_paid_days=0,host_launched_at=now.isoformat(),host_approved_submission=submitted_at,
                    manual_subscription_id=sub_id,is_active=True,days_left=days,auto_renew=False,
                    membership_expires_at=expiry.isoformat(),plan_started_at=now.strftime('%d/%m/%Y'),plan_expires_at=expiry.strftime('%d/%m/%Y'),
                    host_notification=f"Your club request was approved and your placement is active. Your service period started on {now.strftime('%d/%m/%Y')}.")
        if user.get('membership_test_enabled'):
            user.update(test_expires_at=expiry.isoformat(),membership_source='manager')
        conn.execute('UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s',(Jsonb(user),email))
        return True


def delete_club_request(email, submitted_at):
    """Remove from the request queue while retaining placement identity and paid entitlement."""
    def transform(user):
        club=user.get('club_application') or {}
        if not club or club.get('submitted_at','') != submitted_at:
            raise ValueError('The request changed. Reload the review page.')
        if not club.get('deleted_at'):
            user['club_application']=dict(club,deleted_at=datetime.now(timezone.utc).isoformat(),previous_status=club.get('status','pending'),status='archived')
        return user
    if not repository.mutate(email.strip().lower(),transform):
        raise ValueError('Account no longer exists.')
