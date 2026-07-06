"""
K6GTE, CAT interface abstraction
Email: michael.bridak@gmail.com
GPL V3

rig.cwio_set_wpm          n:i  set cwio WPM
rig.cwio_text             i:s  send text via cwio interface
rig.cwio_send             n:i  cwio transmit 1/0 (on/off)
command lines to test the CW API via XMLRPC

Setting WPM
curl -d "<?xml version='1.0'?><methodCall><methodName>rig.cwio_set_wpm</methodName><params><param><value><i4>28</i4></value></param></params></methodCall>" http://localhost:12345

Setting the text to send
curl -d "<?xml version='1.0'?><methodCall><methodName>rig.cwio_text</methodName><params><param><value><string>test test test</string></value></param></params></methodCall>" http://localhost:12345

Enable send
curl -d "<?xml version='1.0'?><methodCall><methodName>rig.cwio_send</methodName><params><param><value><i4>1</i4></value></param></params></methodCall>" http://localhost:12345
"""

import logging
import socket
import xmlrpc.client
import http
import os
from not1mm.lib.cat_interface import CAT

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("cat_flrig")


class FlrigCAT(CAT):
    """CAT control via flrig"""

    def __init__(self, host: str, port: int) -> None:
        """
        Computer Aided Transceiver abstraction class.
        Offers a normalized interface; this is the flrig class.

        Takes 2 inputs to setup the class.

        A string defining the host, example: 'localhost' or '127.0.0.1'

        An integer defining the network port used.
        Commonly 12345 for flrig.

        A variable 'online' is set to True if no error was encountered,
        otherwise False.
        """
        super().__init__(host, port)
        self.server = None
        self.interface = "flrig"

        target = f"http://{self.host}:{self.port}"
        logger.debug("%s", target)
        self.server = xmlrpc.client.ServerProxy(target)
        self.online = True
        try:
            _ = self.server.main.get_version()
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            socket.error,
            socket.gaierror,
            TimeoutError,
            OSError,
        ):
            self.online = False

    def sendcw(self, texttosend):
        """..."""
        logger.debug(f"{texttosend=} {self.interface=}")
        self.sendcwxmlrpc(texttosend)

    def sendcwxmlrpc(self, texttosend):
        """Add text to flrig's cw send buffer."""
        logger.debug(f"{texttosend=}")
        try:
            self.online = True
            self.server.rig.cwio_text(texttosend)
            return
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        return False

    def stopcw(self):
        self.set_cw_send(False)
        self.set_cw_send(True)

    def set_cw_send(self, send: bool) -> None:
        """Turn on flrig cw keyer send flag."""
        try:
            self.online = True
            self.server.rig.cwio_send(int(send))
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            ValueError,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("%s", f"{exception}")

    def set_cw_speed(self, speed):
        """Set flrig's CW send speed"""
        try:
            self.online = True
            self.server.rig.cwio_set_wpm(int(speed))
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            ValueError,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("%s", f"{exception}")

    def get_vfo(self) -> str:
        """Poll the radio for current vfo using the interface"""
        try:
            self.online = True
            vfo_value = self.server.rig.get_vfo()
            logger.debug(f"{vfo_value=}")
            return vfo_value
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            AttributeError,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug(f"{exception=}")
        return ""

    def get_mode(self) -> str:
        """Returns the current mode filter width of the radio"""
        # QMX ['CW-U', 'CW-L', 'DIGI-U', 'DIGI-L']
        # 7300 ['LSB', 'USB', 'AM', 'FM', 'CW', 'CW-R', 'RTTY', 'RTTY-R', 'LSB-D', 'USB-D', 'AM-D', 'FM-D']
        try:
            self.online = True
            mode_value = self.server.rig.get_mode()
            logger.debug(f"{mode_value=}")
            return mode_value
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            AttributeError,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        return ""

    def get_bw(self):
        """Get current vfo bandwidth"""
        try:
            self.online = True
            bandwidth = self.server.rig.get_bw()
            logger.debug(f"{bandwidth=}")
            return bandwidth[0]
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            AttributeError,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("getbw_flrig: %s", f"{exception}")
            return ""

    def get_power(self):
        """Get power level from rig"""
        try:
            self.online = True
            return self.server.rig.get_power()
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("getpower_flrig: %s", f"{exception}")
            return ""

    def get_ptt(self):
        """Get PTT state"""
        try:
            self.online = True
            return self.server.rig.get_ptt()
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        return "0"

    def get_mode_list(self):
        "Get a list of modes supported by the radio"
        try:
            self.online = True
            mode_list = self.server.rig.get_modes()
            logger.debug(f"{mode_list=}")
            return mode_list
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            AttributeError,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        return ""

    def set_vfo(self, freq: str) -> bool:
        """Sets the radios vfo"""
        try:
            return self.__setvfo_flrig(freq)
        except ValueError:
            ...
        return False

    def __setvfo_flrig(self, freq: str) -> bool:
        """Sets the radios vfo"""
        try:
            self.online = True
            return self.server.rig.set_frequency(float(freq))
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            AttributeError,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("setvfo_flrig: %s", f"{exception}")
        return False

    def set_mode(self, mode: str) -> bool:
        """Sets the radios mode"""
        try:
            self.online = True
            logger.debug(f"{mode=}")
            set_mode_result = self.server.rig.set_mode(mode)
            logger.debug(f"self.server.rig.setmode(mode) = {set_mode_result}")
            return set_mode_result
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            AttributeError,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug(f"{exception=}")
        return False

    def set_power(self, power):
        """Sets the radios power"""
        try:
            self.online = True
            return self.server.rig.set_power(power)
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            AttributeError,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("setpower_flrig: %s", f"{exception}")
            return False

    def ptt_on(self):
        """turn ptt on/off"""
        try:
            self.online = True
            return self.server.rig.set_ptt(1)
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            AttributeError,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        return "0"

    def ptt_off(self):
        """turn ptt on/off"""
        try:
            self.online = True
            return self.server.rig.set_ptt(0)
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            AttributeError,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        return "0"

    def send_cat_string(self, cmdstr=""):
        """send a raw cat string to radio"""
        cmdstr = cmdstr.strip()
        test1 = cmdstr.replace(" ", "")
        if test1 == "":
            return True
        working = cmdstr
        test2 = [" ", " x", " X", "\\"]
        test3 = "0123456789ABCDEF "  # trailing space
        ishex = False
        # does this look like hex?
        for c2 in test2:
            if c2 in working:
                ishex = True
        if ishex:
            working = working.replace("x", "")
            working = working.replace("X", "")
            working = working.replace("\\", "")
            working = working.upper()
            # should be space-delimited now
            # any illegal chars?
            for c3 in working:
                if c3 not in test3:
                    logger.debug(f"Bad char in command string: [{cmdstr}]")
                    return True
            # hex checks out so far
            spacesok = True
            for i in range(len(working)):
                if (i + 1) % 3 == 0:  # every 3rd char
                    if working[i] != " ":
                        spacesok = False
            if not spacesok:
                logger.debug(f"Bad delimiters in cmd string: [{cmdstr}]")
                return True
        else:
            """not hex, but plain ascii text - do nothing"""

        return self.__send_cat_string_flrig(working, ishex)

    def __send_cat_string_flrig(self, cmd, thisishex):
        """convert string to flrig format, send to flrig"""
        if thisishex:
            # make string " x" delimited (again) for flrig
            cmd = "x" + cmd
            cmd = cmd.replace(" ", " x")
        else:
            """ascii - do nothing"""
        logger.debug("%s", f"Sending rig command: [{cmd}]")
        try:
            return self.server.rig.cat_string(cmd)
        except (
            ConnectionRefusedError,
            xmlrpc.client.Fault,
            http.client.BadStatusLine,
            http.client.CannotSendRequest,
            http.client.ResponseNotReady,
            AttributeError,
            TimeoutError,
            OSError,
        ) as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        return "0"
