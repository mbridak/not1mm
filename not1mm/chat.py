import datetime
import logging
import os

# import sys

from PyQt6 import uic, QtGui
from PyQt6.QtWidgets import QDockWidget
from PyQt6.QtCore import pyqtSignal

import not1mm.fsutils as fsutils
from json import loads
from json.decoder import JSONDecodeError

logger = logging.getLogger(__name__)

# chat_history  QTextBrowser
# chat_input    QLineedit


class ChatWindow(QDockWidget):
    """The stats window. Shows something important."""

    message = pyqtSignal(dict)
    mycall = ""
    poll_time = datetime.datetime.now() + datetime.timedelta(milliseconds=1000)

    def __init__(self, action):
        super().__init__()
        self.action = action
        self.active: bool = False
        # self.load_pref()
        uic.loadUi(fsutils.APP_DATA_PATH / "chat.ui", self)
        self.chat_input.returnPressed.connect(self.send_chat)

    def send_chat(self):
        """Sends UDP chat packet with text entered in chat_entry field."""
        chat_string = self.chat_input.text()
        packet = {"cmd": "CHAT"}
        #  packet["sender"] = self.preference.get("mycall", "")
        packet["message"] = chat_string
        self.message.emit(packet)
        self.chat_input.setText("")

    def display_chat(self, sender, body):
        """Displays the chat history."""

        if self.mycall in body.upper():
            self.chat_history.setTextColor(QtGui.QColor(245, 121, 0))
        self.chat_history.insertPlainText(f"\n{sender}: {body}")
        self.chat_history.setTextColor(QtGui.QColor(211, 215, 207))
        self.chat_history.ensureCursorVisible()

    def msg_from_main(self, packet):
        """"""

        if packet.get("cmd", "") == "CHAT":
            # {"cmd": "CHAT", "sender": "N2CQR", "message": "I worked your mama on 80 meters."}
            self.display_chat(packet.get("sender", ""), packet.get("message", ""))
            return
        if packet.get("cmd", "") == "CONTESTSTATUS":
            self.mycall = packet.get("operator", "").upper()
            return

    def setActive(self, mode: bool) -> None:
        self.active: bool = bool(mode)

    def load_pref(self) -> None:
        """
        Load preference file to get current db filename and sets the initial darkmode state.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        try:
            if os.path.exists(fsutils.CONFIG_FILE):
                with open(
                    fsutils.CONFIG_FILE, "rt", encoding="utf-8"
                ) as file_descriptor:
                    self.pref = loads(file_descriptor.read())
                    logger.info(f"loaded config file from {fsutils.CONFIG_FILE}")
            else:
                self.pref["current_database"] = "ham.db"

        except (IOError, JSONDecodeError) as exception:
            logger.critical("Error: %s", exception)

    def closeEvent(self, event) -> None:
        self.action.setChecked(False)


if __name__ == "__main__":
    print("This is not a program.\nTry Again.")
