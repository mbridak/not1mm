#!/usr/bin/env python3

"""
Not1MM Contest logger
Email: michael.bridak@gmail.com
GPL V3
"""

# pylint: disable=unused-import, c-extension-no-member, no-member, invalid-name, too-many-lines
# pylint: disable=logging-fstring-interpolation, line-too-long, no-name-in-module

import datetime
import logging

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QEventLoop
from not1mm.lib.cat_interface import CAT

logger = logging.getLogger("cat_interface")


class Radio(QObject):
    """Radio class"""

    poll_callback = pyqtSignal(dict)

    cat = None
    vfoa = "14030000"
    mode = "CW"
    bw = "500"
    delta = 1
    poll_time = datetime.datetime.now() + datetime.timedelta(seconds=delta)
    time_to_quit = False
    online = False
    interface = None
    host = None
    port = None
    modes = ""
    last_data_mode = "RTTY"

    def __init__(self, interface: str, host: str, port: int) -> None:
        super().__init__()
        """setup interface"""
        self.interface = interface
        self.host = host
        self.port = port

    def run(self):
        try:
            self.cat = CAT(self.interface, self.host, self.port)
            self.online = self.cat.online
            self.modes = self.cat.get_mode_list()
        except ConnectionResetError:
            ...
        while not self.time_to_quit:
            if datetime.datetime.now() > self.poll_time:
                self.poll_time = datetime.datetime.now() + datetime.timedelta(
                    seconds=self.delta
                )
                vfoa = self.cat.get_vfo()
                self.online = False
                if vfoa:
                    if not vfoa.isnumeric():
                        logger.debug(f"Bad VFOA data {vfoa=}")
                        continue
                    self.vfoa = vfoa
                    self.online = True
                mode = self.cat.get_mode()
                if mode:
                    self.mode = mode
                    self.store_last_data_mode(mode)
                    self.online = True
                bw = self.cat.get_bw()
                if bw:
                    self.bw = bw
                    self.online = True
                try:
                    self.poll_callback.emit(
                        {
                            "vfoa": self.vfoa,
                            "mode": self.mode,
                            "bw": self.bw,
                            "online": self.online,
                        }
                    )
                except QEventLoop:
                    ...
            QThread.msleep(100)

    def store_last_data_mode(self, the_mode: str = ""):
        """if the last mode is a data mode, save it."""
        # QMX ['CW-U', 'CW-L', 'DIGI-U', 'DIGI-L']
        # 7300 ['LSB', 'USB', 'AM', 'FM', 'CW', 'CW-R', 'RTTY', 'RTTY-R', 'LSB-D', 'USB-D', 'AM-D', 'FM-D']
        datamodes = [
            "RTTY",
            "RTTY-R",
            "LSB-D",
            "USB-D",
            "AM-D",
            "FM-D",
            "DIGI-U",
            "DIGI-L",
            "RTTYR",
            "PKTLSB",
            "PKTUSB",
        ]
        if the_mode in datamodes:
            self.last_data_mode = the_mode

    def sendcw(self, texttosend):
        """..."""
        logger.debug(f"Send CW: {texttosend}")
        if self.cat:
            self.cat.sendcw(texttosend)

    def set_vfo(self, vfo):
        self.vfoa = vfo

        if self.cat:
            self.cat.set_vfo(vfo)

        self.poll_time = datetime.datetime.now()
        # try:
        #     self.poll_callback.emit(
        #         {
        #             "vfoa": str(self.vfoa),
        #             "mode": self.mode,
        #             "bw": self.bw,
        #             "online": self.online,
        #         }
        #     )
        # except RuntimeError:
        #     ...

    def set_mode(self, mode):
        self.mode = mode

        if self.cat:
            self.cat.set_mode(mode)

        self.poll_time = datetime.datetime.now()
        # try:
        #     self.poll_callback.emit(
        #         {
        #             "vfoa": str(self.vfoa),
        #             "mode": self.mode,
        #             "bw": self.bw,
        #             "online": self.online,
        #         }
        #     )
        # except RuntimeError:
        #     ...

    def get_modes(self):
        """get list of modes"""
        return self.modes

    def get_last_data_mode(self):
        """gets last used data mode."""
        return self.last_data_mode

    def ptt_on(self):
        if self.cat:
            self.cat.ptt_on()

    def ptt_off(self):
        if self.cat:
            self.cat.ptt_off()
