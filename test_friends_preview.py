from unittest.mock import patch
from datetime import datetime,timedelta,timezone
from html.parser import HTMLParser
import os
from player_access import directory_access,join_access,render_trial_notice
from views import render_public_card,render_public_page
future=(datetime.now(timezone.utc)+timedelta(days=5)).isoformat()
t={'id':1,'club':'PUBLIC_CLUB','table_name':'PUBLIC_TABLE','union_name':'PUBLIC_UNION','players':6,'seats':6,'owner_name':'OWNER_PRIVATE','owner_telegram':'owner_private_contact','affiliate_name':'AFFILIATE_PRIVATE','affiliate_telegram':'affiliate_private_contact'}
users=[None,{'email':'unverified@example.test'},{'email_verified_at':'yes'},{'email_verified_at':'yes','phone_verified_at':'yes','trial_phone_digest':'x','player_trial_expires_at':future},{'plan':'player','is_active':True,'membership_source':'crypto','membership_expires_at':future},{'plan':'host','is_active':True,'membership_source':'crypto','membership_expires_at':future},{'staff_role':'table_admin'},{'staff_role':'manager','email':'nikita.novikovs@gmail.com'}]
class Parse(HTMLParser):
 def __init__(self):super().__init__();self.buttons=[]
 def handle_starttag(self,tag,attrs):
  if tag=='button':self.buttons.append(dict(attrs))
with patch.dict(os.environ,{'FRIENDS_PREVIEW_ENABLED':'true'}):
 for user in users:
  allowed=bool(user and user.get('staff_role')=='manager')
  assert directory_access(user) and join_access(user)==allowed
  card=render_public_card(t,show_club=directory_access(user),can_join=join_access(user))
  assert all(v in card for v in ('PUBLIC_CLUB','PUBLIC_TABLE','PUBLIC_UNION'))
  assert 'data-name-help' not in card
  assert ('owner_private_contact' in card)==allowed
  assert ('affiliate_private_contact' in card)==allowed
  p=Parse();p.feed(card);b=next(b for b in p.buttons if 'join-' in b.get('class',''))
  if allowed:assert 'disabled' not in b and 'join-open-btn' in b['class'] and 'data-join-help' not in b
  else:assert 'disabled' in b and 'popovertarget' not in b and 'join-locked-btn' in b['class']
  assert render_trial_notice(user)==''
 print('PASS: public names for all 8 account states; Join/contacts only for manager; no trial gate')
with patch.dict(os.environ,{'FRIENDS_PREVIEW_ENABLED':'false'}):
 assert not directory_access(None)
 assert join_access(users[3])
 card=render_public_card(t,show_club=False,can_join=False)
 assert 'PUBLIC_CLUB' not in card and 'data-name-help' in card and 'popovertarget="guest-access"' in card
 assert 'Verify your email and phone number, then start your 14-day Free Trial to join the club.' in card
 print('PASS: switching preview off restores saved stars/locks/text/trial Join')
