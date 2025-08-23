import os, json
from .config import BASE_DIR

LOCALE_DIRS = [
    os.path.join(BASE_DIR, "backend", "locales"),
    os.path.join(BASE_DIR, "backend", "i18n"),
]

NATIVE_NAMES = {
    "en_us": "English (US)",
    "id":    "Bahasa Indonesia",
    "en_gb": "English (UK)",
    "ja":    "日本語 (Japanese)",
    "ko":    "한국어 (Korean)",
    "zh":    "中文（简体）",
    "pt":    "Português",
    "es":    "Español",
    "ar":    "العربية",
}

_cache: dict[str, dict] = {}

def _safe_json_load(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _extract_keys(obj: dict) -> dict:
    if isinstance(obj, dict) and "keys" in obj and isinstance(obj["keys"], dict):
        return obj["keys"]
    return obj if isinstance(obj, dict) else {}

def _load_file_for(code: str) -> dict:
    for d in LOCALE_DIRS:
        p = os.path.join(d, f"{code}.json")
        if os.path.exists(p):
            return _extract_keys(_safe_json_load(p))
    return {}

def list_locales() -> list[str]:
    files = set()
    for d in LOCALE_DIRS:
        try:
            for f in os.listdir(d):
                if f.lower().endswith(".json"):
                    files.add(os.path.splitext(f)[0].lower())
        except Exception:
            pass
    if not files:
        return ["en_us"]
    head = [c for c in ["en_us", "id"] if c in files]
    tail = sorted([c for c in files if c not in head], key=lambda c: NATIVE_NAMES.get(c, c).lower())
    return head + tail

def list_locales_detail() -> list[dict]:
    return [{"code": c, "name": NATIVE_NAMES.get(c, c)} for c in list_locales()]

def load_locale(lang: str) -> dict:
    code = (lang or "en_us").lower()
    if code in _cache:
        return _cache[code]

    result = {}
    for c in ["en_us", "id", code]:
        result.update(_load_file_for(c))

    _cache[code] = result
    return result
