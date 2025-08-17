from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QCheckBox, QFileDialog, QColorDialog, QVBoxLayout
)
from PySide6.QtGui import QColor

class ChatSettings(QDialog):
    """
    Dialog pengaturan tampilan (background) + tombol masuk ke IdentityDialog.
    Identity disimpan & di-handle di dialog terpisah (ui/widgets/identity.py).
    """
    def __init__(self, parent=None, current=None, on_open_identity=None):
        super().__init__(parent)
        self.setWindowTitle("Chat Settings")
        self.resize(460, 280)

        cur = current or {}
        self.bg_mode  = cur.get("bg_mode", "color")
        self.bg_color = cur.get("bg_color", "#0E1426")
        self.bg_image = cur.get("bg_image", "")

        root = QVBoxLayout(self)
        form = QFormLayout()
        root.addLayout(form)

        self.use_image = QCheckBox("Use image background")
        self.use_image.setChecked(self.bg_mode == "image")
        form.addRow(self.use_image)

        img_row = QHBoxLayout()
        self.image_path = QLineEdit(self.bg_image)
        self.image_path.setPlaceholderText("Choose an image file...")
        b_browse = QPushButton("Browse"); b_browse.clicked.connect(self._browse)
        img_row.addWidget(self.image_path, 1); img_row.addWidget(b_browse)
        form.addRow("Image:", img_row)

        color_row = QHBoxLayout()
        self.preview = QLabel("      ")
        self.preview.setStyleSheet(f"background:{self.bg_color}; border:1px solid #2D3550;")
        b_color = QPushButton("Pick Color"); b_color.clicked.connect(self._pick)
        color_row.addWidget(self.preview); color_row.addWidget(b_color)
        form.addRow("Solid color:", color_row)

        self.btn_identity = QPushButton("Identity & Prompt…")
        self.btn_identity.setToolTip("Ganti AI Name, User Name, dan Custom Prompt")
        if on_open_identity:
            self.btn_identity.clicked.connect(on_open_identity)
        root.addWidget(self.btn_identity)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(self, "Choose background image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if p:
            self.image_path.setText(p); self.use_image.setChecked(True)

    def _pick(self):
        col = QColorDialog.getColor(QColor(self.bg_color), self, "Pick chat background color")
        if col.isValid():
            self.bg_color = col.name()
            self.preview.setStyleSheet(f"background:{self.bg_color}; border:1px solid #2D3550;")
            self.use_image.setChecked(False)

    def result_config(self):
        if self.use_image.isChecked() and self.image_path.text().strip():
            return {"bg_mode": "image", "bg_image": self.image_path.text().strip(), "bg_color": self.bg_color}
        else:
            return {"bg_mode": "color", "bg_color": self.bg_color, "bg_image": ""}
