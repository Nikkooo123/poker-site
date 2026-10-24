from datetime import datetime,timedelta,timezone
from html.parser import HTMLParser
import player_access as access
from views import render_public_card,render_public_script
future=(datetime.now(timezone.utc)+timedelta(days=5)).isoformat()
past=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
verified={'email_verified_at':'yes','phone_verified_at':'yes','trial_phone_digest':'digest'}
host={'plan':'host','is_active':True,'membership_source':'crypto','membership_expires_at':future}
cases=[({},False),({'email':'one@example.test'},False),({'email_verified_at':'yes'},False),({'phone_verified_at':'yes','trial_phone_digest':'digest'},False),({**verified,'trial_phone_digest':''},False),(verified,True),({**verified,'player_trial_expires_at':past},True),(host,True),({**host,'membership_expires_at':past},False),({**host,'membership_test_enabled':True},False),({'staff_role':'manager'},True),({'staff_role':'table_admin'},True)]
t={'id':1,'club':'PRIVATE_CLUB','table_name':'PRIVATE_TABLE','players':6,'seats':6,'owner_name':'SECRET_OWNER','owner_telegram':'secret_owner_contact','affiliate_name':'SECRET_AFFILIATE','affiliate_telegram':'secret_affiliate_contact'}
class Buttons(HTMLParser):
    def __init__(self):super().__init__();self.buttons=[]
    def handle_starttag(self,tag,attrs):
        if tag=='button':self.buttons.append(dict(attrs))
for user,allowed in cases:
    assert access.directory_access(user)==allowed,(user,'view')
    assert access.join_access(user)==allowed,(user,'join')
    card=render_public_card(t,show_club=allowed,can_join=allowed)
    assert ('PRIVATE_TABLE' in card)==allowed
    assert ('secret_owner_contact' in card)==allowed
    assert ('secret_affiliate_contact' in card)==allowed
    parser=Buttons();parser.feed(card);button=next(b for b in parser.buttons if 'join-' in b.get('class',''))
    if allowed:
        assert 'join-open-btn' in button['class'] and 'data-join-help' not in button
        assert access.render_trial_notice(user)==''
    else:
        assert 'join-locked-btn' in button['class']
        assert button['data-join-help']=='Register and verify your email and phone number to view club and table details.'
    assert 'title' not in button
assert 'target.dataset.nameHelp || target.dataset.joinHelp' in render_public_script()
print('PASS: 12 launch verification/paid Host/staff cases; names and contacts protected; tooltip on locked Join only')
