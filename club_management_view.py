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
            f'{hidden}<button class="tr-delete-club-button" type="submit" '
            'style="background:#493339;color:#e0c5c8;border:1px solid #725157;border-radius:6px;'
            'padding:4px 7px;min-height:26px;font-size:11px;line-height:1.2;font-weight:500;cursor:pointer">Delete club permanently</button></form>')


def render_club_request_status(status):
    variants = {
        'approved': ('Approved', '#a4dfbd', '#76b990', '#284d3c', '#76b99022'),
        'pending': ('Pending review', '#f0d28a', '#b69a55', '#4d4430', '#d6ad4422'),
        'needs_changes': ('Changes requested', '#f0d28a', '#b69a55', '#4d4430', '#d6ad4422'),
        'rejected': ('Rejected', '#eeb4b8', '#b1737b', '#51353c', '#b1737b22'),
    }
    label, colour, border, background, glow = variants.get(status,
        (str(status or 'Pending review'), '#cfdddd', '#68817c', '#293c3d', '#0000'))
    return (f'<span class="tr-club-request-status" style="display:inline-flex;align-items:center;'
            f'padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700;'
            f'color:{colour};border:1px solid {border};background:{background};box-shadow:0 0 12px {glow}">'
            f'{escape(label)}</span>')
