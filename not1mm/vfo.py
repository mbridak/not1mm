#!/usr/bin/env python3
"""
not1mm Contest logger
Email: michael.bridak@gmail.com
GPL V3
Class: VfoWindow
Purpose: Provide onscreen widget that interacts with DIY VFO knob and remote rig.
"""
# pylint: disable=no-name-in-module, unused-import, no-member, invalid-name, logging-fstring-interpolation, c-extension-no-member

# 115200 pico default speed
# usb-Raspberry_Pi_Pico_E6612483CB1B242A-if00
# usb-Raspberry_Pi_Pico_W_E6614C311B331139-if00

import datetime
import logging
import os
from json import loads
import sys

import serial
from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDockWidget
from PyQt6.QtGui import QPalette

import not1mm.fsutils as fsutils
from not1mm.lib.cat_interface import CAT

logger: logging.Logger = logging.getLogger(__name__)


class VfoWindow(QDockWidget):
    """The VFO window."""

    pref: dict = {}
    old_vfo: int = 0
    old_pico: str = ""
    message_shown: bool = False
    current_palette: QPalette | None = None
    device_reconnect: bool = False
    stale: datetime.datetime = datetime.datetime.now()

    def __init__(self):
        super().__init__()
        uic.loadUi(fsutils.APP_DATA_PATH / "vfo.ui", self)
        self.setWindowTitle("VFO Window")
        self.rig_control: CAT | None = None
        self.timer: QTimer = QTimer()
        self.timer.timeout.connect(self.getwaiting)
        self.load_pref()
        self.lcdNumber.display(0)
        self.pico: serial.Serial | None = None
        self.setup_serial()
        self.poll_rig_timer: QTimer = QTimer()
        self.poll_rig_timer.timeout.connect(self.poll_radio)
        self.poll_rig_timer.start(500)
        self.visibilityChanged.connect(self.window_state_changed)

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
                    self.pref: dict = loads(file_descriptor.read())
                    logger.info("%s", self.pref)

        except IOError as exception:
            logger.critical("Error: %s", exception)

        if self.pref.get("useflrig", False):
            logger.debug(
                "Using flrig: %s",
                f"{self.pref.get('CAT_ip')} {self.pref.get('CAT_port')}",
            )
            self.rig_control: CAT | None = CAT(
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
            self.rig_control: CAT | None = CAT(
                "rigctld",
                self.pref.get("CAT_ip", "127.0.0.1"),
                int(self.pref.get("CAT_port", 4532)),
            )
            self.timer.start(100)

    def discover_device(self) -> str | None:
        """
        Poll all serial devices looking for correct one.

        Rummage thru /dev/serial/by-id/ looking for Raspberry Picos
        Ask each if it's a vfoknob.
        Return the device ID if it is, or None if not found.
        """

        devices: list[str] | None = self.get_devices()
        data: bytes | None = None
        if devices is None:
            return None
        if sys.platform == "darwin":
            for device in devices:
                if "usb" in device:
                    try:
                        with serial.Serial("/dev/" + device, 115200) as ser:
                            ser.timeout = 1000
                            ser.write(b"whatareyou\r")
                            data = ser.readline()
                    except serial.serialutil.SerialException:
                        return None
                    if "vfoknob" in data.decode().strip():
                        return "/dev/" + device
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
                    return "/dev/serial/by-id/" + device

    def get_devices(self) -> list[str] | None:
        try:
            if sys.platform != "darwin":
                return os.listdir("/dev/serial/by-id")
            return os.listdir("/dev/")
        except FileNotFoundError:
            return None
        return None

    def window_state_changed(self) -> None:
        """Setup vfo knob if window is toggled on"""

        if self.isVisible():
            self.setup_serial()

    def setup_serial(self, supress_msg=False) -> None:
        """
        Setup the device returned by discover_device()
        Or display message saying we didn't find one.
        """

        if not self.isVisible():
            return

        device: str | None = self.discover_device()
        if device is not None:
            try:
                self.pico: serial.Serial = serial.Serial(device, 115200)
                self.pico.timeout = 100
                self.lcdNumber.setStyleSheet("QLCDNumber { color: white; }")
                self.device_reconnect: bool = True
            except OSError:
                if self.message_shown is False and supress_msg is False:
                    self.message_shown: bool = True
                    self.show_message_box(
                        "Unable to locate or open the VFO knob serial device."
                    )
                self.lcdNumber.setStyleSheet("QLCDNumber { color: red; }")
        else:
            if self.message_shown is False and supress_msg is False:
                self.message_shown: bool = True
                self.show_message_box(
                    "Unable to locate or open the VFO knob serial device."
                )
            self.lcdNumber.setStyleSheet("QLCDNumber { color: red; }")

    def msg_from_main(self, msg_dict) -> None:
        """
        Watch for a 'HALT' UPD packet from not1mm.
        Exit app if found.
        """
        if msg_dict.get("cmd", "") == "TUNE":
            # b'{"cmd": "TUNE", "freq": 7.0235, "spot": "MM0DGI"}'
            try:
                vfo: float = float(msg_dict.get("freq")) * 1000000
            except ValueError:
                return
            changefreq: str = f"F {int(vfo)}\r"
            try:
                if self.pico is not None:
                    self.pico.write(changefreq.encode())
            except OSError:
                logger.critical("Unable to write to serial device.")
            except AttributeError:
                logger.critical("Unable to write to serial device.")
            return

    def showNumber(self, the_number: int | str) -> None:
        """Display vfo value with dots"""
        dvfo: str = str(the_number)
        if len(dvfo) > 6:
            dnum: str = f"{dvfo[:len(dvfo)-6]}.{dvfo[-6:-3]}.{dvfo[-3:]}"
            self.lcdNumber.display(dnum)

    def poll_radio(self) -> None:
        """
        Poll radio via CAT asking for VFO state.
        If it's with in the HAM bands set the vfo knob to match the radio.
        """
        if not self.isVisible():
            return
        if datetime.datetime.now() < self.stale:
            return
        if self.rig_control is not None:
            if self.rig_control.online is False:
                self.rig_control.reinit()
            if self.rig_control.online is True:
                try:
                    vfo: int = int(self.rig_control.get_vfo())
                except ValueError:
                    return
                # if vfo < 1700000 or vfo > 60000000:
                #     return
                if vfo != self.old_vfo or self.device_reconnect is True:
                    self.old_vfo: int = vfo
                    logger.debug(f"{vfo}")
                    self.showNumber(vfo)
                    cmd: str = f"F {vfo}\r"
                    self.device_reconnect = False
                    try:
                        if self.pico is not None:
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
            if self.pico is not None:
                self.pico.write(b"f\r")
                while self.pico.in_waiting:
                    result: str = self.pico.read(self.pico.in_waiting).decode().strip()
                    # result = result.decode().strip()

                    if self.old_pico != result:
                        self.old_pico: str = result
                        self.stale: datetime.datetime = (
                            datetime.datetime.now() + datetime.timedelta(seconds=1)
                        )
                        if self.rig_control is not None:
                            self.rig_control.set_vfo(result)
                            self.showNumber(result)
            else:
                self.setup_serial(supress_msg=True)
        except OSError:
            logger.critical("Unable to write to serial device.")
            self.pico: serial.Serial | None = None
        except AttributeError:
            logger.critical("Unable to write to serial device.")
            self.pico: serial.Serial | None = None
        except KeyboardInterrupt:
            ...

    def show_message_box(self, message: str) -> None:
        """
        Display an alert box with the supplied message.
        """
        message_box: QtWidgets.QMessageBox = QtWidgets.QMessageBox()
        if self.current_palette is not None:
            message_box.setPalette(self.current_palette)
        message_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        message_box.setText(message)
        message_box.setWindowTitle("Information")
        message_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        _ = message_box.exec()
