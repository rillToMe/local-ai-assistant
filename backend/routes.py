import time, json, os, re
from uuid import uuid4
from flask import jsonify, request
from .core import app
from . import storage
from .persona import persona_prompt
from .ollama_client import generate_text, list_models
from .config import APP_CONFIG_FILE

# MEMORY AI
MAX_WINDOW_TURNS = 8
SUMMERY_EVERY = 4
MAX_FACTS = 12
PROFILE_PATH = "profile.json"
DEFAULT_PROFILE = {"about": "", "job": "", "facts": []}


def _system_header(user_name: str, ai_name: str):
    user = user_name or "sayang"
    ai   = ai_name   or "AI"
    return (
        f"<<SYSTEM>>\n"
        f"- The user's name is '{user}'. Always address them as '{user}'.\n"
        f"- Your name is '{ai}'. If asked 'siapa nama kamu?', answer '{ai}'.\n"
        f"- If asked 'siapa nama saya?', answer '{user}'.\n"
        f"- Be concise and stay in character/persona.\n"
        f"- IMPORTANT: Output ONLY the final reply text. "
        f"Do NOT include labels or meta like 'User:', 'Assistant:', 'System:', 'Analysis:', 'Reasoning:', "
        f"'The conversation:', or any explanations. No role headings, no step-by-step, no quotes of instructions.\n"
        f"<<END>>\n"
        f"User: siapa nama saya?\nAI: {user}\n"
        f"User: siapa nama kamu?\nAI: {ai}\n"
        f"When answering questions from {user}, the answers must be reasonable and easy to understand, complex, and not long-winded.\n"
        f"Use the language specified by the {user}, but use Indonesian slang as the default.\n"
    )

DEFAULT_CONFIG = {
    "user_name": "User",
    "ai_name": "AI",
    "default_model": "gemma3:4b",
    "custom_prompt": (
        "Kamu adalah AI asisten biasa. "
        "Jawab dengan ramah, jelas, dan sederhana dalam bahasa Indonesia."
    )
}
@app.route('/config', methods=['GET'])
def get_config():
    config = DEFAULT_CONFIG.copy()
    if os.path.exists("config.json"):
        try:
            with open("config.json","r",encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except:
            pass

    return jsonify(config)

#MEMORY HELPER
def _build_memory_block(chat: dict) -> str:
    summary = (chat.get("memory_summery") or "").strip()
    facts = chat.get("memory_facts") or []
    if not summary and not facts:
        return ""
    block = "<<MEMORY>>\n"
    if summary:
        block += f"Summary: {summary}\n"
    if facts:
        block += "Facts:\n" + "\n".join(f" - {str(x).strip()}" for x in facts if str(x).strip() + "\n")
    block += "<<END>>\n"
    return block

def _recent_window_text(chat: dict, user_input: str) -> str:
    """Ambil jendela percakapan terakhir + user input terbaru."""
    hist = chat.get("history", [])
    window = hist[-MAX_WINDOW_TURNS:] if MAX_WINDOW_TURNS > 0 else hist
    buf = []
    for m in window:
        u = m.get("user", "")
        a = m.get("changli", "")
        if u: buf.append(f"User: {u}")
        if a: buf.append(f"AI: {a}")
    buf.append(f"User: {user_input}")
    buf.append("AI:")
    return "\n".join(buf)

def _needs_memory_update(chat: dict) -> bool:
    turns = len(chat.get("history", []))
    if turns <= MAX_WINDOW_TURNS:
        return False
    return (turns % SUMMERY_EVERY) == 0

_SUMMARY_PROMPT_TMPL = """<<TASK>>
Kamu akan memperbarui MEMORI singkat untuk percakapan berbahasa Indonesia.
Tujuan: simpan hal-hal penting agar chat tetap nyambung (preferensi user, rencana/komitmen, detail personal yang user bagikan, konteks jangka panjang).
Hindari spekulasi. Jangan simpan hal sensitif yang tidak perlu.

Tulis **dua bagian** persis dengan format:
SUMMARY: (3-5 kalimat, ringkas, bahasa Indonesia)
FACTS:
- (maks 12 butir, 3-12 kata per butir, jelas & spesifik)
<<END>>

MEMORY_LAMA:
SUMMARY_OLD: {old_summary}
FACTS_OLD:
{old_facts}

DIALOG_LAMA (dari yang paling lama):
{old_dialog}

DIALOG_BARU (ringkas, 1-2 item terakhir bila ada):
{new_tail}
"""

def _load_profile():
    if os.path.exists(PROFILE_PATH):
        try:
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {**DEFAULT_PROFILE, **data}
        except Exception:
            pass
    return DEFAULT_PROFILE.copy()

def _save_profile(p):
    try:
        with open(PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump({**DEFAULT_PROFILE, **(p or {})}, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

@app.get("/profile")
def get_profile():
    return jsonify(_load_profile())

@app.post("/profile")
def set_profile():
    data = request.get_json(silent=True) or {}
    prof = _load_profile()
    if "about" in data: prof["about"] = str(data.get("about") or "")
    if "job"   in data: prof["job"]   = str(data.get("job")   or "")
    if isinstance(data.get("facts"), list):
        prof["facts"] = [str(x).strip() for x in data["facts"] if str(x).strip()]
    _save_profile(prof)
    return jsonify({"ok": True, "profile": prof})

def _profile_block():
    p = _load_profile()
    about = (p.get("about") or "").strip()
    job   = (p.get("job") or "").strip()
    facts = p.get("facts") or []
    if not any([about, job, facts]):
        return ""
    lines = ["<<PROFILE>>"]
    if about: lines.append(f"AboutUser: {about}")
    if job:   lines.append(f"Occupation: {job}")
    if facts:
        lines.append("UserFacts:")
        for x in facts:
            s = str(x).strip()
            if s: lines.append(f"- {s}")
    lines.append("<<END>>\n")
    return "\n".join(lines)

def _parse_memory_output(text: str) -> tuple[str, list]:
    """Ambil SUMMARY: ... dan FACTS: - ... robust terhadap noise."""
    if not text:
        return "", []
    t = text.replace("```", "\n")
    summary = ""
    facts = []
    lines = [l.strip() for l in t.splitlines() if l.strip()]
    state = None
    for ln in lines:
        low = ln.lower()
        if low.startswith("summary:"):
            state = "sum"
            summary = ln.split(":",1)[1].strip()
            continue
        if low.startswith("facts:"):
            state = "facts"
            continue
        if state == "sum":
            if re.match(r"^(facts?:|summary:)", low):
                state = "facts" if low.startswith("facts:") else "sum"
                if state == "facts": continue
            summary = (summary + " " + ln).strip()
        elif state == "facts":
            if ln.startswith(("-", "•", "*")):
                facts.append(ln.lstrip("-•* ").strip())
            elif re.match(r"^(summary:|end|metadata:)", low):
                break
    facts = [f for f in facts if f]
    uniq = []
    for f in facts:
        if f not in uniq:
             uniq.append(f)
    return summary.strip(), uniq[:MAX_FACTS]

def _maybe_update_memory(chat: dict, model: str):
    """Ringkas percakapan lama menjadi memory (summary + facts)."""
    if not _needs_memory_update(chat):
        return
    hist = chat.get("history", [])
    if not hist:
        return
    old_part = hist[:-MAX_WINDOW_TURNS] if MAX_WINDOW_TURNS > 0 else hist[:-0]
    if not old_part:
        return

    old_dialog = []
    for m in old_part:
        if m.get("user"):
            old_dialog.append(f"User: {m['user']}")
        if m.get("changli"):
            old_dialog.append(f"AI: {m['changli']}")

    new_tail = []
    tail_src = hist[-2:]
    for m in tail_src:
        if m.get("user"):
            new_tail.append(f"User: {m['user']}")
        if m.get("changli"):
            new_tail.append(f"AI: {m['changli']}")

    prompt = _SUMMARY_PROMPT_TMPL.format(
        old_summary=chat.get("memory_summary",""),
        old_facts="\n".join(f"- {x}" for x in (chat.get("memory_facts") or [])) or "- (tidak ada)",
        old_dialog="\n".join(old_dialog)[:6000], 
        new_tail="\n".join(new_tail)
    )

    out = generate_text(prompt, model=model) 
    new_sum, new_facts = _parse_memory_output(out or "")
    if new_sum:
        chat["memory_summary"] = new_sum
    if new_facts:
        base = chat.get("memory_facts") or []
        merged = []
        for f in (new_facts + base):
            f = f.strip()
            if f and f not in merged:
                merged.append(f)
        chat["memory_facts"] = merged[:MAX_FACTS]



@app.get("/models")
def get_models():
    try:
        from .ollama_client import list_models
        return jsonify({
            "models": list_models(),
            "default": DEFAULT_CONFIG.get("default_model", "gemma3:4b")
        })
    except Exception:
        return jsonify({
            "models": [DEFAULT_CONFIG.get("default_model", "gemma3:4b")],
            "default": DEFAULT_CONFIG.get("default_model", "gemma3:4b")
        })

@app.get("/chats")
def get_chats():
    chats = storage.load_chats()
    summary = [
        {"id": c["id"], "user_name": c.get("user_name","sayang"),
         "last_updated": c.get("last_updated","")}
        for c in chats
    ]
    return jsonify(summary)

@app.get("/chat/<chat_id>")
def get_chat(chat_id):
    chats = storage.load_chats()
    chat = next((c for c in chats if c["id"] == chat_id), None)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    return jsonify(chat)

def _prompt_header(user_name, ai_name):
    ai = ai_name or "AI"
    user = user_name or "sayang"
    return f"<<SYSTEM>> User name: {user}. You are {ai}. Always address the user as '{user}'. If asked about the user's name, confirm it politely as '{user}'. <<END>>\n"

@app.post("/chat")
def new_chat():
    data = request.get_json(silent=True) or {}
    user_input = (data.get("message") or "").strip()
    user_name  = data.get("user_name", "sayang")
    ai_name    = data.get("ai_name", "Changli")
    model      = (data.get("model") or DEFAULT_CONFIG.get("default_model", "gemma3:4b")).strip()

    raw_cp = data.get("custom_prompt")
    custom_prompt = (raw_cp.strip() if raw_cp else "") 

    if not user_input:
        return jsonify({"error": f"Halo {user_name}, ketik sesuatu dulu ya 😘"}), 400
    
    header = _system_header(user_name, ai_name)
    profile_block = _profile_block()
    mem_block = ""
    history_text = f"User: {user_input}\nAI:"
    prompt = f"{header}{custom_prompt}\nUser: {user_input}\nAI:"

    response = generate_text(prompt, model=model) or f"Sorry {user_name}, aku lagi bingung nih... 😢"

    chat = {
        "id": str(uuid4()),
        "user_name": user_name,
        "ai_name": ai_name,
        "model": model,
        "custom_prompt": custom_prompt,
        "history": [{"user": user_input, "changli": response}],
        "memory_summery": "",
        "memory_facts": [],
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    chats = storage.load_chats(); chats.append(chat); storage.save_chats(chats)
    return jsonify({"response": response, "history": chat["history"], "chat_id": chat["id"], "model": model})

@app.post("/chat/<chat_id>/memory/clear")
def continue_chat(chat_id):
    data = request.get_json(silent=True) or {}
    user_input = (data.get("message") or "").strip()

    chats = storage.load_chats()
    chat = next((c for c in chats if c["id"] == chat_id), None)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    if not user_input:
        return jsonify({"history": chat["history"], "chat_id": chat_id, "model": chat.get("model")})

    user_name = data.get("user_name", chat.get("user_name", "sayang"))
    ai_name   = data.get("ai_name",   chat.get("ai_name",   "Changli"))
    model     = (data.get("model") or chat.get("model") or DEFAULT_CONFIG.get("default_model","gemma3:4b")).strip()
    raw_cp = data.get("custom_prompt")
    custom_prompt = (raw_cp.strip() if raw_cp else chat.get("custom_prompt",""))

    history_text = ""
    for msg in chat.get("history", []):
        history_text += f"User: {msg['user']}\nAI: {msg['changli']}\n"
    history_text += f"User: {user_input}\nAI:"

    header = _system_header(user_name, ai_name)
    profile_block = _profile_block
    mem_block = _build_memory_block(chat)
    history_text = _recent_window_text(chat, user_input)
    prompt = f"{header}{custom_prompt}\n{mem_block}{history_text}"

    response = generate_text(prompt, model=model) or f"Sorry {user_name}, aku lagi bingung nih... 😢"

    chat["user_name"] = user_name
    chat["ai_name"]   = ai_name
    chat["model"]     = model
    chat["custom_prompt"] = custom_prompt
    chat.setdefault("history", []).append({"user": user_input, "changli": response})
    storage.touch_chat(chat)
    storage.save_chats(chats)
    return jsonify({"response": response, "history": chat["history"], "chat_id": chat_id, "model": model})

def clear_chat_memory(chat_id):
    chats = storage.load_chats()
    chat = next((c for c in chats if c["id"] == chat_id), None)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    chat["memory_summary"] = ""
    chat["memory_facts"] = []
    storage.save_chats(chats)
    return jsonify({"ok": True})

