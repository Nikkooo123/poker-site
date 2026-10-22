"""Private customer conversations in the existing PostgreSQL database."""
import uuid
import account_repository as repository


def initialize():
    with repository.connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS tableradar_support_threads(
            id BIGSERIAL PRIMARY KEY,email TEXT NOT NULL UNIQUE,status TEXT NOT NULL DEFAULT 'waiting',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())''')
        conn.execute('''CREATE TABLE IF NOT EXISTS tableradar_support_messages(
            id BIGSERIAL PRIMARY KEY,thread_id BIGINT NOT NULL REFERENCES tableradar_support_threads(id),
            sender TEXT NOT NULL CHECK(sender IN ('customer','staff')),actor TEXT NOT NULL,
            body TEXT NOT NULL,nonce TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(thread_id,nonce))''')


def _messages(conn,thread_id):
    rows=conn.execute('''SELECT id,sender,body,created_at FROM tableradar_support_messages
        WHERE thread_id=%s ORDER BY id DESC LIMIT 100''',(thread_id,)).fetchall()
    return [dict(id=row[0],sender=row[1],body=row[2],created_at=row[3].isoformat()) for row in reversed(rows)]


def customer_messages(email):
    with repository.connection() as conn:
        row=conn.execute('SELECT id FROM tableradar_support_threads WHERE email=%s',(email,)).fetchone()
        return _messages(conn,row[0]) if row else []


def staff_messages(thread_id):
    with repository.connection() as conn:
        row=conn.execute('SELECT email,status FROM tableradar_support_threads WHERE id=%s',(thread_id,)).fetchone()
        if not row:
            return None
        return dict(id=thread_id,email=row[0],status=row[1],messages=_messages(conn,thread_id))


def inbox():
    with repository.connection() as conn:
        rows=conn.execute('''SELECT t.id,t.email,t.status,t.updated_at,
            (SELECT m.body FROM tableradar_support_messages m WHERE m.thread_id=t.id ORDER BY m.id DESC LIMIT 1)
            FROM tableradar_support_threads t ORDER BY CASE WHEN status='waiting' THEN 0 ELSE 1 END,updated_at DESC LIMIT 200''').fetchall()
        return [dict(id=row[0],email=row[1],status=row[2],updated_at=row[3].isoformat(),preview=(row[4] or '')[:120]) for row in rows]


def send(email,body,nonce,sender='customer',actor='',thread_id=None):
    body=body.strip()
    if not 1 <= len(body) <= 2000:
        raise ValueError('Write a message between 1 and 2,000 characters.')
    try:
        nonce=str(uuid.UUID(nonce))
    except (ValueError,TypeError,AttributeError):
        raise ValueError('Refresh the chat and try again.')
    if sender not in ('customer','staff'):
        raise ValueError('Invalid sender')
    with repository.connection() as conn:
        if sender=='customer':
            conn.execute('INSERT INTO tableradar_support_threads(email) VALUES(%s) ON CONFLICT(email) DO NOTHING',(email,))
            thread_id=conn.execute('SELECT id FROM tableradar_support_threads WHERE email=%s FOR UPDATE',(email,)).fetchone()[0]
        else:
            if not conn.execute('SELECT id FROM tableradar_support_threads WHERE id=%s FOR UPDATE',(thread_id,)).fetchone():
                raise ValueError('Conversation not found.')
        if conn.execute('SELECT id FROM tableradar_support_messages WHERE thread_id=%s AND nonce=%s',(thread_id,nonce)).fetchone():
            return thread_id
        recent=conn.execute("SELECT COUNT(*) FROM tableradar_support_messages WHERE thread_id=%s AND sender=%s AND created_at>NOW()-INTERVAL '1 minute'",(thread_id,sender)).fetchone()[0]
        if recent>=20:
            raise ValueError('Too many messages. Please wait a minute before sending again.')
        conn.execute('INSERT INTO tableradar_support_messages(thread_id,sender,actor,body,nonce) VALUES(%s,%s,%s,%s,%s)',(thread_id,sender,actor or email,body,nonce))
        conn.execute('UPDATE tableradar_support_threads SET status=%s,updated_at=NOW() WHERE id=%s',('waiting' if sender=='customer' else 'replied',thread_id))
        return thread_id
