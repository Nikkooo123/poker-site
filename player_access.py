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


def friends_preview_enabled():
    """Temporary owner-approved public review. Set false to restore saved rules."""
    return os.getenv('FRIENDS_PREVIEW_ENABLED', 'true').strip().lower() == 'true'


def directory_access(user):
    return True if friends_preview_enabled() else entitled(user)


def join_access(user):
    """Active verified 14-day trial includes Join; paid and staff access remains."""
    if friends_preview_enabled():
        return bool(user and user.get('staff_role') == 'manager')
    return directory_access(user)


def render_trial_notice(user):
    if friends_preview_enabled() or directory_access(user):
        return ''
    return '<section class="tr-info-card tr-access-notice" style="padding:18px;margin:18px 0"><h2 style="font-size:19px">Unlock full table information</h2><p>Verify your email and phone number, then start your 14-day Free Trial to view club and table details.</p><a class="tr-button" href="/verify-account">Verify and start Free Trial</a></section>'


def needs_email_confirmation(user):
    return bool(enabled() and user.get('verification_required') and not user.get('email_verified_at')
                and user.get('staff_role') not in ('manager', 'table_admin'))
