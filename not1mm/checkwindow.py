#!/usr/bin/env python3
"""
Check Window
"""
# pylint: disable=no-name-in-module, unused-import, no-member, invalid-name, c-extension-no-member

import logging
import os
import platform
import queue
from json import loads

from PyQt5 import uic
from PyQt5.QtWidgets import QListWidgetItem, QDockWidget, QWidget

import not1mm.fsutils as fsutils
from not1mm.lib.database import DataBase
from not1mm.lib.multicast import Multicast
from not1mm.lib.super_check_partial import SCP

logger = logging.getLogger(__name__)


class CheckWindow(QWidget):

    multicast_interface = None
    dbname = None
    pref = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_pref()
        self.dbname = fsutils.USER_DATA_PATH / self.pref.get("current_database", "ham.db")
        self.database = DataBase(self.dbname, fsutils.APP_DATA_PATH)
        self.database.current_contest = self.pref.get("contest", 0)

        uic.loadUi(fsutils.APP_DATA_PATH / "checkwindow.ui", self)

        self.logList.clear()
        self.masterList.clear()
        self.telnetList.clear()
        self.callhistoryList.clear()
        self.callhistoryList.hide()
        self.callhistoryListLabel.hide()
        self.mscp = SCP(fsutils.APP_DATA_PATH)
        self._udpwatch = None
        self.udp_fifo = queue.Queue()
        self.multicast_interface = Multicast(
            self.pref.get("multicast_group", "239.1.1.1"),
            self.pref.get("multicast_port", 2239),
            self.pref.get("interface_ip", "127.0.0.1"),
        )
        self.multicast_interface.ready_read_connect(self.watch_udp)


    def load_pref(self):
        """
        Load preference file to get current db filename.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        try:
            if os.path.exists(fsutils.CONFIG_FILE):
                with open(fsutils.CONFIG_FILE, "rt", encoding="utf-8") as file_descriptor:
                    self.pref = loads(file_descriptor.read())
                    logger.info(f"loaded config file from {fsutils.CONFIG_FILE}")
            else:
                self.pref["current_database"] = "ham.db"

        except IOError as exception:
            logger.critical("Error: %s", exception)

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
            logger.error("Got multicast ")
            json_data = self.multicast_interface.read_datagram_as_json()

            if json_data.get("station", "") != platform.node():
                continue
            if json_data.get("cmd", "") == "UPDATELOG":
                self.clear_lists()
            if json_data.get("cmd", "") == "CALLCHANGED":
                call = json_data.get("call", "")
                self.master_list(call)
                self.log_list(call)
                continue
            if json_data.get("cmd", "") == "CHECKSPOTS":
                self.telnetList.clear()
                spots = json_data.get("spots", [])
                self.telnet_list(spots)
                continue
            if json_data.get("cmd", "") == "NEWDB":
                ...
                # self.load_new_db()

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
        self.logList.clear()
        self.masterList.clear()
        self.telnetList.clear()
        self.callhistoryList.clear()

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
        results = self.mscp.super_check(call)
        self.masterList.clear()
        for item in results:
            if "#" in item:
                continue
            listItem = QListWidgetItem(item)
            self.masterList.addItem(listItem)
            self.masterList.show()

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
        self.logList.clear()
        if call:
            result = self.database.get_like_calls_and_bands(call)
            for calls in result:
                listItem = QListWidgetItem(calls)
                self.logList.addItem(listItem)
                self.logList.show()

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
        self.telnetList.clear()
        if spots:
            for calls in spots:
                call = calls.get("callsign", "")
                listItem = QListWidgetItem(call)
                self.telnetList.addItem(listItem)
                self.telnetList.show()


