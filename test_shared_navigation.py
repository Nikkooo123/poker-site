from types import SimpleNamespace
from unittest.mock import patch
from fastapi import FastAPI
import main
import static_pages
import account_membership as accounts
from auth.profile_view import render_account_menu
from views import render_admin_page
from club_subscriptions_view import render_club_subscriptions_page
from auth.auth_views import render_signin_login_page, render_signup_page

user={'email':'manager@example.test','staff_role':'manager'}
pages=[accounts.page('Requests','',user,True),render_admin_page([],manager=True,user=user),render_club_subscriptions_page([],user=user)]
pages += [getattr(static_pages,'render_'+n+'_page')(user) for n in ['about','faq','privacy','terms','contact']]
pages += [render_signin_login_page(user=user),render_signup_page(user=user)]
assert all(user['email'] in h and 'aria-label="Account menu"' in h and 'Staff sign out' not in h for h in pages)
assert '/manager/team' not in render_account_menu({'email':'player@example.test'})
assert '/manager/team' not in render_account_menu({'email':'admin@example.test','staff_role':'table_admin'})
assert 'Sign in →' in static_pages.render_about_page()
with patch.object(main,'get_current_user',return_value=user):
 for name in ['about','faq','privacy','terms','contact']:
  assert user['email'] in getattr(main,name+'_page')(SimpleNamespace())

app=FastAPI()
accounts.install_account_routes(app,lambda r:user)
endpoint=next(r.endpoint for r in app.routes if getattr(r,'path','')=='/manager/membership-test/reset-host')
request=SimpleNamespace(session={'account_csrf':'fixture-csrf'})
with patch.object(accounts,'is_manager',return_value=True), patch('host_test_reset.reset_own_host') as reset:
 assert endpoint(request,csrf='wrong').status_code==403
 reset.assert_not_called()
 response=endpoint(request,csrf='fixture-csrf')
 assert response.status_code==303
 reset.assert_called_once_with(user['email'])
with patch.object(accounts,'is_manager',return_value=False), patch('host_test_reset.reset_own_host') as reset:
 assert endpoint(request,csrf='fixture-csrf').status_code==403
 reset.assert_not_called()
print('PASS: eight page headers, guest menu, staff link visibility, static route user context, reset CSRF/manager/self-only scope')

# The reset preserves identity fields and backs up before deleting only linked data.
from contextlib import contextmanager
import host_test_reset
original=dict(user, username='Nikita',password_hash='fixture-hash',credential_version='fixture-version',
              plan='host',role='host',club_application={'club_name':'Own club'},manual_subscription_id=7)
class Cursor:
 def __init__(self):self.sql=[];self.saved=None
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def execute(self,q,p=None):
  self.sql.append((q,p))
  if q.startswith('UPDATE tableradar_accounts'):self.saved=p[0].obj
 def fetchone(self):return {'document':original}
 def fetchall(self):return [{'id':7,'owner_email':user['email']}] if 'club_subscriptions' in self.sql[-1][0] else [{'id':8,'club_subscription_id':7}]
cursor=Cursor()
@contextmanager
def connection():yield SimpleNamespace(cursor=lambda **kwargs:cursor)
with patch.object(host_test_reset.repository,'connection',connection):
 result=host_test_reset.reset_own_host(user['email'])
assert result['subscriptions']==1 and result['tables']==1
assert all(cursor.saved[k]==original[k] for k in ('email','username','staff_role','password_hash','credential_version'))
assert 'club_application' not in cursor.saved and 'manual_subscription_id' not in cursor.saved
assert cursor.saved['plan']=='inactive' and not cursor.saved['is_active']
queries=[q for q,p in cursor.sql]
assert next(i for i,q in enumerate(queries) if q.startswith('INSERT INTO tableradar_host_reset_backups')) < next(i for i,q in enumerate(queries) if q.startswith('DELETE'))
assert all('tableradar_accounts' not in q for q in queries if q.startswith('DELETE'))
print('PASS: reset identity/staff preservation, linked-only deletion, backup before deletion')
