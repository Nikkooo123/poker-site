from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import contextmanager
from fastapi import FastAPI
from membership_plans import PLANS,host_product,table_limit
from brand import render_host_listing_notice
from auth.profile_view import render_profile,render_payment_page
from payment_choices import membership_payment_page
from crypto_checkout import checkout_page
import account_membership as accounts
import crypto_orders as orders
from host_capacity import require_capacity

assert PLANS['player']['price']=='29.99'
assert PLANS['host_starter']['price']=='299.00' and PLANS['host_starter']['table_limit']==6
assert PLANS['host_pro']['price']=='599.00' and PLANS['host_pro']['table_limit']==20
assert host_product({})=='host_pro' and table_limit({})==20
for tier,limit in (('starter',6),('pro',20)):
 text=render_host_listing_notice(tier)
 assert f'{limit} active tables per club' in text and f'more than {limit} active tables' in text
 assert 'at least one seated player' in text and 'higher blinds and more seated players' in text
 assert 'Heads-up' in text and '$0.50/$1' in text
 if tier=='starter':
  assert '/pay/host_pro' in text and 'more than 6 active tables' in text
  assert 'Live Chat' not in text and 'Telegram' not in text
 else:
  assert 'Live Chat' in text and 'Telegram' in text
for user in ({'email':'fixture@example.test'}, {'email':'fixture@example.test','plan':'host','host_tier':'starter','is_active':True}, {'email':'fixture@example.test','plan':'host','is_active':True,'membership_test_enabled':True,'_can_test':True}):
 html=render_profile(user)
 assert all(f'data-plan="{key}"' in html for key in PLANS)
 assert all(price in html for price in ('$29.99','$299','$599'))
 assert '$600' not in html and 'host_starter' in html and 'host_pro' in html
for key in PLANS:
 request=SimpleNamespace(session={})
 user={'email':'fixture@example.test','email_verified_at':'yes'}
 text=membership_payment_page(request,user,key).body.decode()
 assert PLANS[key]['name'] in text and PLANS[key]['price'] in text
 if key!='player':assert f"{PLANS[key]['table_limit']} active tables" in text
 with patch('crypto_checkout.CryptopayClient') as client:
  client.return_value.ready.return_value=False
  text=checkout_page(request,user,key).body.decode()
  assert PLANS[key]['name'] in text and PLANS[key]['price'] in text
  assert 'Crypto checkout unavailable' in text
class Cursor:
 def __init__(self,tier,count):self.tier=tier;self.count=count;self.stage=0
 def execute(self,q,p):
  if 'FOR UPDATE OF c' in q:self.stage=1
  else:assert self.stage==1;self.stage=2
 def fetchone(self):return {'host_tier':self.tier} if self.stage==1 else {'count':self.count}
for tier,limit in (('starter',6),('pro',20)):
 require_capacity(Cursor(tier,limit-1),4)
 try:require_capacity(Cursor(tier,limit),4)
 except ValueError as e:assert str(limit) in str(e)
 else:raise AssertionError('capacity exceeded')
class Result:
 def fetchone(self):return ('fixture@example.test',)
class Conn:
 def execute(self,*args):return Result()
@contextmanager
def connection():yield Conn()
with patch.object(orders.repository,'connection',connection):
 for key in ('player','host_starter','host_pro','host'):
  order=orders.create('fixture@example.test',key,'BTC','bitcoin')
  assert order['price_amount']==orders.PRICES[key]
  assert order['plan']==('player' if key=='player' else 'host')
  if key!='player':assert order['table_limit']==(6 if key=='host_starter' else 20)
app=FastAPI();fixture={'email':'fixture@example.test'}
accounts.install_account_routes(app,lambda request:fixture)
endpoint=next(r.endpoint for r in app.routes if getattr(r,'path','')=='/account/test-membership')
for key,tier in (('host_starter','starter'),('host_pro','pro')):
 request=SimpleNamespace(session={'account_csrf':'token'})
 with patch.object(accounts,'is_manager',return_value=True),patch.object(accounts,'update_user') as save:
  result=endpoint(request,plan=key,csrf='token')
  assert result.status_code==303
  assert save.call_args.kwargs['plan']=='host' and save.call_args.kwargs['host_tier']==tier
print('PASS: 3 profile cards, prices/terms, legacy Host->Pro, all payment/crypto pages offline, capacity boundaries, order product snapshots, manager preview tier mapping')

# Real grant path with in-memory transaction doubles; never calls a provider/DB.
class Row:
 def __init__(self,value=None):self.value=value
 def fetchone(self):return self.value
class Settlement:
 def __init__(self,order,user):self.order=dict(order);self.user=dict(user);self.account_writes=0
 def execute(self,q,p=None):
  if q.startswith('SELECT document FROM tableradar_crypto_orders'):return Row((self.order,))
  if q.startswith('SELECT document FROM tableradar_accounts'):return Row((self.user,))
  if q.startswith('UPDATE tableradar_accounts'):self.user=dict(p[0].obj);self.account_writes+=1
  if q.startswith('UPDATE tableradar_crypto_orders'):self.order=dict(p[0].obj)
  return Row()
for tier,amount in (('starter','299.00'),('pro','599.00')):
 order=dict(id='test',email='fixture@example.test',plan='host',product='host_'+tier,host_tier=tier,price_amount=amount,environment='production',fulfilled=False)
 conn=Settlement(order,dict(email='fixture@example.test',plan='inactive'))
 @contextmanager
 def db():yield conn
 with patch.object(orders.repository,'connection',db),patch.object(orders,'completed_invoice_matches',return_value=True):
  result=orders.settle('test',{})
  assert result['fulfilled'] and conn.user['plan']=='host' and conn.user['host_tier']==tier
  assert conn.user['host_paid_days']==30 and conn.user['host_service_state']=='preparing'
  orders.settle('test',{})
  assert conn.account_writes==1
# Paid tier changes are held for review, never silently downgrade an active club.
conn=Settlement(dict(id='test',email='fixture@example.test',plan='host',host_tier='starter',environment='production',fulfilled=False),dict(email='fixture@example.test',plan='host',is_active=True,host_tier='pro',membership_expires_at=(datetime.now(timezone.utc)+timedelta(days=10)).isoformat()))
@contextmanager
def db():yield conn
with patch.object(orders.repository,'connection',db),patch.object(orders,'completed_invoice_matches',return_value=True):
 result=orders.settle('test',{})
 assert result['status']=='review_required' and conn.account_writes==0
 assert conn.user['host_tier']=='pro'
print('PASS: confirmed Starter/Pro grant canonical Host with exact tier; replay idempotence; active tier changes require review')

fixture.update(plan='host',host_tier='starter',is_active=True,days_left=30)
host_page=next(r.endpoint for r in app.routes if getattr(r,'path','')=='/host')
request=SimpleNamespace(session={'account_csrf':'token'})
with patch.object(accounts,'account_context',side_effect=lambda r,u:dict(u,_csrf='token')):
 body=host_page(request)
 assert 'Host Starter' in body and 'up to 6 eligible tables' in body and '6 active tables per club' in body
submit=next(r.endpoint for r in app.routes if getattr(r,'path','')=='/host/club')
with patch.object(accounts,'update_user') as save:
 response=submit(request,csrf='token',club_name='Fixture club',application='ClubGG',club_code='123',notes='',owner_name='Fixture',telegram='@fixturehost',currency='USD',listing_conditions='accepted')
 assert response.status_code==303
 application=save.call_args.kwargs['club_application']
 assert application['host_tier']=='starter' and application['table_limit']==6
print('PASS: Starter dashboard conditions and submitted application retain correct 6-table tier')
