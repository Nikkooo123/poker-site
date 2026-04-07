from html import escape
from brand import BRAND_NAME, SUPPORT_EMAIL, TELEGRAM_URL, render_brand_logo

BUSINESS_NAME = BRAND_NAME
CONTACT_EMAIL = SUPPORT_EMAIL
CONTACT_TELEGRAM = TELEGRAM_URL


def _shell(title: str, content: str) -> str:
    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>{escape(title)} · {escape(BUSINESS_NAME)}</title>
        <style>
            .bg-orb {{
                position: fixed;
                border-radius: 999px;
                filter: blur(90px);
                opacity: .28;
                pointer-events: none;
                z-index: 0;
            }}
            .orb-a {{ width: 420px; height: 420px; top: 70px; left: -80px; background: #5ac8fa; }}
            .orb-b {{ width: 360px; height: 360px; top: 180px; right: 120px; background: #7b65c4; }}
            .orb-c {{ width: 420px; height: 420px; bottom: -120px; left: 30%; background: #57b84f; }}

            .glass {{
                background: linear-gradient(180deg, rgba(255,255,255,.12), rgba(255,255,255,.06));
                border: 1px solid rgba(255,255,255,.08);
                box-shadow: 0 18px 42px rgba(0,0,0,.22);
                backdrop-filter: blur(12px);
            }}

            .small-card {{
                background: rgba(255,255,255,.08);
                border: 1px solid rgba(255,255,255,.05);
                border-radius: 14px;
                padding: 16px;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.03);
            }}
        </style>
    </head>
    <body style="
        margin:0;
        background:
            radial-gradient(circle at 14% 18%, rgba(91,199,255,.20), transparent 26%),
            radial-gradient(circle at 86% 20%, rgba(123,101,196,.16), transparent 24%),
            radial-gradient(circle at 50% 100%, rgba(87,184,79,.16), transparent 28%),
            linear-gradient(135deg,#12171b 0%, #0f1217 38%, #131922 100%);
        color:white;
        font-family:Arial,sans-serif;
        min-height:100vh;
        box-sizing:border-box;
        padding:24px;">

        <div class="bg-orb orb-a"></div>
        <div class="bg-orb orb-b"></div>
        <div class="bg-orb orb-c"></div>

        <div style="position:relative;z-index:2;">
            <div style="
                width:100%;
                display:flex;
                justify-content:space-between;
                align-items:flex-start;
                margin-bottom:18px;">

                {render_brand_logo("/")}

                <a href="/" style="
                    display:inline-flex;
                    align-items:center;
                    justify-content:center;
                    min-width:120px;
                    height:42px;
                    padding:0 18px;
                    border:1.5px solid #3fae5a;
                    border-radius:999px;
                    color:#6fce87;
                    background:rgba(14,33,18,.82);
                    text-decoration:none;
                    font:700 14px Arial;
                    box-sizing:border-box;">
                    Back
                </a>
            </div>

            {content}
        </div>
    </body>
    </html>
    """


def render_contact_page() -> str:
    content = f"""
    <div style="width:980px;margin:20px auto 0 auto;">
        <div class="glass" style="border-radius:22px;padding:28px;box-sizing:border-box;">
            <div style="font:700 38px Arial;color:#fff;margin-bottom:10px;">Contact us</div>
            <div style="font:600 17px Arial;color:#d3d8df;margin-bottom:24px;">
                Get in touch with {escape(BUSINESS_NAME)} support or our official affiliate team.
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;">
                <div class="small-card">
                    <div style="color:#b9c0c9;font-size:13px;margin-bottom:8px;">Email</div>
                    <div style="font:700 18px Arial;color:#fff;">{escape(CONTACT_EMAIL)}</div>
                </div>

                <div class="small-card">
                    <div style="color:#b9c0c9;font-size:13px;margin-bottom:8px;">Telegram</div>
                    <div style="font:700 18px Arial;color:#fff;word-break:break-all;">{escape(CONTACT_TELEGRAM)}</div>
                </div>
            </div>

            <div style="margin-top:22px;">
                <a href="{escape(CONTACT_TELEGRAM)}" target="_blank" style="
                    display:inline-flex;
                    align-items:center;
                    justify-content:center;
                    min-width:220px;
                    height:48px;
                    border:none;
                    border-radius:12px;
                    background:linear-gradient(180deg,#2f8f46,#236b34);
                    color:#eef8f0;
                    text-decoration:none;
                    font:700 17px Arial;
                    box-shadow:0 12px 24px rgba(0,0,0,.18);">
                    Open Telegram
                </a>
            </div>
        </div>
    </div>
    """
    return _shell("Contact us", content)


def render_terms_page() -> str:
    content = f"""
    <div style="width:980px;margin:20px auto 0 auto;">
        <div class="glass" style="border-radius:22px;padding:28px;box-sizing:border-box;">
            <div style="font:700 38px Arial;color:#fff;margin-bottom:10px;">Terms & Conditions</div>
            <div style="font:600 16px Arial;color:#d3d8df;line-height:1.7;">
                Below is a draft of business protection terms for {escape(BUSINESS_NAME)}.
            </div>

            <div style="margin-top:22px;display:grid;gap:14px;">
                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">1. Intermediary role</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        {escape(BUSINESS_NAME)} acts as an intermediary / marketing directory between players and third-party club owners or affiliates.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">2. Third-party clubs</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        Clubs listed on the website may be owned or operated by third parties. Each club owner is independently responsible for their own club operations.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">3. Deposits, balances and payouts</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        If a user chooses to join through a direct club contact or club official link, all deposits, balances, settlements and payouts are handled directly between the user and that club owner.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">4. Official affiliate route</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        Where a user joins through the official {escape(BUSINESS_NAME)} affiliate route and the website explicitly states responsibility, {escape(BUSINESS_NAME)} may assist the user regarding onboarding and communication.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">5. No guarantee of third-party performance</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        {escape(BUSINESS_NAME)} does not guarantee the conduct, solvency, performance or availability of any third-party club, app, agent or owner.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">6. User responsibility</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        Users are responsible for verifying who they are dealing with, understanding the selected joining route, and ensuring compliance with their local laws and age requirements.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">7. Changes</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        These terms may be updated from time to time. Continued use of the website means acceptance of the latest version.
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return _shell("Terms & Conditions", content)


def render_faq_page() -> str:
    content = f"""
    <div style="width:980px;margin:20px auto 0 auto;">
        <div class="glass" style="border-radius:22px;padding:28px;box-sizing:border-box;">
            <div style="font:700 38px Arial;color:#fff;margin-bottom:10px;">FAQ</div>
            <div style="font:600 16px Arial;color:#d3d8df;line-height:1.7;margin-bottom:22px;">
                Frequently asked questions about {escape(BUSINESS_NAME)}.
            </div>

            <div style="display:grid;gap:14px;">

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">1. What is this website?</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        This website is a directory and access platform where users can view active tables, compare options and connect through an affiliate or directly through a club contact.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">2. How do I join a table?</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        Press Join on a table. You will see available joining options such as the official website affiliate route or a direct club route.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">3. What is the difference between TableRadar Official and Club Official?</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        TableRadar Official is the official affiliate route of the website. Club Official is the direct contact of the club owner. Responsibility conditions may differ depending on which route the user chooses.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">4. Does the website hold deposits or balances?</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        The website acts as an intermediary / listing platform. If a user joins directly through a club owner, deposits, balances and payouts are handled between the user and that club.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">5. What does the Player plan include?</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        Player plan gives access to the website tables, filters, favorites and profile features.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">6. What does the Host plan include?</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        Host plan includes everything in Player plus the ability to publish one of your own clubs on the website.
                    </div>
                </div>

                <div class="small-card">
                    <div style="font:700 19px Arial;color:#fff;margin-bottom:8px;">7. Who do I contact if I have a problem?</div>
                    <div style="font:600 15px Arial;color:#dce4db;line-height:1.65;">
                        Use the Contact us page or the official Telegram listed by the platform. If you joined directly through a club owner, you may also need to contact that club directly.
                    </div>
                </div>

            </div>
        </div>
    </div>
    """
    return _shell("FAQ", content)