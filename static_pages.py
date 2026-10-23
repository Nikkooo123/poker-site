from html import escape
from brand import BRAND_NAME, SUPPORT_EMAIL, TELEGRAM_URL, render_brand_logo, render_site_theme, render_site_footer

BUSINESS_NAME = BRAND_NAME
CONTACT_EMAIL = SUPPORT_EMAIL
CONTACT_TELEGRAM = TELEGRAM_URL


def _shell(title: str, content: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{escape(title)} · {escape(BUSINESS_NAME)}</title>{render_site_theme()}</head>
    <body style="margin:0"><header class="tr-site-header">{render_brand_logo('/')}
    <a class="tr-button" href="/">← Back to tables</a></header>
    <main class="tr-site-main">{content}</main>{render_site_footer()}</body></html>"""


def render_contact_page() -> str:
    telegram = CONTACT_TELEGRAM if CONTACT_TELEGRAM.startswith('https://t.me/') and 'your_telegram_username' not in CONTACT_TELEGRAM else ''
    telegram_html = f'<p class="tr-muted">Telegram</p><a class="tr-button" href="{escape(telegram)}" target="_blank" rel="noopener noreferrer">Telegram @{escape(telegram.rsplit("/",1)[-1])} ↗</a>' if telegram else '<p class="tr-muted">Telegram contact will be available here once configured.</p>'
    return _shell('Contact', f"""<h1 class="tr-page-title">Let's get in touch.</h1>
    <p class="tr-page-intro">Questions about your membership or listing your club? Contact TableRadar.</p>
    <div class="glass" style="padding:28px;border-radius:22px"><h2 style="font-size:21px;font-weight:600;margin-top:0">Contact the team</h2>
    <p class="tr-muted">Email</p><a href="mailto:{escape(CONTACT_EMAIL)}" style="color:#a8d8c4;overflow-wrap:anywhere">{escape(CONTACT_EMAIL)}</a>
    {telegram_html}<h2 style="font-size:21px;font-weight:600;margin-top:26px">Live chat</h2><p class="tr-muted">Message our administrators and managers. Sign in to save your conversation and receive replies here.</p><button class="tr-button" type="button" data-open-live-chat>Open Live Chat</button></div>""")


def _info_sections(title, intro, sections):
    cards=''.join(f'<section class="tr-info-card" style="padding:20px;margin:14px 0"><h2 style="font-size:19px">{escape(heading)}</h2><p class="tr-muted" style="line-height:1.7">{escape(text)}</p></section>' for heading,text in sections)
    return _shell(title, f'<h1 class="tr-page-title">{escape(title)}</h1><p class="tr-page-intro">{escape(intro)}</p>{cards}')


def render_about_page():
    return _info_sections('About Us', 'Information that helps poker friends find their next game.', [
        ('What is TableRadar?', 'TableRadar is an independent information service for poker players who want to discover clubs and find games with friends. We bring table information into one clear, easy-to-use directory.'),
        ('What we provide', 'Browse game formats, table features, blinds, player counts and club contact details. Use filters and favourites to find the tables that interest you. Registered club owners can submit their club information for review.'),
        ('Our role', 'We publish information and help people find the appropriate club contact. TableRadar does not operate poker clubs or host games. We are not a financial organisation and do not provide financial services.'),
        ('How listings work', 'Our team reviews club submissions and maintains table information manually. Availability and settings can change, so check the current details with the club before joining.'),
        ('Talk to us', 'For help with your TableRadar account, the directory or a club listing, use Contact or Live Chat. Questions about a game or club access should go to that club’s contact.'),
    ])


def render_terms_page() -> str:
    return _info_sections('Terms & Conditions', 'Conditions for using the TableRadar information service.', [
        ('1. Information service', 'TableRadar provides a directory of poker clubs and table information. We do not operate the listed clubs or host their games. We are not a financial organisation.'),
        ('2. Independent clubs', 'Listed clubs and applications are independently operated. A listing or contact link does not mean TableRadar owns, manages or endorses a club. Club access and game participation are arranged with the relevant club.'),
        ('3. Information and availability', 'Table details are maintained manually and may change between updates. Formats, player counts and availability are provided for reference. Confirm the current details and rules with the club.'),
        ('4. Your account', 'Keep your sign-in details secure and provide accurate information. Do not share access, impersonate another person, submit misleading listings or misuse other users’ information. Access to account features depends on the service option shown in your profile.'),
        ('5. Club listings', 'Club submissions are reviewed before placement. Service status and the listing period appear in the Host dashboard. Owners should keep their contact and club details current. TableRadar may correct, decline or remove inaccurate or inappropriate listings.'),
        ('6. Responsible use', 'Use the directory only where permitted and meet the applicable age requirements, including a minimum age of 18. You are responsible for checking the rules of any third-party club or application you choose to use.'),
        ('7. Service support and updates', 'Contact TableRadar about your account or a directory listing. Contact the independent club about its games. The directory and these conditions may be updated as the service develops.'),
    ])


def render_faq_page() -> str:
    questions = [
        ('What is TableRadar?', 'TableRadar is an independent information directory for poker players looking for clubs and games with friends. See About Us to learn how the service works.'),
        ('How do I join a club?', 'Choose Join on a table to see TableRadar and direct club contact options. TableRadar helps you find information; the independent club handles access to its games.'),
        ('How are tables updated?', 'Our team maintains table information manually. Player counts, settings and availability may change between updates. Confirm current details with the club.'),
        ('What do the table icons mean?', 'Icons describe features selected for a table, such as VPIP, Bomb Pot, Double Board or Squid Game. Hover over a feature to see its label. Availability and rules depend on the club and application.'),
        ('What does My Account include?', 'Your profile, account security, favourites and available service options. Registered visitors can currently view full table information without an active Player membership.'),
        ('What does the Host dashboard show?', 'Club owners with Host access can submit their club information and follow its review, preparation and placement status. The service countdown begins when the listing is approved and activated.'),
        ('What are TableRadar Official and Club Official?', 'TableRadar Official is our information and support contact. Club Official is the independent club’s own contact for current table details and access requirements.'),
        ('How can I get help?', 'Use Contact or Live Chat for TableRadar account and listing questions. For questions about a particular game, contact the club directly.'),
    ]
    entries = ''.join(f'<details><summary>{escape(q)}</summary><p>{escape(a)}</p></details>' for q,a in questions)
    content = f"""<h1 class="tr-page-title">A little clarity.</h1><p class="tr-page-intro">Frequently asked questions about TableRadar, memberships and clubs.</p>
    <label for="faq-search" class="tr-muted">Find an answer</label><input id="faq-search" type="search" placeholder="Search questions" style="width:100%;padding:13px 15px;margin:8px 0 24px" autocomplete="off" aria-controls="faq-list">
    <div id="faq-list" class="tr-faq">{entries}</div><p id="faq-empty" hidden class="tr-muted" role="status">No matching questions. Try another search or contact us.</p>
    <script>document.getElementById('faq-search').addEventListener('input',function(){{const query=this.value.trim().toLowerCase();let count=0;document.querySelectorAll('#faq-list details').forEach(function(item){{const match=item.textContent.toLowerCase().includes(query);item.hidden=!match;if(match)count++;}});document.getElementById('faq-empty').hidden=count>0;}});</script>"""
    return _shell('FAQ', content)
