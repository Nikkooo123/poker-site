"""Persistent one-use verification and one Player trial per phone, under row locks."""
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from psycopg.types.json import Jsonb
import account_repository as repository


def digest(kind, value):
    secret = os.environ.get('TRIAL_PHONE_PEPPER', '')
    if len(secret) < 32:
        raise ValueError('Verification is not configured.')
    return hmac.new(secret.encode(), (kind + ':' + value).encode(), hashlib.sha256).hexdigest()


def now():
    return datetime.now(timezone.utc)


def ensure_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS tableradar_verification_challenges (
        id TEXT PRIMARY KEY, email TEXT NOT NULL, kind TEXT NOT NULL, document JSONB NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tableradar_trial_claims (
        phone_digest TEXT PRIMARY KEY, email_digest TEXT UNIQUE NOT NULL,
        claimed_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tableradar_verification_limits (
        bucket TEXT PRIMARY KEY, hits INTEGER NOT NULL, expires_at TIMESTAMPTZ NOT NULL)""")


def _account(conn, email):
    row = conn.execute('SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE', (email,)).fetchone()
    if not row:
        raise ValueError('Sign in again.')
    return dict(row[0])


def _write(conn, user):
    conn.execute('UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s', (Jsonb(user), user['email']))


def _limit(conn, key, maximum, period):
    current = now()
    bucket = digest('rate', key) + ':' + str(int(current.timestamp()) // period)
    row = conn.execute("""INSERT INTO tableradar_verification_limits(bucket,hits,expires_at)
        VALUES(%s,1,%s) ON CONFLICT(bucket) DO UPDATE SET hits=tableradar_verification_limits.hits+1
        RETURNING hits""", (bucket, current + timedelta(seconds=period * 2))).fetchone()
    return row[0] <= maximum


def create(email, kind, target, credential_version, ip=''):
    if kind not in ('email', 'phone'):
        raise ValueError('Invalid verification type.')
    failure = ''
    challenge = None
    with repository.connection() as conn:
        ensure_schema(conn)
        user = _account(conn, email)
        if user.get('credential_version', '') != credential_version:
            raise ValueError('Your session changed. Sign in again.')
        if kind == 'phone' and not user.get('email_verified_at'):
            raise ValueError('Verify your email first.')
        if kind == 'phone' and user.get('player_trial_expires_at'):
            raise ValueError('This account has already received its Player trial.')
        if kind == 'email' and (target != user['email'] or user.get('email_verified_at')):
            raise ValueError('This email does not need verification.')
        if kind == 'phone':
            # Reject already bound identifiers before sending another paid SMS.
            # The unique ledger is permanent; trial expiry does not free a number.
            used = conn.execute(
                'SELECT 1 FROM tableradar_trial_claims WHERE phone_digest=%s OR email_digest=%s',
                (digest('phone', target), digest('trial-email', email)),
            ).fetchone()
            if used:
                raise ValueError('This email or phone is already linked to a Player trial. Contact support.')
        # Account lock serialises resends; IP is a coarse secondary rate limit, not identity.
        allowed = _limit(conn, kind + ':account:' + email, 3, 3600)
        if ip:
            allowed = _limit(conn, kind + ':ip:' + ip, 100, 3600) and allowed
        if kind == 'phone':
            allowed = _limit(conn, 'phone:global', 50, 86400) and allowed
            allowed = _limit(conn, 'phone:target:' + target, 5, 86400) and allowed
        recent = conn.execute("SELECT id FROM tableradar_verification_challenges WHERE email=%s AND kind=%s AND created_at>NOW()-INTERVAL '60 seconds'", (email, kind)).fetchone()
        if not allowed or recent:
            failure = 'Please wait before requesting another code. Verification requests are limited.'
        else:
            conn.execute('DELETE FROM tableradar_verification_challenges WHERE expires_at<NOW() OR (email=%s AND kind=%s)', (email, kind))
            conn.execute('DELETE FROM tableradar_verification_limits WHERE expires_at<NOW()')
            identifier = str(uuid.uuid4())
            code = str(secrets.randbelow(1000000)).zfill(6) if kind == 'email' else ''
            document = dict(target=target, credential_version=credential_version, attempts=0,
                            status='sending', code_hash=digest('code', identifier + ':' + code) if code else '')
            conn.execute('INSERT INTO tableradar_verification_challenges(id,email,kind,document,expires_at) VALUES(%s,%s,%s,%s,%s)',
                (identifier, email, kind, Jsonb(document), now() + timedelta(minutes=10)))
            challenge = dict(id=identifier, code=code)
    # Raising after transaction commit preserves rate-limit counters on rejected sends.
    if failure:
        raise ValueError(failure)
    return challenge


def delivered(email, identifier, sid=''):
    with repository.connection() as conn:
        row = conn.execute('SELECT document FROM tableradar_verification_challenges WHERE id=%s AND email=%s AND expires_at>NOW() FOR UPDATE', (identifier, email)).fetchone()
        if row:
            document = dict(row[0], status='ready', sid=sid)
            conn.execute('UPDATE tableradar_verification_challenges SET document=%s WHERE id=%s', (Jsonb(document), identifier))


def failed(email, identifier):
    with repository.connection() as conn:
        conn.execute("UPDATE tableradar_verification_challenges SET document=%s WHERE id=%s AND email=%s", (Jsonb(dict(status='failed')), identifier, email))


def _attempt(conn, email, kind, version):
    # Same lock order as create/finalize: account, then challenge.
    user = _account(conn, email)
    if user.get('credential_version', '') != version:
        return None
    row = conn.execute('SELECT id,document FROM tableradar_verification_challenges WHERE email=%s AND kind=%s AND expires_at>NOW() ORDER BY created_at DESC LIMIT 1 FOR UPDATE', (email, kind)).fetchone()
    if not row:
        return None
    identifier, document = row[0], dict(row[1])
    if document.get('status') != 'ready' or document.get('credential_version', '') != version or document.get('attempts', 0) >= 5:
        return None
    document['attempts'] += 1
    conn.execute('UPDATE tableradar_verification_challenges SET document=%s WHERE id=%s', (Jsonb(document), identifier))
    return user, identifier, document


def verify_email(email, code, version):
    success = False
    with repository.connection() as conn:
        ensure_schema(conn)
        attempted = _attempt(conn, email, 'email', version)
        if attempted:
            user, identifier, document = attempted
            if hmac.compare_digest(document['code_hash'], digest('code', identifier + ':' + str(code))) and document['target'] == email:
                user.update(email_verified_at=now().isoformat(), email_verification_source='email_code')
                _write(conn, user)
                conn.execute('DELETE FROM tableradar_verification_challenges WHERE id=%s', (identifier,))
                success = True
    return success


def phone_attempt(email, version):
    with repository.connection() as conn:
        ensure_schema(conn)
        attempted = _attempt(conn, email, 'phone', version)
        if not attempted:
            return None
        user, identifier, document = attempted
        if not user.get('email_verified_at'):
            return None
        return dict(id=identifier, phone=document['target'], sid=document['sid'])


def claim_trial(email, identifier, version):
    """Only call after the server has authenticated the provider's approved check."""
    with repository.connection() as conn:
        ensure_schema(conn)
        user = _account(conn, email)
        row = conn.execute('SELECT document FROM tableradar_verification_challenges WHERE id=%s AND email=%s AND kind=%s AND expires_at>NOW() FOR UPDATE', (identifier, email, 'phone')).fetchone()
        if (not row or not user.get('email_verified_at') or user.get('credential_version', '') != version):
            return False
        document = row[0]
        if document.get('status') != 'ready' or document.get('credential_version', '') != version or user.get('player_trial_expires_at'):
            return False
        phone_hash, email_hash = digest('phone', document['target']), digest('trial-email', email)
        started = now()
        expiry = started + timedelta(days=14)
        granted = conn.execute('INSERT INTO tableradar_trial_claims(phone_digest,email_digest,claimed_at,expires_at) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING phone_digest',
            (phone_hash, email_hash, started, expiry)).fetchone()
        conn.execute('DELETE FROM tableradar_verification_challenges WHERE id=%s', (identifier,))
        if not granted:
            return False
        user.update(phone_verified_at=started.isoformat(), trial_phone_digest=phone_hash,
                    player_trial_started_at=started.isoformat(), player_trial_expires_at=expiry.isoformat())
        _write(conn, user)
        # No paid plan, staff role, Host entitlement, renewal or provider credential changes.
        return True
