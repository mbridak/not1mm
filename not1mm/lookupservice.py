#!/usr/bin/env python3
"""
not1mm Contest logger
Email: michael.bridak@gmail.com
GPL V3
Class: LookupService
Purpose: Lookup callsigns with online services.
"""

# pylint: disable=unused-import, c-extension-no-member, no-member, invalid-name, too-many-lines
# pylint: disable=logging-fstring-interpolation, line-too-long, no-name-in-module

import logging
import os
from json import loads

from PyQt6.QtWidgets import QDockWidget
from PyQt6.QtCore import pyqtSignal

import not1mm.fsutils as fsutils

# from not1mm.lib.multicast import Multicast
from not1mm.lib.lookup import QRZlookup, HamQTH

logger = logging.getLogger(__name__)


class LookupService(QDockWidget):
    """The Lookup Service class."""

    message = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._udpwatch = None

        self.look_up = None
        self.settings = self.get_settings()
        if self.settings:

            if self.settings.get("useqrz"):
                self.look_up = QRZlookup(
                    self.settings.get("lookupusername", ""),
                    self.settings.get("lookuppassword", ""),
                )

            if self.settings.get("usehamqth"):
                self.look_up = HamQTH(
                    self.settings.get("lookupusername", ""),
                    self.settings.get("lookuppassword", ""),
                )

    def get_settings(self) -> dict:
        """Get the settings."""
        if os.path.exists(fsutils.CONFIG_FILE):
            with open(fsutils.CONFIG_FILE, "rt", encoding="utf-8") as file_descriptor:
                return loads(file_descriptor.read())
        return {}

    def msg_from_main(self, packet):
        """"""
        if packet.get("cmd", "") == "LOOKUP_CALL":
            if self.look_up:
                call = packet.get("call", "")
                if call:
                    result = self.look_up.lookup(call)
                    cmd = {}
                    cmd["cmd"] = "LOOKUP_RESPONSE"
                    cmd["result"] = result
                    self.message.emit(cmd)
            return

        if packet.get("cmd", "") == "REFRESH_LOOKUP":
            self.settings = self.get_settings()
            self.look_up = None
            if self.settings.get("useqrz"):
                self.look_up = QRZlookup(
                    self.settings.get("lookupusername", ""),
                    self.settings.get("lookuppassword", ""),
                )

            if self.settings.get("usehamqth"):
                self.look_up = HamQTH(
                    self.settings.get("lookupusername", ""),
                    self.settings.get("lookuppassword", ""),
                )
