from html import escape

BRAND_NAME = "TableRadar"
OFFICIAL_AFFILIATE_NAME = "TableRadar Official"
BRAND_DOMAIN = "tableradar.net"

# если нужно — потом поменяешь
TELEGRAM_URL = "https://t.me/your_telegram_username"
SUPPORT_EMAIL = f"support@{BRAND_DOMAIN}"


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
