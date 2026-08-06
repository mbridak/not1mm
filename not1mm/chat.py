import datetime
import logging

from PyQt6 import QtGui, uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDockWidget

from not1mm import fsutils
from not1mm.lib.preferences import Preferences

logger = logging.getLogger(__name__)


class ChatWindow(QDockWidget):
    """The stats window. Shows something important."""

    message = pyqtSignal(dict)
    chatwindow_closed = pyqtSignal()
    poll_time = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(
        milliseconds=1000
    )

    def __init__(self, action):
        super().__init__()
        self.action = action
        self.active: bool = False
        uic.loadUi(fsutils.APP_DATA_PATH / "chat.ui", self)
        self.chat_input.returnPressed.connect(self.send_chat)
        self.pref = Preferences.data()

    def send_chat(self):
        """Sends UDP chat packet with text entered in chat_entry field."""
        chat_string = self.chat_input.text()
        packet = {"cmd": "CHAT"}
        packet["message"] = chat_string
        self.message.emit(packet)
        self.chat_input.setText("")

    def display_chat(self, sender, body):
        """Displays the chat history."""

        if (mycall := self.pref.get("current_op", "")) and mycall in body.upper():
            self.chat_history.setTextColor(QtGui.QColor(245, 121, 0))
        self.chat_history.insertPlainText(f"\n{sender}: {body}")
        self.chat_history.setTextColor(QtGui.QColor(211, 215, 207))
        self.chat_history.ensureCursorVisible()

    def msg_from_main(self, packet):
        """Process messages from the main window."""

        if packet.get("cmd", "") == "CHAT":
            # {"cmd": "CHAT", "sender": "N2CQR", "message": "I worked your mama on 80 meters."}
            self.display_chat(packet.get("sender", ""), packet.get("message", ""))
            return

    def setActive(self, mode: bool) -> None:
        self.active: bool = bool(mode)

    def closeEvent(self, event) -> None:
        self.action.setChecked(False)
        self.chatwindow_closed.emit()
        event.accept()


if __name__ == "__main__":
    print("This is not a program.\nTry Again.")
