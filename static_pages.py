from membership_plans import PLANS
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
    return _info_sections('About Us', 'Discover private poker clubs and games with friends.', [
        ('What is TableRadar?', 'TableRadar is an independent information service for people who enjoy poker and want to discover private clubs and games with friends. We bring table information into one clear, easy-to-use directory.'),
        ('What we provide', 'Browse game formats, table features, blinds, player counts and club contact details. Use filters and favourites to find the tables that interest you. Registered club owners can submit their club information for review.'),
        ('Our role', 'We publish information and help people find the appropriate club contact. Memberships pay for access to our information service; Host memberships pay for club listing and monitoring. TableRadar does not operate the listed clubs or host their games. Each independent club sets its own game rules.'),
        ('How listings work', 'Our team reviews club submissions and maintains table information manually. Availability and settings can change, so check the current details with the club before joining.'),
        ('Host coverage', 'Standard coverage is up to 20 active tables per club at blinds of $0.50/$1 or higher. If a club has more tables, eligible tables are prioritised from the highest blinds down. Heads-up tables are not listed. Contact Live Chat or Telegram @tableradar to discuss coverage beyond 20 tables.'),
        ('Talk to us', 'For help with your TableRadar account, the directory or a club listing, use Contact or Live Chat. Questions about a game or club access should go to that club’s contact.'),
    ])


def render_terms_page() -> str:
    return _info_sections('Terms & Conditions', 'Conditions for using the TableRadar information service.', [
        ('1. Information service', 'TableRadar provides a directory of private poker clubs and table information. Paid Player memberships cover access to our information service; paid Host memberships cover club placement and monitoring. We do not operate the listed clubs or host their games.'),
        ('2. Independent clubs', 'Listed clubs and applications are independently operated. A listing or contact link does not mean TableRadar owns, manages or endorses a club. Club access and game participation are arranged with the relevant club.'),
        ('3. Information and availability', 'Table details are maintained manually and may change between updates. Formats, player counts and availability are provided for reference. Confirm the current details and rules with the club.'),
        ('4. Your account', 'Keep your sign-in details secure and provide accurate information. Do not share access, impersonate another person, submit misleading listings or misuse other users’ information. Access to account features depends on the service option shown in your profile.'),
        ('5. Club listings', 'Club submissions are reviewed before placement. Service status and the listing period appear in the Host dashboard. Owners should keep their contact and club details current. TableRadar may correct, decline or remove inaccurate or inappropriate listings.'),
        ('Host listing coverage', 'Host Starter covers up to 6 active tables per club; Host Pro covers up to 20. Both cover blinds of $0.50/$1 or higher. When a club exceeds its plan limit, eligible tables are selected from the highest blinds down. Heads-up (one-on-one) tables are excluded. Contact Live Chat or Telegram @tableradar to discuss additional coverage.'),
        ('Player trial and payment methods', 'An active 14-day Player Free Trial after email and phone verification includes club and table details and Join. A paid membership is required after the trial ends. Registration or verification alone does not start a trial. Each phone number can receive one trial. Host has no free trial and supports cryptocurrency payment only. Player payment methods are cryptocurrency and, when connected, bank card and PayPal; unavailable methods cannot process payments.'),
        ('6. Responsible use', 'Use the directory only where permitted and meet the applicable age requirements, including a minimum age of 18. You are responsible for checking the rules of any third-party club or application you choose to use.'),
        ('7. Service support and updates', 'TableRadar is responsible for the security of its own service and for the official support it provides. Contact us about your account or a directory listing. Independent clubs are responsible for their own actions, games and arrangements. Contact the club about those matters. The directory and these conditions may be updated as the service develops.'),
    ])


def render_faq_page() -> str:
    questions = [
        ('What is TableRadar?', 'TableRadar is an independent information directory for poker players looking for clubs and games with friends. See About Us to learn how the service works.'),
        ('How do I join a club?', 'Choose Join on a table to see TableRadar and direct club contact options. TableRadar helps you find information; the independent club handles access to its games.'),
        ('How are tables updated?', 'Our team maintains table information manually. Player counts, settings and availability may change between updates. Confirm current details with the club.'),
        ('What do the table icons mean?', 'Icons describe features selected for a table, such as VPIP, Bomb Pot, Double Board or Squid Game. Hover over a feature to see its label. Availability and rules depend on the club and application.'),
        ('What does My Account include?', 'Your profile, account security, favourites and available service options. Verify your email and phone, then start your 14-day Player Free Trial to view club and table details and join clubs. Verification may be unavailable while delivery services are being configured. Host listing requires a separate paid Host plan.'),
        ('What does the Host dashboard show?', 'Club owners with Host access can submit their club information and follow its review, preparation and placement status. The service countdown begins when the listing is approved and activated.'),
        ('What membership plans are available?', f"Player: ${PLANS['player']['price']} for 30 days. Host Starter: $299 for up to 6 active tables in one club. Host Pro: $599 for up to 20 active tables in one club. Host plans also cover 30 days. Payment methods remain unavailable until their service is configured."),
        ('How many tables does Host coverage include?', 'Host Starter covers up to 6 active tables per club; Host Pro covers up to 20. Both cover blinds of $0.50/$1 or higher. We prioritise eligible tables from the highest blinds down and exclude heads-up tables. For coverage beyond your plan limit, contact Live Chat or Telegram @tableradar.'),
        ('What are TableRadar Official and Club Official?', 'TableRadar Official is our official information and support contact. We are responsible for our own service and official assistance. Club Official is the independent club’s own contact; its actions and game arrangements remain the club owner’s responsibility.'),
        ('How can I get help?', 'Use Contact or Live Chat for TableRadar account and listing questions. For questions about a particular game, contact the club directly.'),
    ]
    entries = ''.join(f'<details><summary>{escape(q)}</summary><p>{escape(a)}</p></details>' for q,a in questions)
    content = f"""<h1 class="tr-page-title">A little clarity.</h1><p class="tr-page-intro">Frequently asked questions about TableRadar, memberships and clubs.</p>
    <label for="faq-search" class="tr-muted">Find an answer</label><input id="faq-search" type="search" placeholder="Search questions" style="width:100%;padding:13px 15px;margin:8px 0 24px" autocomplete="off" aria-controls="faq-list">
    <div id="faq-list" class="tr-faq">{entries}</div><p id="faq-empty" hidden class="tr-muted" role="status">No matching questions. Try another search or contact us.</p>
    <script>document.getElementById('faq-search').addEventListener('input',function(){{const query=this.value.trim().toLowerCase();let count=0;document.querySelectorAll('#faq-list details').forEach(function(item){{const match=item.textContent.toLowerCase().includes(query);item.hidden=!match;if(match)count++;}});document.getElementById('faq-empty').hidden=count>0;}});</script>"""
    return _shell('FAQ', content)


def render_privacy_page() -> str:
    content = _info_sections('Privacy Policy', 'How TableRadar handles account and directory information. Updated 23 October 2026.', [
        ('Who we are and how to contact us', 'TableRadar operates the information directory at tableradar.net. For privacy questions or requests about your data, contact '+CONTACT_EMAIL+' or our official Telegram @tableradar. Please do not send passwords or sign-in secrets.'),
        ('Information you provide', 'We store your email address, username, account settings and service status. Password accounts use a password hash rather than a readable password. Club submissions contain the owner name, club name and ID, application, currency, Telegram contact and any notes you submit. We also store support conversations and staff review information.'),
        ('Google and Discord sign-in', 'If you choose Google, we request only openid, email and profile to verify your identity. If you choose Discord, we request identify and email. We receive a provider account identifier, verified email address and display name. We store the provider identifier linked to your TableRadar account, together with your account email and name. We do not request access to Gmail messages, Google Drive, your Discord messages or servers. Provider access and refresh tokens are used during sign-in and are not saved in the account database.'),
        ('How we use information', 'We use account information to authenticate you, maintain your profile and preferences, provide support, review club submissions and control access to service and staff features. Google and Discord identity information is used for sign-in and account linking. We do not use provider identity information for advertising or sell it.'),
        ('What other people can see', 'Approved club listing details and the club contact intended for players may appear in the public directory and Join window. Your account email, private support conversation and sign-in identifiers are not published as part of the directory. Authorised support staff can read support conversations, and authorised staff can review club requests and account service details needed for their work. Do not put private information into public listing fields.'),
        ('Hosting and third-party services', 'TableRadar uses Render to host the website and its PostgreSQL database. Google or Discord processes your chosen sign-in under its own privacy terms. Opening Telegram or an independent club link takes you to a separate service. Hosting or sign-in services may process information outside your country; the location and safeguards depend on the service involved.'),
        ('Email and phone verification and Player trials', 'When verification is enabled, we use Resend to send email confirmation codes and Twilio Verify to send and check SMS codes you request. A trial starts only after email and phone confirmation and lasts 14 days. A keyed cryptographic identifier of the phone number and email is kept to prevent repeat trials across accounts, including after an account is removed. Raw phone numbers are held in short-lived verification records and are removed after expiry during subsequent cleanup; SMS providers may retain their own records under their policies. We retain verification dates, trial dates and temporary attempt limits to prevent abuse. We do not use verification phone numbers for marketing. These delivery integrations are unavailable until configured.'),
        ('Optional activity statistics and security records', 'Approximate active time, the last active date and the last general site section are shared with managers only if you switch on optional activity statistics in My Account → Privacy preferences. This choice is off by default and does not affect membership. You can switch it off at any time; collection then stops, including from older open tabs. Focused visible tabs with recent interaction may count as active; background or idle tabs do not intentionally count. These estimates are not proof of attention. We do not collect typed contents, screenshots, precise location or full browsing URLs for this feature. Existing records are not reconstructed and remain subject to the retention choices below. Successful sign-in dates and counts are kept separately for account operation and security, regardless of this optional choice.'),
        ('Cookies, preferences and technical records', 'An essential signed session cookie keeps you signed in and protects sign-in flows. Browser storage remembers directory preferences and favourites; signed-in filter settings are also saved with your account. Sign-in validation records expire after ten minutes and are removed when consumed or during later sign-in cleanup. Hosting infrastructure may retain technical connection and error logs for operation and security. Blocking essential cookies can prevent sign-in.'),
        ('Retention and your choices', 'Account information, club review records and support history are retained while needed to provide the service, address support or security issues and meet applicable obligations. There is currently no automatic account-deletion control or fixed automatic deletion schedule for these records. Contact us to request access, correction or deletion, or to ask about connected sign-in methods. We may need to verify your identity first. Any rights and exceptions depend on applicable law, and backup copies may remain until their normal replacement. You can also revoke TableRadar access in Google or Discord; revocation does not itself delete your TableRadar account.'),
        ('Security and eligibility', 'We use HTTPS, password hashing and role-based staff access. No online service can guarantee complete security. The directory is intended for adults aged eighteen or older. Contact us if you believe a child has provided personal information.'),
        ('Policy updates', 'We will update this page when our data practices change. Check the date above for the current version. For questions about a listed club’s own handling of data, contact that independent club.'),
    ])
    return content
