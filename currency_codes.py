"""Free-text game currency labels. Blank legacy values are never guessed."""
from html import escape

MAX_CURRENCY_LENGTH = 24


def normalize_currency(value, required=True):
    raw = str(value or '').strip()
    code = ' '.join(raw.split()).upper()
    if code and len(code) <= MAX_CURRENCY_LENGTH and all(ch.isprintable() for ch in raw) and '<' not in code and '>' not in code:
        return code
    if required:
        raise ValueError('Enter a game currency (up to 24 characters), for example USD or USDT.')
    return ''


def currency_input(value=''):
    value = escape(str(value or ''), quote=True)
    return f'<input name="currency" type="text" required maxlength="{MAX_CURRENCY_LENGTH}" placeholder="e.g. USD, USDT" value="{value}" autocapitalize="characters" autocomplete="off" spellcheck="false" style="text-transform:uppercase">'


def currency_badge(value):
    code = escape(normalize_currency(value, required=False), quote=True)
    return f'<span class="tr-currency" aria-label="Game currency {code}" style="display:inline-block;max-width:100%;overflow-wrap:anywhere;margin-left:7px;vertical-align:middle;font-size:10px;font-weight:600;line-height:1.5;letter-spacing:.4px;color:#bcd8d0">{code}</span>' if code else ''
