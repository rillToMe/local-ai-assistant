from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem, 
    QHBoxLayout, QPushButton, QDialogButtonBox, QInputDialog, QMessageBox
)

class ChatHistoryDialog(QDialog):
    def __init__(self, parent=None, sessions=None):
        super().__init__(parent)
        self.setWindowTitle("Chat History")
        self.resize(420, 420)
        self.sessions = sessions or {}

        v = QVBoxLayout(self)

        self.list = QListWidget()
        self.list.setSpacing(4)
        v.addWidget(self.list, 1)

        btn_row = QHBoxLayout()
        self.btn_new    = QPushButton("New Chat")
        self.btn_open   = QPushButton("Open")
        self.btn_ren    = QPushButton("Rename")
        self.btn_del    = QPushButton("Delete")
        for b in (self.btn_new, self.btn_open, self.btn_ren, self.btn_del):
            b.setFixedHeight(28)
        btn_row.addWidget(self.btn_new)
        btn_row.addWidget(self.btn_open)
        btn_row.addWidget(self.btn_ren)
        btn_row.addWidget(self.btn_del)
        v.addLayout(btn_row)

        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        v.addWidget(close)

        self.result_action = None  
        self.result_id = None       

        self.btn_new.clicked.connect(self._new)
        self.btn_open.clicked.connect(self._open)
        self.btn_ren.clicked.connect(self._ren)
        self.btn_del.clicked.connect(self._del)

        self._reload()

    def _reload(self):
        self.list.clear()
        items = sorted(self.sessions.values(),
                       key=lambda x: x.get("updated", x.get("created", "")),
                       reverse=True)
        for sess in items:
            title = sess.get("title") or "(untitled)"
            ts = sess.get("updated") or sess.get("created") or ""
            item = QListWidgetItem(f"{title}\n{ts}")
            item.setData(Qt.UserRole, sess.get("id"))
            self.list.addItem(item)

    def _sel_id(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _new(self):
        self.result_action = "new"
        self.accept()

    def _open(self):
        sid = self._sel_id()
        if not sid: return
        self.result_action = "open"
        self.result_id = sid
        self.accept()

    def _ren(self):
        sid = self._sel_id()
        if not sid: return
        cur = self.sessions.get(sid, {}).get("title") or ""
        title, ok = QInputDialog.getText(self, "Rename Chat", "Title:", text=cur)
        if ok and title.strip():
            self.sessions[sid]["title"] = title.strip()
            self.sessions[sid]["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            self._reload()

    def _del(self):
        sid = self._sel_id()
        if not sid: return
        if QMessageBox.question(self, "Delete Chat", "Delete selected chat?") == QMessageBox.Yes:
            self.sessions.pop(sid, None)
            self._reload()
