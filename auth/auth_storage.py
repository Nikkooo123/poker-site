import json
import hashlib
import hmac
import secrets
from pathlib import Path
from datetime import datetime, timedelta
import account_repository as account_db


USERS_FILE = Path("users.json")


def _now_date() -> str:
    return datetime.now().strftime("%d/%m/%Y")


def _hash_password(password: str) -> str:
    password = str(password or "")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 600000).hex()
    return f'pbkdf2_sha256$600000${salt}${digest}'


def _verify_password(password, stored_hash):
    try:
        if stored_hash.startswith('pbkdf2_sha256$'):
            _, rounds, salt, expected = stored_hash.split('$')
            if not 600000 <= int(rounds) <= 2000000:
                return False
            actual = hashlib.pbkdf2_hmac('sha256', str(password).encode('utf-8'), bytes.fromhex(salt), int(rounds)).hex()
        else:
            # Existing accounts keep working until their passwords are changed.
            expected = stored_hash
            actual = hashlib.sha256(str(password).encode('utf-8')).hexdigest()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def change_password(email, current_password, new_password):
    if not 10 <= len(new_password) <= 256 or len(current_password) > 256:
        return False
    new_hash = _hash_password(new_password)
    def transform(user):
        if not _verify_password(current_password, user.get('password_hash','')):
            raise ValueError('Current password is incorrect')
        user.update(password_hash=new_hash,credential_version=secrets.token_urlsafe(24))
        user.pop('password',None)
        return user
    try:
        if account_db.enabled():
            return account_db.mutate(_normalize_email(email),transform)
        users=load_users()
        for index,user in enumerate(users):
            if user['email']==_normalize_email(email):
                users[index]=transform(user)
                save_users(users)
                return True
    except ValueError:
        return False
    return False


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
        "role": "member",
        "is_active": False,
        "days_left": 0,
        "auto_renew": False,
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
    if account_db.enabled():
        return [_normalize_user(user) for user in account_db.load()]
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
    if account_db.enabled():
        account_db.upsert_many(normalized_users)
        return
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

    if not email or not 8 <= len(password) <= 256:
        return False

    users = load_users()

    if any(_normalize_email(u.get("email")) == email for u in users):
        return False

    user = _default_user(email=email, username=username)
    user["password_hash"] = _hash_password(password)

    if account_db.enabled():
        return account_db.insert(user)
    users.append(user)
    save_users(users)

    return True


def authenticate_user(email: str, password: str):
    email = _normalize_email(email)
    password = _safe(password)

    users = load_users()

    for user in users:
        if _normalize_email(user.get("email")) != email:
            continue

        stored_hash = _safe(user.get("password_hash", ""))

        if _verify_password(password, stored_hash):
            return user

        # запасной вариант, если где-то временно остался plaintext password
        if user.get("password") and _safe(user.get("password")) == password:
            user["password_hash"] = _hash_password(password)
            user.pop("password", None)
            update_user(email, password_hash=user["password_hash"])
            return user

    return None


def set_user_plan(email: str, plan: str, days: int = 30, active: bool = True):
    return update_user(email, plan=_safe(plan).lower(), is_active=bool(active), days_left=int(days),
                       plan_started_at=_now_date(), plan_expires_at=(datetime.now()+timedelta(days=int(days))).strftime("%d/%m/%Y"))


def set_user_auto_renew(email: str, enabled: bool):
    return update_user(email, auto_renew=bool(enabled))


def deactivate_user_plan(email: str):
    return update_user(email, plan="inactive", role="member", is_active=False, days_left=0, auto_renew=False)


def update_user(email: str, **fields):
    email = _normalize_email(email)
    def apply_fields(user):
        for key, value in fields.items():
            if key == "email":
                continue
            if key == "password":
                user["password_hash"] = _hash_password(value)
            else:
                user[key] = value
        return _normalize_user(user)
    if account_db.enabled():
        return account_db.mutate(email, apply_fields)
    users = load_users()
    for index, user in enumerate(users):
        if _normalize_email(user.get("email")) == email:
            users[index] = apply_fields(user)
            save_users(users)
            return True
    return False
