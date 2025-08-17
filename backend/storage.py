import os, json, time
from json import JSONDecodeError
from .config import HISTORY_FILE, DATA_DIR

def _init_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(HISTORY_FILE) or os.path.getsize(HISTORY_FILE) == 0:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write("[]")

def load_chats():
    _init_files()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except JSONDecodeError:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write("[]")
        return []

def save_chats(chats):
    _init_files()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(chats or [], f, indent=2, ensure_ascii=False)

def touch_chat(chat: dict):
    chat["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
