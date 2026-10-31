"""
Not1MM Contest logger
Email: michael.bridak@gmail.com
GPL V3
"""

import datetime
import logging
import time

from PyQt6.QtCore import QEventLoop, QObject, QThread, pyqtSignal

from not1mm.lib.cat_fake import FakeCAT
from not1mm.lib.cat_flrig import FlrigCAT
from not1mm.lib.cat_rigctld import RigctldCAT
from not1mm.lib.cat_tci import TciCAT

logger = logging.getLogger("radio")


class Radio(QObject):
    """Radio class"""

    poll_callback = pyqtSignal(dict)
    vfoa = "14030000"
    mode = "CW"
    bw = "500"
    delta = 500
    poll_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        milliseconds=delta
    )
    time_to_quit = False
    online = False
    interface = None
    host = None
    port = None
    modes = ""
    cw_list = ["CW", "CW-L", "CW-U", "CWR", "CW-R"]  # noqa: RUF012
    rtty_list = [  # noqa: RUF012
        "RTTY",
        "DIGI-L",
        "PKTLSB",
        "LSB-D",
    ]
    last_data_mode = "RTTY"
    vfo_set_at = 0.0
    last_cw_mode = "CW"
    last_ph_mode = "SSB"

    def __init__(
        self, interface: str, host: str, port: int, tci_trx: int = 0
    ) -> None:
        super().__init__()
        """setup interface"""
        self.interface = interface
        self.host = host
        self.port = port
        self.tci_trx = tci_trx
        logger.debug("Using %s: %s %d", interface, host, port)

        try:
            if self.interface == "flrig":
                self.cat = FlrigCAT(self.host, self.port)
            elif self.interface == "rigctld":
                self.cat = RigctldCAT(self.host, self.port)
            elif self.interface == "tci":
                self.cat = TciCAT(self.host, self.port, self.tci_trx)
            else:
                self.cat = FakeCAT(self.host, self.port)
            self.online = self.cat.online
            self.modes = self.cat.get_mode_list()
            for pos_cw in self.cw_list:
                if pos_cw in self.modes:
                    self.last_cw_mode = pos_cw
                    break
            for pos_rtty in self.rtty_list:
                if pos_rtty in self.modes:
                    self.last_data_mode = pos_rtty
                    break
        except ConnectionResetError:
            ...

    def run(self):
        while not self.time_to_quit:
            if datetime.datetime.now(datetime.UTC) > self.poll_time:
                self.poll_time = datetime.datetime.now(
                    datetime.UTC
                ) + datetime.timedelta(milliseconds=self.delta)
                # Captured before reading, so a trx swap mid-poll tags these
                # readings with the trx they actually came from.
                polled_trx = getattr(self.cat, "trx", None)
                polled_at = time.monotonic()
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
                            "online": self.cat.online,
                            # Lets the main window drop a poll that was
                            # queued before a TCI trx swap and lands after.
                            "trx": polled_trx,
                            # Lets the main window drop a poll that was read
                            # before its own set_vfo but delivered after it.
                            "polled_at": polled_at,
                        }
                    )
                except QEventLoop:
                    ...
            QThread.msleep(100)
        # Backends owning their own threads (TCI) must be torn down here, or
        # the app hangs on exit. The others have no close() and no-op.
        close = getattr(self.cat, "close", None)
        if close is not None:
            close()

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
            "FSK",
            "DIGI-U",
            "DIGI-L",
            "RTTYR",
            "PKTLSB",
            "PKTUSB",
        ]
        if the_mode in datamodes:
            self.last_data_mode = the_mode

        cwmodes = ["CW", "CW-L", "CW-U", "CWR"]

        if the_mode in cwmodes:
            self.last_cw_mode = the_mode

    def sendvoicememory(self, memoryspot=1):
        """..."""
        if self.cat:
            self.cat.sendvoicememory(memoryspot)

    def sendcw(self, texttosend, trx=None):
        """..."""
        logger.debug(f"Send CW: {texttosend}")
        if self.cat:
            if trx is None:
                self.cat.sendcw(texttosend)
            else:
                self.cat.sendcw(texttosend, trx=trx)

    def stopcw(self):
        logger.debug("Stopping CW")
        if self.cat:
            self.cat.stopcw()

    def set_cw_speed(self, speed):
        logger.debug("Setting CW speed %d", speed)
        if self.cat:
            self.cat.set_cw_speed(speed)

    def set_cw_send(self, send: bool) -> None:
        logger.debug("Setting CW send %s", send)
        if self.cat:
            self.cat.set_cw_send(send)

    def set_rx_audio(self, trx: int, pan: int, mute: bool) -> bool:
        """Per-trx receive pan/mute, for backends that support it (TCI)."""
        set_audio = getattr(self.cat, "set_rx_audio", None)
        return bool(set_audio and set_audio(trx, pan, mute))

    def set_tci_trx(self, trx: int) -> bool:
        """Switch the TCI backend to another transceiver. Returns False for
        backends that have no notion of trx."""
        set_trx = getattr(self.cat, "set_trx", None)
        if set_trx is None:
            return False
        self.tci_trx = int(trx)
        set_trx(self.tci_trx)
        # Drop the previous trx's cached readings so the next poll carries the
        # new trx's state rather than holding the old one on a falsy getter.
        self.vfoa = self.cat.get_vfo() or self.vfoa
        self.mode = self.cat.get_mode() or self.mode
        self.bw = self.cat.get_bw() or self.bw
        self.poll_time = datetime.datetime.now(datetime.UTC)
        return True

    def set_vfo(self, vfo):
        self.vfoa = vfo
        self.vfo_set_at = time.monotonic()

        if self.cat:
            self.cat.set_vfo(vfo)

        self.poll_time = datetime.datetime.now(datetime.UTC)

    def set_mode(self, mode):
        self.mode = mode
        if self.cat:
            self.cat.set_mode(mode)
        self.poll_time = datetime.datetime.now(datetime.UTC)

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

    def get_ptt(self):
        """Get PTT state from radio"""
        if self.cat:
            return self.cat.get_ptt()
        return 0
