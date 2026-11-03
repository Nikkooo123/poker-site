"""Weekly server-side market FX cache; never send club data to the provider."""
import json
import os
import tempfile
import threading
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import urlopen

WEEK = 7 * 86400
MAX_AGE = 30 * 86400
CACHE = Path(os.environ.get('TABLE_RADAR_FX_CACHE', str(Path(tempfile.gettempdir()) / 'table-radar-fx.json')))
_lock = threading.Lock()
_snapshot = None
_retry_at = 0

def validate(payload):
    if not isinstance(payload, dict) or payload.get('result') != 'success' or payload.get('base_code') != 'USD':
        raise ValueError('Invalid FX response')
    stamp = float(payload['time_last_update_unix'])
    if not time.time() - MAX_AGE < stamp <= time.time() + 86400:
        raise ValueError('Invalid FX date')
    rates = payload['rates']
    if not isinstance(rates, dict) or rates.get('USD') != 1 or len(rates) < 20:
        raise ValueError('Incomplete FX response')
    for code, value in rates.items():
        try:
            rate = Decimal(str(value))
        except InvalidOperation:
            raise ValueError('Invalid FX rate') from None
        if len(code) != 3 or not code.isalpha() or not rate.is_finite() or rate <= 0:
            raise ValueError('Invalid FX rate')
    return payload

def market_usd_rate(currency):
    global _snapshot, _retry_at
    code = str(currency or '').strip().upper()
    if code == 'USD':
        return Decimal(1)
    if len(code) != 3 or not code.isalpha():
        return None
    with _lock:
        now = time.time()
        if _snapshot is None:
            try:
                _snapshot = validate(json.loads(CACHE.read_text(encoding='utf-8')))
            except (OSError, ValueError, KeyError, TypeError):
                pass
        if (_snapshot is None or now - _snapshot['time_last_update_unix'] >= WEEK) and now >= _retry_at:
            _retry_at = now + 3600
            try:
                with urlopen('https://open.er-api.com/v6/latest/USD', timeout=5) as response:
                    fresh = validate(json.loads(response.read(200000)))
                _snapshot = fresh
                try:
                    temporary = CACHE.with_suffix('.tmp')
                    temporary.write_text(json.dumps(fresh), encoding='utf-8')
                    temporary.replace(CACHE)
                except OSError:
                    pass  # Memory cache still serves this worker.
            except (OSError, ValueError, KeyError, TypeError):
                pass  # Keep the last valid rates during a temporary outage.
        if not _snapshot or now - _snapshot['time_last_update_unix'] > MAX_AGE:
            return None
        value = _snapshot['rates'].get(code)
        return Decimal(1) / Decimal(str(value)) if value is not None else None
