"""Shared, resolution-independent table feature badges. Selection is manual per table."""
from html import escape

# Label, colour, SVG artwork. These are TableRadar drawings, not copied app assets.
FEATURES = {
 'fixed_limit': ('Fixed Limit Hold’em · FLH', '#318f91', '<path d="M3 3h18v18H3z" fill="#b9f8ed"/><path d="M4 4h16v4H4z" fill="#69d8d0"/><text x="12" y="16" text-anchor="middle" fill="#125c69" font-family="Arial" font-weight="900" font-size="8">FLH</text>'),
 'pineapple': ('Pineapple · 3-card Hold’em', '#986d21', '<path d="m10 9-5-5 6 2 1-5 2 5 5-2-4 5" fill="#8cd48d"/><ellipse cx="12" cy="15" rx="6.5" ry="7" fill="#ffd271"/><path d="m7 12 10 7M7 17l9-7m-8 11 10-8M6 14l9 8" stroke="#ad6f24" stroke-width="1.1"/><text x="12" y="18" text-anchor="middle" fill="#4c3717" font-family="Arial" font-weight="bold" font-size="7">P</text>'),
 'crazy_pineapple': ('Crazy Pineapple · discard after flop', '#a94f27', '<path d="m10 9-5-5 6 2 1-5 2 5 5-2-4 5" fill="#9fe29a"/><ellipse cx="12" cy="15" rx="6.5" ry="7" fill="#ffbe62"/><path d="m7 12 10 7M7 17l9-7m-8 11 10-8M6 14l9 8" stroke="#b5652d" stroke-width="1.1"/><path d="m6 2 2 2m10-2-2 3" stroke="#fff0b9" stroke-width="1.4"/><text x="12" y="18" text-anchor="middle" fill="#6d2918" font-family="Arial" font-weight="bold" font-size="8">C</text>'),
 'nit_game': ('NIT Game', '#238c95', '<path d="M3 4h18v13H10l-5 5v-5H3z" fill="#c4faff"/><path d="M4 5h16" stroke="#49c3d4" stroke-width="1.5"/><text x="12" y="13" text-anchor="middle" fill="#176377" font-family="Arial" font-weight="900" font-size="7">NIT</text>'),
 'no_emulators': ('No emulators · mobile devices only', '#ad3c46', '<rect x="3" y="4" width="18" height="13" rx="2" fill="#273a46" stroke="#cad6df" stroke-width="1.5"/><path d="M9 21h6m-3-4v4" stroke="#cad6df" stroke-width="1.5"/><circle cx="12" cy="10.5" r="5" fill="#6c2228" stroke="#ff8b8f" stroke-width="1.8"/><path d="m8.4 14 7.2-7" stroke="#ff8b8f" stroke-width="1.8"/>'),
 'triple_board': ('Triple Board · TB', '#8f59af', '<rect x="2" y="2" width="20" height="5" rx="1.3" fill="#f2deff"/><rect x="2" y="9" width="20" height="5" rx="1.3" fill="#deb4f4"/><rect x="2" y="16" width="20" height="5" rx="1.3" fill="#c388e6"/><path d="M8 3v3m8-3v3M8 10v3m8-3v3M8 17v3m8-3v3" stroke="#82539d"/>'),
 'cards_diamond': ('Purple cards & diamond · ClubGG', '#9534c9', '<rect x="2" y="3" width="8" height="11" rx="1.2" fill="#d5a5ff"/><rect x="11" y="3" width="8" height="11" rx="1.2" fill="#e6c2ff"/><path d="M3 7h6m-6 3h6m3-3h6m-6 3h6" stroke="#9a5cbe" stroke-width=".8"/><path d="m15 9 7 6-7 8-7-8z" fill="#f2b4e5"/><path d="m15 9-3 6 3 8 3-8z" fill="#ffc9ef"/>'),
 'double_board_bomb': ('Double Board Bomb Pot', '#aa5146', '<rect x="2" y="3" width="15" height="6" rx="1.5" fill="#f9d5b4"/><rect x="2" y="11" width="15" height="6" rx="1.5" fill="#e5aa88"/><path d="M7 4v4m5-4v4M7 12v4m5-4v4" stroke="#8b4940"/><circle cx="17" cy="17" r="5" fill="#fff0d4"/><path d="m19 12 2-3m-2-1 3 2M14 17c0-2 1-3 2-3" fill="none" stroke="#ffda92" stroke-width="1.5" stroke-linecap="round"/>'),
 'straddle': ('Straddle', '#ba8a13', '<ellipse cx="8" cy="16" rx="5" ry="2" fill="#ffe696"/><path d="M3 12v4m10-4v4M3 13c0 3 10 3 10 0M3 10c0 3 10 3 10 0" fill="none" stroke="#ffe696" stroke-width="1.5"/><ellipse cx="8" cy="10" rx="5" ry="2" fill="#ffedb1"/><path d="M17 4l-5 5h3v10h4V9h3z" fill="#fff0ac"/>'),
 'cucurucho': ('Cucurucho · Pot or Fold', '#9d32c0', '<path d="M5 10a7 7 0 0 1 14 0z" fill="#ffd7fb"/><path d="M5 11h14l-7 11z" fill="#eba2ec"/><path d="M8 13l6 5m2-5l-5 6" stroke="#cb77cd" stroke-width="1"/>'),
 'squid': ('Squid Game', '#b63c64', '<path d="M6 13c-2-5 1-10 6-11 5 1 8 6 6 11l-2 2H8z" fill="#ffcbdf"/><path d="M8 14c0 5-5 2-5 5m7-5c0 6-4 6-5 5m7-5v7m2-7c0 6 4 6 5 5m-3-5c0 5 5 2 5 5" fill="none" stroke="#ffcbdf" stroke-width="1.7" stroke-linecap="round"/><circle cx="10" cy="11" r=".8" fill="#9e3155"/><circle cx="14" cy="11" r=".8" fill="#9e3155"/>'),
 'double_board': ('Double Board · DB', '#b34229', '<defs><linearGradient id="db-red" x2="0" y2="1"><stop stop-color="#e77749"/><stop offset="1" stop-color="#a93824"/></linearGradient></defs><rect x="2" y="2" width="20" height="20" rx="4" fill="url(#db-red)" stroke="#f39567" stroke-width=".6"/><rect x="5" y="5" width="6" height="6" rx="1" fill="#ffd2b1"/><rect x="12" y="5" width="6" height="6" rx="1" fill="#ffd2b1"/><rect x="5" y="12" width="6" height="6" rx="1" fill="#f4ad81"/><rect x="12" y="12" width="6" height="6" rx="1" fill="#f4ad81"/>'),
 'bbj': ('Bad Beat Jackpot · BBJ', '#30271c', '<g transform="rotate(-8 12 12)"><path d="M2 17Q11 23 22 15Q15 20 3 16" fill="#ef8323"/><path d="M3 7L1 10l3 1M20 9l3 2-2 3" fill="none" stroke="#ffbd48" stroke-width=".8"/><text x="12" y="10" text-anchor="middle" fill="#ffce62" font-family="Arial,sans-serif" font-weight="900" font-size="7">BAD</text><text x="12" y="16" text-anchor="middle" fill="#ffb13c" font-family="Arial,sans-serif" font-weight="900" font-style="italic" font-size="7">BEAT</text></g>'),
 'insurance': ('All-in Insurance', '#407d88', '<path d="M12 2l8 3v6c0 5-4 9-8 11-4-2-8-6-8-11V5z" fill="#d4f4ef"/><path d="M8 12l3 3 5-6" fill="none" stroke="#35727e" stroke-width="2"/>'),
 'ev_cashout': ('EV Cashout / EV Chop', '#418165', 'EV'),
 'run_multiple': ('Run It Multiple Times · RIT', '#5e65b3', 'RIT'),
 'hi_lo': ('High / Low · Hi-Lo', '#547ca4', 'H/L'),
 'aof': ('All-in or Fold · AoF', '#a64d4b', 'AoF'),
 'ante': ('Ante', '#a27e3a', 'A'),
 'no_rathole': ('No Rathole', '#6c6986', 'NR'),
 'no_turn_no_show': ('No Turn No Show', '#69788b', 'NS'),
 'private': ('Private Table · Password Required', '#6a6b8e', '<rect x="5" y="10" width="14" height="11" rx="2" fill="#e4e4ff"/><path d="M8 10V7a4 4 0 0 1 8 0v3" fill="none" stroke="#e4e4ff" stroke-width="2"/><circle cx="12" cy="15" r="1.5" fill="#67658c"/>'),
 'buyin_auth': ('Buy-in Authorization Required', '#887e43', 'KEY'),
 'seven_deuce': ('Seven-Deuce Game', '#986b45', '7-2'),
 'stand_up': ('Stand-Up Game', '#657e49', 'UP'),
 'multi_pot': ('Multi-Pot', '#7663a2', 'MP'),
 'pot_fold': ('Pot Fold', '#96577c', 'PF'),
 'high_hand': ('High Hand Promotion', '#927630', 'HH'),
 'leaderboard': ('Leaderboard', '#537f8f', 'LB'),
}
BASE_FEATURES = {
 'bomb': ('Bomb Pot', '#bb624b', '<circle cx="10" cy="14" r="6.3" fill="#fff1d6"/><path d="M13 8l3-3m-2-1l3 2m2-4v2m2 1h-2m1 3l-1-1" fill="none" stroke="#ffe09a" stroke-width="1.6" stroke-linecap="round"/><path d="M6 13c0-2 1-3 3-3" fill="none" stroke="#ce8d70" stroke-width="1.4" stroke-linecap="round"/>'),
 'clock': ('Clock / Timer', '#519c83', '<circle cx="12" cy="12" r="8" fill="#e0f6ed"/><circle cx="12" cy="12" r="5.8" fill="none" stroke="#6da18b" stroke-width=".7"/><path d="M12 7v5l3 2" fill="none" stroke="#315f50" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="12" r="1.1" fill="#315f50"/>'),
}
ICONS = dict(BASE_FEATURES, **FEATURES)
PRIMARY_FEATURES = ('straddle', 'squid', 'double_board', 'double_board_bomb')
EXTRA_VPIP_VALUES = (15, 20, 25, 60, 65, 70, 75)


def extra_vpip_buttons():
    return ''.join(f'<button type="button" class="admin-pick-btn admin-tag-btn tr-vpip-pick" data-value="vpip {value}%" aria-label="VPIP {value}%">{render_vpip_badge(value)}</button>' for value in EXTRA_VPIP_VALUES)

def render_feature_icon(key, focusable=True):
    if key not in ICONS:
        return ''
    label, colour, artwork = ICONS[key]
    if not artwork.startswith('<'):
        artwork = f'<text x="12" y="15.5" text-anchor="middle" fill="#fff8ed" font-family="Arial,sans-serif" font-weight="700" font-size="{8 if len(artwork)>2 else 10}">{escape(artwork)}</text>'
    return f'<span class="tr-feature-icon" data-feature="{key}" role="img" {'tabindex="0"' if focusable else ""} aria-label="{escape(label,quote=True)}" title="{escape(label,quote=True)}" style="display:inline-flex;flex:0 0 22px;align-items:center;justify-content:center;width:22px;height:22px;border-radius:5px;background:linear-gradient(145deg,{colour},#131923);box-shadow:inset 0 1px 0 #ffffff40,0 1px 3px #0005"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">{artwork}</svg></span>'


def feature_buttons(keys, labels=False):
    return ''.join(f'<button type="button" class="admin-pick-btn admin-tag-btn tr-feature-pick{" tr-feature-with-label" if labels else ""}" data-value="{key}" aria-label="{escape(ICONS[key][0],quote=True)}" aria-pressed="false" title="{escape(ICONS[key][0],quote=True)}">{render_feature_icon(key, focusable=False)}{("<span>"+escape(ICONS[key][0].split(" · ")[0])+"</span>") if labels else ""}</button>' for key in keys)


def render_vpip_badge(percent=""):
    label = 'VPIP' + (' '+str(percent)+'%' if str(percent) else '')
    return f'<span class="tr-vpip-badge" style="display:inline-flex;flex-shrink:0;align-items:center;justify-content:center;box-sizing:border-box;height:22px;padding:0 8px;border-radius:5px;background:linear-gradient(145deg,#b78b32,#624319);color:#fff0c9;font:700 10px Arial;letter-spacing:.2px;white-space:nowrap;box-shadow:inset 0 1px 0 #ffffff40,0 1px 3px #0005">{escape(label)}</span>'
