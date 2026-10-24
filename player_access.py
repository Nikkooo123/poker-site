"""Server-side Player entitlement. Trial does not create a paid or Host plan."""
import os
import math
from datetime import datetime, timezone
from html import escape


def enabled():
    return os.getenv('PLAYER_TRIAL_ENABLED', '').lower() == 'true'


def remaining(user):
    try:
        expiry = datetime.fromisoformat(user.get('player_trial_expires_at', ''))
        if expiry.tzinfo is None:
            return 0
        seconds = (expiry - datetime.now(timezone.utc)).total_seconds()
        return max(0, math.ceil(seconds / 86400))
    except (ValueError, TypeError, AttributeError):
        return 0


def entitled(user):
    if not user:
        return False
    if user.get('staff_role') in ('manager', 'table_admin'):
        return True
    if user.get('verification_required') and not user.get('email_verified_at'):
        return False
    from host_lifecycle import awaiting_launch
    if awaiting_launch(user):
        return True
    if user.get('plan') in ('player', 'host') and user.get('is_active') is True:
        expiry = user.get('membership_expires_at') or user.get('test_expires_at')
        if expiry:
            try:
                return datetime.fromisoformat(expiry) > datetime.now(timezone.utc)
            except (TypeError, ValueError):
                return False
        return True
    return bool(user.get('email_verified_at') and user.get('trial_phone_digest')
                and user.get('phone_verified_at') and remaining(user))


def directory_access(user):
    return entitled(user)


def join_access(user):
    """Trial reveals names; only a confirmed paid Player plan reveals contacts."""
    if not user:
        return False
    if user.get('staff_role') in ('manager', 'table_admin'):
        return True
    if user.get('plan') != 'player' or user.get('is_active') is not True:
        return False
    if user.get('membership_test_enabled'):
        return False
    if user.get('membership_source') not in ('manager', 'crypto', 'card', 'paypal'):
        return False
    if user.get('verification_required') and not user.get('email_verified_at'):
        return False
    expiry = user.get('membership_expires_at')
    if not expiry:
        return False
    try:
        return datetime.fromisoformat(expiry) > datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return False


def render_trial_notice(user):
    if not enabled():
        return ''
    days = remaining(user)
    if days and entitled(user):
        title = 'Player free trial: ' + str(days) + ' days remaining'
        text = 'Your trial reveals table and club names. Joining requires a paid Player plan. The trial expires automatically and does not renew or include Host access.'
    elif user.get('player_trial_expires_at'):
        title, text = 'Player free trial ended', 'Choose a paid Player membership to continue viewing full table information.'
    elif entitled(user):
        return ''
    else:
        title, text = 'Unlock full table information', 'Registration alone does not unlock tables. Verify your email and phone to start one 14-day Player trial per phone number, or choose a paid membership. Host has no free trial.'
    return '<section class="tr-info-card" style="padding:18px;margin:18px 0"><h2 style="font-size:19px">'+escape(title)+'</h2><p>'+escape(text)+'</p><a class="tr-button" href="/verify-account">Email, phone and trial</a> <a class="tr-button" href="/profile">Membership options</a></section>'


def needs_email_confirmation(user):
    return bool(enabled() and user.get('verification_required') and not user.get('email_verified_at')
                and user.get('staff_role') not in ('manager', 'table_admin'))
