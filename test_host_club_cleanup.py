from contextlib import contextmanager
from unittest.mock import patch
from types import SimpleNamespace
import club_table_lifecycle as lifecycle
import club_subscriptions_storage as subscriptions
from fastapi import FastAPI
import account_membership as accounts

class Cursor:
 def __init__(self):self.calls=[];self.rowcount=0
 def execute(self,query,params=None):
  self.calls.append((query,params));self.rowcount=2 if 'WITH removed' in query else 0
 def fetchall(self):return [{'id':7},{'id':9}]
 def fetchone(self):return {'id':7,'owner_email':'fixture@example.test','status':'active'}
 def __enter__(self):return self
 def __exit__(self,*args):pass
cursor=Cursor()
assert lifecycle.cleanup_unavailable_tables(cursor)==4
assert 'FOR UPDATE' in cursor.calls[0][0] and 'access_expires_at' in cursor.calls[0][0]
assert cursor.calls[1][1][0]==[7,9]
assert 'club_subscription_id IS NOT NULL' in cursor.calls[2][0] and 'NOT EXISTS' in cursor.calls[2][0]
assert all('to_jsonb(removed)' in q for q,p in cursor.calls if 'WITH removed' in q)
assert lifecycle.remove_linked_tables(cursor,[],'Empty')==0 and len(cursor.calls)==3
for action in ('delete','disable'):
 cursor=Cursor()
 @contextmanager
 def connection():yield SimpleNamespace(cursor=lambda:cursor)
 with patch.object(subscriptions,'init_club_subscriptions_db'),patch.object(subscriptions,'_connect',connection),patch.object(subscriptions,'_sync_linked_account'):
  subscriptions._change_subscription(7,action)
 deletion=next(i for i,(q,p) in enumerate(cursor.calls) if 'WITH removed' in q)
 parent=next(i for i,(q,p) in enumerate(cursor.calls) if q.startswith('DELETE FROM club_subscriptions') or q.startswith("UPDATE club_subscriptions SET status='inactive'"))
 assert deletion<parent and cursor.calls[deletion][1][0]==[7]

user=dict(email='fixture@example.test',plan='host',is_active=True,host_tier='starter')
app=FastAPI();accounts.install_account_routes(app,lambda request:user)
submit=next(r.endpoint for r in app.routes if getattr(r,'path','')=='/host/club')
request=SimpleNamespace(session={'account_csrf':'token'})
kwargs=dict(csrf='token',club_name='Fixture',application='ClubGG',club_code='123',owner_name='Fixture',telegram='@fixture',currency='USD',listing_conditions='accepted')
for notes in ('','   ','\n\t'):
 with patch.object(accounts,'update_user') as save:
  result=submit(request,notes=notes,**kwargs)
  assert result.status_code==400 and b'rakeback' in result.body
  save.assert_not_called()
print('PASS: locked cleanup archives linked expired/orphaned tables, deletion/disable ordering, no unlinked deletion, empty notes rejected')
