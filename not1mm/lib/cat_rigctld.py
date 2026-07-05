"""
K6GTE, CAT interface abstraction
Email: michael.bridak@gmail.com
GPL V3
"""

import logging
import socket
import os
from not1mm.lib.cat_interface import CAT

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("cat_interface")


class RigctldCAT(CAT):
    """CAT control via rigctld"""

    def __init__(self, host: str, port: int) -> None:
        """
        Computer Aided Transceiver abstraction class.
        Offers a normalized interface; this is the rigctld class.

        Takes 2 inputs to setup the class.

        A string defining the host, example: 'localhost' or '127.0.0.1'

        An integer defining the network port used.
        Commonly 4532 for rigctld.

        A variable 'online' is set to True if no error was encountered,
        otherwise False.
        """
        super().__init__(host, port)
        self.rigctrlsocket = None
        self.rigctld_bw = "0"
        self.interface = "rigctld"
        self.__initialize_rigctrld()

    def __initialize_rigctrld(self):
        try:
            logger.debug("Connecting to rigctrld %s %d", self.host, self.port)
            self.rigctrlsocket = socket.socket()
            self.rigctrlsocket.settimeout(1.0)
            self.rigctrlsocket.connect((self.host, self.port))
            logger.debug("Connected to rigctrld")
            self.online = True
        except (
            ConnectionRefusedError,
            TimeoutError,
            OSError,
            socket.error,
            socket.gaierror,
        ) as exception:
            self.rigctrlsocket = None
            self.online = False
            logger.debug("%s", f"{exception}")

    def reinit(self):
        """reinitialise rigctl"""
        self.__initialize_rigctrld()

    def __get_serial_string(self):
        """Gets any serial data waiting"""
        dump = ""
        thegrab = ""
        if self.rigctrlsocket is None:
            return ""
        if hasattr(self.rigctrlsocket, "settimeout"):
            self.rigctrlsocket.settimeout(0.1)
            try:
                while True and hasattr(self.rigctrlsocket, "recv"):
                    thegrab = self.rigctrlsocket.recv(1024).decode()
                    dump += thegrab
                    if thegrab == "":
                        break
            except (socket.error, UnicodeDecodeError):
                ...
            # self.rigctrlsocket.settimeout(0.1)
        # logger.debug("%s", dump)
        if os.environ.get("SEERIGCTLD", False):
            print(repr(dump))
        return dump

    def sendvoicememory(self, memoryspot=1):
        """..."""
        return self.__sendvoicememory_rigctld(memoryspot)

    def __sendvoicememory_rigctld(self, memoryspot=1):
        """..."""
        try:
            self.online = True
            self.rigctrlsocket.send(bytes(f"+\\send_voice_mem {memoryspot}\n", "utf-8"))
            info = self.__get_serial_string()
            logger.debug("%s", info)
            return
        except socket.error as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
            self.rigctrlsocket = None
            return

    def sendcw(self, texttosend):
        """..."""
        logger.debug(f"{texttosend=} {self.interface=}")
        self.sendcwrigctl(texttosend)

    def sendcwrigctl(self, texttosend):
        """Send text via rigctld"""
        if self.rigctrlsocket is not None:
            try:
                self.online = True
                if hasattr(self.rigctrlsocket, "send"):
                    self.rigctrlsocket.send(bytes(f"b {texttosend}\n", "utf-8"))
                else:
                    self.rigctrlsocket = None
                    self.online = False
                    return False
                info = self.__get_serial_string()
                logger.debug("%s", info)
                return True
            except socket.error as exception:
                self.online = False
                logger.debug("setvfo_rigctld: %s", f"{exception}")
                self.rigctrlsocket = None
                return False
        self.__initialize_rigctrld()
        return False

    def stopcw(self):
        """Stop CW via rigctld"""
        if self.rigctrlsocket is not None:
            try:
                self.online = True
                if hasattr(self.rigctrlsocket, "send"):
                    self.rigctrlsocket.send(bytes("\\stop_morse\n", "utf-8"))
                else:
                    self.rigctrlsocket = None
                    self.online = False
                    return False
                _ = self.__get_serial_string()
                return True
            except socket.error as exception:
                self.online = False
                logger.debug("setvfo_rigctld: %s", f"{exception}")
                self.rigctrlsocket = None
                return False
        self.__initialize_rigctrld()
        return False

    def set_cw_speed(self, speed):
        """Set CW speed via rigctld"""
        if self.rigctrlsocket is not None:
            try:
                self.online = True
                if hasattr(self.rigctrlsocket, "send"):
                    self.rigctrlsocket.send(bytes(f"L KEYSPD {speed}\n", "utf-8"))
                else:
                    self.rigctrlsocket = None
                    self.online = False
                    return
                info = self.__get_serial_string()
                logger.debug("%s", info)
                return
            except socket.error as exception:
                self.online = False
                logger.debug("set_level_rigctld: %s", f"{exception}")
                self.rigctrlsocket = None
                return
        self.__initialize_rigctrld()

    def get_vfo(self) -> str:
        """Poll the radio for current vfo using the interface"""
        vfo = self.__getvfo_rigctld()
        if "RPRT -" in vfo:
            vfo = ""
        return vfo

    def __getvfo_rigctld(self) -> str:
        """Returns VFO freq returned from rigctld"""
        if self.rigctrlsocket is not None:
            try:
                self.online = True
                if hasattr(self.rigctrlsocket, "send"):
                    self.rigctrlsocket.send(b"|f\n")
                else:
                    self.rigctrlsocket = None
                    self.online = False
                    return ""
                report = self.__get_serial_string().strip()
                logger.debug("%s", report)
                if report.startswith("get_freq:|") and "RPRT 0" in report:
                    seg_rpt = report.split("|")
                    freq_str = seg_rpt[1].split(" ")[1]
                    return str(int(float(freq_str)))
            except (socket.error, IndexError, ValueError) as exception:
                self.online = False
                logger.debug(f"{exception=}")
                self.rigctrlsocket = None
            return ""

        self.__initialize_rigctrld()
        return ""

    def get_mode(self) -> str:
        """Returns the current mode filter width of the radio"""
        # QMX 'DIGI-U DIGI-L CW-U CW-L' or 'LSB', 'USB', 'CW', 'FM', 'AM', 'FSK'
        # 7300 'AM CW USB LSB RTTY FM CWR RTTYR PKTLSB PKTUSB FM-D AM-D'
        if self.rigctrlsocket is not None:
            try:
                self.online = True
                if hasattr(self.rigctrlsocket, "send"):
                    self.rigctrlsocket.send(b"|m\n")
                else:
                    self.rigctrlsocket = None
                    self.online = False
                    return ""
                # get_mode:|Mode: CW|Passband: 500|RPRT 0
                report = self.__get_serial_string().strip()
                logger.debug("%s", report)
                if report.startswith("get_mode:|") and "RPRT 0" in report:
                    seg_rpt = report.split("|")
                    self.rigctld_bw = seg_rpt[2].split(" ")[1]
                    return seg_rpt[1].split(" ")[1]
            except IndexError as exception:
                logger.debug("%s", f"{exception}")
            except socket.error as exception:
                self.online = False
                logger.debug("%s", f"{exception}")
                self.rigctrlsocket = None
            return ""
        self.__initialize_rigctrld()
        return ""

    def get_bw(self):
        """Get current vfo bandwidth"""
        return self.rigctld_bw

    def get_power(self):
        """Get power level from rig"""
        if self.rigctrlsocket is not None:
            try:
                self.online = True
                if hasattr(self.rigctrlsocket, "send"):
                    self.rigctrlsocket.send(b"|l RFPOWER\n")
                else:
                    self.rigctrlsocket = None
                    self.online = False
                    return ""
                # get_level: RFPOWER|0.000000|RPRT 0
                report = self.__get_serial_string().strip()
                logger.debug("%s", report)
                if "get_level: RFPOWER|" in report and "RPRT 0" in report:
                    seg_rpt = report.split("|")
                    return int(float(seg_rpt[1]) * 100)
            except socket.error as exception:
                self.online = False
                logger.debug("getpower_rigctld: %s", f"{exception}")
                self.rigctrlsocket = None
            return ""

    def get_ptt(self):
        """Get PTT state"""
        if self.rigctrlsocket is not None:
            try:
                self.online = True
                if hasattr(self.rigctrlsocket, "send"):
                    self.rigctrlsocket.send(b"t\n")
                else:
                    self.rigctrlsocket = None
                    self.online = False
                    return "0"
                ptt = self.__get_serial_string()
                logger.debug("%s", ptt)
                ptt = ptt.strip()
                return ptt
            except socket.error as exception:
                self.online = False
                logger.debug("%s", f"{exception}")
                self.rigctrlsocket = None
        return "0"

    def get_mode_list(self):
        "Get a list of modes supported by the radio"
        # Mode list: AM CW USB LSB RTTY FM CWR RTTYR
        if self.rigctrlsocket:
            try:
                self.online = True
                if hasattr(self.rigctrlsocket, "send"):
                    self.rigctrlsocket.send(b"1\n")
                else:
                    self.rigctrlsocket = None
                    self.online = False
                    return ""
                dump = self.__get_serial_string()
                for line in dump.splitlines():
                    if "Mode list:" in line:
                        modes = line.split(":")[1].strip()
                        return modes
                return ""
            except socket.error as exception:
                self.online = False
                logger.debug("%s", f"{exception}")
                self.rigctrlsocket = None
        return ""

    def set_vfo(self, freq: str) -> bool:
        """Sets the radios vfo"""
        try:
            return self.__setvfo_rigctld(freq)
        except ValueError:
            ...
        return False

    def __setvfo_rigctld(self, freq: str) -> bool:
        """sets the radios vfo"""
        if self.rigctrlsocket is not None:
            try:
                self.online = True
                if hasattr(self.rigctrlsocket, "send"):
                    self.rigctrlsocket.send(bytes(f"|F {freq}\n", "utf-8"))
                else:
                    self.rigctrlsocket = None
                    self.online = False
                    return False
                info = self.__get_serial_string()
                logger.debug("%s", info)
                return True
            except socket.error as exception:
                self.online = False
                logger.debug("setvfo_rigctld: %s", f"{exception}")
                self.rigctrlsocket = None
                return False
        self.__initialize_rigctrld()
        return False

    def set_mode(self, mode: str) -> bool:
        """Sets the radios mode"""
        if self.rigctrlsocket:
            try:
                self.online = True
                # logger.debug(f"\nM {mode} 0\n")
                if hasattr(self.rigctrlsocket, "send"):
                    self.rigctrlsocket.send(bytes(f"\n|M {mode} 0\n", "utf-8"))
                else:
                    self.rigctrlsocket = None
                    self.online = False
                    return False
                info = self.__get_serial_string()
                logger.debug("%s", info)
                return True
            except socket.error as exception:
                self.online = False
                logger.debug("setmode_rigctld: %s", f"{exception}")
                self.rigctrlsocket = None
                return False
        self.__initialize_rigctrld()
        return False

    def set_power(self, power):
        """Sets the radios power"""
        if power.isnumeric() and int(power) >= 1 and int(power) <= 100:
            rig_cmd = bytes(f"|L RFPOWER {str(float(power) / 100)}\n", "utf-8")
            try:
                self.online = True
                if hasattr(self.rigctrlsocket, "send"):
                    self.rigctrlsocket.send(rig_cmd)
                else:
                    self.rigctrlsocket = None
                    self.online = False
                    return
                info = self.__get_serial_string()
                logger.debug("%s", info)
            except socket.error:
                self.online = False
                self.rigctrlsocket = None

    def ptt_on(self):
        """turn ptt on/off"""

        # T, set_ptt 'PTT'
        # Set 'PTT'.
        # PTT is a value: ‘0’ (RX), ‘1’ (TX), ‘2’ (TX mic), or ‘3’ (TX data).

        # t, get_ptt
        # Get 'PTT' status.
        # Returns PTT as a value in set_ptt above.

        rig_cmd = bytes("|T 1\n", "utf-8")
        logger.debug("%s", f"{rig_cmd}")
        try:
            self.online = True
            if hasattr(self.rigctrlsocket, "send"):
                self.rigctrlsocket.send(rig_cmd)
            else:
                self.rigctrlsocket = None
                self.online = False
                return
            info = self.__get_serial_string()
            logger.debug("%s", info)
        except socket.error:
            self.online = False
            self.rigctrlsocket = None

    def ptt_off(self):
        """turn ptt on/off"""
        rig_cmd = bytes("|T 0\n", "utf-8")
        logger.debug("%s", f"{rig_cmd}")
        try:
            self.online = True
            if hasattr(self.rigctrlsocket, "send"):
                self.rigctrlsocket.send(rig_cmd)
            else:
                self.rigctrlsocket = None
                self.online = False
                return
            into = self.__get_serial_string()
            logger.debug("%s", into)
        except socket.error:
            self.online = False
            self.rigctrlsocket = None

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

        return self.__send_cat_string_rigctld(working, ishex)

    def __send_cat_string_rigctld(self, cmd, thisishex):
        """convert string to rigctld format, send to rigctld"""
        if not self.rigctrlsocket:
            return 0
        if thisishex:
            # make string "\0x" delimited for rigctld
            cmd = cmd.replace(" ", "\\0x")
            cmd = "|w \\0x" + cmd
        else:
            cmd = "|w " + cmd
        bcmd = bytes(cmd, "utf-8")
        logger.debug("%s", f"Sending rig command: [{bcmd}]")

        try:
            if hasattr(self.rigctrlsocket, "send"):
                self.rigctrlsocket.send(bcmd)
        except socket.error:
            logger.debug("Socket error!")
            self.online = False
            self.rigctrlsocket = None
            return 0
