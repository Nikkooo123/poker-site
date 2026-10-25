from types import SimpleNamespace
from unittest.mock import patch
from fastapi import FastAPI
from html.parser import HTMLParser
import account_membership as accounts
from club_request_changes import updated_request
from auth.profile_view import render_account_menu

old=dict(status='archived',deleted_at='fixture',club_name='OLD-CLUB',owner_name='OLD-OWNER',
         telegram='@oldcontact',club_code='OLD-CODE',currency='GBP',application='ClubGG',notes='OLD-NOTE')
user=dict(email='fixture@example.test',plan='host',is_active=True,host_tier='starter',
          days_left=30,club_application=old)
app=FastAPI(); accounts.install_account_routes(app,lambda r:user)
endpoint=next(r.endpoint for r in app.routes if getattr(r,'path','')=='/host')
with patch.object(accounts,'account_context',side_effect=lambda r,u:dict(u,_csrf='fixture')):
 html=endpoint(SimpleNamespace(session={}))
 assert 'Submit club for review' in html and 'No club submitted' in html
 assert 'Update club request' not in html
 for value in ('OLD-CLUB','OLD-OWNER','@oldcontact','OLD-CODE','OLD-NOTE'):
  assert value not in html
 class Fields(HTMLParser):
  def __init__(self):super().__init__();self.values={}
  def handle_starttag(self,tag,attrs):
   a=dict(attrs)
   if tag=='input' and a.get('name'):self.values[a['name']]=a.get('value','')
 fields=Fields();fields.feed(html)
 assert all(fields.values[k]=='' for k in ('club_name','club_code','owner_name','telegram','currency'))
 user['club_application']=dict(old,status='pending',deleted_at='')
 html=endpoint(SimpleNamespace(session={}))
 assert 'OLD-CLUB' in html and 'Update club request' in html
new=updated_request({'club_name':'NEW'},old)
assert '_comparison_base' not in new and '_is_update' not in new
assert updated_request({'club_name':'NEW'},{'club_name':'OLD','status':'pending'})['_is_update']
menu=render_account_menu(dict(user,staff_role='manager'))
for label in ('Club subscriptions','Staff access','Test Host / Player','Explore tables'):
 assert label not in menu
assert 'Manager workspace' in menu and 'Host dashboard' in menu
print('PASS: archived requests render blank fields, fresh submission baseline, active drafts retained, simplified menu')
