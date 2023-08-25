#!/usr/bin/env python3
"""
VFO Window
"""
# pylint: disable=no-name-in-module, unused-import, no-member, invalid-name, logging-fstring-interpolation

# 115200 pico default speed
# usb-Raspberry_Pi_Pico_E6612483CB1B242A-if00
# usb-Raspberry_Pi_Pico_W_E6614C311B331139-if00

import logging

import os
import pkgutil
import platform
import queue
import sys
from json import loads, JSONDecodeError
from pathlib import Path

import serial
from PyQt5 import QtCore, QtNetwork, uic, QtWidgets
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow

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
    old_pico = ""
    message_shown = False

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
        self.udpsocket = QtNetwork.QUdpSocket(self)
        self.udpsocket.bind(
            QtNetwork.QHostAddress.AnyIPv4,
            MULTICAST_PORT,
            QtNetwork.QUdpSocket.ShareAddress,
        )
        self.udpsocket.joinMulticastGroup(QtNetwork.QHostAddress(MULTICAST_GROUP))
        self.udpsocket.readyRead.connect(self.watch_udp)

    def quit_app(self) -> None:
        """Shutdown the app."""
        app.quit()

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

    def watch_udp(self) -> None:
        """
        Watch for a 'HALT' UPD packet from not1mm.
        Exit app if found.
        """
        while self.udpsocket.hasPendingDatagrams():
            datagram, _, _ = self.udpsocket.readDatagram(
                self.udpsocket.pendingDatagramSize()
            )

            try:
                debug_info = f"{datagram.decode()}"
                logger.debug(debug_info)
                json_data = loads(datagram.decode())
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
            if json_data.get("cmd", "") == "HALT":
                self.quit_app()

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
                    self.lcdNumber.display(vfo)
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
                            self.lcdNumber.display(result)
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


if __name__ == "__main__":
    main()
