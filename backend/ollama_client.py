import os, subprocess
from .config import OLLAMA_PATH, OLLAMA_MODELS

SKIP_PHRASES = [
    "Thinking", "...done thinking",
    "We need to respond as Changli", "Personality:",
    "The user says", "We need to be friendly."
]

def _filter_output(raw: str) -> str:
    lines = []
    for line in (raw or "").splitlines():
        s = line.strip()
        if not s: continue
        if any(p in s for p in SKIP_PHRASES): continue
        lines.append(s)
    out = "\n".join(lines).strip()
    return out or "Sorry sayang, aku lagi bingung nih... 😢"

def generate_text(prompt: str) -> str | None:
    if not os.path.exists(OLLAMA_PATH):
        print(f"[ERROR] Ollama executable not found at {OLLAMA_PATH}")
        return None
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = OLLAMA_MODELS

    try:
        model_check = subprocess.run(
            [OLLAMA_PATH, "list"],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=30
        )
        if "gemma3:4b" not in model_check.stdout:
            print(f"[ERROR] Model gemma3:4b not found in {OLLAMA_MODELS}")
            return None

        result = subprocess.run(
            [OLLAMA_PATH, "run", "gemma3:4b", prompt],
            capture_output=True, text=True, encoding="utf-8", env=env
        )
        return _filter_output(result.stdout)
    except Exception as e:
        print(f"[ERROR] generate_text failed: {e}")
        return None
