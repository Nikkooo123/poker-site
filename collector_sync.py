"""Manager-session bridge for complete, locally verified ClubGG snapshots.

No screenshot upload, API keys or browser credentials in the desktop collector.
Incomplete observations must never be treated as an empty club.
"""
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import re
import unicodedata

from psycopg.types.json import Jsonb
from storage import _connect, _insert_table, _normalize_network, init_db
from club_table_lifecycle import init_archive
from currency_codes import normalize_currency
from membership_plans import table_limit
from table_features import ICONS
from brand import OFFICIAL_AFFILIATE_NAME, TELEGRAM_URL


def text(value, maximum=160):
    if not isinstance(value, str) or not value.strip() or len(value)>maximum:
        raise ValueError('A snapshot field is missing or too long.')
    return value.strip()


def timestamp(value):
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise ValueError('A timezone-aware observation time is required.') from None


def validate_snapshot(document, now=None):
    if not isinstance(document,dict) or type(document.get('schema_version')) is not int or document['schema_version'] not in (1,2):
        raise ValueError('Unsupported collector snapshot.')
    required=('complete','club_identity_verified','running_tables_checked','end_of_list_verified','all_rows_verified')
    if any(document.get(key) is not True for key in required):
        raise ValueError('Incomplete or unverified club snapshot. Existing tables were not changed.')
    observed=timestamp(document.get('observed_at'))
    now=now or datetime.now(timezone.utc)
    if observed<now-timedelta(minutes=10) or observed>now+timedelta(seconds=30):
        raise ValueError('Snapshot is stale or has a future observation time.')
    code=text(document.get('club_code'),32)
    if not re.fullmatch(r'[0-9]{1,32}',code):
        raise ValueError('A numeric ClubGG club ID is required.')
    rows=document.get('tables')
    if not isinstance(rows,list) or len(rows)>100:
        raise ValueError('Invalid table list.')
    if not rows and document.get('empty_club_verified') is not True:
        raise ValueError('An empty result needs explicit verified empty-club evidence.')
    active=[]
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError('Invalid table observation.')
        name=text(row.get('table_name'))
        game=row.get('game')
        if game not in ('NLH','PLO4','PLO5','PLO6'):
            raise ValueError('Unrecognized game format.')
        players=text(row.get('players'),8)
        match=re.fullmatch(r'(\d{1,2})/(\d{1,2})',players)
        if not match or not 0<=int(match[1])<=int(match[2])<=10 or int(match[2])<2:
            raise ValueError('Unrecognized player count.')
        blinds=text(row.get('blinds'),80)
        if not re.fullmatch(r'\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)+(?:\(\d+(?:\.\d+)?\))?',blinds):
            raise ValueError('Unrecognized blinds.')
        buyin=text(row.get('buyin'),30)
        try:
            amount=Decimal(buyin)
            if not amount.is_finite() or amount<=0:
                raise InvalidOperation()
        except InvalidOperation:
            raise ValueError('Unrecognized minimum buy-in.') from None
        tags=row.get('tags')
        features_verified=row.get('features_verified',True)
        if type(features_verified) is not bool:raise ValueError('Invalid feature verification state.')
        required_features=row.get('required_features',[])
        if not isinstance(required_features,list) or any(value!='hi_lo' for value in required_features):
            raise ValueError('Unrecognized required game variant.')
        if required_features and game not in ('PLO4','PLO5','PLO6'):
            raise ValueError('Hi-Lo variant requires a verified Omaha format.')
        if not isinstance(tags,list) or len(tags)>40 or any(not isinstance(t,str) or (t not in ICONS and not re.fullmatch(r'vpip [1-9][0-9]?%',t)) for t in tags):
            raise ValueError('Unrecognized table features.')
        confirmed=row.get('confirmed_tags',[])
        if not isinstance(confirmed,list) or len(confirmed)>40 or any(not isinstance(t,str) or (t not in ICONS and not re.fullmatch(r'vpip [1-9][0-9]?%',t)) for t in confirmed):
            raise ValueError('Unrecognized confirmed table feature.')
        small,big,*_=blinds.split('(')[0].split('/')
        if int(match[1])>0 and Decimal(small)>=Decimal('0.25') and Decimal(big)>=Decimal('0.50'):
            active.append(dict(table_name=name,game=game,players=players,blinds=blinds,
                               buyin=buyin,tags=','.join(sorted(set(tags if features_verified else confirmed)|set(required_features))),
                               required_features=','.join(sorted(set(required_features))),
                               features_verified=features_verified,union_name='-none-'))
    return dict(club_code=code, observed_at=observed, tables=active)


def identity(row):
    # Names alone are not identities. A multiset preserves genuinely duplicate tables.
    name=unicodedata.normalize('NFKC',str(row.get('table_name',''))).replace('\u2019',"'").strip()
    variants=tag_set(row.get('tags'))|tag_set(row.get('required_features'))
    return (name,str(row.get('game','')),'hi_lo' in variants,str(row.get('blinds','')).strip(),
            format(Decimal(str(row.get('buyin') or '0')).normalize(),'f'),str(row.get('players','')).split('/')[-1])


def tag_set(value):
    if isinstance(value,list):return set(value)
    return {item.strip() for item in str(value or '').split(',') if item.strip()}


def update_tags(existing,row):
    if row['features_verified']:return row['tags']
    # Partial icon evidence adds verified marks without erasing unread marks.
    known=tag_set(row['tags'])-{'hi_lo'}
    old=tag_set(existing)-{'hi_lo'}
    if any(t.startswith('vpip ') for t in known):old={t for t in old if not t.startswith('vpip ')}
    return ','.join(sorted(old|known|tag_set(row.get('required_features'))))


def reconciliation(existing, incoming):
    available=defaultdict(deque)
    for row in sorted(existing,key=lambda r:r['id']):
        available[identity(row)].append(row)
    updates=[]; creates=[]
    for row in incoming:
        found=available[identity(row)]
        if found:
            updates.append((found.popleft()['id'],row))
        else:
            creates.append(row)
    removed=[row['id'] for group in available.values() for row in group]
    return updates,creates,removed


def apply_snapshot(document):
    snapshot=validate_snapshot(document)
    init_db()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout = '3s'")
            # Schema setup precedes placement locks, preserving consistent lock order.
            cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('tableradar_collector_schema',0))")
            cur.execute('''CREATE TABLE IF NOT EXISTS tableradar_collector_state (
                club_subscription_id BIGINT PRIMARY KEY REFERENCES club_subscriptions(id) ON DELETE CASCADE,
                observed_at TIMESTAMPTZ NOT NULL, snapshot JSONB NOT NULL)''')
            cur.execute('''SELECT c.*,a.document->>'host_tier' AS host_tier
                FROM club_subscriptions c LEFT JOIN tableradar_accounts a ON a.email=lower(trim(c.owner_email))
                WHERE c.club_code=%s AND c.plan='host' AND c.status='active'
                AND COALESCE(c.access_expires_at,c.expires_at::timestamptz)>clock_timestamp()
                FOR UPDATE OF c''',(snapshot['club_code'],))
            clubs=cur.fetchall()
            clubs=[c for c in clubs if _normalize_network(c.get('application'))=='clubgg']
            if len(clubs)!=1:
                raise ValueError('Club ID must match exactly one active ClubGG placement.')
            club=clubs[0]; selected=club['id']
            if len(snapshot['tables'])>table_limit(club):
                raise ValueError('Snapshot exceeds this club placement table limit.')
            currency=normalize_currency(club.get('currency'))
            cur.execute('SELECT observed_at,snapshot FROM tableradar_collector_state WHERE club_subscription_id=%s',(selected,))
            previous=cur.fetchone()
            if previous and previous['observed_at']>=snapshot['observed_at']:
                if previous['observed_at']==snapshot['observed_at'] and previous['snapshot']==document:
                    return dict(applied=False,reason='already applied')
                raise ValueError('An equal or newer snapshot has already been applied.')
            cur.execute('SELECT * FROM poker_tables WHERE club_subscription_id=%s ORDER BY id FOR UPDATE',(selected,))
            if club.get('union_name') is not None:
                for row in snapshot['tables']:row['union_name']=club['union_name']
            existing=cur.fetchall();by_id={r['id']:r for r in existing}
            updates,creates,removed=reconciliation(existing,snapshot['tables'])
            if removed:
                init_archive(cur)
                cur.execute('''WITH removed AS (
                    DELETE FROM poker_tables WHERE club_subscription_id=%s AND id=ANY(%s) RETURNING *
                ) INSERT INTO tableradar_removed_club_tables(reason,document)
                SELECT 'Absent from verified active ClubGG snapshot',to_jsonb(removed) FROM removed''',(selected,removed))
            for table_id,row in updates:
                cur.execute('''UPDATE poker_tables SET players=%s,seats=%s,tags=%s,union_name=%s,updated_at=NOW()
                    WHERE id=%s AND club_subscription_id=%s''',
                    (row['players'],row['players'].split('/')[1],update_tags(by_id[table_id].get('tags'),row),row['union_name'],table_id,selected))
            for row in creates:
                _insert_table(cur,dict(row,club=club['club_name'],network='clubgg',currency=currency,
                    club_subscription_id=selected,owner_name=club.get('owner_name') or '',
                    owner_telegram=club.get('owner_telegram') or '',affiliate_name=OFFICIAL_AFFILIATE_NAME,
                    affiliate_telegram=TELEGRAM_URL))
            cur.execute('''INSERT INTO tableradar_collector_state(club_subscription_id,observed_at,snapshot)
                VALUES(%s,%s,%s) ON CONFLICT(club_subscription_id) DO UPDATE
                SET observed_at=excluded.observed_at,snapshot=excluded.snapshot''',
                (selected,snapshot['observed_at'],Jsonb(document)))
        conn.commit()
    return dict(applied=True,active=len(snapshot['tables']),updated=len(updates),added=len(creates),removed=len(removed))
