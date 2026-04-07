import json
import os
from datetime import datetime

FILE = "users.json"


def init_users_db():
    if not os.path.exists(FILE):
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_users():
    init_users_db()
    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _today():
    return datetime.now().strftime("%d/%m/%Y")


def _normalize_user(user: dict) -> dict:
    if "nickname" not in user:
        user["nickname"] = user.get("username", "User")
    if "plan" not in user:
        user["plan"] = "inactive"
    if "role" not in user:
        user["role"] = "Player"
    if "country" not in user:
        user["country"] = "United Kingdom"
    if "phone" not in user:
        user["phone"] = "Not added"
    if "company" not in user:
        user["company"] = "Not added"
    if "notes" not in user:
        user["notes"] = "No additional notes"
    if "favorites" not in user:
        user["favorites"] = []
    if "is_active" not in user:
        user["is_active"] = False
    if "days_left" not in user:
        user["days_left"] = 0
    if "registered_at" not in user:
        user["registered_at"] = _today()
    return user


def create_user(username, email, password):
    users = load_users()
    email = str(email).strip().lower()
    username = str(username).strip()
    password = str(password)

    for u in users:
        if str(u.get("email", "")).strip().lower() == email:
            return False

    user = {
        "username": username,
        "nickname": username,
        "email": email,
        "password": password,
        "plan": "inactive",
        "role": "Player",
        "country": "United Kingdom",
        "phone": "Not added",
        "company": "Not added",
        "notes": "No additional notes",
        "favorites": [],
        "is_active": False,
        "days_left": 0,
        "registered_at": _today(),
    }

    users.append(user)
    save_users(users)
    return True


def authenticate_user(email, password):
    users = load_users()
    email = str(email).strip().lower()
    password = str(password)

    for u in users:
        u = _normalize_user(u)
        if str(u.get("email", "")).strip().lower() == email and str(u.get("password", "")) == password:
            return u

    return None


def get_user_by_email(email):
    users = load_users()
    email = str(email).strip().lower()

    for u in users:
        u = _normalize_user(u)
        if str(u.get("email", "")).strip().lower() == email:
            return u

    return None


def set_user_plan(email, plan_name):
    users = load_users()
    email = str(email).strip().lower()
    plan_name = str(plan_name).strip().lower()

    for u in users:
        if str(u.get("email", "")).strip().lower() == email:
            u = _normalize_user(u)

            if plan_name == "player":
                u["plan"] = "player"
                u["role"] = "Player"
                u["is_active"] = True
                u["days_left"] = 30

            elif plan_name == "host":
                u["plan"] = "host"
                u["role"] = "Host"
                u["is_active"] = True
                u["days_left"] = 30

            save_users(users)
            return True

    return False