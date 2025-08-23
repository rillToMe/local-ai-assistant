import json, os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QDialogButtonBox, QHBoxLayout, QMessageBox
)

class IdentityDialog(QDialog):
    def __init__(self, parent, initial, fetch_default_prompt):
        super().__init__(parent)
        self.setWindowTitle("Identity & Prompt")
        self.resize(680, 520)
        self.initial = initial or {}

        v = QVBoxLayout(self)

        form = QFormLayout()
        self.ai_name = QLineEdit(self.initial.get("ai_name", "Changli"))
        self.user_name = QLineEdit(self.initial.get("user_name", "sayang"))
        self.prompt = QTextEdit(self.initial.get("custom_prompt", ""))

        form.addRow("AI Name:", self.ai_name)
        form.addRow("User Name:", self.user_name)
        form.addRow("Custom Prompt:", self.prompt)
        v.addLayout(form)

        row = QHBoxLayout()
        self.btn_default = QPushButton("Default Prompt")
        self.btn_default.setToolTip("Ambil prompt default dari backend (/config)")
        row.addWidget(self.btn_default)
        row.addStretch(1)
        v.addLayout(row)

        self.btn_default.clicked.connect(lambda: self._load_default(fetch_default_prompt))

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        v.addWidget(btns)

    def _load_default(self, fetch_default_prompt):
        try:
            default_text = fetch_default_prompt(self.user_name.text().strip() or "sayang")
            if default_text:
                self.prompt.setPlainText(default_text)
        except Exception as e:
            QMessageBox.warning(self, "Gagal memuat default prompt", str(e))

    def result_identity(self):
        return {
            "ai_name": self.ai_name.text().strip() or "Changli",
            "user_name": self.user_name.text().strip() or "sayang",
            "custom_prompt": self.prompt.toPlainText().strip(),
        }
