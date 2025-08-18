# Local Chat — Changli UI

🚧 **Status:** This project is still in **development**, so expect bugs, incomplete features, and potential breaking changes. 🚧

---

## 📖 Description
Local Chat is an **offline/local AI chat application** featuring:
- **Backend** built with Flask → for API communication and chat storage.
- **Frontend (UI)** built with PySide6 (Qt) → for an interactive chat interface.
- **Ollama Integration** → to run local AI models (example: `gemma3:4b`).

This project is designed to run AI **fully locally**, with customizable identity, persona, and chat history.

---

## 📂 Project Structure
```
local-ai-assistant/
├─ app.py                    
│
├─ backend/
│  ├─ config.py      
│  ├─ core.py           
│  ├─ persona.py            
│  ├─ storage.py             
│  ├─ ollama_client.py       
│  └─ routes.py              
│
├─ ui/
│  ├─ main.py               
│  ├─ chat_window.py         
│  ├─ client.py              
│  ├─ worker.py              
│  └─ widgets/              
│     ├─ settings.py         
│     ├─ history.py          
│     ├─ bubbles.py          
│     └─ identity.py        
│
├─ data/                    
│  ├─ chat_history.json
│  ├─ chat_sessions.json
│  ├─ ui_chat_config.json
│  └─ config.json
│
└─ README.md                 
```

---

## ⚡ Features
- 🖥 **Modern UI** using PySide6 (Qt)
- 📝 **Chat History** → rename, delete, or continue past sessions
- 🎭 **Custom Persona** → change AI name, user name, and prompt
- 🎨 **Custom Background** → solid color or custom image
- ⚙️ **Flask Backend** with `/chat`, `/chats`, `/config` endpoints
- 🤖 **Ollama Integration** → run local AI models such as `gemma3:4b`
- 📂 All data & configs stored locally under `data/`

---

## 🛠️ Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/rillToMe/local-chat.git
cd local-ai-assistant
```

### 2. Create Virtual Environment (recommended)
```bash
python -m venv venv
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Main dependencies:**
- `flask`
- `flask-cors`
- `requests`
- `PySide6`

> ⚠️ **Note**: Make sure you have installed **[Ollama](https://ollama.ai/)** and the required model (`gemma3:4b`).

### 4. Run the App
```bash
python app.py
```

- Flask backend will start on `http://127.0.0.1:5000`
- PySide6 UI will automatically open

---

## 🎮 Usage
- Click **Settings** → change background or update **Identity & Prompt**
- Click **History** → view, rename, or continue previous sessions
- Click **Clear** → start a new conversation
- Default AI identity is **Changli** (can be changed via settings)

---

## 📌 Roadmap / Todo
- [ ] Fix UI crash bugs
- [ ] Add model selection from UI (Ollama integration)
- [ ] Add chat export/import
- [ ] Add multi-tab chat support
- [ ] Optimize performance for long requests

---

## ⚠️ Notes
- This is still in **early development**, expect frequent bugs and issues  
- UI/UX is minimal for now, focused on core functionality  
- Default persona is simple, can be extended with custom prompts  
