"""Placement-locked active table coverage; no account or membership writes."""
import re
from membership_plans import table_limit, host_name


def occupied(players):
    match = re.match(r'^\s*(\d+)', str(players or ''))
    return int(match[1]) if match else 0


def require_capacity(cur, subscription_id, exclude_table_id=0):
    # All inserts/reactivations lock the same placement before counting rows.
    cur.execute("""SELECT a.document->>'host_tier' AS host_tier
        FROM club_subscriptions c LEFT JOIN tableradar_accounts a
        ON a.email=lower(trim(c.owner_email)) WHERE c.id=%s FOR UPDATE OF c""", (subscription_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError('The club placement no longer exists.')
    limit = table_limit(row)
    cur.execute("""SELECT COUNT(*) AS count FROM poker_tables
        WHERE club_subscription_id=%s AND id<>%s
        AND COALESCE(NULLIF(regexp_replace(split_part(players,'/',1),'[^0-9]','','g'),''),'0')::numeric>0""",
        (subscription_id, exclude_table_id))
    if cur.fetchone()['count'] >= limit:
        raise ValueError(f'{host_name(row)} covers up to {limit} active tables. Close an existing table or contact support for more coverage.')
