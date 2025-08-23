import os, sys, time, threading, subprocess, json
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QFrame, QLabel, QLineEdit, QPushButton, QMessageBox, QDialog, QComboBox,
    QTextEdit
)

from .client import Client
from .worker import Worker
from .widgets.settings import ChatSettings
from .widgets.history import ChatHistoryDialog
from .widgets.bubbles import make_tail_pixmap, esc_html
from .widgets.identity import IdentityDialog

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

API_BASE    = os.environ.get("CHANG_LI_API", "http://127.0.0.1:5000").rstrip("/")
BACKEND_APP = os.environ.get("CHANG_LI_BACKEND", os.path.join(BASE_DIR, "app.py"))

UI_CFG_FILE   = os.path.join(DATA_DIR, "ui_chat_config.json")
IDENTITY_FILE = os.path.join(DATA_DIR, "config.json")
SESS_FILE     = os.path.join(DATA_DIR, "chat_sessions.json")

_I18N = {"lang": "en_us", "keys": {}}

_DEFAULT_I18N = {
    "app.title": "{ai} — Local Chat UI",
    "status.online": "Online",
    "status.offline": "Offline",

    "btn.settings": "Settings",
    "btn.history": "History",
    "btn.clear": "Clear",
    "btn.profile": "Profile",
    "btn.clearmem": "Clear Memory",
    "btn.send": "Send",

    "label.language": "Language",
    "label.typing": "{ai} is typing",

    "placeholder.input": "Type a message…",

    "err.load.models": "Failed to load model list: {err}",
    "err.nochat.clear": "No active chat yet. Send a message first to clear memory.",

    "msg.model.set": "Model set to: {model}",
    "msg.loaded.history": "Loaded chat history.",
    "msg.newchat": "New chat started.",
    "msg.mem.cleared": "Memory cleared for this chat."
}

def tr(key: str, **fmt):
    k = key.replace("_", ".")
    val = _I18N["keys"].get(k) or _DEFAULT_I18N.get(k) or k
    try:
        return val.format(**fmt)
    except Exception:
        return val

@dataclass
class Message:
    role: str
    text: str
    ts: datetime

class ChatUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("ChatWindow")
        self.resize(980, 720)

        self.ui_config = self._load_json(UI_CFG_FILE, {"bg_mode":"color","bg_color":"#0E1426","bg_image":""})
        self.identity  = self._load_json(IDENTITY_FILE, {"ai_name":"Changli","user_name":"sayang","custom_prompt":""})

        self.client = Client(
            API_BASE,
            user_name=self.identity["user_name"],
            custom_prompt=self.identity.get("custom_prompt",""),
            ai_name=self.identity.get("ai_name", "AI")
        )
        cfg = self.client.get_config()
        self.client.model = cfg.get("default_model", "gemma3:4b")

        self._available_langs = cfg.get("available_languages", ["en_us","id"])
        self._lang_names = cfg.get("language_names", {
            "en_us":"English (US)","id":"Bahasa Indonesia","en_gb":"English (UK)",
            "ja":"日本語 (Japanese)","ko":"한국어 (Korean)","zh":"中文（简体）",
            "pt":"Português","es":"Español","ar":"العربية"
        })
        _I18N["lang"] = cfg.get("lang", "en_us")
        self._reload_i18n(_I18N["lang"])

        self.setWindowTitle(tr("app.title", ai=self.identity.get('ai_name','Changli')))
        self.setStyleSheet("QWidget#ChatWindow{background:#0B0F1A;}")

        self.worker = Worker(self.client)
        self.worker.done.connect(self._on_ai)
        self.worker.error.connect(self._on_err)

        root = QVBoxLayout(self); root.setContentsMargins(12,12,12,12); root.setSpacing(8)

        top = QHBoxLayout(); top.setSpacing(8)
        self.title = QLabel(tr("app.title", ai=self.identity.get('ai_name','Changli')))
        self.title.setStyleSheet("color:#EAF2FF;font:700 18px 'Segoe UI','Inter';")
        self.status = QLabel(tr("status.offline")); self.status.setFixedWidth(80)
        self.status.setStyleSheet("color:#FF678A;font:600 13px 'Inter';")

        self.btn_settings = QPushButton(tr("btn.settings")); self.btn_settings.clicked.connect(self._open_settings)
        self.btn_history  = QPushButton(tr("btn.history"));  self.btn_history.clicked.connect(self._open_history)
        self.btn_clear    = QPushButton(tr("btn.clear"));    self.btn_clear.clicked.connect(self._clear)
        self.btn_profile  = QPushButton(tr("btn.profile"));  self.btn_profile.clicked.connect(self._open_profile_dialog)
        self.btn_memclr   = QPushButton(tr("btn.clearmem")); self.btn_memclr.clicked.connect(self._clear_memory_current)

        for b in (self.btn_settings, self.btn_history, self.btn_clear, self.btn_profile, self.btn_memclr):
            b.setFixedHeight(28); b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                "QPushButton{background:#1C2238;border:1px solid #2D3550;border-radius:8px;color:#EAF2FF;padding:2px 10px;}"
                "QPushButton:hover{background:#233054;}"
            )

        top.addWidget(self.title); top.addStretch(1)
        top.addWidget(self.btn_settings); top.addWidget(self.btn_history)
        top.addWidget(self.btn_clear); top.addWidget(self.btn_profile)
        top.addWidget(self.btn_memclr); top.addWidget(self.status)
        root.addLayout(top)

        self.btn_memclr.setEnabled(False)

        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setStyleSheet("color:#2A314A;")
        root.addWidget(line)

        self.list = QListWidget()
        self.list.setSpacing(6)
        self.list.setUniformItemSizes(False)
        self.list.setWordWrap(True)
        self.list.setFrameShape(QFrame.NoFrame)
        self.list.setStyleSheet("QListWidget{background:transparent;border:none;} QListView{background:transparent;border:none;}")
        self.list.viewport().setAutoFillBackground(False)
        root.addWidget(self.list, 1)

        self._apply_background(self.ui_config)

        self.typ_lbl = QLabel(""); self.typ_lbl.setVisible(False)
        self.typ_lbl.setStyleSheet("color:#A5AFBF; font:13px 'Inter'; padding-left:6px;")
        root.addWidget(self.typ_lbl, 0, Qt.AlignLeft)

        bottom = QHBoxLayout(); bottom.setSpacing(8)

        self.inp = QLineEdit(); self.inp.setPlaceholderText(tr("placeholder.input"))
        self.inp.setStyleSheet(
            "QLineEdit{background:#121A31;border:1px solid #2D3550;border-radius:10px;padding:12px;color:#EAF2FF;font:15px 'Segoe UI','Inter';}"
            "QLineEdit:focus{border-color:#5CE1E6;}"
        )
        self.inp.returnPressed.connect(self._send)

        self.model_box = QComboBox()
        self.model_box.setFixedHeight(44)
        self.model_box.setMinimumWidth(180)
        self.model_box.setStyleSheet(
            "QComboBox{background:#121A31;border:1px solid #2D3550;"
            "border-radius:10px;color:#EAF2FF;padding:8px 12px;font:15px 'Inter';}"
            "QComboBox::drop-down{border:none;}"
        )
        self.model_box.blockSignals(True)
        self.model_box.addItem(self.client.model or "gemma3:4b")
        self.model_box.blockSignals(False)
        self.model_box.activated.connect(self._on_model_activated)

        self.btn_send = QPushButton(tr("btn.send")); self.btn_send.setFixedHeight(44)
        self.btn_send.clicked.connect(self._send)
        self.btn_send.setStyleSheet(
            "QPushButton{background:#18233F;border:1px solid #2D3550;border-radius:10px;color:#5CE1E6;font:600 15px 'Inter';padding:8px 18px;}"
            "QPushButton:hover{background:#1C2A4D;}"
            "QPushButton:disabled{color:#6B7A9A;}"
        )

        bottom.addWidget(self.inp, 1)
        bottom.addWidget(self.model_box, 0)
        bottom.addWidget(self.btn_send, 0)
        root.addLayout(bottom)

        self._health = QTimer(self); self._health.setInterval(1200)
        self._health.timeout.connect(self._ping); self._health.start()
        self._typing = QTimer(self); self._typing.setInterval(350)
        self._typing.timeout.connect(self._tick); self._phase=0

        self._load_models()

        self._ensure_backend()
        self._add_msg("ai", f"Halo {self.identity.get('user_name','sayang')}~  Aku {self.identity.get('ai_name','Changli')}. Tulis pesanmu ya...")

        self._ensure_history_state()
        self._apply_i18n_labels()

    def _reload_i18n(self, lang: str):
        try:
            data = self.client.get_i18n(lang)
            _I18N["lang"] = data.get("lang", lang)
            _I18N["keys"] = data.get("keys", {})
        except Exception:
            _I18N["lang"] = lang
            _I18N["keys"] = {}

    def _apply_i18n_labels(self):
        self.title.setText(tr("app.title", ai=self.identity.get('ai_name','Changli')))
        self.btn_settings.setText(tr("btn.settings"))
        self.btn_history.setText(tr("btn.history"))
        self.btn_clear.setText(tr("btn.clear"))
        self.btn_profile.setText(tr("btn.profile"))
        self.btn_memclr.setText(tr("btn.clearmem"))
        self.inp.setPlaceholderText(tr("placeholder.input"))
        self.btn_send.setText(tr("btn.send"))

    def _set_language(self, code: str):
        try:
            self.client.set_settings({"lang": code})
            self._reload_i18n(code)
            self._apply_i18n_labels()
            self._system(f"Language set: {code}")
        except Exception as e:
            self._system(f"⚠️ Failed to set language: {e}")

    def _load_models(self):
        try:
            data = self.client.get_models()
            models = data.get("models", [])
            default = data.get("default", self.client.model or "gemma3:4b")

            if isinstance(models, str):
                models = [models]
            elif isinstance(models, dict):
                models = list(models.keys())
            elif not isinstance(models, (list, tuple)):
                models = []
            models = [str(m) for m in models if isinstance(m, (str, bytes)) and str(m).strip()]

            self.model_box.blockSignals(True)
            self.model_box.clear()
            if models:
                self.model_box.addItems(models)
                if default in models:
                    self.model_box.setCurrentText(default)
                    self.client.model = default
                elif self.client.model in models:
                    self.model_box.setCurrentText(self.client.model)
            else:
                self.model_box.addItem(self.client.model or "gemma3:4b")
            self.model_box.blockSignals(False)
        except Exception as e:
            self._system(tr("err.load.models", err=str(e)))
            self.model_box.blockSignals(True)
            self.model_box.clear()
            self.model_box.addItem(self.client.model or "gemma3:4b")
            self.model_box.blockSignals(False)

    def _on_model_activated(self, index: int):
        text = self.model_box.itemText(index)
        if text and text != getattr(self.client, "model", None):
            self.client.model = text
            self._system(tr("msg.model.set", model=text))

    def _load_json(self, path, fallback):
        try:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return fallback.copy()

    def _save_json(self, path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _apply_background(self, cfg):
        self.list.setStyleSheet("QListWidget{background:transparent;border:none;} QListView{background:transparent;border:none;}")
        self.list.viewport().setAutoFillBackground(False)
        if cfg.get("bg_mode") == "image" and cfg.get("bg_image"):
            url = cfg["bg_image"].replace("\\", "/")
            if not url.startswith("file:///"):
                url = "file:///" + url
            self.setStyleSheet(
                "QWidget#ChatWindow{"
                f"  background-color:{cfg.get('bg_color', '#0B0F1A')};"
                f"  background-image:url('{url}');"
                "  background-position:center;"
                "  background-repeat:repeat;"
                "}"
            )
        else:
            self.setStyleSheet(f"QWidget#ChatWindow{{background:{cfg.get('bg_color', '#0B0F1A')};}}")

    def _open_settings(self):
        def open_identity():
            settings_dialog.done(QDialog.Accepted)
            self._open_identity_dialog()

        def open_language():
            cfg = self.client.get_config()
            langs_detail = cfg.get("available_languages_detail", [])
            if not langs_detail:
                codes = cfg.get("available_languages", self._available_langs)
                langs_detail = [{"code": c, "name": self._lang_names.get(c, c)} for c in codes]
            current_lang = cfg.get("lang", _I18N["lang"])

            dlg = QDialog(self); dlg.setWindowTitle(tr("label.language"))
            lay = QVBoxLayout(dlg); lay.setContentsMargins(12,12,12,12); lay.setSpacing(8)
            lab = QLabel(tr("label.language")); lay.addWidget(lab)

            cb = QComboBox()
            for item in langs_detail:
                cb.addItem(item.get("name", item.get("code")), item.get("code"))

            idx = 0
            for i, it in enumerate(langs_detail):
                if it.get("code") == current_lang:
                    idx = i; break
            cb.setCurrentIndex(idx)
            lay.addWidget(cb)

            row = QHBoxLayout()
            btn_cancel = QPushButton("Cancel"); btn_ok = QPushButton("Save")
            btn_cancel.clicked.connect(dlg.reject); btn_ok.clicked.connect(dlg.accept)
            row.addStretch(1); row.addWidget(btn_cancel); row.addWidget(btn_ok)
            lay.addLayout(row)

            if dlg.exec() == QDialog.Accepted:
                code = cb.currentData()
                if code and code != current_lang:
                    self._set_language(code)

        settings_dialog = ChatSettings(self, self.ui_config,
                                       on_open_identity=open_identity,
                                       on_open_language=open_language)
        if settings_dialog.exec() == QDialog.Accepted:
            self.ui_config = settings_dialog.result_config()
            self._apply_background(self.ui_config)
            self._save_json(UI_CFG_FILE, self.ui_config)

    def _open_identity_dialog(self):
        def fetch_default_prompt(user_name: str) -> str:
            cfg = self.client.get_config()
            text = cfg.get("custom_prompt", "")
            return text.replace("{user_name}", user_name or "sayang")

        dlg = IdentityDialog(self, {
            "ai_name": self.identity.get("ai_name","Changli"),
            "user_name": self.identity.get("user_name","sayang"),
            "custom_prompt": self.identity.get("custom_prompt",""),
        }, fetch_default_prompt)

        if dlg.exec() == QDialog.Accepted:
            self.identity = dlg.result_identity()
            self._save_json(IDENTITY_FILE, self.identity)
            self.setWindowTitle(tr("app.title", ai=self.identity['ai_name']))
            self.title.setText(tr("app.title", ai=self.identity['ai_name']))
            self.client.set_identity(
                self.identity["user_name"],
                self.identity.get("custom_prompt",""),
                self.identity.get("ai_name","Changli"),
                self.client.model
            )
            self._system("Identity & Prompt updated.")

    def _clear(self):
        self._start_new_session()

    def _clear_memory_current(self):
        if not self.client.chat_id:
            self._system(tr("err.nochat.clear"))
            return
        try:
            self.client.clear_memory(self.client.chat_id)
            self._system(tr("msg.mem.cleared"))
        except Exception as e:
            self._system(f"⚠️ {e}")

    def _open_profile_dialog(self):
        dlg = QDialog(self)
        ai_display = (self.identity.get("ai_name") or "AI").strip()
        dlg.setWindowTitle(f"User Profile — {ai_display}")
        lay = QVBoxLayout(dlg); lay.setContentsMargins(12,12,12,12); lay.setSpacing(8)

        about = ""; job = ""
        try:
            prof = self.client.get_profile()
            about = prof.get("about","")
            job   = prof.get("job","")
        except Exception:
            pass

        lab1 = QLabel(f"Anything else {ai_display} should know about you?")
        txt_about = QTextEdit(); txt_about.setPlainText(about)
        txt_about.setFixedHeight(110)
        txt_about.setStyleSheet("QTextEdit{background:#121A31;border:1px solid #2D3550;border-radius:8px;color:#EAF2FF;padding:8px;}")

        lab2 = QLabel("What do you do?")
        in_job = QLineEdit(); in_job.setText(job)
        in_job.setStyleSheet("QLineEdit{background:#121A31;border:1px solid #2D3550;border-radius:8px;color:#EAF2FF;padding:8px;}")

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("Save"); btn_ok.clicked.connect(dlg.accept)
        btn_cancel = QPushButton("Cancel"); btn_cancel.clicked.connect(dlg.reject)
        for b in (btn_ok, btn_cancel):
            b.setStyleSheet("QPushButton{background:#18233F;border:1px solid #2D3550;border-radius:8px;color:#EAF2FF;padding:6px 14px;}")
        btn_row.addStretch(1); btn_row.addWidget(btn_cancel); btn_row.addWidget(btn_ok)

        lay.addWidget(lab1); lay.addWidget(txt_about)
        lay.addWidget(lab2); lay.addWidget(in_job)
        lay.addLayout(btn_row)

        if dlg.exec() == QDialog.Accepted:
            try:
                self.client.save_profile(txt_about.toPlainText().strip(), in_job.text().strip())
                self._system("✅ Profile disimpan. (Ingat lintas chat)")
            except Exception as e:
                self._system(f"⚠️ Gagal simpan profile: {e}")

    def _ensure_backend(self):
        if self.client.healthy(): return
        flags=0
        if os.name=="nt":
            CREATE_NO_WINDOW=0x08000000; DETACHED_PROCESS=0x00000008
            flags = CREATE_NO_WINDOW | DETACHED_PROCESS
        try:
            subprocess.Popen([sys.executable, BACKEND_APP],
                             stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                             creationflags=flags if os.name=="nt" else 0,
                             cwd=BASE_DIR)
        except Exception as e:
            QMessageBox.critical(self,"Gagal start backend",str(e)); return
        t0=time.time()
        def wait():
            while time.time()-t0<25:
                if self.client.healthy(): break
                time.sleep(0.6)
        threading.Thread(target=wait, daemon=True).start()

    def _ping(self):
        online = self.client.healthy()
        self.status.setText(tr("status.online") if online else tr("status.offline"))
        self.status.setStyleSheet(f"color:{'#5CE1E6' if online else '#FF678A'};font:600 13px 'Inter';")

    def _send(self):
        msg = self.inp.text().strip()
        if not msg: return
        self.inp.clear()
        self._add_msg("user", msg)
        self._record_first_user_title(msg)
        self.btn_send.setEnabled(False)
        self._set_typing(True)
        self.worker.client = self.client
        self.worker.send(msg)

    def _on_ai(self, role, text):
        self._maybe_create_session_after_first_ai()
        self._touch_session_updated()
        self._set_typing(False)
        self.btn_send.setEnabled(True)
        self._add_msg(role, text)

    def _on_err(self, err):
        self._touch_session_updated()
        self._set_typing(False)
        self.btn_send.setEnabled(True)
        self._system(f"⚠️ {err}")

    def _set_typing(self, on: bool):
        if on:
            self._phase = 0
            self.typ_lbl.setText(tr("label.typing", ai=self.identity.get('ai_name','Changli')))
            self.typ_lbl.setVisible(True)
            self._typing.start()
        else:
            self._typing.stop(); self.typ_lbl.setVisible(False)

    def _tick(self):
        dots = "." * (self._phase % 4); self._phase += 1
        self.typ_lbl.setText(tr("label.typing", ai=self.identity.get('ai_name','Changli')) + dots)

    def _load_history(self):
        try:
            if os.path.exists(SESS_FILE):
                with open(SESS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_history(self):
        try:
            with open(SESS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._history, f, indent=2)
        except Exception:
            pass

    def _load_and_render_history(self, chat_id: str):
        try:
            data = self.client.get_history(chat_id)
            hist = data.get("history", [])
            self._render_history_list(hist)
            self._current_session_id = chat_id
            self.client.chat_id = chat_id
            self.btn_memclr.setEnabled(True)

            m = data.get("model")
            if m:
                if self.model_box.findText(m) == -1:
                    self.model_box.addItem(m)
                self.model_box.blockSignals(True)
                self.model_box.setCurrentText(m)
                self.model_box.blockSignals(False)
                self.client.model = m

            self._touch_session_updated()
            self._system(tr("msg.loaded.history"))
        except Exception as e:
            self._system(f"⚠️ Gagal memuat history: {e}")

    def _ensure_history_state(self):
        if not hasattr(self, "_history"):
            self._history = self._load_history()
        if not hasattr(self, "_current_session_id"):
            self._current_session_id = None
        if not hasattr(self, "_pending_title"):
            self._pending_title = None

    def _start_new_session(self):
        self.client.chat_id = None
        self._current_session_id = None
        self._pending_title = None
        self.list.clear()
        self._system(tr("msg.newchat"))
        self.btn_memclr.setEnabled(False)

    def _record_first_user_title(self, msg_text: str):
        if self._current_session_id is None and self.client.chat_id is None:
            self._pending_title = (msg_text or "").strip()[:36] or "(untitled)"

    def _maybe_create_session_after_first_ai(self):
        if self._current_session_id is None and self.client.chat_id:
            sid = self.client.chat_id
            if sid not in self._history:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                self._history[sid] = {
                    "id": sid,
                    "title": self._pending_title or "(untitled)",
                    "created": now,
                    "updated": now
                }
                self._current_session_id = sid
                self._save_history()
            else:
                self._current_session_id = sid

            self.btn_memclr.setEnabled(True)

    def _touch_session_updated(self):
        if getattr(self, "_current_session_id", None) and self._current_session_id in self._history:
            self._history[self._current_session_id]["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            self._save_history()

    def _render_history_list(self, hist):
        self.list.clear()
        for item in hist:
            try:
                if isinstance(item, dict):
                    if "user" in item or "changli" in item:
                        u = item.get("user")
                        a = item.get("changli")
                        if u: self._add_msg("user", str(u))
                        if a: self._add_msg("ai", str(a))
                    elif "role" in item and "text" in item:
                        self._add_msg("user" if item["role"]=="user" else "ai", str(item["text"]))
                    else:
                        self._add_msg("ai", str(item))
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    role, text = item[0], item[1]
                    self._add_msg("user" if str(role).lower()=="user" else "ai", str(text))
                else:
                    self._add_msg("ai", str(item))
            except Exception:
                continue
        self.list.scrollToBottom()

    def _open_history(self):
        dlg = ChatHistoryDialog(self, self._history.copy())
        if dlg.exec() == QDialog.Accepted:
            action = dlg.result_action
            self._history = dlg.sessions
            self._save_history()
            if action == "new":
                self._start_new_session()
            elif action == "open" and dlg.result_id:
                sid = dlg.result_id
                if sid in self._history:
                    self.client.chat_id = sid
                    self._current_session_id = sid
                    self._pending_title = None
                    self._load_and_render_history(sid)

    def _add_msg(self, role: str, text: str):
        item_widget = QWidget()
        row = QHBoxLayout(item_widget); row.setContentsMargins(10,2,10,2); row.setSpacing(0)

        stack = QVBoxLayout(); stack.setContentsMargins(0,0,0,0); stack.setSpacing(2)
        bubble = QFrame(); bubble.setObjectName("bubble")
        bubble_layout = QVBoxLayout(bubble); bubble_layout.setContentsMargins(12,10,12,8); bubble_layout.setSpacing(4)

        text_lbl = QLabel(); text_lbl.setTextFormat(Qt.RichText)
        text_lbl.setText(f"<span style=\"font:15px 'Segoe UI','Inter'; line-height:1.5; color:#FFFFFF;\">{esc_html(text)}</span>")
        text_lbl.setWordWrap(True); text_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        time_lbl = QLabel(datetime.now().strftime("%H:%M")); time_lbl.setStyleSheet("color:#9AA7BF;font:12px 'Inter';"); time_lbl.setAlignment(Qt.AlignRight)
        bubble_layout.addWidget(text_lbl); bubble_layout.addWidget(time_lbl)

        if role == "user":
            col = QColor(37, 98, 122, 230)
            bubble.setStyleSheet("QFrame#bubble{background:rgba(37,98,122,0.90);border:1px solid rgba(255,255,255,0.06);border-radius:18px 18px 8px 18px;}")
            tail = QLabel(); tail.setPixmap(make_tail_pixmap("right", col)); tail.setFixedSize(16,12)
            stack.addWidget(bubble, 0, Qt.AlignRight); stack.addWidget(tail, 0, Qt.AlignRight)
            row.addStretch(1); row.addLayout(stack, 0)
        else:
            col = QColor(20, 28, 48, 235)
            bubble.setStyleSheet("QFrame#bubble{background:rgba(20,28,48,0.92);border:1px solid rgba(255,255,255,0.06);border-radius:18px 18px 18px 8px;}")
            tail = QLabel(); tail.setPixmap(make_tail_pixmap("left", col)); tail.setFixedSize(16,12)
            stack.addWidget(bubble, 0, Qt.AlignLeft); stack.addWidget(tail, 0, Qt.AlignLeft)
            row.addLayout(stack, 0); row.addStretch(1)

        item = QListWidgetItem(); item.setSizeHint(item_widget.sizeHint())
        self.list.addItem(item); self.list.setItemWidget(item, item_widget)
        self.list.scrollToBottom()

    def _system(self, text):
        item = QListWidgetItem(f"   {text}")
        item.setForeground(QColor("#A5AFBF"))
        self.list.addItem(item); self.list.scrollToBottom()
