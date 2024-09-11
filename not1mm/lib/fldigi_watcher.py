import xmlrpc.client
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QEventLoop


class FlDigiWatcher(QObject):
    """fldigi watcher"""

    poll_callback = pyqtSignal(str)
    time_to_quit = False

    def __init__(self):
        super().__init__()
        ...

        self.target = "http://127.0.0.1:7362"
        self.payload = ""
        self.response = ""

    def run(self):
        while not self.time_to_quit:
            try:
                server = xmlrpc.client.ServerProxy(self.target)
                self.response = server.logbook.last_record()
            except OSError:
                QThread.msleep(100)
                continue
            if self.payload != self.response:
                self.payload = self.response
                try:
                    self.poll_callback.emit(self.payload)
                except QEventLoop:
                    ...
            QThread.msleep(100)
