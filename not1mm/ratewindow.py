#!/usr/bin/env python3
"""
not1mm Contest logger
Email: michael.bridak@gmail.com
GPL V3
Class: RateWindow
Purpose: not sure yet
"""
# pylint: disable=no-name-in-module, unused-import, no-member, invalid-name, c-extension-no-member
# pylint: disable=logging-fstring-interpolation, line-too-long

import logging
import os

from PyQt6 import uic
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QDockWidget
from PyQt6.QtGui import QMouseEvent, QColorConstants, QPalette, QColor
from PyQt6.QtCore import pyqtSignal

import not1mm.fsutils as fsutils
from not1mm.lib.database import DataBase

from json import loads
from json.decoder import JSONDecodeError
from pathlib import Path

logger = logging.getLogger(__name__)


class RateWindow(QDockWidget):
    """The rate window. Shows something important."""

    message = pyqtSignal(dict)
    dbname = None
    pref = {}

    def __init__(self):
        super().__init__()
        self.active = False
        self.load_pref()
        self.dbname = fsutils.USER_DATA_PATH / self.pref.get(
            "current_database", "ham.db"
        )
        self.database = DataBase(self.dbname, fsutils.APP_DATA_PATH)
        self.database.current_contest = self.pref.get("contest", 0)

        uic.loadUi(fsutils.APP_DATA_PATH / "ratewindow.ui", self)

    def msg_from_main(self, packet):
        """"""
        if packet.get("cmd", "") == "DARKMODE":
            self.setDarkMode(packet.get("state", False))
            return

        if self.active is False:
            return

        if packet.get("cmd", "") == "NEWDB":
            ...
            # self.load_new_db()

    def setActive(self, mode: bool):
        self.active = bool(mode)

    def setDarkMode(self, dark: bool) -> None:
        """Forces a darkmode palette."""

        if dark:
            darkPalette = QPalette()
            darkColor = QColor(56, 56, 56)
            disabledColor = QColor(127, 127, 127)
            darkPalette.setColor(QPalette.ColorRole.Window, darkColor)
            darkPalette.setColor(QPalette.ColorRole.WindowText, QColorConstants.White)
            darkPalette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
            darkPalette.setColor(QPalette.ColorRole.AlternateBase, darkColor)
            darkPalette.setColor(QPalette.ColorRole.Text, QColorConstants.White)
            darkPalette.setColor(QPalette.ColorRole.Button, darkColor)
            darkPalette.setColor(QPalette.ColorRole.ButtonText, QColorConstants.White)
            darkPalette.setColor(QPalette.ColorRole.BrightText, QColorConstants.Red)
            darkPalette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
            darkPalette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
            darkPalette.setColor(
                QPalette.ColorRole.HighlightedText, QColorConstants.Black
            )
            darkPalette.setColor(
                QPalette.ColorGroup.Disabled,
                QPalette.ColorRole.ButtonText,
                disabledColor,
            )
            darkPalette.setColor(
                QPalette.ColorGroup.Disabled,
                QPalette.ColorRole.HighlightedText,
                disabledColor,
            )
            darkPalette.setColor(
                QPalette.ColorGroup.Disabled,
                QPalette.ColorRole.Text,
                disabledColor,
            )

            self.setPalette(darkPalette)
        else:
            palette = self.style().standardPalette()
            self.setPalette(palette)

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
        self.setDarkMode(self.pref.get("darkmode", False))
