from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor

def make_tail_pixmap(side: str, color: QColor) -> QPixmap:
    w, h = 16, 12
    pm = QPixmap(w, h); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHints(QPainter.Antialiasing, True)
    p.setBrush(color); p.setPen(Qt.NoPen)
    path = QPainterPath()
    if side == "right":
        path.moveTo(0, h)
        path.cubicTo(w*0.45, h, w*0.7, h*0.75, w, 0)
        path.lineTo(w, h)
        path.closeSubpath()
    else:
        path.moveTo(w, h)
        path.cubicTo(w*0.55, h, w*0.3, h*0.75, 0, 0)
        path.lineTo(0, h)
        path.closeSubpath()
    p.drawPath(path); p.end()
    return pm

def esc_html(s: str) -> str:
    return (
        s.replace("&","&amp;")
         .replace("<","&lt;")
         .replace(">","&gt;")
         .replace("\n","<br>")
    )
