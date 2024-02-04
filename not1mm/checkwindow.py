#!/usr/bin/env python3
"""
Check Window
"""
# pylint: disable=no-name-in-module, unused-import, no-member, invalid-name, c-extension-no-member

import logging

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

WORKING_PATH = os.path.dirname(__loader__.get_filename())

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


class MainWindow(QMainWindow):
    """
    The main window
    """

    multicast_interface = None
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
        self.multicast_interface = Multicast(
            self.pref.get("multicast_group", "239.1.1.1"),
            self.pref.get("multicast_port", 2239),
            self.pref.get("interface_ip", "0.0.0.0"),
        )
        self.multicast_interface.ready_read_connect(self.watch_udp)

    def quit_app(self):
        """
        Called when the user clicks the exit button.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        app.quit()

    def load_pref(self):
        """
        Load preference file to get current db filename.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
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
        """
        Puts UDP datagrams in a FIFO queue.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        while self.multicast_interface.server_udp.hasPendingDatagrams():
            json_data = self.multicast_interface.read_datagram_as_json()

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
        """
        Clear match lists.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        self.logList.clear()
        self.masterList.clear()
        self.telnetList.clear()
        self.callhistoryList.clear()

    def master_list(self, call: str) -> None:
        """
        Get MASTER.SCP matches to call and display in list.

        Parameters
        ----------
        call : str
        Call to get matches for

        Returns
        -------
        None
        """
        results = self.mscp.super_check(call)
        self.masterList.clear()
        for item in results:
            listItem = QListWidgetItem(item)
            self.masterList.addItem(listItem)
            self.masterList.show()

    def log_list(self, call: str) -> None:
        """
        Get log matches to call and display in list.

        Parameters
        ----------
        call : str
        Call to get matches for

        Returns
        -------
        None
        """
        self.logList.clear()
        if call:
            result = self.database.get_like_calls_and_bands(call)
            for calls in result:
                listItem = QListWidgetItem(calls)
                self.logList.addItem(listItem)
                self.logList.show()

    def telnet_list(self, spots: list) -> None:
        """
        Get telnet matches to call and display in list.

        Parameters
        ----------
        spots : list
        List of spots to get matches for

        Returns
        -------
        None
        """
        self.telnetList.clear()
        if spots:
            for calls in spots:
                call = calls.get("callsign", "")
                listItem = QListWidgetItem(call)
                self.telnetList.addItem(listItem)
                self.telnetList.show()


def load_fonts_from_dir(directory: str) -> set:
    """
    Load fonts from directory.

    Parameters
    ----------
    directory : str
    The directory to load fonts from.

    Returns
    -------
    set
    The set of font families loaded.
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
