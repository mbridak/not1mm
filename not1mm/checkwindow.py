#!/usr/bin/env python3
"""
Check Window
"""
# pylint: disable=no-name-in-module, unused-import, no-member, invalid-name

import logging
import pkgutil
import platform
import queue
import os
import sys

from json import JSONDecodeError, loads, dumps
from pathlib import Path

from PyQt5 import uic
from PyQt5.QtCore import QDir, Qt
from PyQt5.QtWidgets import QApplication, QListWidget, QListWidgetItem, QMainWindow
from PyQt5 import QtNetwork
from PyQt5.QtGui import QFontDatabase

from not1mm.lib.database import DataBase
from not1mm.lib.multicast import Multicast
from not1mm.lib.super_check_partial import SCP

os.environ["QT_QPA_PLATFORMTHEME"] = "gnome"

loader = pkgutil.get_loader("not1mm")
WORKING_PATH = os.path.dirname(loader.get_filename())

if "XDG_DATA_HOME" in os.environ:
    DATA_PATH = os.environ.get("XDG_DATA_HOME")
else:
    DATA_PATH = str(Path.home() / ".local" / "share")
DATA_PATH += "/not1mm"

if "XDG_CONFIG_HOME" in os.environ:
    CONFIG_PATH = os.environ.get("XDG_CONFIG_HOME")
else:
    CONFIG_PATH = str(Path.home() / ".config")
CONFIG_PATH += "/not1mm"

MULTICAST_PORT = 2239
MULTICAST_GROUP = "239.1.1.1"
INTERFACE_IP = "0.0.0.0"


class MainWindow(QMainWindow):
    """
    The main window
    """

    dbname = None
    pref = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_pref()
        self.dbname = DATA_PATH + "/" + self.pref.get("current_database", "ham.db")
        self.database = DataBase(self.dbname, WORKING_PATH)
        self.database.current_contest = self.pref.get("contest", 0)
        data_path = WORKING_PATH + "/data/checkwindow.ui"
        uic.loadUi(data_path, self)
        self.setWindowTitle("CheckWindow")
        self.logList.clear()
        self.masterList.clear()
        self.telnetList.clear()
        self.callhistoryList.clear()
        # self.logList.hide()
        # self.telnetList.hide()
        # self.telnetListLabel.hide()
        self.callhistoryList.hide()
        self.callhistoryListLabel.hide()
        self.mscp = SCP(WORKING_PATH)
        self._udpwatch = None
        self.udp_fifo = queue.Queue()
        self.udpsocket = QtNetwork.QUdpSocket(self)
        self.udpsocket.bind(
            QtNetwork.QHostAddress.AnyIPv4,
            MULTICAST_PORT,
            QtNetwork.QUdpSocket.ShareAddress,
        )
        self.udpsocket.joinMulticastGroup(QtNetwork.QHostAddress(MULTICAST_GROUP))
        self.udpsocket.readyRead.connect(self.watch_udp)

    def quit_app(self):
        """doc"""
        app.quit()

    def load_pref(self):
        """Load preference file to get current db filename."""
        try:
            if os.path.exists(CONFIG_PATH + "/not1mm.json"):
                with open(
                    CONFIG_PATH + "/not1mm.json", "rt", encoding="utf-8"
                ) as file_descriptor:
                    self.pref = loads(file_descriptor.read())
                    logger.info("%s", self.pref)
            else:
                self.pref["current_database"] = "ham.db"

        except IOError as exception:
            logger.critical("Error: %s", exception)

    def watch_udp(self):
        """Puts UDP datagrams in a FIFO queue"""
        while self.udpsocket.hasPendingDatagrams():
            datagram, _, _ = self.udpsocket.readDatagram(
                self.udpsocket.pendingDatagramSize()
            )

            try:
                debug_info = f"{datagram.decode()}"
                logger.debug(debug_info)
                json_data = loads(datagram.decode())
            except UnicodeDecodeError as err:
                the_error = f"Not Unicode: {err}\n{datagram}"
                logger.debug(the_error)
                continue
            except JSONDecodeError as err:
                the_error = f"Not JSON: {err}\n{datagram}"
                logger.debug(the_error)
                continue
            if json_data.get("station", "") != platform.node():
                continue
            if json_data.get("cmd", "") == "UPDATELOG":
                self.clear_lists()
            if json_data.get("cmd", "") == "CALLCHANGED":
                call = json_data.get("call", "")
                self.master_list(call)
                self.log_list(call)
                continue
            if json_data.get("cmd", "") == "CHECKSPOTS":
                self.telnetList.clear()
                spots = json_data.get("spots", [])
                self.telnet_list(spots)
                continue
            if json_data.get("cmd", "") == "NEWDB":
                ...
                # self.load_new_db()
            if json_data.get("cmd", "") == "HALT":
                self.quit_app()

    def clear_lists(self) -> None:
        """Clear match lists"""
        self.logList.clear()
        self.masterList.clear()
        self.telnetList.clear()
        self.callhistoryList.clear()

    def master_list(self, call: str) -> None:
        """Get MASTER.SCP matches to call"""
        results = self.mscp.super_check(call)
        self.masterList.clear()
        for item in results:
            listItem = QListWidgetItem(item)
            self.masterList.addItem(listItem)
            self.masterList.show()

    def log_list(self, call: str) -> None:
        """Parse calls in log for matches"""
        self.logList.clear()
        if call:
            result = self.database.get_like_calls_and_bands(call)
            for calls in result:
                listItem = QListWidgetItem(calls)
                self.logList.addItem(listItem)
                self.logList.show()

    def telnet_list(self, spots: list) -> None:
        """Parse matching calls from telnet cluster"""
        self.telnetList.clear()
        if spots:
            for calls in spots:
                call = calls.get("callsign", "")
                listItem = QListWidgetItem(call)
                self.telnetList.addItem(listItem)
                self.telnetList.show()


def load_fonts_from_dir(directory: str) -> set:
    """
    Well it loads fonts from a directory...
    """
    font_families = set()
    for _fi in QDir(directory).entryInfoList(["*.ttf", "*.woff", "*.woff2"]):
        _id = QFontDatabase.addApplicationFont(_fi.absoluteFilePath())
        font_families |= set(QFontDatabase.applicationFontFamilies(_id))
    return font_families


def main():
    """main entry"""
    sys.exit(app.exec())


logger = logging.getLogger("__main__")
handler = logging.StreamHandler()
formatter = logging.Formatter(
    datefmt="%H:%M:%S",
    fmt="[%(asctime)s] %(levelname)s %(module)s - %(funcName)s Line %(lineno)d:\n%(message)s",
)
handler.setFormatter(formatter)
logger.addHandler(handler)

if Path("./debug").exists():
    logger.setLevel(logging.DEBUG)
    logger.debug("debugging on")
else:
    logger.setLevel(logging.WARNING)
    logger.warning("debugging off")

app = QApplication(sys.argv)
app.setStyle("Adwaita-Dark")
font_path = WORKING_PATH + "/data"
_families = load_fonts_from_dir(os.fspath(font_path))
window = MainWindow()
window.show()

if __name__ == "__main__":
    main()
