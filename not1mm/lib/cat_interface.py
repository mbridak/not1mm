"""
K6GTE, CAT interface abstraction
Email: michael.bridak@gmail.com
GPL V3
"""

import logging

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("cat_interface")


class CAT:
    """CAT control base class"""

    def __init__(self, host: str, port: int) -> None:
        """
        Computer Aided Transceiver abstraction class.
        Offers a normalized interface; this is the base class.

        Takes 2 inputs to setup the class.

        A string defining the host, example: 'localhost' or '127.0.0.1'

        An integer defining the network port used.
        Commonly 12345 for flrig, or 4532 for rigctld.

        Exposed methods are:

        reinit()
        get_vfo() set_vfo()
        get_mode() set_mode()
        get_power() set_power()
        get_ptt() ptt_on() ptt_off()
        sendcw() stopcw() set_cw_speed() set_cw_send()

        A variable 'online' is set to True if no error was encountered,
        otherwise False.
        """
        self.interface = ""
        self.host = host
        self.port = port
        self.online = False

    def reinit(self):
        """reinitialise rigctl"""

    def sendvoicememory(self, memoryspot=1):
        """..."""

    def sendcw(self, texttosend):
        """..."""

    def stopcw(self):
        """..."""

    def set_cw_send(self, send: bool) -> None:
        """Enable or disable the radio's CW keyer send flag."""

    def get_vfo(self) -> str:
        """Poll the radio for current vfo using the interface"""

    def get_mode(self) -> str:
        """Returns the current mode filter width of the radio"""

    def get_bw(self):
        """Get current vfo bandwidth"""

    def get_power(self):
        """Get power level from rig"""

    def get_ptt(self):
        """Get PTT state"""

    def get_mode_list(self):
        "Get a list of modes supported by the radio"

    def set_vfo(self, freq: str):
        """Sets the radios VFO. Defaults to VFOA."""

    def set_sync_vfos(self, sync_vfos: bool) -> bool:
        """Turn Sync VFOs on/off"""

    def set_mode(self, mode: str) -> bool:
        """Sets the radios mode"""

    def set_power(self, power):
        """Sets the radios power"""

    def ptt_on(self):
        """turn ptt on/off"""

    def ptt_off(self):
        """turn ptt on/off"""
