"""Table creation restricted to active operator placements; contacts never come from staff input."""
import re
from brand import OFFICIAL_AFFILIATE_NAME, TELEGRAM_URL
from storage import _connect, _insert_table, _normalize_network


def add_operator_table(subscription_id, *, table_name, union_name, game, blinds, buyin, players, tags=""):
    values = dict(table_name=table_name, union_name=union_name, blinds=blinds, buyin=buyin, players=players)
    for field, value in values.items():
        values[field] = str(value or "").strip()
        if not values[field] or len(values[field]) > 160:
            raise ValueError("Enter table name, union name, blinds, minimum buy-in and players (up to 160 characters each).")
    if game not in ("NLH", "PLO4", "PLO5", "PLO6"):
        raise ValueError("Choose a game format.")
    if not re.fullmatch(r"[0-9]{1,10}(?:[.,][0-9]{1,2})?", values['buyin']) or float(values['buyin'].replace(',', '.')) <= 0:
        raise ValueError("Enter a positive minimum buy-in amount.")
    match = re.fullmatch(r"(\d{1,2})\s*/\s*(\d{1,2})", values['players'])
    if not match or not 0 <= int(match[1]) <= int(match[2]) <= 10 or int(match[2]) < 2:
        raise ValueError("Enter players as occupied seats / total seats, for example 4/6.")
    try:
        selected = int(subscription_id)
    except (TypeError, ValueError):
        raise ValueError("Select an active club from Clubs to monitor.") from None
    with _connect() as conn:
        with conn.cursor() as cur:
            # The shared row lock prevents disable/delete/renewal changing this placement mid-insert.
            # No account lock is acquired, preserving the account-first order used by approval.
            cur.execute("""SELECT club_name, application, owner_name, owner_telegram
                FROM club_subscriptions WHERE id=%s AND plan='host' AND status='active'
                AND COALESCE(access_expires_at,expires_at::timestamptz)>clock_timestamp()
                FOR SHARE""", (selected,))
            club = cur.fetchone()
            if not club:
                raise ValueError("This club is not active in Clubs to monitor. Refresh the page and choose an active club.")
            network = _normalize_network(club['application'])
            if network not in ('pppoker','pokerbros','clubgg','xpoker'):
                raise ValueError("The manager must record a supported application for this club before tables can be added.")
            telegram = str(club.get('owner_telegram') or '').strip()
            if re.fullmatch(r'@[A-Za-z0-9_]{3,64}', telegram):
                telegram = 'https://t.me/' + telegram[1:]
            if not re.fullmatch(r'https://t\.me/[A-Za-z0-9_]{3,64}/?', telegram):
                raise ValueError("The manager must save the club owner's Telegram in Club subscriptions before adding tables.")
            return _insert_table(cur, dict(values, game=game, tags=str(tags)[:250],
                club=club['club_name'], network=network, affiliate_name=OFFICIAL_AFFILIATE_NAME,
                affiliate_telegram=TELEGRAM_URL, owner_name=club['owner_name'], owner_telegram=telegram))
