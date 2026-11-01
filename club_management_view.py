"""Shared manager-only confirmation form. No deletion is triggered by rendering."""
from html import escape
import json


def render_club_delete_form(action, csrf, club_name, fields=None):
    name = str(club_name or "Untitled club")
    message = (f'Permanently delete "{name}"? This removes its subscription, linked club request '
               'and monitoring tables. The owner account and unrelated clubs are kept.')
    confirmation = escape(json.dumps(message), quote=True)
    values = dict(fields or {}, csrf=csrf)
    hidden = ''.join(f'<input type="hidden" name="{escape(str(key), quote=True)}" '
                     f'value="{escape(str(value or ""), quote=True)}">' for key, value in values.items())
    return (f'<form method="post" action="{escape(action, quote=True)}" '
            f'onsubmit="return confirm({confirmation})" class="tr-delete-club-form" style="margin:0">'
            f'{hidden}<button class="tr-button" type="submit" '
            'style="background:#8f2e36;color:#fff1f1;border:1px solid #b96870;border-radius:8px;'
            'padding:7px 10px;font-weight:700;cursor:pointer">Delete club permanently</button></form>')
