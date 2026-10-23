"""Private support cases; original roots/messages retained, history never deleted."""
import uuid
import account_repository as repository

_initialized = False


def initialize():
    global _initialized
    if _initialized:
        with repository.connection() as conn:
            _migrate_messages(conn)
        return
    with repository.connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('tableradar_support_cases_schema',0))")
        conn.execute("""CREATE TABLE IF NOT EXISTS tableradar_support_threads(
            id BIGSERIAL PRIMARY KEY,email TEXT NOT NULL UNIQUE,status TEXT NOT NULL DEFAULT 'waiting',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
        conn.execute("""CREATE TABLE IF NOT EXISTS tableradar_support_messages(
            id BIGSERIAL PRIMARY KEY,thread_id BIGINT NOT NULL REFERENCES tableradar_support_threads(id),
            sender TEXT NOT NULL CHECK(sender IN ('customer','staff')),actor TEXT NOT NULL,
            body TEXT NOT NULL,nonce TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(thread_id,nonce))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS tableradar_support_cases(
            id TEXT PRIMARY KEY,thread_id BIGINT NOT NULL REFERENCES tableradar_support_threads(id),
            legacy_root BIGINT UNIQUE,status TEXT NOT NULL DEFAULT 'open',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            closed_at TIMESTAMPTZ)""")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS tableradar_support_one_open_case ON tableradar_support_cases(thread_id) WHERE status='open'")
        conn.execute('ALTER TABLE tableradar_support_messages ADD COLUMN IF NOT EXISTS case_id TEXT REFERENCES tableradar_support_cases(id)')
        conn.execute('CREATE INDEX IF NOT EXISTS tableradar_support_case_messages ON tableradar_support_messages(case_id,id)')
        _migrate_messages(conn)
    _initialized = True


def _migrate_messages(conn):
    # Also catches an in-flight old worker send during a rolling deployment.
    roots = conn.execute('SELECT id FROM tableradar_support_threads t WHERE EXISTS(SELECT 1 FROM tableradar_support_messages m WHERE m.thread_id=t.id AND m.case_id IS NULL)').fetchall()
    for (root,) in roots:
        conn.execute('SELECT id FROM tableradar_support_threads WHERE id=%s FOR UPDATE', (root,))
        if not conn.execute('SELECT 1 FROM tableradar_support_messages WHERE thread_id=%s AND case_id IS NULL LIMIT 1', (root,)).fetchone():
            continue
        row = conn.execute("SELECT id FROM tableradar_support_cases WHERE thread_id=%s AND status='open' ORDER BY created_at DESC LIMIT 1", (root,)).fetchone()
        if row:
            case_id = row[0]
        else:
            existing = conn.execute('SELECT 1 FROM tableradar_support_cases WHERE thread_id=%s LIMIT 1', (root,)).fetchone()
            case_id = str(uuid.uuid4()) if existing else str(uuid.uuid5(uuid.NAMESPACE_URL, 'tableradar-support-legacy:' + str(root)))
            conn.execute('INSERT INTO tableradar_support_cases(id,thread_id,legacy_root,created_at,updated_at) SELECT %s,%s,%s,COALESCE(MIN(created_at),NOW()),COALESCE(MAX(created_at),NOW()) FROM tableradar_support_messages WHERE thread_id=%s AND case_id IS NULL', (case_id, root, None if existing else root, root))
        conn.execute('UPDATE tableradar_support_messages SET case_id=%s WHERE thread_id=%s AND case_id IS NULL', (case_id, root))


def _case(conn, identifier, email=None, lock=False):
    identifier = str(identifier or '')
    legacy = int(identifier) if identifier.isascii() and identifier.isdigit() and len(identifier)<18 else -1
    query = """SELECT c.id,t.email,c.status,c.thread_id FROM tableradar_support_cases c
        JOIN tableradar_support_threads t ON t.id=c.thread_id
        WHERE (c.id=%s OR c.legacy_root=%s)"""
    args = [identifier, legacy]
    if email is not None:
        query += ' AND t.email=%s'
        args.append(email)
    if lock:
        query += ' FOR UPDATE OF c'
    row = conn.execute(query, tuple(args)).fetchone()
    return dict(id=row[0],email=row[1],state=row[2],root=row[3]) if row else None


def _messages(conn, case_id, before=None):
    if before is not None:
        rows = conn.execute('SELECT id,sender,body,created_at FROM tableradar_support_messages WHERE case_id=%s AND id<%s ORDER BY id DESC LIMIT 100', (case_id, before)).fetchall()
    else:
        rows = conn.execute('SELECT id,sender,body,created_at FROM tableradar_support_messages WHERE case_id=%s ORDER BY id DESC LIMIT 100', (case_id,)).fetchall()
    return [dict(id=r[0],sender=r[1],body=r[2],created_at=r[3].isoformat()) for r in reversed(rows)]


def _detail(conn, item, before=None):
    messages = _messages(conn, item['id'], before)
    last_id = conn.execute('SELECT COALESCE(MAX(id),0) FROM tableradar_support_messages WHERE case_id=%s', (item['id'],)).fetchone()[0]
    first_id = messages[0]['id'] if messages else 0
    older = bool(first_id and conn.execute('SELECT 1 FROM tableradar_support_messages WHERE case_id=%s AND id<%s LIMIT 1',(item['id'],first_id)).fetchone())
    return dict(id=item['id'],email=item['email'],state=item['state'],status=item['state'],
                messages=messages,last_message_id=last_id,has_older=older)


def customer_state(email, selected='', before=None):
    with repository.connection() as conn:
        rows = conn.execute('SELECT c.id,c.status,c.created_at FROM tableradar_support_cases c JOIN tableradar_support_threads t ON t.id=c.thread_id WHERE t.email=%s ORDER BY c.created_at DESC,c.id DESC LIMIT 200', (email,)).fetchall()
        cases = [dict(id=r[0],state=r[1],created_at=r[2].isoformat()) for r in rows]
        active = next((c['id'] for c in cases if c['state']=='open'), '')
        identifier = selected or active or (cases[0]['id'] if cases else '')
        item = _case(conn, identifier, email) if identifier else None
        if selected and not item:
            return None
        return dict(cases=cases,active_case_id=active,conversation=_detail(conn,item,before) if item else None)


def customer_messages(email):
    state = customer_state(email)
    return (state['conversation'] or {}).get('messages', [])


def staff_messages(identifier, before=None):
    with repository.connection() as conn:
        item = _case(conn, identifier)
        return _detail(conn,item,before) if item else None


def inbox(state='open'):
    if state not in ('open','finished','archived'):
        raise ValueError('Invalid conversation filter.')
    with repository.connection() as conn:
        rows = conn.execute("""SELECT c.id,t.email,c.status,c.updated_at,
            (SELECT m.body FROM tableradar_support_messages m WHERE m.case_id=c.id ORDER BY m.id DESC LIMIT 1),
            (SELECT COUNT(*) FROM tableradar_support_messages m WHERE m.case_id=c.id AND m.sender='customer'
             AND m.id>COALESCE((SELECT MAX(s.id) FROM tableradar_support_messages s WHERE s.case_id=c.id AND s.sender='staff'),0))
            FROM tableradar_support_cases c JOIN tableradar_support_threads t ON t.id=c.thread_id
            WHERE c.status=%s ORDER BY 6 DESC,c.updated_at DESC LIMIT 200""", (state,)).fetchall()
        return [dict(id=r[0],email=r[1],state=r[2],status='waiting' if r[5] else 'replied',
                     updated_at=r[3].isoformat(),preview=(r[4] or '')[:120],unanswered=int(r[5])) for r in rows]


def waiting_count():
    with repository.connection() as conn:
        return conn.execute("""SELECT COUNT(*) FROM tableradar_support_cases c WHERE c.status='open' AND
            COALESCE((SELECT MAX(m.id) FROM tableradar_support_messages m WHERE m.case_id=c.id AND m.sender='customer'),0)>
            COALESCE((SELECT MAX(m.id) FROM tableradar_support_messages m WHERE m.case_id=c.id AND m.sender='staff'),0)""").fetchone()[0]


def send(email, body, nonce, sender='customer', actor='', thread_id=None):
    body = body.strip()
    if not 1 <= len(body) <= 2000:
        raise ValueError('Write a message between 1 and 2,000 characters.')
    try:
        nonce = str(uuid.UUID(nonce))
    except (ValueError,TypeError,AttributeError):
        raise ValueError('Refresh the chat and try again.')
    if sender not in ('customer','staff'):
        raise ValueError('Invalid sender.')
    with repository.connection() as conn:
        if sender=='customer':
            conn.execute('INSERT INTO tableradar_support_threads(email) VALUES(%s) ON CONFLICT(email) DO NOTHING', (email,))
            root = conn.execute('SELECT id FROM tableradar_support_threads WHERE email=%s FOR UPDATE', (email,)).fetchone()[0]
            previous = conn.execute('SELECT case_id FROM tableradar_support_messages WHERE thread_id=%s AND nonce=%s', (root,nonce)).fetchone()
            if previous:
                return previous[0]
            if thread_id:
                item = _case(conn, thread_id, email, lock=True)
                if not item:
                    raise ValueError('Conversation not found.')
                if item['state']!='open':
                    raise ValueError('This conversation has finished. Start a new request below.')
                case_id = item['id']
            else:
                row = conn.execute("SELECT id FROM tableradar_support_cases WHERE thread_id=%s AND status='open' FOR UPDATE", (root,)).fetchone()
                case_id = row[0] if row else str(uuid.uuid4())
                if not row:
                    conn.execute('INSERT INTO tableradar_support_cases(id,thread_id) VALUES(%s,%s)', (case_id,root))
        else:
            item = _case(conn, thread_id)
            if not item:
                raise ValueError('Conversation not found.')
            root = item['root']
            conn.execute('SELECT id FROM tableradar_support_threads WHERE id=%s FOR UPDATE', (root,))
            item = _case(conn, item['id'], lock=True)
            previous = conn.execute('SELECT case_id FROM tableradar_support_messages WHERE thread_id=%s AND nonce=%s', (root,nonce)).fetchone()
            if previous:
                return previous[0]
            if item['state']!='open':
                raise ValueError('This conversation is finished. Replies are disabled; its history is preserved.')
            case_id = item['id']
        recent = conn.execute("SELECT COUNT(*) FROM tableradar_support_messages WHERE thread_id=%s AND sender=%s AND created_at>NOW()-INTERVAL '1 minute'", (root,sender)).fetchone()[0]
        if recent>=20:
            raise ValueError('Too many messages. Please wait a minute before sending again.')
        conn.execute('INSERT INTO tableradar_support_messages(thread_id,case_id,sender,actor,body,nonce) VALUES(%s,%s,%s,%s,%s,%s)', (root,case_id,sender,actor or email,body,nonce))
        conn.execute('UPDATE tableradar_support_threads SET status=%s,updated_at=NOW() WHERE id=%s', ('waiting' if sender=='customer' else 'replied',root))
        conn.execute('UPDATE tableradar_support_cases SET updated_at=NOW() WHERE id=%s', (case_id,))
        return case_id


def finish(identifier, expected_last):
    with repository.connection() as conn:
        item = _case(conn, identifier)
        if not item:
            raise ValueError('Conversation not found.')
        conn.execute('SELECT id FROM tableradar_support_threads WHERE id=%s FOR UPDATE',(item['root'],))
        item = _case(conn,item['id'],lock=True)
        last_id = conn.execute('SELECT COALESCE(MAX(id),0) FROM tableradar_support_messages WHERE case_id=%s',(item['id'],)).fetchone()[0]
        if last_id != expected_last:
            raise ValueError('A new message arrived. Read the latest messages before finishing.')
        if item['state']=='open':
            conn.execute("UPDATE tableradar_support_cases SET status='finished',closed_at=NOW(),updated_at=NOW() WHERE id=%s", (item['id'],))


def archive(identifier):
    with repository.connection() as conn:
        item = _case(conn,identifier,lock=True)
        if not item:
            raise ValueError('Conversation not found.')
        if item['state']=='open':
            raise ValueError('Finish the conversation before archiving it.')
        conn.execute("UPDATE tableradar_support_cases SET status='archived',updated_at=NOW() WHERE id=%s", (item['id'],))
