import datetime
import logging
import os

# import sys

from PyQt6 import uic, QtWidgets
from PyQt6.QtWidgets import QDockWidget
from PyQt6.QtCore import pyqtSignal, QTimer

# from PyQt6.QtGui import QColorConstants, QPalette, QColor

import not1mm.fsutils as fsutils
from not1mm.lib.database import DataBase

from json import loads
from json.decoder import JSONDecodeError

logger = logging.getLogger(__name__)


class StatsWindow(QDockWidget):
    """The stats window. Shows something important."""

    message = pyqtSignal(dict)
    dbname = None
    pref = {}
    poll_time = datetime.datetime.now() + datetime.timedelta(milliseconds=1000)

    def __init__(self):
        super().__init__()
        self.active = False
        self.load_pref()
        self.dbname = fsutils.USER_DATA_PATH / self.pref.get(
            "current_database", "ham.db"
        )
        self.database = DataBase(self.dbname, fsutils.APP_DATA_PATH)
        self.database.current_contest = self.pref.get("contest", 0)
        self.load_pref()
        self.dbname = fsutils.USER_DATA_PATH / self.pref.get(
            "current_database", "ham.db"
        )
        self.database = DataBase(self.dbname, fsutils.APP_DATA_PATH)
        self.database.current_contest = self.pref.get("contest", 0)
        uic.loadUi(fsutils.APP_DATA_PATH / "statistics.ui", self)
        self.timer = QTimer()
        self.timer.timeout.connect(self.get_run_and_total_qs)
        self.timer.start(5000)

    def msg_from_main(self, packet):
        """"""
        if packet.get("cmd", "") == "DARKMODE":
            self.setDarkMode(packet.get("state", False))
            return

        if self.active is False:
            return

        if packet.get("cmd", "") == "UPDATELOG":
            logger.debug("External refresh command.")
            self.get_run_and_total_qs()
            return

        if packet.get("cmd", "") == "NEWDB":
            self.load_pref()
            self.dbname = fsutils.USER_DATA_PATH / self.pref.get(
                "current_database", "ham.db"
            )
            self.database = DataBase(self.dbname, fsutils.APP_DATA_PATH)
            self.database.current_contest = self.pref.get("contest", 0)

    def setActive(self, mode: bool) -> None:
        self.active = bool(mode)

    def setDarkMode(self, dark: bool) -> None:
        """Forces a darkmode palette."""

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

        except (IOError, JSONDecodeError) as exception:
            logger.critical("Error: %s", exception)
        self.setDarkMode(self.pref.get("darkmode", False))

    def get_run_and_total_qs(self):
        """get numbers"""
        if self.active is False:
            return
        self.tableWidget.clear()
        self.tableWidget.setColumnCount(7)
        self.tableWidget.setHorizontalHeaderLabels(
            ["BAND", "QSO", "CALLS", "CW", "PH", "DI", "PTS"]
        )
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.tableWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection
        )
        query = f"select DISTINCT(Band) as band from DXLOG where ContestNR = {self.database.current_contest};"
        result = self.database.exec_sql_mult(query)
        self.tableWidget.setRowCount(len(result) + 1)
        row = 0
        for band in result:
            query = f"select count(*) as qs, count(DISTINCT(Call)) as calls, sum(Points) as points from DXLOG where ContestNR = {self.database.current_contest} and Band = '{band['band']}';"
            result = self.database.exec_sql(query)
            item = QtWidgets.QTableWidgetItem(str(band["band"]))
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 0, item)
            item = QtWidgets.QTableWidgetItem(str(result["qs"]))
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 1, item)
            item = QtWidgets.QTableWidgetItem(str(result["calls"]))
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 2, item)
            item = QtWidgets.QTableWidgetItem(str(result["points"]))
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 6, item)
            query = f"select sum(sortedmode.mode == 'CW') as CW, sum(sortedmode.mode == 'PH') as PH, sum(sortedmode.mode == 'DI') as DI from (select CASE Mode WHEN 'LSB' THEN 'PH' WHEN 'USB' THEN 'PH' WHEN 'CW' THEN 'CW' WHEN 'RTTY' THEN 'DI' ELSE 'OTHER' END mode from DXLOG where ContestNR = {self.database.current_contest} and Band = '{band['band']}') as sortedmode;"
            result = self.database.exec_sql(query)
            item = QtWidgets.QTableWidgetItem(str(result["CW"]))
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 3, item)
            item = QtWidgets.QTableWidgetItem(str(result["PH"]))
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 4, item)
            item = QtWidgets.QTableWidgetItem(str(result["DI"]))
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 5, item)

            row += 1
        query = f"select count(*) as qs, count(DISTINCT(Call)) as calls, sum(Points) as points from DXLOG where ContestNR = {self.database.current_contest};"
        result = self.database.exec_sql(query)
        item = QtWidgets.QTableWidgetItem("TOTAL")
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 0, item)
        item = QtWidgets.QTableWidgetItem(str(result["qs"]))
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 1, item)
        item = QtWidgets.QTableWidgetItem(str(result["calls"]))
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 2, item)
        item = QtWidgets.QTableWidgetItem(str(result["points"]))
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 6, item)

        query = f"select sum(sortedmode.mode == 'CW') as CW, sum(sortedmode.mode == 'PH') as PH, sum(sortedmode.mode == 'DI') as DI from (select CASE Mode WHEN 'LSB' THEN 'PH' WHEN 'USB' THEN 'PH' WHEN 'CW' THEN 'CW' WHEN 'RTTY' THEN 'DI' ELSE 'OTHER' END mode from DXLOG where ContestNR = {self.database.current_contest}) as sortedmode;"
        result = self.database.exec_sql(query)
        item = QtWidgets.QTableWidgetItem(str(result["CW"]))
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 3, item)
        item = QtWidgets.QTableWidgetItem(str(result["PH"]))
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 4, item)
        item = QtWidgets.QTableWidgetItem(str(result["DI"]))
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 5, item)
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.resizeRowsToContents()


if __name__ == "__main__":
    print("This is not a program.\nTry Again.")
