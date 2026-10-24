from datetime import datetime,timedelta,timezone
from html.parser import HTMLParser
import player_access as access
from views import render_public_card,render_public_script
future=(datetime.now(timezone.utc)+timedelta(days=5)).isoformat()
past=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
trial={'email_verified_at':'yes','phone_verified_at':'yes','trial_phone_digest':'digest','player_trial_expires_at':future}
paid={'plan':'player','is_active':True,'membership_source':'crypto','membership_expires_at':future,'email_verified_at':'yes'}
cases=[({},False,False),(trial,True,False),(paid,True,True),({**paid,'membership_expires_at':past},False,False),({**paid,'membership_test_enabled':True},True,False),({**paid,'plan':'host'},True,False),({'staff_role':'manager'},True,True),({**paid,'membership_source':'unconfirmed'},True,False)]
for u,view,join in cases:
    assert access.directory_access(u)==view,(u,'view')
    assert access.join_access(u)==join,(u,'join')
t={'id':1,'club':'PRIVATE_CLUB','table_name':'PRIVATE_TABLE','players':6,'seats':6,'owner_name':'SECRET_OWNER','owner_telegram':'secret_owner_contact','affiliate_name':'SECRET_AFFILIATE','affiliate_telegram':'secret_affiliate_contact'}
class Buttons(HTMLParser):
    def __init__(self):super().__init__();self.buttons=[]
    def handle_starttag(self,tag,attrs):
        if tag=='button':self.buttons.append(dict(attrs))
for user in ({},trial,paid):
    card=render_public_card(t,show_club=access.directory_access(user),can_join=access.join_access(user))
    if not access.join_access(user):
        assert 'secret_owner_contact' not in card and 'secret_affiliate_contact' not in card
        assert 'join-open-btn' not in card and 'join-locked-btn' in card
    else:
        assert 'secret_owner_contact' in card and 'join-open-btn' in card
    assert ('PRIVATE_TABLE' in card)==access.directory_access(user)
    parser=Buttons();parser.feed(card)
    join=next(b for b in parser.buttons if 'join-' in b.get('class',''))
    assert join['data-join-help']=='Paid Player plan required to join the club.'
    assert 'title' not in join
assert 'target.dataset.nameHelp || target.dataset.joinHelp' in render_public_script()
print('PASS: 8 entitlement cases; guest/trial/paid names and contacts; locked button and instant shared tooltip')
