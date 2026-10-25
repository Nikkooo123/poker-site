from membership_plans import PLANS, product, product_key, host_tier
"""Persistent one-time payment orders. No grant until verified provider settlement."""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from psycopg.types.json import Jsonb
import account_repository as repository
from crypto_provider import completed_invoice_matches
from host_lifecycle import prepare_paid_host

PRICES = {key: spec['price'] for key, spec in PLANS.items()}
PRICES['host'] = PLANS['host_pro']['price']  # Legacy checkout URL aliases Host Pro.


def initialize():
    with repository.connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS tableradar_crypto_orders(
            id TEXT PRIMARY KEY,email TEXT NOT NULL,document JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())''')
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS tableradar_crypto_invoice_unique ON tableradar_crypto_orders((document->>'invoice_id')) WHERE document->>'invoice_id' IS NOT NULL")


def create(email, plan, coin, network, environment='sandbox'):
    if plan not in PRICES:
        raise ValueError('Unknown membership')
    if environment not in ('sandbox','production'):
        raise ValueError('Invalid payment environment')
    spec = product(plan)
    order = dict(id=str(uuid.uuid4()),email=email.strip().lower(),plan=spec['role'],product=product_key(plan),host_tier=spec.get('tier'),table_limit=spec['table_limit'],environment=environment,
                 price_amount=PRICES[plan],price_currency='USD',pay_currency=coin,network=network,
                 status='creating',fulfilled=False)
    with repository.connection() as conn:
        if not conn.execute('SELECT email FROM tableradar_accounts WHERE email=%s',(order['email'],)).fetchone():
            raise ValueError('Account no longer exists')
        conn.execute('INSERT INTO tableradar_crypto_orders(id,email,document) VALUES(%s,%s,%s)',(order['id'],order['email'],Jsonb(order)))
    return order


def get(order_id, email=None):
    with repository.connection() as conn:
        row = conn.execute('SELECT email,document FROM tableradar_crypto_orders WHERE id=%s',(order_id,)).fetchone()
        if not row or (email is not None and row[0] != email.strip().lower()):
            return None
        return row[1]


def find_by_invoice(invoice_id):
    with repository.connection() as conn:
        row = conn.execute("SELECT document FROM tableradar_crypto_orders WHERE document->>'invoice_id'=%s",(invoice_id,)).fetchone()
        return row[0] if row else None


def attach_invoice(order_id, invoice):
    with repository.connection() as conn:
        row=conn.execute('SELECT document FROM tableradar_crypto_orders WHERE id=%s FOR UPDATE',(order_id,)).fetchone()
        if not row:
            raise ValueError('Order not found')
        order=dict(row[0])
        if order.get('invoice_id'):
            return order
        # Verify the provider associated the newly created invoice with our exact order.
        expected=dict(order,invoice_id=invoice.get('id'))
        candidate=dict(invoice,status='completed',status_context=None)
        if not invoice.get('id') or not completed_invoice_matches(candidate,expected):
            raise ValueError('Provider invoice details do not match this order')
        order.update(invoice_id=invoice['id'],status=invoice.get('status','new'),
                     hosted_page_url=invoice.get('hosted_page_url',''),expires_at=invoice.get('expires_at',''))
        conn.execute('UPDATE tableradar_crypto_orders SET document=%s,updated_at=NOW() WHERE id=%s',(Jsonb(order),order_id))
        return order


def settle(order_id, invoice):
    """Caller supplies a freshly retrieved, authenticated API invoice, never a browser claim."""
    with repository.connection() as conn:
        row=conn.execute('SELECT document FROM tableradar_crypto_orders WHERE id=%s FOR UPDATE',(order_id,)).fetchone()
        if not row:
            raise ValueError('Order not found')
        order=dict(row[0])
        if order.get('fulfilled'):
            return order  # Duplicate callbacks never extend the membership twice.
        if not completed_invoice_matches(invoice,order):
            # Preserve unresolved/underpaid/pending status without granting access.
            if invoice.get('id')==order.get('invoice_id'):
                order['status']='review_required' if invoice.get('status')=='completed' else str(invoice.get('status') or 'pending')[:40]
                order['status_context']=str(invoice.get('status_context') or '')[:80]
                conn.execute('UPDATE tableradar_crypto_orders SET document=%s,updated_at=NOW() WHERE id=%s',(Jsonb(order),order_id))
            return order
        if order.get('environment') != 'production':
            # Sandbox completion is evidence for the test order only, never paid membership.
            order.update(status='test_completed',fulfilled=True,fulfilled_at=datetime.now(timezone.utc).isoformat())
            conn.execute('UPDATE tableradar_crypto_orders SET document=%s,updated_at=NOW() WHERE id=%s',(Jsonb(order),order_id))
            return order
        account=conn.execute('SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE',(order['email'],)).fetchone()
        if not account:
            raise ValueError('Paid order needs operator review: account missing')
        user=dict(account[0])
        now=datetime.now(timezone.utc)
        if order['plan'] == 'host':
            purchased_tier = order.get('host_tier') or 'pro'
            current_expiry = user.get('membership_expires_at') or user.get('test_expires_at')
            still_live = False
            try:
                still_live = bool(user.get('is_active') and datetime.fromisoformat(current_expiry) > now)
            except (TypeError, ValueError):
                pass
            # Never silently downgrade/upgrade an already paid service period.
            if user.get('plan') == 'host' and not user.get('membership_test_enabled') and (still_live or int(user.get('host_paid_days') or 0)>0) and host_tier(user) != purchased_tier:
                order.update(status='review_required',status_context='host_tier_change')
                conn.execute('UPDATE tableradar_crypto_orders SET document=%s,updated_at=NOW() WHERE id=%s',(Jsonb(order),order_id))
                return order
            user['host_tier'] = purchased_tier
        start=now
        if user.get('is_active') and user.get('plan')==order['plan'] and not user.get('membership_test_enabled'):
            try:
                expiry=datetime.fromisoformat(user.get('membership_expires_at',''))
                if expiry.tzinfo is not None:
                    start=max(now,expiry)
            except (ValueError,TypeError):
                pass
        pending_host = order['plan']=='host' and start==now
        if pending_host:
            prepare_paid_host(user, now)
            user.update(membership_source='crypto', last_payment_order=order_id)
            order.update(status='completed',fulfilled=True,fulfilled_at=now.isoformat(),host_awaiting_launch=True)
        else:
            expiry=start+timedelta(days=30)
            user.update(plan=order['plan'],role=order['plan'],is_active=True,auto_renew=False,
                        membership_test_enabled=False,membership_source='crypto',membership_expires_at=expiry.isoformat(),
                        plan_started_at=user.get('plan_started_at') or now.strftime('%d/%m/%Y'),plan_expires_at=expiry.strftime('%d/%m/%Y'),
                        last_payment_order=order_id,days_left=int((expiry-now).total_seconds()+86399)//86400)
            if order['plan']=='host' and user.get('manual_subscription_id'):
                conn.execute("UPDATE club_subscriptions SET expires_at=%s,access_expires_at=%s,updated_at=NOW() WHERE id=%s AND lower(owner_email)=%s AND status='active'",(expiry.date(),expiry,user['manual_subscription_id'],order['email']))
            order.update(status='completed',fulfilled=True,fulfilled_at=now.isoformat(),membership_expires_at=expiry.isoformat())
        conn.execute('UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s',(Jsonb(user),order['email']))
        conn.execute('UPDATE tableradar_crypto_orders SET document=%s,updated_at=NOW() WHERE id=%s',(Jsonb(order),order_id))
        return order
