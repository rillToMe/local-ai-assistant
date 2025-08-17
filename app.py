import os, sys, subprocess, threading
from backend.core import app
import backend.routes 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_backend():
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

def run_ui():
    subprocess.Popen(
        [sys.executable, "-m", "ui.main"],
        cwd=BASE_DIR
    )

if __name__ == "__main__":
    t = threading.Thread(target=run_backend, daemon=True)
    t.start()
    run_ui()
    t.join()
