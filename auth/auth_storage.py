import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta


USERS_FILE = Path("users.json")


def _now_date() -> str:
    return datetime.now().strftime("%d/%m/%Y")


def _hash_password(password: str) -> str:
    password = str(password or "")
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _safe(value, default=""):
    if value is None:
        return default
    return str(value)


def _normalize_email(email: str) -> str:
    return _safe(email).strip().lower()


def _default_user(email: str, username: str = "") -> dict:
    email = _normalize_email(email)
    username = _safe(username).strip() or email

    return {
        "username": username,
        "email": email,
        "password_hash": "",
        "registered_at": _now_date(),
        "plan": "inactive",
        "role": "player",
        "is_active": False,
        "days_left": 0,
        "auto_renew": True,
        "country": "United Kingdom",
        "favorites": [],
        "created_at": _now_date(),
    }


def _normalize_user(user: dict) -> dict:
    if not isinstance(user, dict):
        user = {}

    email = _normalize_email(user.get("email", ""))
    username = _safe(user.get("username", "")).strip() or email

    normalized = {
        "username": username,
        "email": email,
        "password_hash": _safe(user.get("password_hash", "")),
        "registered_at": _safe(
            user.get("registered_at", user.get("registered", user.get("created_at", "-")))
        ) or "-",
        "plan": _safe(user.get("plan", "inactive")).lower(),
        "role": _safe(user.get("role", "player")).lower(),
        "is_active": bool(user.get("is_active", user.get("active", False))),
        "days_left": int(user.get("days_left", user.get("days", 0)) or 0),
        "auto_renew": bool(user.get("auto_renew", True)),
        "country": _safe(user.get("country", "United Kingdom")),
        "favorites": user.get("favorites", []),
        "created_at": _safe(user.get("created_at", user.get("registered_at", "-"))) or "-",
    }

    # если в старом users.json был plaintext password, переведём в hash
    if not normalized["password_hash"] and user.get("password"):
        normalized["password_hash"] = _hash_password(user.get("password"))

    # сохраняем дополнительные поля, если они были
    for key, value in user.items():
        if key not in normalized and key != "password":
            normalized[key] = value

    return normalized


def load_users() -> list:
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")
        return []

    try:
        text = USERS_FILE.read_text(encoding="utf-8").strip()
        if not text:
            return []

        users = json.loads(text)
        if not isinstance(users, list):
            return []

        normalized_users = [_normalize_user(u) for u in users if isinstance(u, dict)]
        return normalized_users

    except Exception:
        return []


def save_users(users: list) -> None:
    normalized_users = [_normalize_user(u) for u in users if isinstance(u, dict)]
    USERS_FILE.write_text(
        json.dumps(normalized_users, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_user_by_email(email: str):
    email = _normalize_email(email)

    for user in load_users():
        if _normalize_email(user.get("email")) == email:
            return user

    return None


def get_user_by_username(username: str):
    username = _safe(username).strip().lower()

    for user in load_users():
        if _safe(user.get("username")).strip().lower() == username:
            return user

    return None


def create_user(*args, **kwargs):
    """
    Работает с разными вариантами вызова:

    create_user(email, password)
    create_user(username, email, password)
    create_user(email="...", password="...", username="...")
    """

    username = kwargs.get("username", "")
    email = kwargs.get("email", "")
    password = kwargs.get("password", "")

    if len(args) == 2:
        email = args[0]
        password = args[1]

    elif len(args) >= 3:
        username = args[0]
        email = args[1]
        password = args[2]

    email = _normalize_email(email)
    username = _safe(username).strip() or email
    password = _safe(password)

    if not email or not password:
        return False

    users = load_users()

    if any(_normalize_email(u.get("email")) == email for u in users):
        return False

    user = _default_user(email=email, username=username)
    user["password_hash"] = _hash_password(password)

    users.append(user)
    save_users(users)

    return True


def authenticate_user(email: str, password: str):
    email = _normalize_email(email)
    password = _safe(password)
    password_hash = _hash_password(password)

    users = load_users()

    for user in users:
        if _normalize_email(user.get("email")) != email:
            continue

        stored_hash = _safe(user.get("password_hash", ""))

        if stored_hash == password_hash:
            return user

        # запасной вариант, если где-то временно остался plaintext password
        if user.get("password") and _safe(user.get("password")) == password:
            user["password_hash"] = password_hash
            user.pop("password", None)
            save_users(users)
            return user

    return None


def set_user_plan(email: str, plan: str, days: int = 30, active: bool = True):
    email = _normalize_email(email)
    plan = _safe(plan).lower()

    users = load_users()

    for user in users:
        if _normalize_email(user.get("email")) == email:
            user["plan"] = plan
            user["is_active"] = bool(active)
            user["days_left"] = int(days)
            user["plan_started_at"] = _now_date()
            user["plan_expires_at"] = (
                datetime.now() + timedelta(days=int(days))
            ).strftime("%d/%m/%Y")

            save_users(users)
            return True

    return False


def set_user_auto_renew(email: str, enabled: bool):
    email = _normalize_email(email)

    users = load_users()

    for user in users:
        if _normalize_email(user.get("email")) == email:
            user["auto_renew"] = bool(enabled)
            save_users(users)
            return True

    return False


def deactivate_user_plan(email: str):
    email = _normalize_email(email)

    users = load_users()

    for user in users:
        if _normalize_email(user.get("email")) == email:
            user["plan"] = "inactive"
            user["is_active"] = False
            user["days_left"] = 0
            user["auto_renew"] = False
            save_users(users)
            return True

    return False


def update_user(email: str, **fields):
    email = _normalize_email(email)

    users = load_users()

    for user in users:
        if _normalize_email(user.get("email")) == email:
            for key, value in fields.items():
                if key == "email":
                    continue
                if key == "password":
                    user["password_hash"] = _hash_password(value)
                    continue
                user[key] = value

            save_users(users)
            return True

    return False