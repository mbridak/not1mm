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
from json import loads, JSONDecodeError

import serial
from PyQt6 import QtCore, QtGui, QtWidgets, uic
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDockWidget
from PyQt6.QtGui import QColorConstants

import not1mm.fsutils as fsutils
from not1mm.lib.cat_interface import CAT
from not1mm.lib.multicast import Multicast

logger = logging.getLogger(__name__)


class VfoWindow(QDockWidget):
    """The VFO window."""

    pref = {}
    old_vfo = ""
    old_pico = ""
    message_shown = False
    multicast_interface = None
    current_palette = None

    def __init__(self):
        super().__init__()
        uic.loadUi(fsutils.APP_DATA_PATH / "vfo.ui", self)
        self.setWindowTitle("VFO Window")

        self.rig_control = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.getwaiting)
        self.load_pref()
        self.lcdNumber.display(0)
        self.pico = None
        self._udpwatch = None

        self.multicast_interface = Multicast(
            self.pref.get("multicast_group", "239.1.1.1"),
            self.pref.get("multicast_port", 2239),
            self.pref.get("interface_ip", "0.0.0.0"),
        )
        self.multicast_interface.ready_read_connect(self.watch_udp)

        self.setup_serial()
        self.poll_rig_timer = QtCore.QTimer()
        self.poll_rig_timer.timeout.connect(self.poll_radio)
        self.poll_rig_timer.start(500)

    def setDarkMode(self, dark: bool):
        """testing"""

        if dark:
            darkPalette = QtGui.QPalette()
            darkColor = QtGui.QColor(56, 56, 56)
            self.text_color = QColorConstants.White
            disabledColor = QtGui.QColor(127, 127, 127)
            darkPalette.setColor(QtGui.QPalette.ColorRole.Window, darkColor)
            darkPalette.setColor(
                QtGui.QPalette.ColorRole.WindowText, QColorConstants.White
            )
            darkPalette.setColor(
                QtGui.QPalette.ColorRole.Base, QtGui.QColor(45, 45, 45)
            )
            darkPalette.setColor(QtGui.QPalette.ColorRole.AlternateBase, darkColor)
            darkPalette.setColor(QtGui.QPalette.ColorRole.Text, QColorConstants.White)
            darkPalette.setColor(
                QtGui.QPalette.ColorGroup.Disabled,
                QtGui.QPalette.ColorRole.Text,
                disabledColor,
            )
            darkPalette.setColor(QtGui.QPalette.ColorRole.Button, darkColor)
            darkPalette.setColor(
                QtGui.QPalette.ColorRole.ButtonText, QColorConstants.White
            )
            darkPalette.setColor(
                QtGui.QPalette.ColorGroup.Disabled,
                QtGui.QPalette.ColorRole.ButtonText,
                disabledColor,
            )
            darkPalette.setColor(
                QtGui.QPalette.ColorRole.BrightText, QColorConstants.Red
            )
            darkPalette.setColor(
                QtGui.QPalette.ColorRole.Link, QtGui.QColor(42, 130, 218)
            )
            darkPalette.setColor(
                QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(42, 130, 218)
            )
            darkPalette.setColor(
                QtGui.QPalette.ColorRole.HighlightedText, QColorConstants.Black
            )
            darkPalette.setColor(
                QtGui.QPalette.ColorGroup.Disabled,
                QtGui.QPalette.ColorRole.HighlightedText,
                disabledColor,
            )

            self.setPalette(darkPalette)
            self.current_palette = darkPalette
        else:
            palette = self.style().standardPalette()
            self.current_palette = palette
            self.setPalette(palette)

    def load_pref(self) -> None:
        """
        Load preference file.
        Get CAT interface.
        """
        try:
            if os.path.exists(fsutils.CONFIG_FILE):
                with open(
                    fsutils.CONFIG_FILE, "rt", encoding="utf-8"
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
        # app.processEvents()
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

        device = self.discover_device()
        if device:
            try:
                self.pico = serial.Serial("/dev/serial/by-id/" + device, 115200)
                self.pico.timeout = 100
                self.lcdNumber.setStyleSheet("QLCDNumber { color: white; }")
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
        # app.processEvents()

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
            # app.processEvents()

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
                    # app.processEvents()
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
                            # app.processEvents()
        except OSError:
            logger.critical("Unable to write to serial device.")
        except AttributeError:
            logger.critical("Unable to write to serial device.")
        # app.processEvents()

    def show_message_box(self, message: str) -> None:
        """
        Display an alert box with the supplied message.
        """
        message_box = QtWidgets.QMessageBox()
        if self.current_palette:
            message_box.setPalette(self.current_palette)
        message_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        message_box.setText(message)
        message_box.setWindowTitle("Information")
        message_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        _ = message_box.exec()
