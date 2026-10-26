"""Remove only explicitly linked tables whose club placement is unavailable."""


def init_archive(cur):
    cur.execute('''CREATE TABLE IF NOT EXISTS tableradar_removed_club_tables (
        id BIGSERIAL PRIMARY KEY, removed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        reason TEXT NOT NULL, document JSONB NOT NULL)''')


def remove_linked_tables(cur, subscription_ids, reason):
    if not subscription_ids:
        return 0
    cur.execute('''WITH removed AS (
        DELETE FROM poker_tables WHERE club_subscription_id=ANY(%s) RETURNING *
    ) INSERT INTO tableradar_removed_club_tables(reason,document)
      SELECT %s,to_jsonb(removed) FROM removed''', (list(subscription_ids),reason))
    return max(0,cur.rowcount)


def cleanup_unavailable_tables(cur):
    # Renewals and table creation lock the same placement. A renewed row is
    # rechecked by PostgreSQL after waiting for its lock, before being selected.
    cur.execute('''SELECT c.id FROM club_subscriptions c
        WHERE (c.plan IS DISTINCT FROM 'host' OR c.status IS DISTINCT FROM 'active'
        OR COALESCE(c.access_expires_at,c.expires_at::timestamptz,'-infinity'::timestamptz)<=clock_timestamp())
        AND EXISTS(SELECT 1 FROM poker_tables t WHERE t.club_subscription_id=c.id)
        ORDER BY c.id FOR UPDATE OF c''')
    ids=[row['id'] for row in cur.fetchall()]
    removed=remove_linked_tables(cur,ids,'Club placement expired or inactive')
    # Repair previously orphaned rows without guessing ownership from club names.
    # Legacy/unlinked/demo tables are deliberately outside this operation.
    cur.execute('''WITH removed AS (
        DELETE FROM poker_tables t WHERE t.club_subscription_id IS NOT NULL
        AND NOT EXISTS(SELECT 1 FROM club_subscriptions c WHERE c.id=t.club_subscription_id)
        RETURNING t.*
    ) INSERT INTO tableradar_removed_club_tables(reason,document)
      SELECT 'Club placement previously deleted',to_jsonb(removed) FROM removed''')
    return removed+max(0,cur.rowcount)
