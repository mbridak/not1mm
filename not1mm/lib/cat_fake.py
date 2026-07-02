"""
K6GTE, CAT interface abstraction
Email: michael.bridak@gmail.com
GPL V3
"""

import logging
import os
from not1mm.lib.cat_interface import CAT

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("cat_interface")


class FakeCAT(CAT):
    """CAT control fake radio for testing without a real rig"""

    def __init__(self, host: str, port: int) -> None:
        """
        Computer Aided Transceiver abstraction class.
        Offers a normalized interface; this is the "fake" class.

        Takes 2 inputs to setup the class.

        A string defining the host, example: 'localhost' or '127.0.0.1'

        An integer defining the network port used.
        Commonly 12345 for flrig, or 4532 for rigctld.

        A variable 'online' is always True.
        """
        super().__init__(host, port)
        self.interface = "fake"
        self.online = True
        self.fake_radio = {
            "vfo": "14032000",
            "mode": "CW",
            "bw": "500",
            "power": "100",
            "modes": ["CW", "USB", "LSB", "RTTY"],
            "ptt": False,
        }
        logger.debug("Using Fake Rig")

    def get_vfo(self) -> str:
        """Poll the radio for current vfo using the interface"""
        vfo = self.fake_radio.get("vfo", "")
        return vfo

    def get_mode(self) -> str:
        """Returns the current mode filter width of the radio"""
        mode = self.fake_radio.get("mode")
        return mode

    def get_bw(self):
        """Get current vfo bandwidth"""
        return self.fake_radio.get("bw")

    def get_power(self):
        """Get power level from rig"""
        return self.fake_radio.get("power", "100")

    def get_ptt(self):
        return self.fake_radio.get("ptt", False)

    def get_mode_list(self):
        "Get a list of modes supported by the radio"
        return self.fake_radio.get("modes")

    def set_vfo(self, freq: str) -> bool:
        try:
            self.fake_radio["vfo"] = str(freq)
            return True
        except ValueError:
            ...
        return False

    def set_mode(self, mode: str) -> bool:
        """Sets the radios mode"""
        self.fake_radio["mode"] = mode
        return True

    def set_power(self, power):
        """Sets the radios power"""
        self.fake_radio["power"] = str(power)
        return True

    def ptt_on(self):
        """turn ptt on/off"""
        self.fake_radio["ptt"] = True
        return True

    def ptt_off(self):
        """turn ptt on/off"""
        self.fake_radio["ptt"] = False
        return True
