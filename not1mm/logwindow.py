#!/usr/bin/env python3
"""
Display current log
"""

# QTableWidget
# focusedLog, generalLog
import os
import pkgutil

from json import dumps, loads
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import (
    QDir,
    QPoint,  # pylint: disable=no-name-in-module
    QRect,
    QSize,
    Qt,
)
from PyQt5.QtGui import QFontDatabase  # pylint: disable=no-name-in-module

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.database = DataBase(self.dbname, WORKING_PATH)
        self.contact = self.database.empty_contact
        data_path = WORKING_PATH + "/data/logwindow.ui"
        uic.loadUi(data_path, self)
