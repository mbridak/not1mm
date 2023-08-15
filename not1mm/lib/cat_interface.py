"""
K6GTE, CAT interface abstraction
Email: michael.bridak@gmail.com
GPL V3
"""

import logging
import socket
import xmlrpc.client

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("__main__")


class CAT:
    """CAT control rigctld or flrig"""

    def __init__(self, interface: str, host: str, port: int) -> None:
        """
        Computer Aided Tranceiver abstraction class.
        Offers a normalized rigctld or flrig interface.

        Takes 3 inputs to setup the class.

        A string defining the type of interface, either 'flrig' or 'rigctld'.

        A string defining the host, example: 'localhost' or '127.0.0.1'

        An interger defining the network port used.
        Commonly 12345 for flrig, or 4532 for rigctld.

        Exposed methods are:

        get_vfo()

        get_mode()

        get_power()

        get_ptt()

        set_vfo()

        set_mode()

        set_power()

        A variable 'online' is set to True if no error was encountered,
        otherwise False.
        """
        self.server = None
        self.rigctrlsocket = None
        self.interface = interface.lower()
        self.host = host
        self.port = port
        self.online = False
        if self.interface == "flrig":
            target = f"http://{host}:{port}"
            logger.debug("%s", target)
            self.server = xmlrpc.client.ServerProxy(target)
            self.online = True
            try:
                _ = self.server.main.get_version()
            except ConnectionRefusedError:
                self.online = False
            except xmlrpc.client.Fault:
                self.online = False
        if self.interface == "rigctld":
            self.__initialize_rigctrld()

    def __initialize_rigctrld(self):
        try:
            self.rigctrlsocket = socket.socket()
            self.rigctrlsocket.settimeout(0.5)
            self.rigctrlsocket.connect((self.host, self.port))
            logger.debug("Connected to rigctrld")
            self.online = True
        except ConnectionRefusedError as exception:
            self.rigctrlsocket = None
            self.online = False
            logger.debug("%s", f"{exception}")
            return
        except TimeoutError as exception:
            self.rigctrlsocket = None
            self.online = False
            logger.debug("%s", f"{exception}")
            return
        except OSError as exception:
            self.rigctrlsocket = None
            self.online = False
            logger.debug("%s", f"{exception}")

    def reinit(self):
        """reinitialise rigctl"""
        if self.interface == "rigctld":
            self.__initialize_rigctrld()

    def get_vfo(self) -> str:
        """Poll the radio for current vfo using the interface"""
        vfo = ""
        if self.interface == "flrig":
            vfo = self.__getvfo_flrig()
        if self.interface == "rigctld":
            vfo = self.__getvfo_rigctld()
            if "RPRT -" in vfo:
                vfo = ""
        return vfo

    def __getvfo_flrig(self) -> str:
        """Poll the radio using flrig"""
        try:
            self.online = True
            return self.server.rig.get_vfo()
        except ConnectionRefusedError as exception:
            self.online = False
            logger.debug("getvfo_flrig: %s", f"{exception}")
        except xmlrpc.client.Fault as exception:
            self.online = False
            logger.debug("getvfo_flrig: %s", f"{exception}")
        return ""

    def __getvfo_rigctld(self) -> str:
        """Returns VFO freq returned from rigctld"""
        if self.rigctrlsocket:
            try:
                self.online = True
                self.rigctrlsocket.send(b"f\n")
                return self.rigctrlsocket.recv(1024).decode().strip()
            except socket.error as exception:
                self.online = False
                logger.debug("getvfo_rigctld: %s", f"{exception}")
                self.rigctrlsocket = None
            return ""

        self.__initialize_rigctrld()
        return ""

    def get_mode(self) -> str:
        """Returns the current mode filter width of the radio"""
        mode = ""
        if self.interface == "flrig":
            mode = self.__getmode_flrig()
        if self.interface == "rigctld":
            mode = self.__getmode_rigctld()
        return mode

    def __getmode_flrig(self) -> str:
        """Returns mode via flrig"""
        try:
            self.online = True
            return self.server.rig.get_mode()
        except ConnectionRefusedError as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        except xmlrpc.client.Fault as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        return ""

    def __getmode_rigctld(self) -> str:
        """Returns mode vai rigctld"""
        if self.rigctrlsocket:
            try:
                self.online = True
                self.rigctrlsocket.send(b"m\n")
                mode = self.rigctrlsocket.recv(1024).decode()
                mode = mode.strip().split()[0]
                # logger.debug("%s", mode)
                return mode
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
        if self.interface == "flrig":
            return self.__getbw_flrig()
        if self.interface == "rigctld":
            return self.__getbw_rigctld()
        return False

    def __getbw_flrig(self):
        """return bandwidth"""
        try:
            self.online = True
            bandwidth = self.server.rig.get_bw()
            return bandwidth[0]
        except ConnectionRefusedError as exception:
            self.online = False
            logger.debug("getbw_flrig: %s", f"{exception}")
            return ""
        except xmlrpc.client.Fault as exception:
            self.online = False
            logger.debug("getbw_flrig: %s", f"{exception}")
            return ""

    def __getbw_rigctld(self):
        """return bandwidth"""
        if self.rigctrlsocket:
            try:
                self.online = True
                self.rigctrlsocket.send(b"m\n")
                mode = self.rigctrlsocket.recv(1024).decode()
                mode = mode.strip().split()[1]
                # logger.debug("%s", mode)
                return mode
            except IndexError as exception:
                logger.debug("%s", f"{exception}")
            except socket.error as exception:
                self.online = False
                logger.debug("%s", f"{exception}")
                self.rigctrlsocket = None
            return ""
        self.__initialize_rigctrld()
        return ""

    def get_power(self):
        """Get power level from rig"""
        if self.interface == "flrig":
            return self.__getpower_flrig()
        if self.interface == "rigctld":
            return self.__getpower_rigctld()
        return False

    def __getpower_flrig(self):
        try:
            self.online = True
            return self.server.rig.get_power()
        except ConnectionRefusedError as exception:
            self.online = False
            logger.debug("getpower_flrig: %s", f"{exception}")
            return ""
        except xmlrpc.client.Fault as exception:
            self.online = False
            logger.debug("getpower_flrig: %s", f"{exception}")
            return ""

    def __getpower_rigctld(self):
        if self.rigctrlsocket:
            try:
                self.online = True
                self.rigctrlsocket.send(b"l RFPOWER\n")
                return int(float(self.rigctrlsocket.recv(1024).decode().strip()) * 100)
            except socket.error as exception:
                self.online = False
                logger.debug("getpower_rigctld: %s", f"{exception}")
                self.rigctrlsocket = None
            return ""

    def get_ptt(self):
        """Get PTT state"""
        if self.interface == "flrig":
            return self.__getptt_flrig()
        if self.interface == "rigctld":
            return self.__getptt_rigctld()
        return False

    def __getptt_flrig(self):
        """Returns ptt state via flrig"""
        try:
            self.online = True
            return self.server.rig.get_ptt()
        except ConnectionRefusedError as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        except xmlrpc.client.Fault as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        return "0"

    def __getptt_rigctld(self):
        """Returns ptt state via rigctld"""
        if self.rigctrlsocket:
            try:
                self.online = True
                self.rigctrlsocket.send(b"t\n")
                ptt = self.rigctrlsocket.recv(1024).decode()
                logger.debug("%s", ptt)
                ptt = ptt.strip()
                return ptt
            except socket.error as exception:
                self.online = False
                logger.debug("%s", f"{exception}")
                self.rigctrlsocket = None
        return "0"

    def set_vfo(self, freq: str) -> bool:
        """Sets the radios vfo"""
        if self.interface == "flrig":
            return self.__setvfo_flrig(freq)
        if self.interface == "rigctld":
            return self.__setvfo_rigctld(freq)
        return False

    def __setvfo_flrig(self, freq: str) -> bool:
        """Sets the radios vfo"""
        try:
            self.online = True
            return self.server.rig.set_frequency(float(freq))
        except ConnectionRefusedError as exception:
            self.online = False
            logger.debug("setvfo_flrig: %s", f"{exception}")
        except xmlrpc.client.Fault as exception:
            self.online = False
            logger.debug("setvfo_flrig: %s", f"{exception}")
        return False

    def __setvfo_rigctld(self, freq: str) -> bool:
        """sets the radios vfo"""
        if self.rigctrlsocket:
            try:
                self.online = True
                self.rigctrlsocket.send(bytes(f"F {freq}\n", "utf-8"))
                _ = self.rigctrlsocket.recv(1024).decode().strip()
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
        if self.interface == "flrig":
            return self.__setmode_flrig(mode)
        if self.interface == "rigctld":
            return self.__setmode_rigctld(mode)
        return False

    def __setmode_flrig(self, mode: str) -> bool:
        """Sets the radios mode"""
        try:
            self.online = True
            return self.server.rig.set_mode(mode)
        except ConnectionRefusedError as exception:
            self.online = False
            logger.debug("setmode_flrig: %s", f"{exception}")
        except xmlrpc.client.Fault as exception:
            self.online = False
            logger.debug("setmode_flrig: %s", f"{exception}")
        return False

    def __setmode_rigctld(self, mode: str) -> bool:
        """sets the radios mode"""
        if self.rigctrlsocket:
            try:
                self.online = True
                self.rigctrlsocket.send(bytes(f"M {mode} 0\n", "utf-8"))
                _ = self.rigctrlsocket.recv(1024).decode().strip()
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
        if self.interface == "flrig":
            return self.__setpower_flrig(power)
        if self.interface == "rigctld":
            return self.__setpower_rigctld(power)
        return False

    def __setpower_flrig(self, power):
        try:
            self.online = True
            return self.server.rig.set_power(power)
        except ConnectionRefusedError as exception:
            self.online = False
            logger.debug("setpower_flrig: %s", f"{exception}")
            return False
        except xmlrpc.client.Fault as exception:
            self.online = False
            logger.debug("setpower_flrig: %s", f"{exception}")
            return False

    def __setpower_rigctld(self, power):
        if power.isnumeric() and int(power) >= 1 and int(power) <= 100:
            rig_cmd = bytes(f"L RFPOWER {str(float(power) / 100)}\n", "utf-8")
            try:
                self.online = True
                self.rigctrlsocket.send(rig_cmd)
                _ = self.rigctrlsocket.recv(1024).decode().strip()
            except socket.error:
                self.online = False
                self.rigctrlsocket = None

    def ptt_on(self):
        """turn ptt on/off"""
        if self.interface == "flrig":
            return self.__ptt_on_flrig()
        if self.interface == "rigctld":
            return self.__ptt_on_rigctld()
        return False

    def __ptt_on_rigctld(self):
        """Toggle PTT state on"""

        # T, set_ptt 'PTT'
        # Set 'PTT'.
        # PTT is a value: ‘0’ (RX), ‘1’ (TX), ‘2’ (TX mic), or ‘3’ (TX data).

        # t, get_ptt
        # Get 'PTT' status.
        # Returns PTT as a value in set_ptt above.

        rig_cmd = bytes("T 1\n", "utf-8")
        logger.debug("%s", f"{rig_cmd}")
        try:
            self.online = True
            self.rigctrlsocket.send(rig_cmd)
            _ = self.rigctrlsocket.recv(1024).decode().strip()
        except socket.error:
            self.online = False
            self.rigctrlsocket = None

    def __ptt_on_flrig(self):
        """Toggle PTT state on"""
        try:
            self.online = True
            return self.server.rig.set_ptt(1)
        except ConnectionRefusedError as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        except xmlrpc.client.Fault as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        return "0"

    def ptt_off(self):
        """turn ptt on/off"""
        if self.interface == "flrig":
            return self.__ptt_off_flrig()
        if self.interface == "rigctld":
            return self.__ptt_off_rigctld()
        return False

    def __ptt_off_rigctld(self):
        """Toggle PTT state off"""
        rig_cmd = bytes("T 0\n", "utf-8")
        logger.debug("%s", f"{rig_cmd}")
        try:
            self.online = True
            self.rigctrlsocket.send(rig_cmd)
            _ = self.rigctrlsocket.recv(1024).decode().strip()
        except socket.error:
            self.online = False
            self.rigctrlsocket = None

    def __ptt_off_flrig(self):
        """Toggle PTT state off"""
        try:
            self.online = True
            return self.server.rig.set_ptt(0)
        except ConnectionRefusedError as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        except xmlrpc.client.Fault as exception:
            self.online = False
            logger.debug("%s", f"{exception}")
        return "0"
