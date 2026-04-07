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
    <a href="{escape(home_href)}" style="
        display:inline-flex;
        align-items:center;
        gap:14px;
        text-decoration:none;">
        <span style="
            width:58px;
            height:58px;
            border-radius:50%;
            background:radial-gradient(circle at 35% 35%, #1f8d45 0%, #17683a 55%, #114c2c 100%);
            display:inline-flex;
            align-items:center;
            justify-content:center;
            box-shadow:
                0 12px 24px rgba(0,0,0,.22),
                inset 0 1px 0 rgba(255,255,255,.12);">
            <svg viewBox="0 0 64 64" width="36" height="36" fill="none">
                <circle cx="32" cy="32" r="22" fill="#0f1611" stroke="#246e44" stroke-width="3.5"/>
                <circle cx="32" cy="32" r="5" fill="#e7f0e9"/>

                <circle cx="32" cy="32" r="9" stroke="#5ea977" stroke-width="1" opacity=".55"/>
                <circle cx="32" cy="32" r="14" stroke="#5ea977" stroke-width="1" opacity=".45"/>
                <circle cx="32" cy="32" r="18" stroke="#5ea977" stroke-width="1" opacity=".35"/>

                <path d="M32 10v44" stroke="#5ea977" stroke-width="1" opacity=".35"/>
                <path d="M10 32h44" stroke="#5ea977" stroke-width="1" opacity=".35"/>
                <path d="M16 16l32 32" stroke="#5ea977" stroke-width="1" opacity=".22"/>
                <path d="M48 16L16 48" stroke="#5ea977" stroke-width="1" opacity=".22"/>

                <path d="M32 32L47 19" stroke="#edf5ef" stroke-width="3" stroke-linecap="round"/>
                <path d="M32 10a22 22 0 0 1 21 17" stroke="#77d890" stroke-width="2.2" stroke-linecap="round" opacity=".9"/>
                <path d="M44 14a22 22 0 0 1 10 15" stroke="#77d890" stroke-width="2.2" stroke-linecap="round" opacity=".55"/>

                <circle cx="40" cy="23" r="2.5" fill="#b7f3c8"/>
                <circle cx="26" cy="39" r="2.5" fill="#b7f3c8"/>
                <circle cx="21" cy="27" r="2.5" fill="#b7f3c8"/>

                <circle cx="40" cy="23" r="5.5" stroke="#b7f3c8" stroke-width="1" opacity=".35"/>
                <circle cx="26" cy="39" r="5.5" stroke="#b7f3c8" stroke-width="1" opacity=".25"/>
            </svg>
        </span>

        <span style="
            font:800 30px Arial;
            color:#c6cdd4;
            letter-spacing:.2px;
            text-shadow:0 6px 18px rgba(0,0,0,.22);">
            {escape(BRAND_NAME)}
        </span>
    </a>
    """