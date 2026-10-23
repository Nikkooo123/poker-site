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


def render_terms_page() -> str:
    content = f"""
    <div style="width:980px;margin:20px auto 0 auto;">
        <div class="glass" style="border-radius:22px;padding:28px;box-sizing:border-box;">
            <div style="font:600 38px 'Segoe UI',Arial;color:#fff;margin-bottom:10px;">Terms & Conditions</div>
            <div style="font:600 16px Arial;color:#d3d8df;line-height:1.7;">
                Below is a draft of business protection terms for {escape(BUSINESS_NAME)}.
            </div>

            <div style="margin-top:22px;display:grid;gap:14px;">
                <div class="small-card">
                    <div style="font:600 19px 'Segoe UI',Arial;color:#fff;margin-bottom:8px;">1. Intermediary role</div>
                    <div style="font:400 15px 'Segoe UI',Arial;color:#dce4db;line-height:1.65;">
                        {escape(BUSINESS_NAME)} acts as an intermediary / marketing directory between players and third-party club owners or affiliates.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:600 19px 'Segoe UI',Arial;color:#fff;margin-bottom:8px;">2. Third-party clubs</div>
                    <div style="font:400 15px 'Segoe UI',Arial;color:#dce4db;line-height:1.65;">
                        Clubs listed on the website may be owned or operated by third parties. Each club owner is independently responsible for their own club operations.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:600 19px 'Segoe UI',Arial;color:#fff;margin-bottom:8px;">3. Deposits, balances and payouts</div>
                    <div style="font:400 15px 'Segoe UI',Arial;color:#dce4db;line-height:1.65;">
                        If a user chooses to join through a direct club contact or club official link, all deposits, balances, settlements and payouts are handled directly between the user and that club owner.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:600 19px 'Segoe UI',Arial;color:#fff;margin-bottom:8px;">4. Official affiliate route</div>
                    <div style="font:400 15px 'Segoe UI',Arial;color:#dce4db;line-height:1.65;">
                        Where a user joins through the official {escape(BUSINESS_NAME)} affiliate route and the website explicitly states responsibility, {escape(BUSINESS_NAME)} may assist the user regarding onboarding and communication.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:600 19px 'Segoe UI',Arial;color:#fff;margin-bottom:8px;">5. No guarantee of third-party performance</div>
                    <div style="font:400 15px 'Segoe UI',Arial;color:#dce4db;line-height:1.65;">
                        {escape(BUSINESS_NAME)} does not guarantee the conduct, solvency, performance or availability of any third-party club, app, agent or owner.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:600 19px 'Segoe UI',Arial;color:#fff;margin-bottom:8px;">6. User responsibility</div>
                    <div style="font:400 15px 'Segoe UI',Arial;color:#dce4db;line-height:1.65;">
                        Users are responsible for verifying who they are dealing with, understanding the selected joining route, and ensuring compliance with their local laws and age requirements.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:600 19px 'Segoe UI',Arial;color:#fff;margin-bottom:8px;">7. Changes</div>
                    <div style="font:400 15px 'Segoe UI',Arial;color:#dce4db;line-height:1.65;">
                        These terms may be updated from time to time. Continued use of the website means acceptance of the latest version.
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return _shell("Terms & Conditions", content)


def render_faq_page() -> str:
    questions = [
        ('What is TableRadar?', 'TableRadar is a directory of active poker tables. Compare the listed games, formats, blinds and player counts, then find the contact for the club you want to join.'),
        ('How do I join a club?', 'Choose Join on a table to see the available club and affiliate contact options. TableRadar does not seat you in a game; you arrange access with the relevant club contact.'),
        ('How are tables updated?', 'Table information is maintained manually. Player counts and availability may change between updates, so confirm the current game with the club.'),
        ('What does Player membership include?', 'Player membership is priced at $29.99 USD for 30 days and provides access to table information, search filters, favorites and your profile. Payment processing is being configured.'),
        ('What does Host membership include?', 'Host membership is priced at $600 USD for 30 days and includes the listing and manual monitoring of one club, in addition to the Player features. Contact TableRadar for club onboarding.'),
        ('Can I pay with crypto or through my bank?', 'Crypto and bank payment options are being prepared. The planned crypto options include Bitcoin, ETH on Ethereum, USDT on Ethereum or TRON, and TRX on TRON. Payments are not available until the payment services are connected.'),
        ('Are memberships automatically renewed?', 'Automatic renewal is not enabled yet. A recurring payment service and customer authorization must be configured before automatic collection can be offered.'),
        ('What are TableRadar Official and Club Official?', 'TableRadar Official identifies the platform affiliate contact; Club Official identifies the direct club contact. Check the joining route and the applicable terms before proceeding.'),
        ('Does TableRadar hold club balances or deposits?', 'Club deposits, balances and payouts are handled separately from a TableRadar membership. Confirm the arrangements directly with the club or the selected contact.'),
        ('How can I get help?', 'Use the Contact page for questions about your account or listing. For an issue inside a club, contact that club directly.')
    ]
    entries = ''.join(f'<details><summary>{escape(q)}</summary><p>{escape(a)}</p></details>' for q,a in questions)
    content = f"""<h1 class="tr-page-title">A little clarity.</h1><p class="tr-page-intro">Frequently asked questions about TableRadar, memberships and clubs.</p>
    <label for="faq-search" class="tr-muted">Find an answer</label><input id="faq-search" type="search" placeholder="Search questions" style="width:100%;padding:13px 15px;margin:8px 0 24px" autocomplete="off" aria-controls="faq-list">
    <div id="faq-list" class="tr-faq">{entries}</div><p id="faq-empty" hidden class="tr-muted" role="status">No matching questions. Try another search or contact us.</p>
    <script>document.getElementById('faq-search').addEventListener('input',function(){{const query=this.value.trim().toLowerCase();let count=0;document.querySelectorAll('#faq-list details').forEach(function(item){{const match=item.textContent.toLowerCase().includes(query);item.hidden=!match;if(match)count++;}});document.getElementById('faq-empty').hidden=count>0;}});</script>"""
    return _shell('FAQ', content)
