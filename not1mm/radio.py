#!/usr/bin/env python3

"""
Not1MM Contest logger
Email: michael.bridak@gmail.com
GPL V3
"""

# pylint: disable=unused-import, c-extension-no-member, no-member, invalid-name, too-many-lines
# pylint: disable=logging-fstring-interpolation, line-too-long, no-name-in-module

import datetime

from PyQt6.QtCore import QObject, pyqtSignal
from not1mm.lib.cat_interface import CAT


class Radio(QObject):
    """Radio class"""

    poll_callback = pyqtSignal(dict)

    cat = None
    vfoa = "14030000"
    mode = "CW"
    bw = "500"
    delta = 10
    poll_time = datetime.datetime.now() + datetime.timedelta(seconds=delta)
    time_to_quit = False
    online = False

    def __init__(self, interface: str, host: str, port: int) -> None:
        super().__init__()
        """setup interface"""
        self.cat = CAT(interface, host, port)

    def run(self):
        while not self.time_to_quit:
            if datetime.datetime.now() > self.poll_time:
                self.poll_time = datetime.datetime.now() + datetime.timedelta(
                    seconds=self.delta
                )
                vfoa = self.cat.get_vfo()
                self.online = False
                if vfoa:
                    self.vfoa = vfoa
                    self.online = True
                mode = self.cat.get_mode()
                if mode:
                    self.mode = mode
                    self.online = True
                bw = self.cat.get_bw()
                if bw:
                    self.bw = bw
                    self.online = True
                self.poll_callback.emit(
                    {
                        "vfoa": self.vfoa,
                        "mode": self.mode,
                        "bw": self.bw,
                        "online": self.online,
                    }
                )

    def set_vfo(self, vfo):
        self.cat.set_vfo(vfo)
        self.vfoa = vfo

    def set_mode(self, mode):
        self.cat.set_mode(mode)
        self.mode = mode

    def ptt_on(self):
        self.cat.ptt_on()

    def ptt_off(self):
        self.cat.ptt_off()

    # if self.pref.get("userigctld", False):
    #     logger.debug(
    #         "Using rigctld: %s",
    #         f"{self.pref.get('CAT_ip')} {self.pref.get('CAT_port')}",
    #     )
    #     self.rig_control = CAT(
    #         "rigctld",
    #         self.pref.get("CAT_ip", "127.0.0.1"),
    #         int(self.pref.get("CAT_port", 4532)),
    #     )
