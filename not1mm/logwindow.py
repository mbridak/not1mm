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
from PyQt5.QtCore import QDir, QItemSelectionModel
from PyQt5.QtGui import QFontDatabase
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

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


class Watcher:
    """Keep an eye out"""

    def __init__(self, directory=".", handler=FileSystemEventHandler()):
        self.observer = Observer()
        self.handler = handler
        self.directory = directory

    def start(self):
        """Starts the file watcher"""
        self.observer.schedule(self.handler, self.directory, recursive=True)
        self.observer.start()

    def stop(self):
        """Stops the file watcher"""
        self.observer.stop()
        self.observer.join()


class Handler(FileSystemEventHandler):
    """Make them accoutable"""

    def on_modified(self, event):
        if not event.is_directory:
            window.get_log()


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
        self.generalLog.setColumnCount(11)
        # item = QtWidgets.QTableWidgetItem("")
        self.generalLog.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem("MM-DD"))
        self.generalLog.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem("HH:MM"))
        self.generalLog.setHorizontalHeaderItem(2, QtWidgets.QTableWidgetItem("Call"))
        self.generalLog.setHorizontalHeaderItem(3, QtWidgets.QTableWidgetItem("Freq"))
        self.generalLog.setHorizontalHeaderItem(4, QtWidgets.QTableWidgetItem("Snt"))
        self.generalLog.setHorizontalHeaderItem(5, QtWidgets.QTableWidgetItem("Rcv"))
        self.generalLog.setHorizontalHeaderItem(6, QtWidgets.QTableWidgetItem("M1"))
        self.generalLog.setHorizontalHeaderItem(7, QtWidgets.QTableWidgetItem("ZN"))
        self.generalLog.setHorizontalHeaderItem(8, QtWidgets.QTableWidgetItem("M2"))
        self.generalLog.setHorizontalHeaderItem(9, QtWidgets.QTableWidgetItem("PFX"))
        self.generalLog.setHorizontalHeaderItem(10, QtWidgets.QTableWidgetItem("PTS"))
        path = sys.argv[1] if len(sys.argv) > 1 else DATA_PATH + "/ham.db"
        watcher = Watcher(path, Handler())
        watcher.start()
        self.get_log()

    def get_log(self):
        """Get Log, Show it."""
        current_log = self.database.fetch_all_contacts_asc()
        self.generalLog.setRowCount(0)
        for log_item in current_log:
            number_of_rows = self.generalLog.rowCount()
            self.generalLog.insertRow(number_of_rows)
            time_stamp = log_item.get("TS", "MM-DD HH:MM")
            month_day, hour_min = time_stamp.split(" ")
            _, month, day = month_day.split("-")
            hour, minute, _ = hour_min.split(":")
            month_day = f"{month}-{day}"
            hour_min = f"{hour}:{minute}"

            first_item = QtWidgets.QTableWidgetItem(month_day)
            self.generalLog.setItem(number_of_rows, 0, first_item)
            self.generalLog.setCurrentItem(first_item, QItemSelectionModel.NoUpdate)
            self.generalLog.setItem(
                number_of_rows, 1, QtWidgets.QTableWidgetItem(hour_min)
            )

            self.generalLog.setItem(
                number_of_rows,
                2,
                QtWidgets.QTableWidgetItem(str(log_item.get("Call", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                3,
                QtWidgets.QTableWidgetItem(str(log_item.get("Freq", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                4,
                QtWidgets.QTableWidgetItem(str(log_item.get("SNT", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                5,
                QtWidgets.QTableWidgetItem(str(log_item.get("RCV", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                6,
                QtWidgets.QTableWidgetItem(str(log_item.get("IsMultiplier1", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                7,
                QtWidgets.QTableWidgetItem(str(log_item.get("ZN", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                8,
                QtWidgets.QTableWidgetItem(str(log_item.get("IsMultiplier2", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                9,
                QtWidgets.QTableWidgetItem(str(log_item.get("WPXPrefix", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                10,
                QtWidgets.QTableWidgetItem(str(log_item.get("Points", ""))),
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
    sys.exit(app.exec())


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    font_path = WORKING_PATH + "/data"
    _families = load_fonts_from_dir(os.fspath(font_path))
    window = MainWindow()
    window.setWindowTitle("Log Display")
    window.show()
    main()
