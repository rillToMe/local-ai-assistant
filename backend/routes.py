import time, json, os
from uuid import uuid4
from flask import jsonify, request
from .core import app
from . import storage
from .persona import persona_prompt
from .ollama_client import generate_text
from .config import APP_CONFIG_FILE


def _system_header(user_name: str, ai_name: str):
    user = user_name or "sayang"
    ai   = ai_name   or "AI"
    return (
        f"<<SYSTEM>>\n"
        f"- The user's name is '{user}'. Always address them as '{user}'.\n"
        f"- Your name is '{ai}'. If asked 'siapa nama kamu?', answer '{ai}'.\n"
        f"- If asked 'siapa nama saya?', answer '{user}'.\n"
        f"- Be concise and stay in character/persona.\n"
        f"<<END>>\n"
        f"User: siapa nama saya?\nAI: {user}\n"
        f"User: siapa nama kamu?\nAI: {ai}\n"
        f"When answering questions from {user}, the answers must be reasonable and easy to understand, complex, and not long-winded.\n"
        f"Use the language specified by the {user}, but use Indonesian slang as the default.\n"
    )

DEFAULT_CONFIG = {
    "user_name": "User",
    "ai_name": "AI",
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


@app.get("/chats")
def get_chats():
    chats = storage.load_chats()
    summary = [
        {"id": c["id"], "user_name": c.get("user_name","sayang"),
         "last_updated": c.get("last_updated","")}
        for c in chats
    ]
    return jsonify(summary)

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

    raw_cp = data.get("custom_prompt")
    custom_prompt = (raw_cp.strip() if raw_cp else "") 

    if not user_input:
        return jsonify({"error": f"Halo {user_name}, ketik sesuatu dulu ya 😘"}), 400
    
    header = _system_header(user_name, ai_name)
    prompt = f"{header}{custom_prompt}\nUser: {user_input}\nAI:"

    response = generate_text(prompt) or f"Sorry {user_name}, aku lagi bingung nih... 😢"

    chat = {
        "id": str(uuid4()),
        "user_name": user_name,
        "ai_name": ai_name,
        "custom_prompt": custom_prompt,
        "history": [{"user": user_input, "changli": response}],
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    chats = storage.load_chats(); chats.append(chat); storage.save_chats(chats)
    return jsonify({"response": response, "history": chat["history"], "chat_id": chat["id"]})

@app.post("/chat/<chat_id>")
def continue_chat(chat_id):
    data = request.get_json(silent=True) or {}
    user_input = (data.get("message") or "").strip()

    chats = storage.load_chats()
    chat = next((c for c in chats if c["id"] == chat_id), None)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    if not user_input:
        return jsonify({"history": chat["history"], "chat_id": chat_id})

    user_name = data.get("user_name", chat.get("user_name", "sayang"))
    ai_name   = data.get("ai_name",   chat.get("ai_name",   "Changli"))

    raw_cp = data.get("custom_prompt")
    custom_prompt = (raw_cp.strip() if raw_cp else chat.get("custom_prompt",""))

    history_text = ""
    for msg in chat.get("history", []):
        history_text += f"User: {msg['user']}\nAI: {msg['changli']}\n"
    history_text += f"User: {user_input}\nAI:"

    header = _system_header(user_name, ai_name)
    prompt = f"{header}{custom_prompt}\n{history_text}"

    response = generate_text(prompt) or f"Sorry {user_name}, aku lagi bingung nih... 😢"

    chat["user_name"] = user_name
    chat["ai_name"]   = ai_name
    chat["custom_prompt"] = custom_prompt
    chat.setdefault("history", []).append({"user": user_input, "changli": response})
    storage.touch_chat(chat)
    storage.save_chats(chats)
    return jsonify({"response": response, "history": chat["history"], "chat_id": chat_id})