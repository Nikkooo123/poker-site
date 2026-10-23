"""Shared game-currency choices. Blank legacy values are never guessed."""
from html import escape

CURRENCY_CODES = ('USD','GBP','EUR','CAD','AUD','NZD','CHF','JPY','CNY','HKD','SGD','AED','BRL','MXN','ARS','CLP','COP','PEN','RUB','UAH','KZT','TRY','INR','IDR','MYR','PHP','THB','VND','KRW','ZAR','PLN','CZK','HUF','RON','SEK','NOK','DKK','ILS','SAR')


def normalize_currency(value, required=True):
    code = str(value or '').strip().upper()
    if code in CURRENCY_CODES:
        return code
    if required:
        raise ValueError('Choose the game currency, for example USD, GBP or EUR.')
    return ''


def currency_options(selected=''):
    selected = normalize_currency(selected, required=False)
    return '<option value="">Select currency</option>' + ''.join(f'<option value="{code}"{" selected" if code == selected else ""}>{code}</option>' for code in CURRENCY_CODES)


def currency_badge(value):
    code = normalize_currency(value, required=False)
    return f'<span class="tr-currency" aria-label="Game currency {code}" style="display:inline-block;margin-left:7px;vertical-align:middle;font-size:10px;font-weight:600;line-height:1.5;letter-spacing:.4px;color:#bcd8d0">{code}</span>' if code else ''
