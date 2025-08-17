import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

HISTORY_FILE = os.path.join(DATA_DIR, "chat_history.json")
APP_CONFIG_FILE = os.path.join(DATA_DIR, "config.json")       
UI_CONFIG_FILE  = os.path.join(DATA_DIR, "ui_chat_config.json")  
SESSIONS_FILE   = os.path.join(DATA_DIR, "chat_sessions.json")  

CUDA_VISIBLE_DEVICES = os.environ.get("CUDA_VISIBLE_DEVICES", "1")
OLLAMA_MODELS = os.environ.get("OLLAMA_MODELS", "D:/Tools/ollama")
OLLAMA_PATH   = os.environ.get("OLLAMA_PATH", "C:/Users/LOQ/AppData/Local/Programs/Ollama/ollama.exe")

API_HOST = os.environ.get("CHANG_LI_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("CHANG_LI_PORT", "5000"))
