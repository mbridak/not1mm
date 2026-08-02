"""
K6GTE, CAT interface abstraction
Email: michael.bridak@gmail.com
GPL V3

TCI backend, for SDRs such as AetherSDR and ExpertSDR.

Unlike flrig and rigctld, nothing here queries the radio. TCI pushes state
changes and TCIClient caches them, so the getters are cache reads: instant,
non-blocking, and fresher than a poll would be.
"""

import logging

from not1mm.lib.cat_interface import CAT
from not1mm.lib.tci_client import TCIClient
from not1mm.lib.tci_protocol import build_command, not1mm_mode_to_tci

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("cat_tci")

# Long enough for a local SDR's handshake, short enough not to stall startup.
READY_TIMEOUT_MS = 1500


class TciCAT(CAT):
    """CAT control via the TCI protocol"""

    def __init__(self, host: str, port: int) -> None:
        """
        Computer Aided Transceiver abstraction class.
        Offers a normalized interface; this is the TCI class.

        Takes 2 inputs to setup the class.

        A string defining the host, example: 'localhost' or '127.0.0.1'

        An integer defining the network port used. Commonly 50001 for TCI.

        A variable 'online' is set to True once the TCI server completes its
        handshake, otherwise False.
        """
        super().__init__(host, port)
        self.interface = "tci"
        self.client = TCIClient(host, port)
        # Radio.__init__ reads get_mode_list() immediately, so give the
        # handshake a moment to land before returning.
        self.client.wait_for_ready(READY_TIMEOUT_MS)

    @property
    def online(self) -> bool:
        """True once the TCI server has completed its handshake.

        Reads straight through to the transport rather than caching, so a
        server that dies is reflected immediately instead of only after the
        next getter call happens to refresh a stale flag.
        """
        return self.client.online

    @online.setter
    def online(self, _value: bool) -> None:
        """No-op: CAT.__init__ does `self.online = False`, which would raise
        against a read-only property. Swallow that one assignment; `online`
        itself always reads through to the client."""

    # ---- getters ----
    # Offline returns "" rather than cached values: Radio only overwrites on a
    # truthy result, so "" holds the last known reading and reports offline.
    # Returning stale cache would paint a dead radio as live.

    def get_vfo(self) -> str:
        """Poll the radio for current vfo using the interface"""
        if not self.online:
            return ""
        return self.client.get("vfo", "")

    def get_mode(self) -> str:
        """Returns the current mode of the radio"""
        if not self.online:
            return ""
        return self.client.get("mode", "")

    def get_bw(self) -> str:
        """Get current vfo bandwidth"""
        if not self.online:
            return ""
        return self.client.get("bw", "")

    def get_ptt(self) -> str:
        """Get PTT state"""
        if not self.online:
            return "0"
        return self.client.get("ptt", "0")

    def get_mode_list(self) -> list:
        """Get a list of modes supported by the radio.

        Served even while offline: it is a device capability captured at
        handshake, and Radio caches it once at construction.
        """
        return self.client.get("modes", [])

    # ---- setters ----

    def set_vfo(self, freq: str) -> bool:
        """Sets the radios VFO. Defaults to VFOA."""
        if not self.online:
            return False
        self.client.send(build_command("vfo", 0, 0, str(freq)))
        return True

    def set_mode(self, mode: str) -> bool:
        """Sets the radios mode"""
        if not self.online:
            return False
        self.client.send(build_command("modulation", 0, not1mm_mode_to_tci(mode)))
        return True

    def ptt_on(self) -> bool:
        """turn ptt on"""
        if not self.online:
            return False
        self.client.send(build_command("trx", 0, "true"))
        return True

    def ptt_off(self) -> bool:
        """turn ptt off"""
        if not self.online:
            return False
        self.client.send(build_command("trx", 0, "false"))
        return True

    # ---- CW, reached via the existing "CW via CAT" option (cwtype == 3) ----

    def sendcw(self, texttosend) -> None:
        """Send CW text through the radio's keyer"""
        if not self.online:
            return
        # self.client.send(build_command("cw_msg", 0, "", "", texttosend))
        self.client.send(build_command("cw_macros", 0, texttosend))

    def stopcw(self) -> None:
        """Abort CW transmission"""
        if not self.online:
            return
        self.client.send(build_command("cw_terminate"))
        self.client.send(build_command("cw_macros_stop"))

    def set_cw_speed(self, speed: int) -> None:
        """Set the CW speed in wpm"""
        if not self.online:
            return
        self.client.send(build_command("cw_macros_speed", int(speed)))

    def close(self) -> None:
        """Shut down the transport thread. Radio.run() calls this on exit."""
        self.client.close()
