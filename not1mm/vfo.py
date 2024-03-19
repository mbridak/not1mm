#!/usr/bin/env python3
"""
VFO Window
"""
# pylint: disable=no-name-in-module, unused-import, no-member, invalid-name, logging-fstring-interpolation, c-extension-no-member

# 115200 pico default speed
# usb-Raspberry_Pi_Pico_E6612483CB1B242A-if00
# usb-Raspberry_Pi_Pico_W_E6614C311B331139-if00

import logging
import os
import platform
import queue
import sys

from json import loads, JSONDecodeError
from pathlib import Path

import serial

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import QDir, Qt, QTimer
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import QApplication, QMainWindow

from not1mm.lib.cat_interface import CAT
from not1mm.lib.multicast import Multicast

if __loader__:
    WORKING_PATH = os.path.dirname(__loader__.get_filename())
else:
    WORKING_PATH = os.path.dirname(os.path.realpath(__file__))

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


class MainWindow(QMainWindow):
    """
    The main window
    """

    pref = {}
    old_vfo = ""
    old_pico = ""
    message_shown = False
    multicast_interface = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data_path = WORKING_PATH + "/data/vfo.ui"
        uic.loadUi(data_path, self)
        self.rig_control = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.getwaiting)
        self.load_pref()
        self.setWindowTitle("VFO Window")
        self.lcdNumber.display(0)
        self.pico = None
        self._udpwatch = None
        self.udp_fifo = queue.Queue()
        self.multicast_interface = Multicast(
            self.pref.get("multicast_group", "239.1.1.1"),
            self.pref.get("multicast_port", 2239),
            self.pref.get("interface_ip", "0.0.0.0"),
        )
        self.multicast_interface.ready_read_connect(self.watch_udp)

    def quit_app(self) -> None:
        """Shutdown the app."""
        app.quit()

    def setDarkMode(self, dark: bool):
        """testing"""

        if dark:
            darkPalette = QtGui.QPalette()
            darkColor = QtGui.QColor(45, 45, 45)
            disabledColor = QtGui.QColor(127, 127, 127)
            darkPalette.setColor(QtGui.QPalette.Window, darkColor)
            darkPalette.setColor(QtGui.QPalette.WindowText, Qt.white)
            darkPalette.setColor(QtGui.QPalette.Base, QtGui.QColor(18, 18, 18))
            darkPalette.setColor(QtGui.QPalette.AlternateBase, darkColor)
            darkPalette.setColor(QtGui.QPalette.Text, Qt.white)
            darkPalette.setColor(
                QtGui.QPalette.Disabled, QtGui.QPalette.Text, disabledColor
            )
            darkPalette.setColor(QtGui.QPalette.Button, darkColor)
            darkPalette.setColor(QtGui.QPalette.ButtonText, Qt.white)
            darkPalette.setColor(
                QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, disabledColor
            )
            darkPalette.setColor(QtGui.QPalette.BrightText, Qt.red)
            darkPalette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
            darkPalette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
            darkPalette.setColor(QtGui.QPalette.HighlightedText, Qt.black)
            darkPalette.setColor(
                QtGui.QPalette.Disabled, QtGui.QPalette.HighlightedText, disabledColor
            )

            self.setPalette(darkPalette)
        else:
            palette = self.style().standardPalette()
            self.setPalette(palette)

    def load_pref(self) -> None:
        """
        Load preference file.
        Get CAT interface.
        """
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
            self.timer.start(100)
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
            self.timer.start(100)
        self.setDarkMode(self.pref.get("darkmode", False))

    def discover_device(self) -> str:
        """
        Poll all serial devices looking for correct one.

        Rummage thru /dev/serial/by-id/ looking for Raspberry Picos
        Ask each if it's a vfoknob.
        Return the device ID if it is, or None if not found.
        """

        devices = None
        data = None
        app.processEvents()
        try:
            devices = os.listdir("/dev/serial/by-id")
        except FileNotFoundError:
            return None

        for device in devices:
            if "usb-Raspberry_Pi_Pico" in device:
                try:
                    with serial.Serial("/dev/serial/by-id/" + device, 115200) as ser:
                        ser.timeout = 1000
                        ser.write(b"whatareyou\r")
                        data = ser.readline()
                except serial.serialutil.SerialException:
                    return None
                if "vfoknob" in data.decode().strip():
                    return device

    def setup_serial(self) -> None:
        """
        Setup the device returned by discover_device()
        Or display message saying we didn't find one.
        """
        while True:
            device = self.discover_device()
            if device:
                try:
                    self.pico = serial.Serial("/dev/serial/by-id/" + device, 115200)
                    self.pico.timeout = 100
                    self.lcdNumber.setStyleSheet("QLCDNumber { color: white; }")
                    break
                except OSError:
                    if self.message_shown is False:
                        self.message_shown = True
                        self.show_message_box(
                            "Unable to locate or open the VFO knob serial device."
                        )
                    self.lcdNumber.setStyleSheet("QLCDNumber { color: red; }")
            else:
                if self.message_shown is False:
                    self.message_shown = True
                    self.show_message_box(
                        "Unable to locate or open the VFO knob serial device."
                    )
                self.lcdNumber.setStyleSheet("QLCDNumber { color: red; }")
            app.processEvents()

    def watch_udp(self) -> None:
        """
        Watch for a 'HALT' UPD packet from not1mm.
        Exit app if found.
        """
        while self.multicast_interface.server_udp.hasPendingDatagrams():
            datagram = self.multicast_interface.getpacket()
            try:
                debug_info = f"{datagram}"
                logger.debug(debug_info)
                json_data = loads(datagram)
            except UnicodeDecodeError as err:
                the_error = f"Not Unicode: {err}\n{datagram}"
                logger.debug(the_error)
                continue
            except JSONDecodeError as err:
                the_error = f"Not JSON: {err}\n{datagram}"
                logger.debug(the_error)
                continue
            if json_data.get("station", "") != platform.node():
                continue
            logger.debug(f"{json_data=}")
            if json_data.get("cmd", "") == "HALT":
                self.quit_app()
            if json_data.get("cmd", "") == "TUNE":
                # b'{"cmd": "TUNE", "freq": 7.0235, "spot": "MM0DGI"}'
                vfo = json_data.get("freq")
                vfo = float(vfo) * 1000000
                changefreq = f"F {int(vfo)}\r"
                try:
                    if self.pico:
                        self.pico.write(changefreq.encode())
                except OSError:
                    logger.critical("Unable to write to serial device.")
                except AttributeError:
                    logger.critical("Unable to write to serial device.")
                continue
            if json_data.get("cmd", "") == "DARKMODE":
                self.setDarkMode(json_data.get("state", False))

    def showNumber(self, the_number) -> None:
        """Display vfo value with dots"""
        dvfo = str(the_number)
        if len(dvfo) > 6:
            dnum = f"{dvfo[:len(dvfo)-6]}.{dvfo[-6:-3]}.{dvfo[-3:]}"
            self.lcdNumber.display(dnum)
            app.processEvents()

    def poll_radio(self) -> None:
        """
        Poll radio via CAT asking for VFO state.
        If it's with in the HAM bands set the vfo knob to match the radio.
        """
        if self.rig_control:
            if self.rig_control.online is False:
                self.rig_control.reinit()
            if self.rig_control.online:
                vfo = self.rig_control.get_vfo()
                try:
                    vfo = int(vfo)
                except ValueError:
                    return
                if vfo < 1700000 or vfo > 60000000:
                    return
                if vfo != self.old_vfo:
                    self.old_vfo = vfo
                    logger.debug(f"{vfo}")
                    self.showNumber(vfo)
                    # self.lcdNumber.display(dnum)
                    app.processEvents()
                    cmd = f"F {vfo}\r"
                    try:
                        if self.pico:
                            self.pico.write(cmd.encode())
                    except OSError:
                        logger.critical("Unable to write to serial device.")
                    except AttributeError:
                        logger.critical("Unable to write to serial device.")

    def getwaiting(self) -> None:
        """
        Get the USB VFO knob state.
        Set the radio's VFO to match if it has changed.
        """
        try:
            if self.pico:
                self.pico.write(b"f\r")
                while self.pico.in_waiting:
                    result = self.pico.read(self.pico.in_waiting)
                    result = result.decode().strip()
                    if self.old_pico != result:
                        self.old_pico = result
                        if self.rig_control:
                            self.rig_control.set_vfo(result)
                            self.showNumber(result)
                            # self.lcdNumber.display(result)
                            app.processEvents()
        except OSError:
            logger.critical("Unable to write to serial device.")
        except AttributeError:
            logger.critical("Unable to write to serial device.")
        app.processEvents()

    def show_message_box(self, message: str) -> None:
        """
        Display an alert box with the supplied message.
        """
        message_box = QtWidgets.QMessageBox()
        message_box.setIcon(QtWidgets.QMessageBox.Information)
        message_box.setText(message)
        message_box.setWindowTitle("Information")
        message_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        _ = message_box.exec_()


def main():
    """main entry"""
    window.show()
    window.setup_serial()
    app.processEvents()
    timer = QtCore.QTimer()
    timer.timeout.connect(window.poll_radio)
    timer.start(250)
    sys.exit(app.exec())


def load_fonts_from_dir(directory: str) -> set:
    """
    Well it loads fonts from a directory...

    Parameters
    ----------
    directory : str
    The directory to load fonts from.

    Returns
    -------
    set
    A set of font families installed in the directory.
    """
    font_families = set()
    for _fi in QDir(directory).entryInfoList(["*.ttf", "*.woff", "*.woff2"]):
        _id = QFontDatabase.addApplicationFont(_fi.absoluteFilePath())
        font_families |= set(QFontDatabase.applicationFontFamilies(_id))
    return font_families


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
# app.setStyle("Adwaita-Dark")
font_path = WORKING_PATH + "/data"
families = load_fonts_from_dir(os.fspath(font_path))
logger.info(families)
window = MainWindow()


if __name__ == "__main__":
    main()
