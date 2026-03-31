import json
import os

DATA_FILE = "tables.json"


def load_tables():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_tables(tables):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tables, f, ensure_ascii=False, indent=4)