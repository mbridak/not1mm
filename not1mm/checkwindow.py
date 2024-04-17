#!/usr/bin/env python3
"""
Check Window
"""
# pylint: disable=no-name-in-module, unused-import, no-member, invalid-name, c-extension-no-member
# pylint: disable=logging-fstring-interpolation, line-too-long

import logging
import os
import platform
import queue
from json import loads
import Levenshtein

from PyQt6 import QtGui, uic
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QDockWidget
from PyQt6.QtGui import QMouseEvent, QColorConstants

import not1mm.fsutils as fsutils
from not1mm.lib.database import DataBase
from not1mm.lib.multicast import Multicast
from not1mm.lib.super_check_partial import SCP

logger = logging.getLogger(__name__)


class CheckWindow(QDockWidget):
    """The check window. Shows list or probable stations."""

    multicast_interface = None
    dbname = None
    pref = {}
    call = None
    masterLayout: QVBoxLayout = None
    dxcLayout: QVBoxLayout = None
    qsoLayout: QVBoxLayout = None

    character_remove_color = "#dd3333"
    character_add_color = "#3333dd"
    character_match_color = "#33dd33"

    masterScrollWidget: QWidget = None

    def __init__(self):
        super().__init__()
        self.load_pref()
        self.dbname = fsutils.USER_DATA_PATH / self.pref.get(
            "current_database", "ham.db"
        )
        self.database = DataBase(self.dbname, fsutils.APP_DATA_PATH)
        self.database.current_contest = self.pref.get("contest", 0)

        uic.loadUi(fsutils.APP_DATA_PATH / "checkwindow.ui", self)
        self.mscp = SCP(fsutils.APP_DATA_PATH)
        self._udpwatch = None
        self.udp_fifo = queue.Queue()
        self.multicast_interface = Multicast(
            self.pref.get("multicast_group", "239.1.1.1"),
            self.pref.get("multicast_port", 2239),
            self.pref.get("interface_ip", "0.0.0.0"),
        )
        self.multicast_interface.ready_read_connect(self.watch_udp)

    def item_clicked(self, item):
        """docstring for item_clicked"""
        if item:
            cmd = {}
            cmd["cmd"] = "CHANGECALL"
            cmd["station"] = platform.node()
            cmd["call"] = item
            self.multicast_interface.send_as_json(cmd)

    def setDarkMode(self, dark: bool):
        """Forces a darkmode palette."""

        if dark:
            darkPalette = QtGui.QPalette()
            darkColor = QtGui.QColor(56, 56, 56)
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
            # self.CheckPartialWindow.setPalette(darkPalette)
        else:
            palette = self.style().standardPalette()
            self.setPalette(palette)

    def load_pref(self) -> None:
        """
        Load preference file to get current db filename and sets the initial darkmode state.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        try:
            if os.path.exists(fsutils.CONFIG_FILE):
                with open(
                    fsutils.CONFIG_FILE, "rt", encoding="utf-8"
                ) as file_descriptor:
                    self.pref = loads(file_descriptor.read())
                    logger.info(f"loaded config file from {fsutils.CONFIG_FILE}")
            else:
                self.pref["current_database"] = "ham.db"

        except IOError as exception:
            logger.critical("Error: %s", exception)
        self.setDarkMode(self.pref.get("darkmode", False))

    def watch_udp(self):
        """
        Puts UDP datagrams in a FIFO queue.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        while self.multicast_interface.server_udp.hasPendingDatagrams():
            logger.debug("Got multicast ")
            json_data = self.multicast_interface.read_datagram_as_json()

            if json_data.get("station", "") != platform.node():
                continue
            if json_data.get("cmd", "") == "UPDATELOG":
                self.clear_lists()
            if json_data.get("cmd", "") == "CALLCHANGED":
                call = json_data.get("call", "")
                self.call = call
                self.master_list(call)
                self.log_list(call)
                continue
            if json_data.get("cmd", "") == "CHECKSPOTS":
                self.populate_layout(self.dxcLayout, [])
                spots = json_data.get("spots", [])
                self.telnet_list(spots)
                continue
            if json_data.get("cmd", "") == "NEWDB":
                ...
                # self.load_new_db()

            if json_data.get("cmd", "") == "DARKMODE":
                self.setDarkMode(json_data.get("state", False))

    def clear_lists(self) -> None:
        """
        Clear match lists.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        self.populate_layout(self.masterLayout, [])
        self.populate_layout(self.qsoLayout, [])
        self.populate_layout(self.dxcLayout, [])

    def master_list(self, call: str) -> None:
        """
        Get MASTER.SCP matches to call and display in list.

        Parameters
        ----------
        call : str
        Call to get matches for

        Returns
        -------
        None
        """
        self.populate_layout(self.masterLayout, [])
        results = self.mscp.super_check(call)
        self.populate_layout(self.masterLayout, filter(lambda x: "#" not in x, results))

    def log_list(self, call: str) -> None:
        """
        Get log matches to call and display in list.

        Parameters
        ----------
        call : str
        Call to get matches for

        Returns
        -------
        None
        """
        self.populate_layout(self.qsoLayout, [])
        if call:
            result = self.database.get_like_calls_and_bands(call)
            self.populate_layout(self.qsoLayout, result)

    def telnet_list(self, spots: list) -> None:
        """
        Get telnet matches to call and display in list.

        Parameters
        ----------
        spots : list
        List of spots to get matches for

        Returns
        -------
        None
        """
        self.populate_layout(self.dxcLayout, [])
        if spots:
            self.populate_layout(
                self.dxcLayout,
                filter(lambda x: x, [x.get("callsign", None) for x in spots]),
            )

    def populate_layout(self, layout, call_list) -> None:
        """Apply blackmagic to a layout."""
        for i in reversed(range(layout.count())):
            if layout.itemAt(i).widget():
                layout.itemAt(i).widget().setParent(None)
            else:
                layout.removeItem(layout.itemAt(i))
        call_items = []
        for call in call_list:
            if call:
                if self.call:
                    label_text = ""
                    diff_score = 0
                    for tag, i1, i2, j1, j2 in Levenshtein.opcodes(call, self.call):
                        if tag == "equal":
                            label_text += call[i1:i2]
                            continue
                        elif tag == "replace":
                            label_text += f"<span style='background-color: {self.character_remove_color};'>{call[i1:i2]}</span>"
                            diff_score += max((i2 - i1), (j2 - j1)) * (
                                len(call) + 1 - i2
                            )
                        elif tag == "insert" or tag == "delete":
                            label_text += f"<span style='background-color: {self.character_add_color};'>{call[i1:i2]}</span>"
                            diff_score += max((i2 - i1), (j2 - j1)) * (len(call) - i2)
                    if call == self.call:
                        label_text = f"<span style='background-color: {self.character_match_color};'>{call}</span>"
                    call_items.append((diff_score, label_text, call))

        call_items = sorted(call_items, key=lambda x: x[0])
        for i in reversed(range(layout.count())):
            if layout.itemAt(i).widget():
                layout.itemAt(i).widget().setParent(None)
            else:
                layout.removeItem(layout.itemAt(i))

        for _, label_text, call in call_items:
            label = CallLabel(label_text, call=call, callback=self.item_clicked)
            layout.addWidget(label)
        layout.addStretch(0)


class CallLabel(QLabel):
    call: str = None

    def __init__(
        self,
        *args,
        call=None,
        callback=None,
    ):
        super().__init__(*args)
        self.call = call
        self.callback = callback

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if self.call and self.callback:
            self.callback(self.call)
