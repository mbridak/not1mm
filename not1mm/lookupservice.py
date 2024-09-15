#!/usr/bin/env python3
"""
not1mm Contest logger
Email: michael.bridak@gmail.com
GPL V3
Class: BandMapWindow
Purpose: Onscreen widget to show realtime spots from an AR cluster.
"""

# pylint: disable=unused-import, c-extension-no-member, no-member, invalid-name, too-many-lines
# pylint: disable=logging-fstring-interpolation, line-too-long, no-name-in-module

import logging
import os
import platform
from json import loads

from PyQt6.QtWidgets import QDockWidget

import not1mm.fsutils as fsutils
from not1mm.lib.multicast import Multicast
from not1mm.lib.lookup import QRZlookup, HamQTH

logger = logging.getLogger(__name__)


class LookupService(QDockWidget):
    """The Lookup Service class."""

    multicast_interface = None

    def __init__(self):
        super().__init__()
        self._udpwatch = None

        self.look_up = None
        self.settings = self.get_settings()
        if self.settings:

            if self.settings.get("useqrz"):
                self.look_up = QRZlookup(
                    self.settings.get("lookupusername"),
                    self.settings.get("lookuppassword"),
                )

            if self.settings.get("usehamqth"):
                self.look_up = HamQTH(
                    self.settings.get("lookupusername"),
                    self.settings.get("lookuppassword"),
                )

            self.multicast_interface = Multicast(
                self.settings.get("multicast_group", "239.1.1.1"),
                self.settings.get("multicast_port", 2239),
                self.settings.get("interface_ip", "0.0.0.0"),
            )
            self.multicast_interface.ready_read_connect(self.watch_udp)

    def get_settings(self) -> dict:
        """Get the settings."""
        if os.path.exists(fsutils.CONFIG_FILE):
            with open(fsutils.CONFIG_FILE, "rt", encoding="utf-8") as file_descriptor:
                return loads(file_descriptor.read())

    def watch_udp(self):
        """doc"""
        while self.multicast_interface.server_udp.hasPendingDatagrams():
            packet = self.multicast_interface.read_datagram_as_json()

            if packet.get("station", "") != platform.node():
                continue
            if packet.get("cmd", "") == "LOOKUP_CALL":
                if self.look_up:
                    call = packet.get("call", "")
                    if call:
                        result = self.look_up.lookup(call)
                        cmd = {}
                        cmd["cmd"] = "LOOKUP_RESPONSE"
                        cmd["station"] = platform.node()
                        cmd["result"] = result
                        self.multicast_interface.send_as_json(cmd)
                continue

            if packet.get("cmd", "") == "REFRESH_LOOKUP":
                self.settings = self.get_settings()
                self.look_up = None
                if self.settings.get("useqrz"):
                    self.look_up = QRZlookup(
                        self.settings.get("lookupusername"),
                        self.settings.get("lookuppassword"),
                    )

                if self.settings.get("usehamqth"):
                    self.look_up = HamQTH(
                        self.settings.get("lookupusername"),
                        self.settings.get("lookuppassword"),
                    )
