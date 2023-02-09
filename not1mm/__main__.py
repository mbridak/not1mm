#!/usr/bin/env python3
"""
NOT1MM Logger
"""
# pylint: disable=unused-import, c-extension-no-member

import logging
import os
import pkgutil
import re
import socket
import sqlite3
import sys
from datetime import datetime
from json import dumps, loads
from pathlib import Path
from shutil import copyfile
from xmlrpc.client import Error, ServerProxy
from _frozen_importlib_external import SourceFileLoader

import psutil
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import QDir, Qt  # pylint: disable=no-name-in-module
from PyQt5.QtGui import QFontDatabase  # pylint: disable=no-name-in-module

try:
    from not1mm.lib.cwinterface import CW
    from not1mm.lib.lookup import QRZlookup

    # from not1mm.lib.settings import Settings
except ModuleNotFoundError:
    from lib.cwinterface import CW
    from lib.lookup import QRZlookup

    # from lib.settings import Settings


loader = pkgutil.get_loader("not1mm")
assert isinstance(loader, SourceFileLoader)
WORKING_PATH = os.path.dirname(loader.get_filename())


class MainWindow(QtWidgets.QMainWindow):
    """
    The main window
    """

    def __init__(self, *args, **kwargs):
        logging.info("MainWindow: __init__")
        super().__init__(*args, **kwargs)
        data_path = WORKING_PATH + "/data/main.ui"
        uic.loadUi(data_path, self)
        self.score.setText("0")
        self.callsign.textEdited.connect(self.callsign_changed)
        self.sent.setText("59")
        self.receive.setText("59")

    def callsign_changed(self):
        text = self.callsign.text()
        text = text.upper()
        self.callsign.setText(text)
        stripped_text = text.strip()
        if text[-1:] == " ":
            if stripped_text == "CW":
                self.setmode("CW")
                self.callsign.setText("")
                return
            if stripped_text == "SSB":
                self.setmode("SSB")
                self.callsign.setText("")
                return
            ...

    def setmode(self, mode: str) -> None:
        if mode == "CW":
            self.mode.setText("CW")
            self.sent.setText("599")
            self.receive.setText("599")
            return
        if mode == "SSB":
            self.mode.setText("SSB")
            self.sent.setText("59")
            self.receive.setText("59")


def load_fonts_from_dir(directory: str) -> set:
    """
    Well it loads fonts from a directory...
    """
    font_families = set()
    for _fi in QDir(directory).entryInfoList(["*.ttf", "*.woff", "*.woff2"]):
        _id = QFontDatabase.addApplicationFont(_fi.absoluteFilePath())
        font_families |= set(QFontDatabase.applicationFontFamilies(_id))
    return font_families


def run():
    """
    Main Entry
    """

    os.system(
        "xdg-icon-resource install --size 32 --context apps --mode user "
        f"{WORKING_PATH}/data/k6gte.not1mm-32.png k6gte-not1mm"
    )
    os.system(
        "xdg-icon-resource install --size 64 --context apps --mode user "
        f"{WORKING_PATH}/data/k6gte.not1mm-64.png k6gte-not1mm"
    )
    os.system(
        "xdg-icon-resource install --size 128 --context apps --mode user "
        f"{WORKING_PATH}/data/k6gte.not1mm-128.png k6gte-not1mm"
    )
    os.system(f"xdg-desktop-menu install {WORKING_PATH}/data/k6gte-not1mm.desktop")

    sys.exit(app.exec())


if Path("./debug").exists():
    logging.basicConfig(
        format=(
            "[%(asctime)s] %(levelname)s %(module)s - "
            "%(funcName)s Line %(lineno)d:\n%(message)s"
        ),
        datefmt="%H:%M:%S",
        level=logging.INFO,
    )
else:
    logging.basicConfig(
        format=(
            "[%(asctime)s] %(levelname)s %(module)s - "
            "%(funcName)s Line %(lineno)d:\n%(message)s"
        ),
        datefmt="%H:%M:%S",
        level=logging.WARNING,
    )

app = QtWidgets.QApplication(sys.argv)
app.setStyle("Fusion")
font_path = WORKING_PATH + "/data"
families = load_fonts_from_dir(os.fspath(font_path))
logging.info(families)
window = MainWindow()
window.show()


if __name__ == "__main__":
    run()
