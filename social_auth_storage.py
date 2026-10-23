"""Atomic social identities and short-lived, one-use login flow bindings."""
import hashlib
import re
import secrets
from psycopg.types.json import Jsonb
import account_repository as repository
from auth.auth_storage import _default_user


class PublicAuthError(ValueError):
    pass


def ensure_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS tableradar_social_identities (
        provider TEXT NOT NULL, subject TEXT NOT NULL, email TEXT NOT NULL REFERENCES tableradar_accounts(email) ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY(provider,subject), UNIQUE(provider,email))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tableradar_social_flows (
        state_hash TEXT PRIMARY KEY, browser_hash TEXT NOT NULL, provider TEXT NOT NULL,
        document JSONB NOT NULL, expires_at TIMESTAMPTZ NOT NULL)""")


def _digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def create_flow(state, browser, provider, user=None):
    data = dict(purpose='connect' if user else 'signin', email=(user or {}).get('email',''), credential_version=(user or {}).get('credential_version',''))
    with repository.connection() as conn:
        ensure_schema(conn)
        conn.execute('DELETE FROM tableradar_social_flows WHERE expires_at<NOW() OR (browser_hash=%s AND provider=%s)',(_digest(browser),provider))
        conn.execute("INSERT INTO tableradar_social_flows(state_hash,browser_hash,provider,document,expires_at) VALUES(%s,%s,%s,%s,NOW()+INTERVAL '10 minutes')",(_digest(state),_digest(browser),provider,Jsonb(data)))


def consume_flow(state, browser, provider):
    if not state or not browser:
        raise PublicAuthError('Sign-in expired. Start again.')
    with repository.connection() as conn:
        ensure_schema(conn)
        row = conn.execute('DELETE FROM tableradar_social_flows WHERE state_hash=%s AND browser_hash=%s AND provider=%s AND expires_at>NOW() RETURNING document',(_digest(state),_digest(browser),provider)).fetchone()
        if not row:
            raise PublicAuthError('Sign-in expired. Start again.')
        return dict(row[0])


def linked_providers(email):
    with repository.connection() as conn:
        ensure_schema(conn)
        return {row[0] for row in conn.execute('SELECT provider FROM tableradar_social_identities WHERE email=%s',(email,)).fetchall()}


def _verified_email(conn, user, email, provider):
    from player_access import enabled
    if enabled() and user['email'] == email and not user.get('email_verified_at'):
        from datetime import datetime, timezone
        user.update(email_verified_at=datetime.now(timezone.utc).isoformat(), email_verification_source=provider)
        conn.execute('UPDATE tableradar_accounts SET document=%s,updated_at=NOW() WHERE email=%s', (Jsonb(user), user['email']))
    return user


def resolve_identity(provider, subject, email, name, connect=None):
    email = str(email or '').strip().lower()
    subject = str(subject or '')
    if provider not in ('google','discord') or not subject or len(subject)>255 or any(ch.isspace() or not ch.isprintable() for ch in subject):
        raise PublicAuthError('The provider did not return a valid account identity.')
    if len(email)>254 or not re.fullmatch(r'[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+',email):
        raise PublicAuthError('A verified email address is required.')
    with repository.connection() as conn:
        ensure_schema(conn)
        # Serialise identical identities, then lock the canonical account before attaching.
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(provider+':'+subject,))
        row = conn.execute('SELECT a.document FROM tableradar_social_identities i JOIN tableradar_accounts a ON a.email=i.email WHERE i.provider=%s AND i.subject=%s FOR UPDATE OF a',(provider,subject)).fetchone()
        if row:
            user = dict(row[0])
            if connect and (user['email']!=connect['email'] or user.get('credential_version','')!=connect.get('credential_version','')):
                raise PublicAuthError('This provider account is already connected elsewhere, or your session changed.')
            return _verified_email(conn, user, email, provider)
        if connect:
            if email != connect['email']:
                raise PublicAuthError('Choose a provider account with the same verified email as your TableRadar account.')
            row = conn.execute('SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE',(email,)).fetchone()
            if not row or row[0].get('credential_version','')!=connect.get('credential_version',''):
                raise PublicAuthError('Your session changed. Sign in again.')
            user = dict(row[0])
        else:
            if conn.execute('SELECT email FROM tableradar_accounts WHERE email=%s',(email,)).fetchone():
                raise PublicAuthError('An account with this email already exists. Sign in with your password, then connect this provider in My Account.')
            user = _default_user(email,str(name or '').strip()[:100] or email)
            user.update(password_login_enabled=False,credential_version=secrets.token_urlsafe(24))
            inserted = conn.execute('INSERT INTO tableradar_accounts(email,document) VALUES(%s,%s) ON CONFLICT(email) DO NOTHING RETURNING email',(email,Jsonb(user))).fetchone()
            if not inserted:
                raise PublicAuthError('This email already has an account. Sign in first to connect it.')
        if conn.execute('SELECT subject FROM tableradar_social_identities WHERE provider=%s AND email=%s',(provider,email)).fetchone():
            raise PublicAuthError('A different account from this provider is already connected.')
        conn.execute('INSERT INTO tableradar_social_identities(provider,subject,email) VALUES(%s,%s,%s)',(provider,subject,email))
        return _verified_email(conn, user, email, provider)
