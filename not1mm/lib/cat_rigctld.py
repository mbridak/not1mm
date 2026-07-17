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

logger = logging.getLogger("cat_rigctld")


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
        self.reinit()

    def reinit(self):
        """initialise rigctld

        This routine is called whenever the rig is initialized (startup,
        settings changed), and each rigctld_command() call will use it when the
        connection was lost in flight.

        Rigctld is set into "VFO mode" which requires a VFO argument in most
        commands ("f VFOA 1810000"). The advantage is this lets us get/set the
        inactive VFO without flickering the display.
        """
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
            logger.info("%s", f"{exception}")
        # turn on "VFO mode" so we can set/get VFO A/B directly (no automatic reinit here to avoid loop)
        self.rigctld_command("\\set_vfo_opt 1", auto_reinit=False)

    def rigctld_command(self, command: str, prefix="+", auto_reinit=True) -> str:
        """Send a command to rigctld and return the reply.

        The reply is expected to end with "RPRT N" which is guaranteed in the
        extended response protocol (prefix="+").
        """

        if (
            not self.online
            or self.rigctrlsocket is None
            or not hasattr(self.rigctrlsocket, "send")
        ):
            if auto_reinit:
                self.reinit()
        if not self.online:
            return ""
        try:
            logger.debug("> %s", command)
            self.rigctrlsocket.send(bytes(prefix + command + "\n", "utf-8"))
            report = ""
            while "RPRT" not in report:  # read until we get "RPRT X" from rigctld
                thegrab = self.rigctrlsocket.recv(1024).decode()
                if thegrab == "":  # socket closed
                    break
                report += thegrab
            logger.debug("< %s", report)
            return report
        except (TimeoutError, OSError, UnicodeDecodeError, socket.error) as exception:
            self.online = False
            logger.info("%s", f"{exception}")
            self.rigctrlsocket = None
        return ""

    def rigctld_parse(self, report: str) -> dict:
        """Parse a extended response protocol message (prefix +) into fields.

        +\\get_vfo_list
        get_vfo_list: currVFO
        VFOs: Sub Main MEM
        RPRT 0

        -> {"get_vfo_list": "currVFO", "VFOs": "Sub Main MEM"}

        +l VFOA RFPOWER
        get_level: VFOA:RFPOWER
        1
        RPRT 0

        If a line does not have a label, it is stored as "line":

        -> {"get_level": "VFOA:RFPOWER", "line": "1"}
        """

        fields = {}
        for line in report.splitlines():
            if ": " in line:
                k, _, v = line.partition(": ")
                fields[k] = v
            elif line.startswith("RPRT "):
                k, _, v = line.partition(" ")
                fields["RPRT"] = v
            else:  # some response parts don't have labels
                fields["line"] = line
        return fields

    def sendvoicememory(self, memoryspot=1):
        self.rigctld_command(f"\\send_voice_mem {memoryspot}")

    def sendcw(self, texttosend):
        """Send text via rigctld"""
        self.rigctld_command(f"b {texttosend}")

    def stopcw(self):
        """Stop CW via rigctld"""
        self.rigctld_command("\\stop_morse")

    def set_cw_speed(self, speed):
        """Set CW speed via rigctld"""
        self.rigctld_command(f"L VFOA KEYSPD {speed}")

    def get_vfo(self) -> str:
        """Poll the radio for current vfo using the interface"""
        report = self.rigctld_parse(self.rigctld_command("f VFOA"))
        freq = report.get("Frequency", "")
        if freq.isnumeric():
            return str(int(float(freq)))
        else:
            return ""

    def get_mode(self) -> str:
        """Returns the current mode filter width of the radio"""
        # QMX 'DIGI-U DIGI-L CW-U CW-L' or 'LSB', 'USB', 'CW', 'FM', 'AM', 'FSK'
        # 7300 'AM CW USB LSB RTTY FM CWR RTTYR PKTLSB PKTUSB FM-D AM-D'
        report = self.rigctld_parse(self.rigctld_command("m VFOA"))
        # get_mode:|Mode: CW|Passband: 500|RPRT 0
        self.rigctld_bw = report.get("Passband", "0")
        return report.get("Mode", "")

    def get_bw(self) -> str:
        """Get current vfo bandwidth"""
        return self.rigctld_bw

    def get_power(self) -> int:
        """Get power level from rig"""
        report = self.rigctld_parse(self.rigctld_command("l VFOA RFPOWER"))
        # get_level: RFPOWER |0.000000|RPRT 0
        return int(float(report.get("line", 0)) * 100)

    def get_ptt(self) -> str:
        """Get PTT state"""
        report = self.rigctld_parse(self.rigctld_command("t VFOA"))
        return report.get("PTT", "0")

    def get_mode_list(self) -> list:
        "Get a list of modes supported by the radio"
        # set_mode: VFOA:?|AM CW USB LSB RTTY FM CWR RTTYR PKTLSB PKTUSB FM-D AM-D PSK PSKR
        # RPRT 0
        report = self.rigctld_parse(self.rigctld_command("M VFOA ?"))
        return report.get("line", "").split(" ")

    def set_vfo(self, freq: str) -> bool:
        """Sets the radios vfo"""
        self.rigctld_command(f"F VFOA {freq}")
        return True

    def set_mode(self, mode: str) -> bool:
        """Sets the radios mode"""
        self.rigctld_command(f"M VFOA {mode} 0")
        return True

    def set_power(self, power):
        """Sets the radios power"""
        if power.isnumeric() and int(power) >= 1 and int(power) <= 100:
            rig_cmd = f"L VFOA RFPOWER {str(float(power) / 100)}"
            self.rigctld_command(rig_cmd)
            return True
        else:
            return False

    def ptt_on(self) -> bool:
        """turn ptt on/off

        # T, set_ptt 'PTT'
        # Set 'PTT'.
        # PTT is a value: ‘0’ (RX), ‘1’ (TX), ‘2’ (TX mic), or ‘3’ (TX data).

        # t, get_ptt
        # Get 'PTT' status.
        # Returns PTT as a value in set_ptt above.
        """
        self.rigctld_command("T VFOA 1")
        return True

    def ptt_off(self) -> bool:
        """turn ptt on/off"""
        self.rigctld_command("T VFOA 0")
        return True

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
