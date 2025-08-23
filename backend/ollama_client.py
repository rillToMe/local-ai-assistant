import os, subprocess, re
from .config import OLLAMA_PATH, OLLAMA_MODELS

SKIP_PHRASES = [
    "Thinking", "...done thinking",
    "We need to respond as Changli", "Personality:",
    "The user says", "We need to be friendly."
    "We need to respond to" 
    "The user is" 
    "so address them as" 
    "Keep it friendly, simple, Indonesian slang default." 
    "So answer" 
    "That is concise."
]

_META_RE = [
    re.compile(r'^\s*(analysis|reasoning|thoughts?|system|meta|notes?|context|tool(?:s)?|plan|guidelines)\s*[:\-]\s*', re.I),
    re.compile(r'^\s*(assistant|user|developer)\s*[:\-]\s*', re.I),
    re.compile(r'^\s*the conversation\s*[:\-]\s*', re.I),
    re.compile(r'^\s*as (an )?ai\b', re.I),
    re.compile(r'^\s*final answer\s*[:\-]\s*', re.I),
]

def _filter_output(raw: str) -> str:
    if not raw:
        return "Sorry sayang, aku lagi bingung nih... 😢"

    s = raw.replace("```", "\n")

    kept = []
    for line in s.splitlines():
        t = line.strip()
        if not t:
            kept.append("") 
            continue
        if any(p.lower() in t.lower() for p in SKIP_PHRASES):
            continue
        if any(rx.match(t) for rx in _META_RE):
            continue
        if (t.startswith("[") and t.endswith("]")) or (t.startswith("(") and t.endswith(")")):
            low = t.lower()
            if any(k in low for k in ("analysis", "system", "thought", "tool", "meta", "context")):
                continue
        kept.append(t)

    out = "\n".join([k for k in kept if k != ""]).strip()
    if out:
        return out

    paras = [p.strip() for p in re.split(r'\n\s*\n', s) if p.strip()]
    for p in reversed(paras):
        low = p.lower()
        if any(rx.match(p) for rx in _META_RE):
            continue
        if any(lbl in low for lbl in ("the conversation:", "assistant:", "user:", "system:", "analysis:", "reasoning:")):
            continue
        return p.strip()

    return "Sorry sayang, aku lagi bingung nih... 😢"

def list_models() -> list[str]:
    if not os.path.exists(OLLAMA_PATH):
        return []
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = OLLAMA_MODELS
    try:
        r = subprocess.run(
            [OLLAMA_PATH, "list"],
            capture_output=True, text=True, encoding="utf-8",
            env=env, timeout=30
        )
        names = []
        for line in r.stdout.splitlines():
            parts = line.split()
            if parts:
                name = parts[0]
                if ":" in name:
                    names.append(name)
        return sorted(set(names))
    except Exception:
        return []

def generate_text(prompt: str, model: str = "gemma3:4b") -> str | None:
    if not os.path.exists(OLLAMA_PATH):
        print(f"[ERROR] Ollama executable not found at {OLLAMA_PATH}")
        return None
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = OLLAMA_MODELS

    try:
        r_list = subprocess.run(
            [OLLAMA_PATH, "list"],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=30
        )
        if "gemma3:4b" not in r_list.stdout:
            print(f"[ERROR] Model {model} not found in {OLLAMA_MODELS}")
            return None

        result = subprocess.run(
            [OLLAMA_PATH, "run", model, prompt],
            capture_output=True, text=True, encoding="utf-8", env=env
        )
        return _filter_output(result.stdout)
    except Exception as e:
        print(f"[ERROR] generate_text failed: {e}")
        return None
