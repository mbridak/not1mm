#!/usr/bin/env python3
"""
Display current log
"""
# pylint: disable=no-name-in-module, unused-import, no-member
# QTableWidget
# focusedLog, generalLog
import logging
import math
import os
import pkgutil
import platform
import queue
import socket
import sys
import time
import threading

from json import JSONDecodeError, loads, dumps
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets, uic, Qt
from PyQt5.QtCore import QDir, QItemSelectionModel
from PyQt5 import QtNetwork
from PyQt5.QtGui import QFontDatabase

from not1mm.lib.database import DataBase
from not1mm.lib.multicast import Multicast
from not1mm.lib.edit_contact import EditContact
from not1mm.lib.n1mm import N1MM

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

DARK_STYLESHEET = ""


MULTICAST_PORT = 2239
MULTICAST_GROUP = "239.1.1.1"
INTERFACE_IP = "0.0.0.0"


class MainWindow(QtWidgets.QMainWindow):
    """
    The main window
    """

    dbname = None
    edit_contact_dialog = None
    pref = {}
    columns = {
        0: "YYYY-MM-DD HH:MM:SS",
        1: "Call",
        2: "Freq",
        3: "Mode",
        4: "Snt",
        5: "Rcv",
        6: "SentNr",
        7: "RcvNr",
        8: "Exchange1",
        9: "CK",
        10: "Prec",
        11: "Sect",
        12: "WPX",
        13: "Power",
        14: "M1",
        15: "ZN",
        16: "M2",
        17: "PFX",
        18: "PTS",
        19: "Name",
        20: "Comment",
        21: "UUID",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.table_loading = True
        self._udpwatch = None
        self.udp_fifo = queue.Queue()
        self.n1mm = None
        self.load_pref()
        if self.pref.get("dark_mode"):
            self.setStyleSheet(DARK_STYLESHEET)
        self.dbname = DATA_PATH + "/" + self.pref.get("current_database", "ham.db")
        self.database = DataBase(self.dbname, WORKING_PATH)
        self.database.current_contest = self.pref.get("contest", 0)
        self.contact = self.database.empty_contact
        data_path = WORKING_PATH + "/data/logwindow.ui"
        uic.loadUi(data_path, self)
        self.setWindowTitle(
            f"Log Display - {self.pref.get('current_database', 'ham.db')}"
        )
        self.generalLog.setColumnCount(len(self.columns))
        self.focusedLog.setColumnCount(len(self.columns))
        icon_path = WORKING_PATH + "/data/"
        self.checkmark = QtGui.QPixmap(icon_path + "check.png")
        self.checkicon = QtGui.QIcon()
        self.checkicon.addPixmap(self.checkmark)
        self.generalLog.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.generalLog.customContextMenuRequested.connect(self.edit_contact_selected)
        for column_number, column_name in self.columns.items():
            self.generalLog.setHorizontalHeaderItem(
                column_number, QtWidgets.QTableWidgetItem(column_name)
            )
            self.focusedLog.setHorizontalHeaderItem(
                column_number, QtWidgets.QTableWidgetItem(column_name)
            )

        self.generalLog.cellDoubleClicked.connect(self.double_clicked)
        self.generalLog.cellChanged.connect(self.cell_changed)

        self.focusedLog.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.focusedLog.customContextMenuRequested.connect(
            self.edit_focused_contact_selected
        )
        for log in (self.generalLog, self.focusedLog):
            log.setColumnWidth(self.get_column("YYYY-MM-DD HH:MM:SS"), 200)
            log.setColumnWidth(self.get_column("Snt"), 50)
            log.setColumnWidth(self.get_column("Rcv"), 50)
            log.setColumnWidth(self.get_column("SentNr"), 75)
            log.setColumnWidth(self.get_column("RcvNr"), 75)

            log.setColumnWidth(self.get_column("WPX"), 50)
            log.setColumnWidth(self.get_column("Power"), 50)
            log.setColumnWidth(self.get_column("M1"), 50)
            log.setColumnWidth(self.get_column("ZN"), 50)
            log.setColumnWidth(self.get_column("PTS"), 50)
            log.setColumnWidth(self.get_column("Name"), 75)
            log.setColumnWidth(self.get_column("Comment"), 200)
            log.setColumnHidden(self.get_column("UUID"), True)
            log.verticalHeader().setVisible(False)

        self.get_log()
        self.udpsocket = QtNetwork.QUdpSocket(self)
        self.udpsocket.bind(
            QtNetwork.QHostAddress.AnyIPv4,
            MULTICAST_PORT,
            QtNetwork.QUdpSocket.ShareAddress,
        )
        self.udpsocket.joinMulticastGroup(QtNetwork.QHostAddress(MULTICAST_GROUP))
        self.udpsocket.readyRead.connect(self.watch_udp)

        cmd = {}
        cmd["cmd"] = "GETCOLUMNS"
        cmd["station"] = platform.node()

        packet = bytes(dumps(cmd), encoding="ascii")
        self.udpsocket.writeDatagram(
            packet, QtNetwork.QHostAddress(MULTICAST_GROUP), MULTICAST_PORT
        )

    def get_column(self, name: str) -> int:
        """returns the column number of the given column name."""
        for key, value in self.columns.items():
            if value == name:
                return key

    def load_pref(self):
        """Load preference file to get current db filename."""
        try:
            if os.path.exists(CONFIG_PATH + "/not1mm.json"):
                with open(
                    CONFIG_PATH + "/not1mm.json", "rt", encoding="utf-8"
                ) as file_descriptor:
                    self.pref = loads(file_descriptor.read())
                    logger.info("%s", self.pref)
            else:
                self.pref["current_database"] = "ham.db"

        except IOError as exception:
            logger.critical("Error: %s", exception)

        try:
            self.n1mm = N1MM(
                self.pref.get("n1mm_radioport", "127.0.0.1:12060"),
                self.pref.get("n1mm_contactport", "127.0.0.1:12061"),
                self.pref.get("n1mm_lookupport", "127.0.0.1:12060"),
                self.pref.get("n1mm_scoreport", "127.0.0.1:12060"),
            )
        except ValueError:
            logger.warning("%s", f"{ValueError}")
        self.n1mm.send_radio_packets = self.pref.get("send_n1mm_radio", False)
        self.n1mm.send_contact_packets = self.pref.get("send_n1mm_contact", False)
        self.n1mm.send_lookup_packets = self.pref.get("send_n1mm_lookup", False)
        self.n1mm.send_score_packets = self.pref.get("send_n1mm_score", False)
        self.n1mm.radio_info["StationName"] = self.pref.get("n1mm_station_name", "")

    def load_new_db(self):
        """if db changes reload it."""
        self.load_pref()
        self.dbname = DATA_PATH + "/" + self.pref.get("current_database", "ham.db")
        self.database = DataBase(self.dbname, WORKING_PATH)
        self.database.current_contest = self.pref.get("contest", 0)
        self.contact = self.database.empty_contact
        self.get_log()
        self.setWindowTitle(
            f"Log Display - {self.pref.get('current_database', 'ham.db')}"
        )

    def double_clicked(self, _row, _column):
        """Slot for doubleclick event"""
        if self.table_loading:
            return
        logger.debug("DoubleClicked")

    def cell_changed(self, row, column):
        """Slot for changed cell"""
        logger.debug("Cell Changed")
        self.contact = self.database.fetch_contact_by_uuid(
            self.generalLog.item(row, self.get_column("UUID")).text()
        )
        db_record = {
            "TS": self.generalLog.item(
                row, self.get_column("YYYY-MM-DD HH:MM:SS")
            ).text(),
            "Call": self.generalLog.item(row, self.get_column("Call")).text().upper(),
            "Freq": self.generalLog.item(row, self.get_column("Freq")).text(),
            "Mode": self.generalLog.item(row, self.get_column("Mode")).text(),
            "SNT": self.generalLog.item(row, self.get_column("Snt")).text(),
            "RCV": self.generalLog.item(row, self.get_column("Rcv")).text(),
            "SentNr": self.generalLog.item(row, self.get_column("SentNr")).text(),
            "NR": self.generalLog.item(row, self.get_column("RcvNr")).text(),
            "Exchange1": self.generalLog.item(row, self.get_column("Exchange1")).text(),
            "CK": self.generalLog.item(row, self.get_column("CK")).text(),
            "Prec": self.generalLog.item(row, self.get_column("Prec")).text(),
            "Sect": self.generalLog.item(row, self.get_column("Sect")).text(),
            "WPXPrefix": self.generalLog.item(row, self.get_column("WPX")).text(),
            "Power": self.generalLog.item(row, self.get_column("Power")).text(),
            "IsMultiplier1": self.generalLog.item(row, self.get_column("M1")).text(),
            "ZN": self.generalLog.item(row, self.get_column("ZN")).text(),
            "IsMultiplier2": self.generalLog.item(row, self.get_column("M2"))
            .text()
            .upper(),
            "CountryPrefix": self.generalLog.item(row, self.get_column("PFX")).text(),
            "Points": self.generalLog.item(row, self.get_column("PTS")).text(),
            "Name": self.generalLog.item(row, self.get_column("Name")).text(),
            "Comment": self.generalLog.item(row, self.get_column("Comment")).text(),
            "ID": self.generalLog.item(row, self.get_column("UUID")).text(),
        }
        self.database.change_contact(db_record)

        if self.n1mm.send_contact_packets:
            self.n1mm.contact_info["timestamp"] = db_record["TS"]
            self.n1mm.contact_info["contestname"] = self.contact["ContestName"].replace(
                "-", ""
            )
            self.n1mm.contact_info["contestnr"] = self.contact["ContestNR"]
            self.n1mm.contact_info["operator"] = self.contact["Operator"]
            self.n1mm.contact_info["mycall"] = self.contact["Operator"]
            # self.n1mm.contact_info[""] = self.contact[""]
            self.n1mm.contact_info["band"] = self.contact["Band"]
            self.n1mm.contact_info["mode"] = self.contact["Mode"]
            self.n1mm.contact_info["stationprefix"] = self.contact["StationPrefix"]
            self.n1mm.contact_info["continent"] = self.contact["Continent"]
            self.n1mm.contact_info["gridsquare"] = self.contact["GridSquare"]
            self.n1mm.contact_info["ismultiplier1"] = self.contact["IsMultiplier1"]
            self.n1mm.contact_info["ismultiplier2"] = self.contact["IsMultiplier2"]

            self.n1mm.contact_info["call"] = db_record["Call"]
            self.n1mm.contact_info["oldcall"] = self.contact["Call"]

            self.n1mm.contact_info["rxfreq"] = self.n1mm.contact_info["txfreq"] = str(
                int(float(db_record["Freq"]) * 100)
            )
            self.n1mm.contact_info["snt"] = db_record["SNT"]
            self.n1mm.contact_info["rcv"] = db_record["RCV"]
            self.n1mm.contact_info["sntnr"] = db_record["SentNr"]
            self.n1mm.contact_info["rcvnr"] = db_record["NR"]
            self.n1mm.contact_info["exchange1"] = db_record.get("Exchange1", "")
            self.n1mm.contact_info["ck"] = db_record["CK"]
            self.n1mm.contact_info["prec"] = db_record["Prec"]
            self.n1mm.contact_info["section"] = db_record["Sect"]
            self.n1mm.contact_info["wpxprefix"] = db_record["WPXPrefix"]
            self.n1mm.contact_info["power"] = db_record["Power"]

            self.n1mm.contact_info["zone"] = db_record["ZN"]

            self.n1mm.contact_info["countryprefix"] = db_record["CountryPrefix"]
            self.n1mm.contact_info["points"] = db_record["Points"]
            self.n1mm.contact_info["name"] = db_record["Name"]
            self.n1mm.contact_info["misctext"] = db_record["Comment"]
            self.n1mm.contact_info["ID"] = db_record["ID"]
            self.n1mm.send_contactreplace()

        self.get_log()
        self.generalLog.scrollToItem(self.generalLog.item(row, column))

    def dummy(self):
        """the dummy"""

    def edit_focused_contact_selected(self, clicked_cell):
        """Show edit contact dialog"""
        logger.debug("Opening EditContact dialog")
        item = self.focusedLog.itemAt(clicked_cell)
        uuid = self.focusedLog.item(item.row(), self.get_column("UUID")).text()
        self.edit_contact(uuid)

    def edit_contact_selected(self, clicked_cell):
        """Show edit contact dialog"""
        logger.debug("Opening EditContact dialog")
        item = self.generalLog.itemAt(clicked_cell)
        uuid = self.generalLog.item(item.row(), self.get_column("UUID")).text()
        self.edit_contact(uuid)

    def edit_contact(self, uuid):
        """Show edit contact dialog"""
        logger.debug("Edit: %s", uuid)
        self.edit_contact_dialog = EditContact(WORKING_PATH)
        if self.pref.get("dark_mode"):
            self.edit_contact_dialog.setStyleSheet(DARK_STYLESHEET)
        self.edit_contact_dialog.accepted.connect(self.save_edited_contact)
        self.contact = self.database.fetch_contact_by_uuid(uuid)
        self.edit_contact_dialog.delete_2.clicked.connect(self.delete_contact)

        self.edit_contact_dialog.call.setText(self.contact.get("Call", ""))
        self.edit_contact_dialog.time_stamp.setText(self.contact.get("TS", ""))
        self.edit_contact_dialog.rx_freq.setText(str(self.contact.get("Freq", "")))
        self.edit_contact_dialog.tx_freq.setText(str(self.contact.get("QSXFreq", "")))
        self.edit_contact_dialog.mode.setText(self.contact.get("Mode", ""))
        self.edit_contact_dialog.contest.setText(self.contact.get("ContestName", ""))
        self.edit_contact_dialog.rst_sent.setText(self.contact.get("SNT", ""))
        self.edit_contact_dialog.rst_rcv.setText(self.contact.get("RCV", ""))
        self.edit_contact_dialog.country.setText(self.contact.get("CountryPrefix", ""))
        self.edit_contact_dialog.station_call.setText(
            self.contact.get("StationPrefix", "")
        )
        self.edit_contact_dialog.name.setText(self.contact.get("Name", ""))
        self.edit_contact_dialog.qth.setText(self.contact.get("QTH", ""))
        self.edit_contact_dialog.comment.setText(self.contact.get("Comment", ""))

        self.edit_contact_dialog.nr.setText(str(self.contact.get("NR", "0")))
        self.edit_contact_dialog.nr_sent.setText(str(self.contact.get("SentNr", "0")))
        self.edit_contact_dialog.points.setText(str(self.contact.get("Points", "0")))
        self.edit_contact_dialog.power.setText(str(self.contact.get("Power", "0")))
        self.edit_contact_dialog.zone.setText(str(self.contact.get("ZN", "")))
        self.edit_contact_dialog.section.setText(self.contact.get("Sect", ""))
        the_band = self.contact.get("Band", "0")
        c_band = (
            str(int(the_band))
            if float(math.floor(the_band)) == the_band
            else str(the_band)
        )
        self.edit_contact_dialog.band.setText(c_band)
        self.edit_contact_dialog.check.setText(str(self.contact.get("CK", "")))
        self.edit_contact_dialog.prec.setText(self.contact.get("Prec", ""))
        self.edit_contact_dialog.wpx.setText(self.contact.get("WPXPrefix", ""))
        self.edit_contact_dialog.exchange.setText(self.contact.get("Exchange1", ""))
        self.edit_contact_dialog.run_12.setText(str(self.contact.get("Run1Run2", "")))
        self.edit_contact_dialog.radio.setText(str(self.contact.get("RadioNR", "")))
        self.edit_contact_dialog.grid.setText(self.contact.get("GridSquare", ""))
        self.edit_contact_dialog.op.setText(self.contact.get("Operator", ""))
        self.edit_contact_dialog.misc.setText(self.contact.get("MiscText", ""))
        self.edit_contact_dialog.rover_qth.setText(
            self.contact.get("RoverLocation", "")
        )

        self.edit_contact_dialog.mult_1.setChecked(
            bool(self.contact.get("IsMultiplier1", ""))
        )
        self.edit_contact_dialog.mult_2.setChecked(
            bool(self.contact.get("IsMultiplier2", ""))
        )
        self.edit_contact_dialog.mult_3.setChecked(
            bool(self.contact.get("IsMultiplier3", ""))
        )

        self.edit_contact_dialog.show()
        debugline = f"Right Clicked Item: {uuid}"
        logger.debug(debugline)

    def save_edited_contact(self):
        """save the goods"""
        self.contact["Call"] = self.edit_contact_dialog.call.text()
        self.contact["TS"] = self.edit_contact_dialog.time_stamp.text()
        self.contact["Freq"] = self.edit_contact_dialog.rx_freq.text()
        self.contact["QSXFreq"] = self.edit_contact_dialog.tx_freq.text()
        self.contact["Mode"] = self.edit_contact_dialog.mode.text()
        self.contact["ContestName"] = self.edit_contact_dialog.contest.text()
        self.contact["SNT"] = self.edit_contact_dialog.rst_sent.text()
        self.contact["RCV"] = self.edit_contact_dialog.rst_rcv.text()
        self.contact["CountryPrefix"] = self.edit_contact_dialog.country.text()
        self.contact["Operator"] = self.edit_contact_dialog.station_call.text()
        self.contact["Name"] = self.edit_contact_dialog.name.text()
        self.contact["QTH"] = self.edit_contact_dialog.qth.text()
        self.contact["Comment"] = self.edit_contact_dialog.comment.text()

        self.contact["NR"] = self.edit_contact_dialog.nr.text()
        self.contact["SentNr"] = self.edit_contact_dialog.nr_sent.text()
        self.contact["Points"] = self.edit_contact_dialog.points.text()
        self.contact["Power"] = self.edit_contact_dialog.power.text()
        self.contact["ZN"] = self.edit_contact_dialog.zone.text()
        self.contact["Sect"] = self.edit_contact_dialog.section.text()
        self.contact["Band"] = self.edit_contact_dialog.band.text()
        self.contact["CK"] = self.edit_contact_dialog.check.text()
        self.contact["Prec"] = self.edit_contact_dialog.prec.text()
        self.contact["WPXPrefix"] = self.edit_contact_dialog.wpx.text()
        self.contact["Exchange1"] = self.edit_contact_dialog.exchange.text()
        self.contact["Run1Run2"] = self.edit_contact_dialog.run_12.text()
        self.contact["RadioNR"] = self.edit_contact_dialog.radio.text()
        self.contact["GridSquare"] = self.edit_contact_dialog.grid.text()
        self.contact["Operator"] = self.edit_contact_dialog.op.text()
        self.contact["MiscText"] = self.edit_contact_dialog.misc.text()
        self.contact["RoverLocation"] = self.edit_contact_dialog.rover_qth.text()

        self.database.change_contact(self.contact)
        self.get_log()
        self.show_like_calls(self.contact.get("Call", ""))

    def delete_contact(self):
        """Delete Contact"""
        self.database.delete_contact(self.contact.get("ID", ""))
        if self.n1mm:
            if self.n1mm.send_contact_packets:
                self.n1mm.contactdelete["timestamp"] = self.contact.get("TS", "")
                self.n1mm.contactdelete["call"] = self.contact.get("Call", "")
                self.n1mm.contactdelete["contestnr"] = self.contact.get("ContestNR", 1)
                self.n1mm.contactdelete["StationName"] = self.pref.get(
                    "n1mm_station_name"
                )
                self.n1mm.contactdelete["ID"] = self.contact.get("ID", "")
                self.n1mm.send_contact_delete()
        self.edit_contact_dialog.close()
        self.get_log()
        self.show_like_calls(self.contact.get("Call", ""))

    def get_log(self):
        """Get Log, Show it."""

        # The horizontal flags are:

        # Constant	Value	Description
        # Qt::AlignLeft	0x0001	Aligns with the left edge.
        # Qt::AlignRight	0x0002	Aligns with the right edge.
        # Qt::AlignHCenter	0x0004	Centers horizontally in the available space.
        # Qt::AlignJustify	0x0008	Justifies the text in the available space.

        # The vertical flags are:

        # Constant	Value	Description
        # Qt::AlignTop	0x0020	Aligns with the top.
        # Qt::AlignBottom	0x0040	Aligns with the bottom.
        # Qt::AlignVCenter	0x0080	Centers vertically in the available space.
        # Qt::AlignBaseline	0x0100	Aligns with the baseline.

        logger.debug("Getting Log")
        self.generalLog.blockSignals(True)
        current_log = self.database.fetch_all_contacts_asc()
        self.generalLog.setRowCount(0)
        for log_item in current_log:
            number_of_rows = self.generalLog.rowCount()
            self.generalLog.insertRow(number_of_rows)
            time_stamp = log_item.get("TS", "YY-MM-DD HH:MM:SS")
            first_item = QtWidgets.QTableWidgetItem(time_stamp)
            self.generalLog.setItem(
                number_of_rows, self.get_column("YYYY-MM-DD HH:MM:SS"), first_item
            )
            self.generalLog.setCurrentItem(first_item, QItemSelectionModel.NoUpdate)
            self.generalLog.item(
                number_of_rows, self.get_column("YYYY-MM-DD HH:MM:SS")
            ).setTextAlignment(0x0004 | 0x0080)

            self.generalLog.setItem(
                number_of_rows,
                self.get_column("Call"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Call", ""))),
            )
            freq = log_item.get("Freq", "")
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("Freq"),
                QtWidgets.QTableWidgetItem(str(round(float(freq), 2))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("Mode"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Mode", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("Snt"),
                QtWidgets.QTableWidgetItem(str(log_item.get("SNT", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("Rcv"),
                QtWidgets.QTableWidgetItem(str(log_item.get("RCV", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("SentNr"),
                QtWidgets.QTableWidgetItem(str(log_item.get("SentNr", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("RcvNr"),
                QtWidgets.QTableWidgetItem(str(log_item.get("NR", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("Exchange1"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Exchange1", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("CK"),
                QtWidgets.QTableWidgetItem(str(log_item.get("CK", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("Prec"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Prec", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("Sect"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Sect", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("WPX"),
                QtWidgets.QTableWidgetItem(str(log_item.get("WPXPrefix", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("Power"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Power", ""))),
            )
            item = QtWidgets.QTableWidgetItem()
            if log_item.get("IsMultiplier1", False):
                item.setIcon(self.checkicon)
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("M1"),
                item,
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("ZN"),
                QtWidgets.QTableWidgetItem(str(log_item.get("ZN", ""))),
            )
            item = QtWidgets.QTableWidgetItem()
            if log_item.get("IsMultiplier2", False):
                item.setIcon(self.checkicon)
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("M2"),
                item,
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("PFX"),
                QtWidgets.QTableWidgetItem(str(log_item.get("CountryPrefix", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("PTS"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Points", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("Name"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Name", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("Comment"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Comment", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                self.get_column("UUID"),
                QtWidgets.QTableWidgetItem(str(log_item.get("ID", ""))),
            )
        self.generalLog.blockSignals(False)

    def watch_udp(self):
        """Puts UDP datagrams in a FIFO queue"""
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
            if json_data.get("cmd", "") == "UPDATELOG":
                logger.debug("External refresh command.")
                self.get_log()
            if json_data.get("cmd", "") == "CALLCHANGED":
                call = json_data.get("call", "")
                self.show_like_calls(call)
            if json_data.get("cmd", "") == "NEWDB":
                self.load_new_db()
            if json_data.get("cmd", "") == "SHOWCOLUMNS":
                for column in range(len(self.columns)):
                    self.generalLog.setColumnHidden(column, True)
                    self.focusedLog.setColumnHidden(column, True)
                columns_to_show = json_data.get("COLUMNS", [])
                for column in columns_to_show:
                    self.generalLog.setColumnHidden(self.get_column(column), False)
                    self.focusedLog.setColumnHidden(self.get_column(column), False)

    def show_like_calls(self, call):
        """Show like calls"""
        if call == "":
            self.focusedLog.setRowCount(0)
            return
        lines = self.database.fetch_like_calls(call)
        debug_line = f"{lines}"
        logger.debug(debug_line)
        self.focusedLog.setRowCount(0)
        for log_item in lines:
            number_of_rows = self.focusedLog.rowCount()
            self.focusedLog.insertRow(number_of_rows)
            time_stamp = log_item.get("TS", "YY-MM-DD HH:MM:SS")
            first_item = QtWidgets.QTableWidgetItem(time_stamp)
            self.focusedLog.setItem(
                number_of_rows, self.get_column("YYYY-MM-DD HH:MM:SS"), first_item
            )
            self.focusedLog.setCurrentItem(first_item, QItemSelectionModel.NoUpdate)
            try:
                self.focusedLog.item(
                    number_of_rows, self.get_column("YYYY-MM-DD HH:MM:SS")
                ).setTextAlignment(0x0004 | 0x0080)
            except AttributeError:
                ...
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("Call"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Call", ""))),
            )
            freq = log_item.get("Freq", "")
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("Freq"),
                QtWidgets.QTableWidgetItem(str(round(float(freq), 2))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("Mode"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Mode", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("Snt"),
                QtWidgets.QTableWidgetItem(str(log_item.get("SNT", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("Rcv"),
                QtWidgets.QTableWidgetItem(str(log_item.get("RCV", ""))),
            )

            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("SentNr"),
                QtWidgets.QTableWidgetItem(str(log_item.get("SentNr", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("RcvNr"),
                QtWidgets.QTableWidgetItem(str(log_item.get("NR", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("Exchange1"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Exchange1", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("CK"),
                QtWidgets.QTableWidgetItem(str(log_item.get("CK", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("Prec"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Prec", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("Sect"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Sect", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("WPX"),
                QtWidgets.QTableWidgetItem(str(log_item.get("WPXPrefix", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("Power"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Power", ""))),
            )
            item = QtWidgets.QTableWidgetItem()
            if log_item.get("IsMultiplier1", False):
                item.setIcon(self.checkicon)
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("M1"),
                item,
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("ZN"),
                QtWidgets.QTableWidgetItem(str(log_item.get("ZN", ""))),
            )
            item = QtWidgets.QTableWidgetItem()
            if log_item.get("IsMultiplier2", False):
                item.setIcon(self.checkicon)
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("M2"),
                item,
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("PFX"),
                QtWidgets.QTableWidgetItem(str(log_item.get("CountryPrefix", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("PTS"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Points", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("Name"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Name", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("Comment"),
                QtWidgets.QTableWidgetItem(str(log_item.get("Comment", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                self.get_column("UUID"),
                QtWidgets.QTableWidgetItem(str(log_item.get("ID", ""))),
            )


def load_fonts_from_dir(directory: str) -> set:
    """
    Well it loads fonts from a directory...
    """
    font_families = set()
    for _fi in QDir(directory).entryInfoList(["*.ttf", "*.woff", "*.woff2"]):
        _id = QFontDatabase.addApplicationFont(_fi.absoluteFilePath())
        font_families |= set(QFontDatabase.applicationFontFamilies(_id))
    return font_families


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

app = QtWidgets.QApplication(sys.argv)
app.setStyle("Adwaita-Dark")
font_path = WORKING_PATH + "/data"
_families = load_fonts_from_dir(os.fspath(font_path))
window = MainWindow()
window.show()

if __name__ == "__main__":
    main()
