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


def verified_account(user):
    """Only server-confirmed email and a bound, SMS-confirmed phone qualify."""
    return bool(user and user.get('email_verified_at') and user.get('phone_verified_at')
                and user.get('trial_phone_digest'))


def paid_host_access(user):
    if not user or user.get('plan') != 'host' or user.get('membership_test_enabled'):
        return False
    if user.get('membership_source') not in ('manager', 'crypto'):
        return False
    from host_lifecycle import awaiting_launch
    if awaiting_launch(user):
        return True
    if user.get('is_active') is not True:
        return False
    try:
        return datetime.fromisoformat(user.get('membership_expires_at', '')) > datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return False


def directory_access(user):
    return bool(user and (user.get('staff_role') in ('manager', 'table_admin')
                          or verified_account(user) or paid_host_access(user)))


def join_access(user):
    """Launch policy: verified accounts can see names and join without payment."""
    return directory_access(user)


def render_trial_notice(user):
    if directory_access(user):
        return ''
    return '<section class="tr-info-card tr-access-notice" style="padding:18px;margin:18px 0"><h2 style="font-size:19px">Unlock full table information</h2><p>Verify your email and phone number to view club and table details.</p><a class="tr-button" href="/verify-account">Verify email and phone</a></section>'


def needs_email_confirmation(user):
    return bool(enabled() and user.get('verification_required') and not user.get('email_verified_at')
                and user.get('staff_role') not in ('manager', 'table_admin'))
