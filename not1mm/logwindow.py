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
import queue
import socket
import sys
import time
import threading

from json import JSONDecodeError, loads, dumps
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets, uic, Qt
from PyQt5.QtCore import QDir, QItemSelectionModel
from PyQt5.QtGui import QFontDatabase

from not1mm.lib.database import DataBase
from not1mm.lib.multicast import Multicast
from not1mm.lib.edit_contact import EditContact

# from not1mm.lib.n1mm import N1MM

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
MULTICAST_GROUP = "224.1.1.1"
INTERFACE_IP = "0.0.0.0"
# NODE_RED_SERVER_IP = "127.0.0.1"
# NODE_RED_SERVER_PORT = 12062

# n1mm_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)


class MainWindow(QtWidgets.QMainWindow):
    """
    The main window
    """

    # dbname = DATA_PATH + "/ham.db"
    dbname = sys.argv[1] if len(sys.argv) > 1 else DATA_PATH + "/ham.db"
    edit_contact_dialog = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._udpwatch = None
        self.udp_fifo = queue.Queue()
        self.database = DataBase(self.dbname, WORKING_PATH)
        self.contact = self.database.empty_contact
        data_path = WORKING_PATH + "/data/logwindow.ui"
        uic.loadUi(data_path, self)
        self.generalLog.setColumnCount(14)
        self.focusedLog.setColumnCount(14)
        icon_path = WORKING_PATH + "/data/"
        self.checkmark = QtGui.QPixmap(icon_path + "check.png")
        self.checkicon = QtGui.QIcon()
        self.checkicon.addPixmap(self.checkmark)
        self.generalLog.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.generalLog.customContextMenuRequested.connect(self.edit_contact_selected)
        self.generalLog.setHorizontalHeaderItem(
            0, QtWidgets.QTableWidgetItem("YYYY-MM-DD HH:MM:SS")
        )
        self.generalLog.verticalHeader().setVisible(False)
        self.generalLog.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem("Call"))
        self.generalLog.setHorizontalHeaderItem(2, QtWidgets.QTableWidgetItem("Freq"))
        self.generalLog.setHorizontalHeaderItem(3, QtWidgets.QTableWidgetItem("Snt"))
        self.generalLog.setHorizontalHeaderItem(4, QtWidgets.QTableWidgetItem("Rcv"))
        self.generalLog.setHorizontalHeaderItem(5, QtWidgets.QTableWidgetItem("SentNr"))
        self.generalLog.setHorizontalHeaderItem(6, QtWidgets.QTableWidgetItem("RcvNr"))
        self.generalLog.setHorizontalHeaderItem(7, QtWidgets.QTableWidgetItem("WPX"))
        self.generalLog.setHorizontalHeaderItem(8, QtWidgets.QTableWidgetItem("M1"))
        self.generalLog.setHorizontalHeaderItem(9, QtWidgets.QTableWidgetItem("ZN"))
        self.generalLog.setHorizontalHeaderItem(10, QtWidgets.QTableWidgetItem("M2"))
        self.generalLog.setHorizontalHeaderItem(11, QtWidgets.QTableWidgetItem("PFX"))
        self.generalLog.setHorizontalHeaderItem(12, QtWidgets.QTableWidgetItem("PTS"))
        self.generalLog.setHorizontalHeaderItem(13, QtWidgets.QTableWidgetItem("UUID"))
        self.generalLog.setColumnWidth(0, 200)
        self.generalLog.setColumnWidth(3, 50)
        self.generalLog.setColumnWidth(4, 50)
        self.generalLog.setColumnWidth(5, 75)
        self.generalLog.setColumnWidth(6, 75)
        self.generalLog.setColumnWidth(7, 50)
        self.generalLog.setColumnWidth(8, 50)
        self.generalLog.setColumnWidth(9, 50)
        self.generalLog.setColumnWidth(12, 50)
        self.generalLog.cellDoubleClicked.connect(self.double_clicked)
        self.generalLog.cellChanged.connect(self.cell_changed)
        self.generalLog.setColumnHidden(9, True)
        self.generalLog.setColumnHidden(10, True)
        self.generalLog.setColumnHidden(11, True)
        self.generalLog.setColumnHidden(13, True)

        self.focusedLog.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.focusedLog.customContextMenuRequested.connect(
            self.edit_focused_contact_selected
        )
        self.focusedLog.setHorizontalHeaderItem(
            0, QtWidgets.QTableWidgetItem("YYYY-MM-DD HH:MM:SS")
        )
        self.focusedLog.verticalHeader().setVisible(False)
        self.focusedLog.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem("Call"))
        self.focusedLog.setHorizontalHeaderItem(2, QtWidgets.QTableWidgetItem("Freq"))
        self.focusedLog.setHorizontalHeaderItem(3, QtWidgets.QTableWidgetItem("Snt"))
        self.focusedLog.setHorizontalHeaderItem(4, QtWidgets.QTableWidgetItem("Rcv"))
        self.focusedLog.setHorizontalHeaderItem(5, QtWidgets.QTableWidgetItem("SentNr"))
        self.focusedLog.setHorizontalHeaderItem(6, QtWidgets.QTableWidgetItem("RcvNr"))
        self.focusedLog.setHorizontalHeaderItem(7, QtWidgets.QTableWidgetItem("WPX"))
        self.focusedLog.setHorizontalHeaderItem(8, QtWidgets.QTableWidgetItem("M1"))
        self.focusedLog.setHorizontalHeaderItem(9, QtWidgets.QTableWidgetItem("ZN"))
        self.focusedLog.setHorizontalHeaderItem(10, QtWidgets.QTableWidgetItem("M2"))
        self.focusedLog.setHorizontalHeaderItem(11, QtWidgets.QTableWidgetItem("PFX"))
        self.focusedLog.setHorizontalHeaderItem(12, QtWidgets.QTableWidgetItem("PTS"))
        self.focusedLog.setHorizontalHeaderItem(13, QtWidgets.QTableWidgetItem("UUID"))
        self.focusedLog.setColumnWidth(0, 200)
        self.focusedLog.setColumnWidth(3, 50)
        self.focusedLog.setColumnWidth(4, 50)
        self.focusedLog.setColumnWidth(5, 75)
        self.focusedLog.setColumnWidth(6, 75)
        self.focusedLog.setColumnWidth(7, 50)
        self.focusedLog.setColumnWidth(8, 50)
        self.focusedLog.setColumnWidth(9, 50)
        self.focusedLog.setColumnWidth(12, 50)
        # self.focusedLog.cellDoubleClicked.connect(self.double_clicked)
        # self.focusedLog.cellChanged.connect(self.cell_changed)
        self.focusedLog.setColumnHidden(9, True)
        self.focusedLog.setColumnHidden(10, True)
        self.focusedLog.setColumnHidden(11, True)
        self.focusedLog.setColumnHidden(13, True)
        self.get_log()
        self.multicast_interface = Multicast(
            MULTICAST_GROUP, MULTICAST_PORT, INTERFACE_IP
        )

        if self._udpwatch is None:
            self._udpwatch = threading.Thread(
                target=self.watch_udp,
                daemon=True,
            )
            self._udpwatch.start()

        # self.n1mm = N1MM(
        #     ip_address=self.preference.get("n1mm_ip"),
        #     radioport=self.preference.get("n1mm_radioport"),
        #     contactport=self.preference.get("n1mm_contactport"),
        # )

    def double_clicked(self, _row, _column):
        """Slot for doubleclick event"""
        if self.table_loading:
            return
        logger.debug("DoubleClicked")

    def cell_changed(self, row, column):
        """Slot for changed cell"""
        if self.table_loading:
            return
        db_record = {
            "TS": self.generalLog.item(row, 0).text(),
            "Call": self.generalLog.item(row, 1).text().upper(),
            "Freq": self.generalLog.item(row, 2).text(),
            "SNT": self.generalLog.item(row, 3).text(),
            "RCV": self.generalLog.item(row, 4).text(),
            "SentNr": self.generalLog.item(row, 5).text(),
            "NR": self.generalLog.item(row, 6).text(),
            "WPXPrefix": self.generalLog.item(row, 7).text(),
            "IsMultiplier1": self.generalLog.item(row, 8).text(),
            "ZN": self.generalLog.item(row, 9).text(),
            "IsMultiplier2": self.generalLog.item(row, 10).text().upper(),
            "CountryPrefix": self.generalLog.item(row, 11).text(),
            "Points": self.generalLog.item(row, 12).text(),
            "ID": self.generalLog.item(row, 13).text(),
        }
        self.database.change_contact(db_record)
        self.get_log()
        self.generalLog.scrollToItem(self.generalLog.item(row, column))

    def dummy(self):
        """the dummy"""

    def edit_focused_contact_selected(self, clicked_cell):
        """Show edit contact dialog"""
        logger.debug("Opening EditContact dialog")
        item = self.focusedLog.itemAt(clicked_cell)
        uuid = self.focusedLog.item(item.row(), 13).text()
        self.edit_contact(uuid)

    def edit_contact_selected(self, clicked_cell):
        """Show edit contact dialog"""
        logger.debug("Opening EditContact dialog")
        item = self.generalLog.itemAt(clicked_cell)
        uuid = self.generalLog.item(item.row(), 13).text()
        self.edit_contact(uuid)

    def edit_contact(self, uuid):
        """Show edit contact dialog"""
        logger.debug("Edit: %s", uuid)
        self.edit_contact_dialog = EditContact(WORKING_PATH)
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
        self.edit_contact_dialog.close()
        self.get_log()
        self.show_like_calls(self.contact.get("Call", ""))

    def get_log(self):
        """Get Log, Show it."""
        self.generalLog.cellChanged.connect(self.dummy)
        self.table_loading = True
        current_log = self.database.fetch_all_contacts_asc()
        self.generalLog.setRowCount(0)
        for log_item in current_log:
            number_of_rows = self.generalLog.rowCount()
            self.generalLog.insertRow(number_of_rows)
            time_stamp = log_item.get("TS", "YY-MM-DD HH:MM:SS")
            first_item = QtWidgets.QTableWidgetItem(time_stamp)
            self.generalLog.setItem(number_of_rows, 0, first_item)
            self.generalLog.setCurrentItem(first_item, QItemSelectionModel.NoUpdate)
            self.generalLog.item(number_of_rows, 0).setTextAlignment(0x0004)

            self.generalLog.setItem(
                number_of_rows,
                1,
                QtWidgets.QTableWidgetItem(str(log_item.get("Call", ""))),
            )
            freq = log_item.get("Freq", "")
            self.generalLog.setItem(
                number_of_rows,
                2,
                QtWidgets.QTableWidgetItem(str(round(float(freq), 2))),
            )
            self.generalLog.setItem(
                number_of_rows,
                3,
                QtWidgets.QTableWidgetItem(str(log_item.get("SNT", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                4,
                QtWidgets.QTableWidgetItem(str(log_item.get("RCV", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                5,
                QtWidgets.QTableWidgetItem(str(log_item.get("SentNr", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                6,
                QtWidgets.QTableWidgetItem(str(log_item.get("NR", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                7,
                QtWidgets.QTableWidgetItem(str(log_item.get("WPXPrefix", ""))),
            )
            item = QtWidgets.QTableWidgetItem()
            if log_item.get("IsMultiplier1", False):
                item.setIcon(self.checkicon)
            self.generalLog.setItem(
                number_of_rows,
                8,
                item,
            )
            self.generalLog.setItem(
                number_of_rows,
                9,
                QtWidgets.QTableWidgetItem(str(log_item.get("ZN", ""))),
            )
            item = QtWidgets.QTableWidgetItem()
            if log_item.get("IsMultiplier2", False):
                item.setIcon(self.checkicon)
            self.generalLog.setItem(
                number_of_rows,
                10,
                item,
            )
            self.generalLog.setItem(
                number_of_rows,
                11,
                QtWidgets.QTableWidgetItem(str(log_item.get("CountryPrefix", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                12,
                QtWidgets.QTableWidgetItem(str(log_item.get("Points", ""))),
            )
            self.generalLog.setItem(
                number_of_rows,
                13,
                QtWidgets.QTableWidgetItem(str(log_item.get("ID", ""))),
            )
        self.table_loading = False
        self.generalLog.cellChanged.connect(self.cell_changed)

    # def testing(self, a):
    #     """ignore"""
    #     item = self.generalLog.itemAt(a)
    #     if item:
    #         print(
    #             f"{item.row()}, {item.column()} {item.icon().isNull()}*TESTING*"
    #         )

    def watch_udp(self):
        """Puts UDP datagrams in a FIFO queue"""
        while True:
            try:
                datagram = self.multicast_interface.server_udp.recv(1500)
                logger.debug(datagram.decode())
            except socket.timeout:
                time.sleep(0.1)
                continue
            if datagram:
                self.udp_fifo.put(datagram)

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
            self.focusedLog.setItem(number_of_rows, 0, first_item)
            self.focusedLog.setCurrentItem(first_item, QItemSelectionModel.NoUpdate)
            try:
                self.focusedLog.item(number_of_rows, 0).setTextAlignment(0x0004)
            except AttributeError:
                ...
            self.focusedLog.setItem(
                number_of_rows,
                1,
                QtWidgets.QTableWidgetItem(str(log_item.get("Call", ""))),
            )
            freq = log_item.get("Freq", "")
            self.focusedLog.setItem(
                number_of_rows,
                2,
                QtWidgets.QTableWidgetItem(str(round(float(freq), 2))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                3,
                QtWidgets.QTableWidgetItem(str(log_item.get("SNT", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                4,
                QtWidgets.QTableWidgetItem(str(log_item.get("RCV", ""))),
            )

            self.focusedLog.setItem(
                number_of_rows,
                5,
                QtWidgets.QTableWidgetItem(str(log_item.get("SentNr", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                6,
                QtWidgets.QTableWidgetItem(str(log_item.get("NR", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                7,
                QtWidgets.QTableWidgetItem(str(log_item.get("WPXPrefix", ""))),
            )

            item = QtWidgets.QTableWidgetItem()
            if log_item.get("IsMultiplier1", False):
                item.setIcon(self.checkicon)
            self.focusedLog.setItem(
                number_of_rows,
                8,
                item,
            )
            self.focusedLog.setItem(
                number_of_rows,
                9,
                QtWidgets.QTableWidgetItem(str(log_item.get("ZN", ""))),
            )
            item = QtWidgets.QTableWidgetItem()
            if log_item.get("IsMultiplier2", False):
                item.setIcon(self.checkicon)
            self.focusedLog.setItem(
                number_of_rows,
                10,
                item,
            )
            self.focusedLog.setItem(
                number_of_rows,
                11,
                QtWidgets.QTableWidgetItem(str(log_item.get("CountryPrefix", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                12,
                QtWidgets.QTableWidgetItem(str(log_item.get("Points", ""))),
            )
            self.focusedLog.setItem(
                number_of_rows,
                13,
                QtWidgets.QTableWidgetItem(str(log_item.get("ID", ""))),
            )

    def check_udp_traffic(self):
        """Checks UDP Traffic"""
        while not self.udp_fifo.empty():
            datagram = self.udp_fifo.get()
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
            if json_data.get("cmd", "") == "UPDATELOG":
                logger.debug("External refresh command.")
                self.get_log()
            if json_data.get("cmd", "") == "CALLCHANGED":
                call = json_data.get("call", "")
                self.show_like_calls(call)


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
    timer.start(1000)
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
font_path = WORKING_PATH + "/data"
_families = load_fonts_from_dir(os.fspath(font_path))
window = MainWindow()
window.setWindowTitle("Log Display")
window.show()
timer = QtCore.QTimer()
timer.timeout.connect(window.check_udp_traffic)

if __name__ == "__main__":
    main()
