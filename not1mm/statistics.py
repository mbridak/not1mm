import datetime
import logging
import os

# import sys

from PyQt6 import uic, QtWidgets
from PyQt6.QtWidgets import QDockWidget, QTableWidgetItem
from PyQt6.QtCore import pyqtSignal, Qt

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
        self.active: bool = False
        self.load_pref()
        self.dbname: str = fsutils.USER_DATA_PATH / self.pref.get(
            "current_database", "ham.db"
        )
        self.database: DataBase = DataBase(self.dbname, fsutils.APP_DATA_PATH)
        self.database.current_contest = self.pref.get("contest", 0)
        uic.loadUi(fsutils.APP_DATA_PATH / "statistics.ui", self)

    def msg_from_main(self, packet):
        """"""
        if packet.get("cmd", "") == "NEWDB":
            self.load_pref()
            self.dbname: str = fsutils.USER_DATA_PATH / self.pref.get(
                "current_database", "ham.db"
            )
            self.database: DataBase = DataBase(self.dbname, fsutils.APP_DATA_PATH)
            self.database.current_contest = self.pref.get("contest", 0)
            self.get_run_and_total_qs()

        if self.active is False:
            return

        if packet.get("cmd", "") in ("CONTACTCHANGED", "UPDATELOG", "DELETED"):
            self.get_run_and_total_qs()
            return

    def setActive(self, mode: bool) -> None:
        self.active: bool = bool(mode)

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

    def get_run_and_total_qs(self):
        """get numbers"""
        if self.active is False:
            return
        self.tableWidget.clear()
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
            item: QTableWidgetItem = QTableWidgetItem(
                str(band.get("band", "")).replace("None", "")
            )
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 0, item)
            item: QTableWidgetItem = QTableWidgetItem(
                str(result.get("qs", "0")).replace("None", "0")
            )
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 1, item)
            item: QTableWidgetItem = QTableWidgetItem(
                str(result.get("calls", "0")).replace("None", "0")
            )
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 2, item)
            item: QTableWidgetItem = QTableWidgetItem(
                str(result.get("points", "0")).replace("None", "0")
            )
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 6, item)
            query: str = (
                f"select sum(sortedmode.mode == 'CW') as CW, sum(sortedmode.mode == 'PH') as PH, sum(sortedmode.mode == 'DI') as DI from (select CASE WHEN Mode IN ('LSB','USB','SSB','FM','AM') THEN 'PH' WHEN Mode IN ('CW','CW-R') THEN 'CW' WHEN Mode IN ('FT8','FT4','RTTY','PSK31','FSK441','MSK144','JT65','JT9','Q65') THEN 'DI' ELSE 'OTHER' END mode from DXLOG where ContestNR = {self.database.current_contest} and Band = '{band['band']}') as sortedmode;"
            )
            result: dict = self.database.exec_sql(query)
            item: QTableWidgetItem = QTableWidgetItem(
                str(result.get("CW", "0")).replace("None", "0")
            )
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 3, item)
            item: QTableWidgetItem = QTableWidgetItem(
                str(result.get("PH", "0")).replace("None", "0")
            )
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 4, item)
            item: QTableWidgetItem = QTableWidgetItem(
                str(result.get("DI", "0")).replace("None", "0")
            )
            item.setTextAlignment(0x0002)
            self.tableWidget.setItem(row, 5, item)

            row += 1
        query: str = (
            f"select count(*) as qs, count(DISTINCT(Call)) as calls, sum(Points) as points from DXLOG where ContestNR = {self.database.current_contest};"
        )
        result: dict = self.database.exec_sql(query)
        item: QTableWidgetItem = QTableWidgetItem("TOTAL")
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 0, item)
        item: QTableWidgetItem = QTableWidgetItem(
            str(result.get("qs", "0")).replace("None", "0")
        )
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 1, item)
        item: QTableWidgetItem = QTableWidgetItem(
            str(result.get("calls", "0")).replace("None", "0")
        )
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 2, item)
        item: QTableWidgetItem = QTableWidgetItem(
            str(result.get("points", "0")).replace("None", "0")
        )
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 6, item)

        query: str = (
            f"select sum(sortedmode.mode == 'CW') as CW, sum(sortedmode.mode == 'PH') as PH, sum(sortedmode.mode == 'DI') as DI from (select CASE WHEN Mode IN ('LSB','USB','SSB','FM','AM') THEN 'PH' WHEN Mode IN ('CW','CW-R') THEN 'CW' WHEN Mode In ('FT8','FT4','RTTY','PSK31','FSK441','MSK144','JT65','JT9','Q65') THEN 'DI' ELSE 'OTHER' END mode from DXLOG where ContestNR = {self.database.current_contest}) as sortedmode;"
        )
        result: dict = self.database.exec_sql(query)
        item: QTableWidgetItem = QTableWidgetItem(
            str(result.get("CW", "0")).replace("None", "0")
        )
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 3, item)
        item: QTableWidgetItem = QTableWidgetItem(
            str(result.get("PH", "0")).replace("None", "0")
        )
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 4, item)
        item: QTableWidgetItem = QTableWidgetItem(
            str(result.get("DI", "0")).replace("None", "0")
        )
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, 5, item)
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.resizeRowsToContents()


if __name__ == "__main__":
    print("This is not a program.\nTry Again.")
