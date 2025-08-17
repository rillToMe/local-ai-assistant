import sys, os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

if __package__ is None or __package__ == "":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ui.chat_window import ChatUI
else:
    from .chat_window import ChatUI

def main():
    app = QApplication(sys.argv)
    ui = ChatUI()
    ui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
