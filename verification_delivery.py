"""Outbound verification adapters. No sandbox bypass and no credential logging."""
import os
import re
import httpx


class DeliveryUnavailable(ValueError):
    pass


def ready():
    names = ('RESEND_API_KEY', 'VERIFICATION_EMAIL_FROM', 'TWILIO_API_KEY',
             'TWILIO_API_SECRET', 'TWILIO_VERIFY_SERVICE_SID', 'TRIAL_PHONE_PEPPER')
    return all(os.getenv(name, '').strip() for name in names) and len(os.getenv('TRIAL_PHONE_PEPPER', '')) >= 32


def phone_number(value):
    value = str(value or '').strip()
    if not re.fullmatch(r'\+[1-9][0-9]{7,14}', value):
        raise ValueError('Enter your phone in international format, for example +447700900123, without spaces.')
    return value


def send_email(email, code, identifier):
    response = httpx.post('https://api.resend.com/emails',
        headers={'Authorization': 'Bearer ' + os.environ['RESEND_API_KEY'],
                 'Idempotency-Key': identifier},
        json={'from': os.environ['VERIFICATION_EMAIL_FROM'], 'to': [email],
              'subject': 'Your TableRadar email verification code',
              'text': 'Your TableRadar verification code is: ' + code + '. It expires in 10 minutes. If you did not request it, ignore this email. Never share the code.'},
        timeout=15, follow_redirects=False)
    if response.status_code not in (200, 201) or not response.json().get('id'):
        raise DeliveryUnavailable('Email could not be sent. Try again later.')


def _twilio(endpoint, data):
    service = os.environ['TWILIO_VERIFY_SERVICE_SID']
    if not re.fullmatch(r'VA[0-9a-fA-F]{32}', service):
        raise DeliveryUnavailable('Phone verification is not configured.')
    response = httpx.post('https://verify.twilio.com/v2/Services/' + service + '/' + endpoint,
        auth=(os.environ['TWILIO_API_KEY'], os.environ['TWILIO_API_SECRET']),
        data=data, timeout=15, follow_redirects=False)
    if response.status_code not in (200, 201):
        raise DeliveryUnavailable('Phone verification is unavailable or the code expired. Request a new code later.')
    return response.json()


def send_phone(phone):
    result = _twilio('Verifications', {'To': phone, 'Channel': 'sms'})
    if (result.get('status') != 'pending' or result.get('to') != phone
            or result.get('service_sid') != os.environ['TWILIO_VERIFY_SERVICE_SID']
            or not re.fullmatch(r'VE[0-9a-fA-F]{32}', str(result.get('sid', '')))):
        raise DeliveryUnavailable('Phone verification could not be started.')
    return result['sid']


def check_phone(phone, sid, code):
    if not re.fullmatch(r'[0-9]{4,10}', str(code)):
        return False
    result = _twilio('VerificationCheck', {'VerificationSid': sid, 'Code': code})
    return (result.get('status') == 'approved' and result.get('to') == phone
            and result.get('sid') == sid and result.get('service_sid') == os.environ['TWILIO_VERIFY_SERVICE_SID'])
