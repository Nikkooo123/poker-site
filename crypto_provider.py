"""Cryptopay protocol adapter. Disabled until the owner configures an approved merchant.

Official references: developers.cryptopay.me/guides/api-basics/authentication/signature
and developers.cryptopay.me/guides/api-basics/callbacks.
Credentials belong in server configuration only. No wallet keys are needed.
"""
import base64
import hashlib
import hmac
import json
import os
import re
from decimal import Decimal, InvalidOperation
from email.utils import formatdate
from urllib.request import Request, build_opener, HTTPRedirectHandler


class CryptoUnavailable(RuntimeError):
    pass


POPULAR_PAIRS = {('BTC','bitcoin'),('ETH','ethereum'),('USDT','ethereum'),('USDT','tron'),
                 ('USDT','solana'),('USDC','ethereum'),('USDC','solana'),('TRX','tron'),
                 ('SOL','solana'),('BNB','bnb_smart_chain')}


def checkout_options(response):
    """Only advertise supported, invoice-enabled coin/network pairs from the provider."""
    options=[]
    for coin in response.get('data',[]):
        for network in coin.get('networks',[]):
            pair=(coin.get('currency'),network.get('network'))
            if pair in POPULAR_PAIRS and network.get('invoices',{}).get('enabled') is True:
                options.append(dict(currency=pair[0],network=pair[1],label=pair[0]+' · '+str(network.get('name') or pair[1])))
    return options


def callback_verified(raw_body: bytes, signature: str, secret: str) -> bool:
    if not secret or len(raw_body) > 131072 or not re.fullmatch('[0-9a-f]{64}', signature):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def authorization_headers(method, path, body, api_key, api_secret, date=None):
    date = date or formatdate(usegmt=True)
    content_type = 'application/json'
    digest = hashlib.md5(body).hexdigest() if body else ''
    message = '\n'.join((method.upper(), digest, content_type, date, path))
    signature = base64.b64encode(hmac.new(api_secret.encode(), message.encode(), hashlib.sha1).digest()).decode()
    return {'Authorization': f'HMAC {api_key}:{signature}', 'Date': date, 'Content-Type': content_type}


def completed_invoice_matches(invoice, order):
    """The caller must retrieve invoice server-side; a redirect is never payment proof."""
    try:
        amount = Decimal(str(invoice['price_amount']))
        expected = Decimal(str(order['price_amount']))
        return (invoice.get('status') == 'completed'
                and invoice.get('status_context') is None
                and invoice.get('id') == order['invoice_id']
                and invoice.get('custom_id') == order['id']
                and invoice.get('price_currency') == order['price_currency']
                and invoice.get('pay_currency') == order['pay_currency']
                and invoice.get('network') == order['network']
                and amount.is_finite() and expected.is_finite()
                and expected > 0 and amount == expected)
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return False


class CryptopayClient:
    def __init__(self):
        self.key = os.getenv('CRYPTOPAY_API_KEY', '')
        self.secret = os.getenv('CRYPTOPAY_API_SECRET', '')
        self.environment = os.getenv('CRYPTOPAY_ENVIRONMENT', 'sandbox')
        self.sandbox = self.environment == 'sandbox'
        self.enabled = os.getenv('CRYPTOPAY_ENABLED', '') == 'true'
        self.approved = os.getenv('CRYPTOPAY_MERCHANT_APPROVED', '') == 'true'

    def ready(self):
        return bool(self.environment in ('sandbox', 'production') and self.enabled and self.key and self.secret and (self.sandbox or self.approved))

    def request(self, method, path, payload=None):
        if not self.ready():
            raise CryptoUnavailable('Crypto checkout is not configured.')
        # Restrict outgoing operations to invoice creation/status and currency discovery.
        if not ((method == 'GET' and (path == '/api/coins' or re.fullmatch('/api/invoices/[a-zA-Z0-9-]{1,80}',path)))
                or (method == 'POST' and path == '/api/invoices')) or '?' in path or '..' in path:
            raise ValueError('Unsupported provider operation')
        body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode() if payload is not None else b''
        headers = authorization_headers(method, path, body, self.key, self.secret)
        base = 'https://business-sandbox.cryptopay.me' if self.sandbox else 'https://business.cryptopay.me'
        request = Request(base + path, data=body if payload is not None else None, headers=headers, method=method)
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None  # Never forward merchant Authorization to a redirect destination.
        with build_opener(NoRedirect()).open(request, timeout=8) as response:
            return json.loads(response.read(1048576))
