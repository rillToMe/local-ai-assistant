from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QColorDialog, QLineEdit
)

class ChatSettings(QDialog):
    def __init__(self, parent, ui_config: dict,
                 on_open_identity=None, on_open_language=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._cfg = dict(ui_config or {})
        self._on_open_identity = on_open_identity
        self._on_open_language = on_open_language

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Background Mode"))
        self.mode = QComboBox()
        self.mode.addItems(["color", "image"])
        self.mode.setCurrentText(self._cfg.get("bg_mode", "color"))
        row1.addWidget(self.mode, 1)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Background Color"))
        self.color = QLineEdit(self._cfg.get("bg_color", "#0E1426"))
        btn_pick = QPushButton("Pick")
        def pick():
            dlg = QColorDialog(self)
            if dlg.exec():
                c = dlg.selectedColor()
                if c.isValid():
                    self.color.setText(c.name())
        btn_pick.clicked.connect(pick)
        row2.addWidget(self.color, 1)
        row2.addWidget(btn_pick)
        lay.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Background Image (path)"))
        self.img = QLineEdit(self._cfg.get("bg_image", ""))
        row3.addWidget(self.img, 1)
        lay.addLayout(row3)

        row_actions = QHBoxLayout()
        btn_identity = QPushButton("Identity & Prompt")
        btn_identity.clicked.connect(lambda: self._on_open_identity and self._on_open_identity())
        btn_language = QPushButton("Language")
        btn_language.clicked.connect(lambda: self._on_open_language and self._on_open_language())
        row_actions.addWidget(btn_identity)
        row_actions.addWidget(btn_language)
        row_actions.addStretch(1)
        lay.addLayout(row_actions)

        foot = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_ok = QPushButton("Save")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)
        foot.addStretch(1)
        foot.addWidget(btn_cancel)
        foot.addWidget(btn_ok)
        lay.addLayout(foot)

    def result_config(self) -> dict:
        return {
            "bg_mode": self.mode.currentText(),
            "bg_color": self.color.text().strip() or "#0E1426",
            "bg_image": self.img.text().strip()
        }
