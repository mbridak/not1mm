#!/usr/bin/env python3
"""
VFO Window
"""
# pylint: disable=no-name-in-module, unused-import, no-member, invalid-name

# 115200 pico default speed

import logging
import pkgutil
import platform
import queue
import os
import sys
import serial
from serial.tools.list_ports import comports


from json import JSONDecodeError, loads, dumps
from pathlib import Path

from PyQt5 import uic, QtCore
from PyQt5.QtCore import QDir, Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import QtNetwork

from not1mm.lib.multicast import Multicast
from not1mm.lib.cat_interface import CAT

os.environ["QT_QPA_PLATFORMTHEME"] = "gnome"

loader = pkgutil.get_loader("not1mm")
WORKING_PATH = os.path.dirname(loader.get_filename())

if "XDG_DATA_HOME" in os.environ:
    DATA_PATH = os.environ.get("XDG_DATA_HOME")
else:
    DATA_PATH = str(Path.home() / ".local" / "share")
DATA_PATH += "/not1mm"

if "XDG_CONFIG_HOME" in os.environ:
    CONFIG_PATH = os.environ.get("XDG_CONFIG_HOME")
else:
    CONFIG_PATH = str(Path.home() / ".config")
CONFIG_PATH += "/not1mm"

MULTICAST_PORT = 2239
MULTICAST_GROUP = "239.1.1.1"
INTERFACE_IP = "0.0.0.0"


class MainWindow(QMainWindow):
    """
    The main window
    """

    pref = {}
    old_vfo = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rig_control = None
        self.load_pref()
        data_path = WORKING_PATH + "/data/vfo.ui"
        uic.loadUi(data_path, self)
        self.setWindowTitle("VFO Window")
        self.lcdNumber.display(0)
        self.pico = serial.Serial("/dev/ttyACM0", 115200)
        self.pico.timeout = 0
        self.pico.close()
        self.pico.open()
        self.timer = QTimer()
        self.timer.timeout.connect(self.getwaiting)
        self.timer.start(100)

    def load_pref(self):
        """Load preference file"""
        try:
            if os.path.exists(CONFIG_PATH + "/not1mm.json"):
                with open(
                    CONFIG_PATH + "/not1mm.json", "rt", encoding="utf-8"
                ) as file_descriptor:
                    self.pref = loads(file_descriptor.read())
                    logger.info("%s", self.pref)

        except IOError as exception:
            logger.critical("Error: %s", exception)

        if self.pref.get("useflrig", False):
            logger.debug(
                "Using flrig: %s",
                f"{self.pref.get('CAT_ip')} {self.pref.get('CAT_port')}",
            )
            self.rig_control = CAT(
                "flrig",
                self.pref.get("CAT_ip", "127.0.0.1"),
                int(self.pref.get("CAT_port", 12345)),
            )
        if self.pref.get("userigctld", False):
            logger.debug(
                "Using rigctld: %s",
                f"{self.pref.get('CAT_ip')} {self.pref.get('CAT_port')}",
            )
            self.rig_control = CAT(
                "rigctld",
                self.pref.get("CAT_ip", "127.0.0.1"),
                int(self.pref.get("CAT_port", 4532)),
            )

    def poll_radio(self):
        """Poll radio"""
        if self.rig_control:
            if self.rig_control.online is False:
                self.rig_control.reinit()
            if self.rig_control.online:
                vfo = self.rig_control.get_vfo()
                if vfo != self.old_vfo:
                    self.old_vfo = vfo
                    self.lcdNumber.display(vfo)
                    cmd = f"F {vfo}\r"
                    self.pico.write(cmd.encode())

    def getwaiting(self):
        """
        Checks to see the keyer has data to send to us.
        Could be a status change.
        Could be the user has twisted that turney bit thingy with the knob on it.
        It could also be an echo of the last character it has sent or is sending.
        """
        try:
            self.pico.write(b"f\r")
            while self.pico.in_waiting:
                result = self.pico.read(self.pico.in_waiting)
                print(result.decode().strip())
                if self.rig_control:
                    self.rig_control.set_vfo(result.decode().strip())
        except OSError as err:
            print(f"{err}")


def main():
    """main entry"""
    sys.exit(app.exec())


logger = logging.getLogger("__main__")
handler = logging.StreamHandler()
formatter = logging.Formatter(
    datefmt="%H:%M:%S",
    fmt="[%(asctime)s] %(levelname)s %(module)s - %(funcName)s Line %(lineno)d:\n%(message)s",
)
handler.setFormatter(formatter)
logger.addHandler(handler)

if Path("./debug").exists():
    logger.setLevel(logging.DEBUG)
    logger.debug("debugging on")
else:
    logger.setLevel(logging.WARNING)
    logger.warning("debugging off")

app = QApplication(sys.argv)
app.setStyle("Adwaita-Dark")
window = MainWindow()
window.show()
timer = QtCore.QTimer()
timer.timeout.connect(window.poll_radio)
timer.start(250)

if __name__ == "__main__":
    main()
