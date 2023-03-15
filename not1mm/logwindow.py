#!/usr/bin/env python3
"""
Display current log
"""
# pylint: disable=no-name-in-module, unused-import, no-member
# QTableWidget
# focusedLog, generalLog
import os
import pkgutil
import sys

# from json import dumps, loads
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import QDir

from PyQt5.QtGui import QFontDatabase

from not1mm.lib.database import DataBase

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


class MainWindow(QtWidgets.QMainWindow):
    """
    The main window
    """

    dbname = DATA_PATH + "/ham.db"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.database = DataBase(self.dbname, WORKING_PATH)
        self.contact = self.database.empty_contact
        data_path = WORKING_PATH + "/data/logwindow.ui"
        uic.loadUi(data_path, self)
        self.generalLog.setColumnCount(3)
        item = QtWidgets.QTableWidgetItem()
        self.generalLog.setHorizontalHeaderItem(0, item)
        self.generalLog.setHorizontalHeaderItem(1, item)
        self.generalLog.setHorizontalHeaderItem(2, item)

    def get_log(self):
        """Get Log, Show it."""
        current_log = self.database.fetch_all_contacts_asc()
        for log_item in current_log:
            print(f"Log Item {log_item}")
            numRows = self.generalLog.rowCount()
            print(f"num rows {numRows}")
            self.generalLog.insertRow(numRows)
            self.generalLog.setItem(
                numRows, 0, QtWidgets.QTableWidgetItem(log_item.get("TS", ""))
            )
            self.generalLog.setItem(
                numRows, 1, QtWidgets.QTableWidgetItem(log_item.get("Call", ""))
            )
            self.generalLog.setItem(
                numRows, 2, QtWidgets.QTableWidgetItem(str(log_item.get("Freq", "")))
            )


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
    app = QtWidgets.QApplication(sys.argv)
    font_path = WORKING_PATH + "/data"
    _families = load_fonts_from_dir(os.fspath(font_path))
    window = MainWindow()
    window.show()
    timer = QtCore.QTimer()
    timer.timeout.connect(window.get_log)
    timer.start(1000)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
