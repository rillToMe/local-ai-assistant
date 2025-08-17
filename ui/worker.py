import threading
from PySide6.QtCore import QObject, Signal
from .client import Client

class Worker(QObject):
    done = Signal(str, str)
    error = Signal(str)

    def __init__(self, client: Client):
        super().__init__()
        self.client = client

    def send(self, text: str):
        def run():
            try:
                resp = self.client.send(text)
                self.done.emit("ai", resp)
            except Exception as e:
                self.error.emit(str(e))
        threading.Thread(target=run, daemon=True).start()

