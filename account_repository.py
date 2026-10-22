"""Persistent account documents in the site's existing PostgreSQL database.

Migration is explicit: existing runtime accounts must be copied before deploying
this backend. Database failures never silently fall back to an obsolete JSON file.
"""
import os
from contextlib import contextmanager

import psycopg
from psycopg.types.json import Jsonb


def enabled():
    return bool(os.getenv("DATABASE_URL"))


@contextmanager
def connection():
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=10) as conn:
        yield conn


def load():
    with connection() as conn:
        return [row[0] for row in conn.execute("SELECT document FROM tableradar_accounts ORDER BY email").fetchall()]


def insert(user):
    with connection() as conn:
        row = conn.execute(
            "INSERT INTO tableradar_accounts (email, document) VALUES (%s,%s) ON CONFLICT (email) DO NOTHING RETURNING email",
            (user["email"], Jsonb(user)),
        ).fetchone()
        return row is not None


def upsert_many(users):
    # Compatibility helper: preserve records omitted by a caller; no bulk deletes.
    with connection() as conn:
        for user in users:
            conn.execute(
                "INSERT INTO tableradar_accounts(email,document) VALUES (%s,%s) ON CONFLICT(email) DO UPDATE SET document=EXCLUDED.document, updated_at=NOW()",
                (user["email"], Jsonb(user)),
            )


def mutate(email, transform):
    with connection() as conn:
        row = conn.execute("SELECT document FROM tableradar_accounts WHERE email=%s FOR UPDATE", (email,)).fetchone()
        if row is None:
            return False
        user = transform(dict(row[0]))
        conn.execute("UPDATE tableradar_accounts SET document=%s, updated_at=NOW() WHERE email=%s", (Jsonb(user), email))
        return True
