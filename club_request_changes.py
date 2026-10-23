"""Server-owned comparison snapshots for club request updates."""
from html import escape

FIELDS = {
    'owner_name': 'Owner name', 'telegram': 'Telegram', 'club_name': 'Club name',
    'application': 'Application', 'currency': 'Game currency',
    'club_code': 'Club ID', 'notes': 'Notes for the operator',
}


def snapshot(club):
    return {key: str(club.get(key) or '') for key in FIELDS}


def updated_request(details, previous):
    result = dict(details)
    if previous:
        baseline = previous.get('_comparison_base') if previous.get('_is_update') else None
        result['_comparison_base'] = snapshot(baseline if isinstance(baseline, dict) else previous)
        result['_is_update'] = True
    return result


def reviewed_request(club, **review):
    return dict(club, **review, _comparison_base=snapshot(club), _is_update=False)


def changed_fields(club):
    baseline = club.get('_comparison_base')
    if not club.get('_is_update') or not isinstance(baseline, dict):
        return ()
    return tuple(key for key in FIELDS if str(club.get(key) or '') != str(baseline.get(key) or ''))


def field_html(club, key, fallback=''):
    value = escape(str(club.get(key) or fallback), quote=True)
    if key in changed_fields(club):
        return f'<span class="tr-request-changed" data-changed-field="{key}">{value or "(removed)"}</span>'
    return value


def changes_html(club):
    changed = changed_fields(club)
    if not club.get('_is_update'):
        return ''
    if not changed:
        return '<p class="tr-request-update-note">Updated request · No field changes</p>'
    baseline = club['_comparison_base']
    rows = ''.join(
        '<div class="tr-request-diff-row"><dt>'+FIELDS[key]+'</dt><dd>'
        +'<span class="tr-request-before">Previously: '+escape(str(baseline.get(key) or '(empty)'), quote=True)+'</span>'
        +field_html(club,key)+'</dd></div>' for key in changed)
    return '<div class="tr-request-diff"><p class="tr-request-update-note">Updated request · Changed fields</p><dl>'+rows+'</dl></div>'
