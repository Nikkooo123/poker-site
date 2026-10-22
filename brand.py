from html import escape

BRAND_NAME = "TableRadar"
OFFICIAL_AFFILIATE_NAME = "TableRadar Official"
BRAND_DOMAIN = "tableradar.net"

# если нужно — потом поменяешь
TELEGRAM_URL = "https://t.me/your_telegram_username"
SUPPORT_EMAIL = f"support@{BRAND_DOMAIN}"


def render_site_theme() -> str:
    """Shared visual tokens and controls. Game/application state colors remain distinct."""
    return """<style id="tableradar-theme">
    :root{--tr-bg:#10171b;--tr-panel:#1b282e;--tr-text:#edf3f2;--tr-muted:#a5b4b6;--tr-line:rgba(200,223,221,.12);--tr-accent:#a8d8c4;--tr-radius:18px;color-scheme:dark}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{background:radial-gradient(ellipse at 12% 0%,#203d3c80,transparent 52%),radial-gradient(ellipse at 95% 60%,#332c3b60,transparent 50%),var(--tr-bg)!important;color:var(--tr-text)!important;font-family:'Segoe UI',Arial,sans-serif!important;min-height:100vh}
    button,input,select,textarea{font-family:'Segoe UI',Arial,sans-serif!important}a,button,input,select,summary{touch-action:manipulation}a:focus-visible,button:focus-visible,summary:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:2px solid var(--tr-accent);outline-offset:4px}
    button{cursor:pointer}button:disabled{opacity:.5;cursor:not-allowed}a{text-underline-offset:4px}.bg-orb{display:none!important}
    .glass,.glass-bar{background:linear-gradient(145deg,#202d32f0,#172126f0)!important;border:1px solid var(--tr-line)!important;box-shadow:0 16px 40px #00000015!important;backdrop-filter:blur(12px)}
    .small-card,.mini-card{background:#ffffff04!important;border:1px solid var(--tr-line)!important;border-radius:14px!important;box-shadow:none!important;color:var(--tr-text)}
    input:not([type=checkbox]):not([type=radio]):not([type=hidden]),select,textarea{background:#142127!important;border:1px solid #c8dfdd26!important;color:var(--tr-text)!important;border-radius:10px!important;box-shadow:none!important}input::placeholder,textarea::placeholder{color:#9aadaf;opacity:1}select option{background:#17262c;color:var(--tr-text)}
    .tr-site-header{max-width:1200px;margin:0 auto;padding:25px 36px;display:flex;justify-content:space-between;align-items:center;gap:20px;border-bottom:1px solid var(--tr-line);flex-wrap:wrap}.tr-site-main{max-width:1080px;margin:0 auto;padding:36px 36px 60px}.tr-site-main>div{max-width:100%!important;width:100%!important;margin-top:0!important}.tr-site-main .glass{padding:30px!important}.tr-site-footer{max-width:1008px;margin:0 auto;padding:22px 0 30px;border-top:1px solid var(--tr-line);display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap;font-size:12px;color:var(--tr-muted)}.tr-site-footer a{color:var(--tr-muted);text-decoration:none}.tr-site-footer a:hover{color:var(--tr-text)}.tr-site-footer nav{display:flex;gap:22px;flex-wrap:wrap}
    .tr-button{display:inline-flex;align-items:center;justify-content:center;gap:10px;padding:11px 17px;border:1px solid var(--tr-line);border-radius:11px;background:#25343a;color:var(--tr-text);text-decoration:none;font:600 13px/1.5 'Segoe UI',Arial,sans-serif}.tr-button:hover{background:#30434a}.tr-button-primary{background:var(--tr-accent);color:#172b23;border-color:var(--tr-accent)}.tr-button-primary:hover{background:#bee9d8}.tr-muted{color:var(--tr-muted)}
    .join-open-btn{background:var(--tr-accent)!important;color:#142920!important;border:1px solid #a8d8c433!important;box-shadow:none!important;border-radius:12px!important}.join-open-btn:hover{background:#c2e9d9!important}.game-filter-btn,.club-filter-btn{border-radius:10px!important}.game-filter-btn:hover,.club-filter-btn:hover{filter:brightness(1.1)}.join-help-tip,#profile-dropdown{background:#1e2a30!important;border-color:var(--tr-line)!important;box-shadow:0 15px 35px #0005!important}.join-help-tip{line-height:1.6!important}
    #profile-menu-btn{border-radius:12px!important;border:1px solid var(--tr-line)!important;background:#203035!important;box-shadow:none!important}#join-modal-card{border-radius:22px!important}#join-modal-overlay{backdrop-filter:blur(6px)}
    .tr-directory{padding:0!important}.tr-table-scroll{overflow-x:auto;overscroll-behavior-x:contain;padding:0 4px 16px;scrollbar-color:#45645b transparent}.tr-scroll-hint{display:none;color:var(--tr-muted);font-size:12px;padding:0 20px;margin:12px 0}.tr-auth-body{padding:0 20px 40px}.tr-auth-panel{width:440px;max-width:100%;padding:30px;border-radius:22px;background:linear-gradient(145deg,#202d32ef,#172126ef);border:1px solid var(--tr-line);box-shadow:0 16px 40px #0002}.tr-auth-panel h1{font-size:32px;line-height:1.2;font-weight:600;letter-spacing:-1px;margin:0 0 10px}.tr-auth-panel .tr-muted{font-size:14px;margin:0 0 26px}.tr-auth-panel label{display:block;font-size:13px;color:#bacbca;margin-bottom:6px}.tr-auth-panel input{width:100%;height:48px;padding:0 13px;margin-bottom:20px}.tr-auth-panel button{width:100%;min-height:46px}.tr-auth-panel .tr-auth-link{display:block;text-align:center;margin-top:22px;color:var(--tr-accent);font-size:13px}.tr-auth-wrap{display:flex;justify-content:center;padding:54px 0 20px}
    .tr-faq details{border:1px solid var(--tr-line);border-radius:14px;background:#ffffff04;padding:0 20px}.tr-faq details+details{margin-top:12px}.tr-faq summary{cursor:pointer;font-size:16px;font-weight:600;padding:18px 0;list-style:none;display:flex;justify-content:space-between;gap:20px}.tr-faq summary::after{content:'+';color:var(--tr-accent);font-size:20px;line-height:1}.tr-faq details[open] summary::after{content:'−'}.tr-faq summary::-webkit-details-marker{display:none}.tr-faq details p{margin:0 0 22px;color:#b8c7c8;line-height:1.8;font-size:14px}.tr-faq details[hidden]{display:none}.tr-page-title{font-size:clamp(28px,4vw,38px);font-weight:600;letter-spacing:-1px;line-height:1.2;margin:0 0 12px}.tr-page-intro{color:var(--tr-muted);font-size:15px;line-height:1.8;margin:0 0 26px}.tr-payment-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.tr-payment-choice{padding:24px;border:1px solid var(--tr-line);border-radius:18px;background:#ffffff04}.tr-payment-choice h2{font-size:22px;margin:0 0 10px;font-weight:600}.tr-payment-choice p,.tr-payment-choice li{color:var(--tr-muted);font-size:14px}.tr-payment-choice .tr-button{width:100%;margin-top:20px}.tr-status-pill{display:inline-flex;padding:4px 10px;font-size:11px;color:var(--tr-accent);border:1px solid #a8d8c435;border-radius:100px;background:#a8d8c40c}
    @media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{transition:none!important;animation:none!important}}
    @media(max-width:1120px){.tr-scroll-hint{display:block}.tr-table-scroll>div{margin-left:0!important}}
    @media(max-width:680px){.tr-site-header{padding:20px}.tr-site-main{padding:28px 20px 40px}.tr-site-main .glass{padding:22px!important}.tr-site-main [style*="grid-template-columns:1fr 1fr"]{grid-template-columns:1fr!important}.tr-site-footer{margin:0 20px}.tr-auth-panel{padding:24px}.tr-auth-wrap{padding-top:32px}.tr-payment-grid{grid-template-columns:1fr}.tr-site-main [style*="font:700 38px"]{font-size:30px!important}}
    </style>"""


def render_site_footer() -> str:
    return '<footer class="tr-site-footer"><span>TableRadar · Find your next table.</span><nav aria-label="Footer"><a href="/faq">FAQ</a><a href="/terms">Terms & Conditions</a><a href="/contact">Contact</a></nav></footer>'


def normalize_affiliate_name(value: str) -> str:
    s = (value or "").strip()
    if not s:
        return OFFICIAL_AFFILIATE_NAME

    if s.lower() in {
        "boom247",
        "boom247 official",
        "tableradar",
        "tableradar official",
    }:
        return OFFICIAL_AFFILIATE_NAME

    return s


def render_brand_logo(home_href: str = "/") -> str:
    return f"""
    <a href="{escape(home_href, quote=True)}" aria-label="TableRadar home" style="display:inline-flex;align-items:center;gap:11px;text-decoration:none;flex-shrink:0">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="42" height="42" fill="none" aria-hidden="true">
        <rect x="1" y="1" width="46" height="46" rx="14" fill="#233c36" stroke="#a8d8c4" stroke-opacity=".22"/>
        <rect x="10" y="14" width="28" height="20" rx="10" stroke="#a8d8c4" stroke-width="1.6"/>
        <path d="M24 24 35 13M24 8v3M24 37v3M8 24h3M37 24h3" stroke="#d4efe2" stroke-width="1.6" stroke-linecap="round"/>
        <circle cx="24" cy="24" r="3" fill="#d4efe2"/>
        <circle cx="35" cy="13" r="2.5" fill="#a8d8c4"/>
      </svg>
      <span style="font:600 25px/1.1 'Segoe UI',Arial,sans-serif;letter-spacing:-1px;color:#eff5f2">Table<span style="color:#a8d8c4">Radar</span></span>
    </a>
    """
