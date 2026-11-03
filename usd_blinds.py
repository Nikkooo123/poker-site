"""Approximate USD equivalents with optional club-specific rate overrides."""
from exchange_rates import market_usd_rate
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re


def normalize_usd_rate(value):
    if value is None or str(value).strip() == '':
        return None
    try:
        rate = Decimal(str(value).strip())
    except InvalidOperation:
        raise ValueError('Enter a positive USD value for one club unit.') from None
    if not rate.is_finite() or not Decimal('0.00000001') <= rate <= Decimal('1000000'):
        raise ValueError('USD value per unit must be between 0.00000001 and 1000000.')
    return rate.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)


def usd_equivalent(blinds, currency, configured_rate=None):
    try:
        rate = normalize_usd_rate(configured_rate)
    except ValueError:
        return None
    if rate is None:
        rate = market_usd_rate(currency)
        if rate is None:
            return None
    match = re.fullmatch(r'\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*([0-9]+(?:\.[0-9]+)?)(?:\s*\(\s*([0-9]+(?:\.[0-9]+)?)\s*\))?\s*', str(blinds or ''))
    if not match:
        return None
    values = [Decimal(x) * rate for x in match.groups() if x is not None]
    if values[0] <= 0 or values[1] <= 0:
        return None
    def money(value):
        if 0 < value < Decimal('.01'):
            return '<0.01'
        return format(value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP), 'f').rstrip('0').rstrip('.')
    label = money(values[0]) + '/' + money(values[1])
    if len(values) == 3:
        label += '(' + money(values[2]) + ')'
    return dict(big_blind=format(values[1], 'f'), label='≈ ' + label + ' USD')
