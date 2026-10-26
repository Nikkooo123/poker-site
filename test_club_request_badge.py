import json
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import FastAPI
import account_membership as accounts
from auth.profile_view import render_account_menu

app=FastAPI();accounts.install_account_routes(app,lambda request:None)
endpoint=next(r.endpoint for r in app.routes if getattr(r,'path','')=='/manager/club-requests/count')
with patch.object(accounts,'is_manager',return_value=False),patch.object(accounts,'pending_club_request_count') as count:
 assert endpoint(SimpleNamespace()).status_code==403
 count.assert_not_called()
for n in (0,1,10):
 with patch.object(accounts,'is_manager',return_value=True),patch.object(accounts,'pending_club_request_count',return_value=n):
  response=endpoint(SimpleNamespace())
  assert response.status_code==200 and json.loads(response.body)=={'pending_count':n}
  assert response.headers['cache-control']=='no-store'
fixtures=[{'club_application':{'status':'pending'}},{'club_application':{}},
          {'club_application':{'status':'approved'}},{'club_application':{'status':'needs_changes'}},
          {'club_application':{'status':'pending','deleted_at':'fixture'}},{'club_application':{'club_name':'New'}}]
with patch.object(accounts,'load_users',return_value=fixtures):assert accounts.pending_club_request_count()==2
html=render_account_menu({'email':'manager@example.test','staff_role':'manager'})
assert 'Club requests<span class="tr-club-request-count"' in html
assert '/manager/club-requests/count' in html and 'setInterval(refresh,15000)' in html
assert '/manager/club-requests/count' not in render_account_menu({'email':'player@example.test'})
print('PASS: manager-only counts 0/1/10, no cache, pending-only filtering, badge in dropdown and background refresh')
