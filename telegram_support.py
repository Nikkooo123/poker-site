"""Private Telegram customer conversations bridged to a staff-only forum.

No Telegram token or customer identifiers are rendered into the website.
Staff must reply to a relayed customer message; ordinary topic discussion stays internal.
"""
import hashlib
import hmac
import logging
import os
import re
import secrets

import httpx
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool

import account_repository as repository

LOG = logging.getLogger(__name__)
_ready = False


class TelegramError(Exception):
    pass


def settings():
    token = os.getenv('TELEGRAM_SUPPORT_BOT_TOKEN', '').strip()
    username = os.getenv('TELEGRAM_SUPPORT_BOT_USERNAME', '').strip().lstrip('@')
    chat = os.getenv('TELEGRAM_SUPPORT_STAFF_CHAT_ID', '').strip()
    if not token or not re.fullmatch(r'[A-Za-z0-9_]{5,32}', username) or not re.fullmatch(r'-[0-9]{1,19}', chat):
        return None
    return token, username, int(chat)


def webhook_secret(token):
    return hmac.new(token.encode(), b'TableRadar Telegram webhook v1', hashlib.sha256).hexdigest()


def contact_url(table_id=None):
    if not settings() or not _ready:
        from brand import TELEGRAM_URL
        return TELEGRAM_URL
    return '/telegram/contact' + (f'/{int(table_id)}' if table_id is not None else '')


class API:
    def __init__(self, token):
        self.token = token

    def call(self, method, **values):
        # Never propagate httpx exceptions: they can contain the token-bearing URL.
        try:
            response = httpx.post(f'https://api.telegram.org/bot{self.token}/{method}', json=values, timeout=15)
            data = response.json()
        except Exception:
            raise TelegramError('Telegram connection failed') from None
        if response.status_code != 200 or not data.get('ok'):
            raise TelegramError('Telegram rejected ' + method) from None
        return data.get('result')


def initialize():
    with repository.connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('tableradar_telegram_schema',0))")
        conn.execute('''CREATE TABLE IF NOT EXISTS tableradar_tg_intents(
            token TEXT PRIMARY KEY,context TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())''')
        conn.execute('''CREATE TABLE IF NOT EXISTS tableradar_tg_cases(
            id BIGSERIAL PRIMARY KEY,chat_id BIGINT NOT NULL,topic_id BIGINT,
            intent TEXT UNIQUE,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())''')
        conn.execute('''CREATE TABLE IF NOT EXISTS tableradar_tg_current(
            chat_id BIGINT PRIMARY KEY,case_id BIGINT NOT NULL REFERENCES tableradar_tg_cases(id))''')
        conn.execute('''CREATE TABLE IF NOT EXISTS tableradar_tg_updates(
            id BIGINT PRIMARY KEY,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())''')
        conn.execute('''CREATE TABLE IF NOT EXISTS tableradar_tg_messages(
            staff_message_id BIGINT PRIMARY KEY,case_id BIGINT NOT NULL REFERENCES tableradar_tg_cases(id))''')


def new_intent(context):
    token = secrets.token_urlsafe(18)
    with repository.connection() as conn:
        conn.execute('INSERT INTO tableradar_tg_intents(token,context) VALUES (%s,%s)', (token, context[:500]))
    return token


def display_name(person):
    name = ' '.join(str(person.get(k, '')).strip() for k in ('first_name', 'last_name')).strip()
    return re.sub(r'[\x00-\x1f\x7f]', '', name or person.get('username', '') or 'Team member')[:100]


def valid_message(message):
    return bool(message.get('text') or any(message.get(k) for k in ('photo', 'document', 'video', 'voice', 'audio', 'sticker', 'animation', 'video_note')))


def relay_private(conn, api, message, staff_chat):
    chat_id = message['chat']['id']
    text = message.get('text', '')
    command, _, payload = text.partition(' ')
    if command in ('/help', '/settings'):
        api.call('sendMessage', chat_id=chat_id, text='Send a message to contact TableRadar support. /new starts a separate enquiry. Replies include the team member’s name. This is a private conversation; other customers cannot see it.')
        return
    if text.startswith('/') and command not in ('/start', '/new'):
        api.call('sendMessage', chat_id=chat_id, text='Use /new for a new enquiry, or send your message here.')
        return
    intent = None
    context = 'General support enquiry'
    if command == '/start' and payload:
        row = conn.execute("SELECT context FROM tableradar_tg_intents WHERE token=%s AND created_at>NOW()-INTERVAL '24 hours'", (payload,)).fetchone()
        if not row:
            api.call('sendMessage', chat_id=chat_id, text='This website link has expired. Please reopen Telegram from the website, or use /new for general support.')
            return
        intent, context = payload, row[0]
        existing = conn.execute('SELECT id,chat_id,topic_id FROM tableradar_tg_cases WHERE intent=%s', (intent,)).fetchone()
        if existing and existing[1] != chat_id:
            api.call('sendMessage', chat_id=chat_id, text='This link has already been used. Please open a new link from the website.')
            return
    else:
        existing = None
    current = conn.execute('SELECT c.id,c.chat_id,c.topic_id FROM tableradar_tg_current a JOIN tableradar_tg_cases c ON c.id=a.case_id WHERE a.chat_id=%s', (chat_id,)).fetchone()
    case = existing or (None if command in ('/new', '/start') else current)
    if case is None:
        person = message.get('from', {})
        case_id = conn.execute('INSERT INTO tableradar_tg_cases(chat_id,intent) VALUES (%s,%s) RETURNING id', (chat_id, intent)).fetchone()[0]
        topic = api.call('createForumTopic', chat_id=staff_chat, name=f'#{case_id} · {display_name(person)}'[:128])
        topic_id = topic['message_thread_id']
        conn.execute('UPDATE tableradar_tg_cases SET topic_id=%s WHERE id=%s', (topic_id, case_id))
        case = (case_id, chat_id, topic_id)
        header = api.call('sendMessage', chat_id=staff_chat, message_thread_id=topic_id,
            text=f'New private enquiry #{case_id}\nFrom: {display_name(person)}\n{context}\n\nReply to a customer message to send your response. Normal discussion here stays internal. Only the bot and your first/last name are shown to the customer.')
        conn.execute('INSERT INTO tableradar_tg_messages(staff_message_id,case_id) VALUES (%s,%s)', (header['message_id'], case_id))
        api.call('sendMessage', chat_id=chat_id, text=f'Your private enquiry #{case_id} is open. Send your message here; our team will reply in this chat. Only you and the TableRadar team can read this conversation. Use /new for a separate enquiry.')
    conn.execute('INSERT INTO tableradar_tg_current(chat_id,case_id) VALUES (%s,%s) ON CONFLICT(chat_id) DO UPDATE SET case_id=EXCLUDED.case_id', (chat_id, case[0]))
    if command in ('/start', '/new'):
        return
    if not valid_message(message):
        api.call('sendMessage', chat_id=chat_id, text='Please send text, a photo, a document, or a voice/video message.')
        return
    copied = api.call('copyMessage', chat_id=staff_chat, message_thread_id=case[2], from_chat_id=chat_id, message_id=message['message_id'])
    conn.execute('INSERT INTO tableradar_tg_messages(staff_message_id,case_id) VALUES (%s,%s)', (copied['message_id'], case[0]))


def relay_staff(conn, api, message, staff_chat):
    person = message.get('from', {})
    if person.get('is_bot') or message.get('sender_chat') or not person.get('id'):
        return
    reply = message.get('reply_to_message') or {}
    if not reply.get('message_id') or not valid_message(message):
        return  # Internal discussion is never broadcast to the customer.
    case = conn.execute('SELECT c.chat_id,c.topic_id,c.id FROM tableradar_tg_messages m JOIN tableradar_tg_cases c ON c.id=m.case_id WHERE m.staff_message_id=%s', (reply['message_id'],)).fetchone()
    if not case or message.get('message_thread_id') != case[1]:
        return
    member = api.call('getChatMember', chat_id=staff_chat, user_id=person['id'])
    if member.get('status') not in ('creator', 'administrator', 'member'):
        return
    # Plain text prevents customer/staff names from becoming formatting or links.
    prefix = f'{display_name(person)} · TableRadar · enquiry #{case[2]}\n\n'
    if message.get('text'):
        text = prefix + message['text']
        for offset in range(0, len(text), 4000):
            api.call('sendMessage', chat_id=case[0], text=text[offset:offset+4000])
    else:
        api.call('sendMessage', chat_id=case[0], text=prefix.strip())
        api.call('copyMessage', chat_id=case[0], from_chat_id=staff_chat, message_id=message['message_id'])
    api.call('sendMessage', chat_id=staff_chat, message_thread_id=case[1], text=f'Sent to the customer · {display_name(person)}', reply_parameters={'message_id': message['message_id']})


def process(update, config):
    message = update.get('message')
    if not isinstance(message, dict) or not isinstance(update.get('update_id'), int):
        return
    person = message.get('from') or {}
    if person.get('is_bot'):
        return
    api = API(config[0])
    with repository.connection() as conn:
        # Serializes duplicate deliveries and starts for the same bot across workers.
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('tableradar_telegram_delivery',0))")
        if not conn.execute('INSERT INTO tableradar_tg_updates(id) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id', (update['update_id'],)).fetchone():
            return
        chat = message.get('chat') or {}
        if chat.get('type') == 'private' and chat.get('id') == person.get('id'):
            relay_private(conn, api, message, config[2])
        elif chat.get('id') == config[2] and chat.get('type') == 'supergroup':
            relay_staff(conn, api, message, config[2])


def setup_webhook():
    global _ready
    _ready = False
    config = settings()
    if not config:
        return
    initialize()
    api = API(config[0])
    me = api.call('getMe')
    if me.get('username', '').lower() != config[1].lower():
        raise TelegramError('Bot username does not match configuration')
    chat = api.call('getChat', chat_id=config[2])
    member = api.call('getChatMember', chat_id=config[2], user_id=me['id'])
    if chat.get('type') != 'supergroup' or not chat.get('is_forum') or member.get('status') != 'administrator' or not member.get('can_manage_topics'):
        raise TelegramError('The bot needs Manage Topics permission in the configured staff forum')
    api.call('setWebhook', url='https://tableradar.net/telegram/webhook', secret_token=webhook_secret(config[0]), allowed_updates=['message'], max_connections=1, drop_pending_updates=False)
    _ready = True


def install_routes(app, get_current_user):
    @app.on_event('startup')
    def telegram_startup():
        try:
            setup_webhook()
        except Exception:
            # A Telegram outage must not take down the website; never log the token.
            LOG.error('Telegram support setup failed; check bot permissions and configuration.')

    @app.get('/telegram/contact')
    def general_contact():
        config = settings()
        if not config or not _ready:
            return HTMLResponse('Telegram support is being configured. Please email support@tableradar.net.', status_code=503)
        return RedirectResponse(f'https://t.me/{config[1]}?start={new_intent("General website enquiry")}', status_code=303, headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})

    @app.get('/telegram/contact/{table_id}')
    def table_contact(request: Request, table_id: int):
        import player_access
        from storage import load_tables
        user = get_current_user(request)
        if not user:
            return RedirectResponse('/signin', status_code=303)
        if not player_access.join_access(user):
            return HTMLResponse('Please select an eligible account role before contacting the team.', status_code=403)
        config = settings()
        if not config or not _ready:
            return HTMLResponse('Telegram support is being configured. Please email support@tableradar.net.', status_code=503)
        table = next((t for t in load_tables() if int(t.get('id', 0)) == table_id), None)
        if not table:
            return HTMLResponse('Listing not found.', status_code=404)
        context = 'Website enquiry\nClub: ' + str(table.get('club', ''))[:200] + '\nTable: ' + str(table.get('table_name', ''))[:200]
        return RedirectResponse(f'https://t.me/{config[1]}?start={new_intent(context)}', status_code=303, headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})

    @app.post('/telegram/webhook', include_in_schema=False)
    async def webhook(request: Request):
        config = settings()
        supplied = request.headers.get('x-telegram-bot-api-secret-token', '')
        if not config or not secrets.compare_digest(supplied, webhook_secret(config[0])):
            return JSONResponse({'ok': False}, status_code=403)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 131072:
                return JSONResponse({'ok': False}, status_code=413)
        import json
        try:
            update = json.loads(body)
            if not isinstance(update, dict):
                raise ValueError()
        except (ValueError, TypeError):
            return JSONResponse({'ok': False}, status_code=400)
        try:
            await run_in_threadpool(process, update, config)
        except Exception:
            LOG.error('Telegram support delivery failed; Telegram will retry this update.')
            return JSONResponse({'ok': False}, status_code=503)
        return {'ok': True}
