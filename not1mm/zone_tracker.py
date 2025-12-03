from PyQt6.QtWidgets import QDockWidget
from PyQt6.QtGui import QBrush, QColor

# from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6 import uic, QtWidgets
import not1mm.fsutils as fsutils
from not1mm.lib.database import DataBase
import os
from json import loads

import logging

logger = logging.getLogger(__name__)


class ZoneWindow(QDockWidget):
    message = pyqtSignal(dict)
    dbname = None
    db = None
    model = None
    pref = {}
    columns = {
        0: "Zone",
        1: "160m",
        2: "80m",
        3: "40m",
        4: "20m",
        5: "15m",
        6: "10m",
        7: "Total",
    }

    def __init__(self, action):
        super().__init__()
        self.action = action
        self.active = False
        uic.loadUi(fsutils.APP_DATA_PATH / "zone_tracker.ui", self)
        self.zone_table.setColumnCount(len(self.columns))
        for column_number, column_name in self.columns.items():
            self.zone_table.setHorizontalHeaderItem(
                column_number, QtWidgets.QTableWidgetItem(column_name)
            )
        self.setWindowTitle("Zone Tracker")
        self.load_pref()

        self.dbname = fsutils.USER_DATA_PATH / self.pref.get(
            "current_database", "ham.db"
        )
        self.database = DataBase(self.dbname, fsutils.USER_DATA_PATH)

        self.database.current_contest = self.pref.get("contest", 0)

        self.get_log()
        self.zone_table.resizeColumnsToContents()
        self.zone_table.resizeRowsToContents()

    def setActive(self, mode: bool):
        self.active = bool(mode)

    def get_log(self):
        """zone_table"""

        # result=[
        # {'ZN': '4', '160m': 0, '80m': 0, '40m': 0, '20m': 7, '15m': 0, '10m': 0, 'Total': 7},
        # {'ZN': '6', '160m': 0, '80m': 0, '40m': 0, '20m': 1, '15m': 0, '10m': 0, 'Total': 1},
        # {'ZN': '21', '160m': 0, '80m': 0, '40m': 0, '20m': 1, '15m': 0, '10m': 0, 'Total': 1}
        # ]

        if not self.active:
            return

        result = self.database.fetch_zone_by_band_count()
        self.zone_table.setRowCount(0)
        for row_number, row_data in enumerate(result):
            self.zone_table.insertRow(row_number)
            for column, data in enumerate(row_data.values()):
                item = QtWidgets.QTableWidgetItem(str(data))
                if column > 0 and column < 7:
                    if data == 0:
                        item.setBackground(QBrush(QColor(44, 138, 44)))
                    else:
                        item.setBackground(QBrush(QColor(155, 100, 100)))
                self.zone_table.setItem(row_number, column, item)
        self.zone_table.resizeColumnsToContents()
        self.zone_table.resizeRowsToContents()

    def scrollToZone(self, item: str):
        """Scrolls zone table to the item"""
        if (
            self.active is True
            and self.isVisible()
            and isinstance(item, str)
            and self.scrolltoCheckBox.isChecked()
        ):
            matchingitems = self.zone_table.findItems(
                item.upper(), Qt.MatchFlag.MatchExactly
            )
            if matchingitems:
                matcheditem = matchingitems[0]  # take the first
                self.zone_table.scrollToItem(matcheditem)

    def load_pref(self) -> None:
        """
        Loads the preferences from the config file into the self.pref dictionary.

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
                    logger.info("%s", self.pref)
            else:
                self.pref["current_database"] = "ham.db"

        except IOError as exception:
            logger.critical("Error: %s", exception)

    def load_new_db(self) -> None:
        """
        If the database changes reload it.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        self.load_pref()
        self.dbname = fsutils.USER_DATA_PATH / self.pref.get(
            "current_database", "ham.db"
        )
        self.database = DataBase(self.dbname, fsutils.APP_DATA_PATH)
        self.database.current_contest = self.pref.get("contest", 0)
        self.contact = self.database.empty_contact
        self.get_log()

    def msg_from_main(self, msg):
        """"""
        if self.active is True and self.isVisible():
            if msg.get("cmd", "") in (
                "UPDATELOG",
                "CONTACTCHANGED",
                "DELETE",
                "DELETED",
            ):
                ...
                self.get_log()
            if msg.get("cmd", "") == "NEWDB":
                ...
                self.load_new_db()
                self.get_log()
            if msg.get("cmd", "") == "SCROLLTOZone":
                if self.cqButton.isChecked():
                    self.scrollToZone(str(msg.get("cq", "")))
                else:
                    self.scrollToZone(str(msg.get("itu", "")))

    def closeEvent(self, event) -> None:
        self.action.setChecked(False)
