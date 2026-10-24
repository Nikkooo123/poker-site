import contextlib,os
from unittest.mock import patch
import verification_storage as store
from auth.auth_storage import create_user
class Result:
    def __init__(self,value=None):self.value=value
    def fetchone(self):return self.value
class Conn:
    def __init__(self,used):self.used=used;self.created=False
    def execute(self,sql,args=None):
        if 'SELECT document FROM tableradar_accounts' in sql:
            return Result(({'email':'new@example.test','email_verified_at':'yes','credential_version':'v1'},))
        if 'SELECT 1 FROM tableradar_trial_claims' in sql:
            assert all(len(v)==64 for v in args)
            return Result((1,) if self.used else None)
        if 'INSERT INTO tableradar_verification_challenges' in sql:self.created=True
        return Result()
for used in (True,False):
    conn=Conn(used)
    @contextlib.contextmanager
    def connect():yield conn
    with patch.dict(os.environ,{'TRIAL_PHONE_PEPPER':'test-only-private-pepper-'*3}),patch.object(store.repository,'connection',connect),patch.object(store,'ensure_schema'),patch.object(store,'_limit',return_value=True):
        if used:
            try:store.create('new@example.test','phone','+447700900123','v1')
            except ValueError as exc:assert 'already linked' in str(exc)
            else:raise AssertionError('reserved identity accepted')
            assert not conn.created
        else:
            assert store.create('new@example.test','phone','+447700900124','v1')['id']
            assert conn.created
with patch('auth.auth_storage.load_users',return_value=[{'email':'existing@example.test'}]):
    assert create_user(' EXISTING@EXAMPLE.TEST ','safe-password-123') is False
print('PASS: reserved email/phone fails before challenge/send, new identifiers eligible, email case/spacing duplicate rejected')
