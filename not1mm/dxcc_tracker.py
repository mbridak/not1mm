from PyQt6.QtWidgets import QDockWidget, QTableView
from PyQt6.QtSql import QSqlDatabase, QSqlQueryModel, QSqlQuery
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6 import uic
import not1mm.fsutils as fsutils
import os
from json import loads

import logging

logger = logging.getLogger(__name__)


class CustomSqlModel(QSqlQueryModel):
    def data(self, index, role):
        if role == Qt.ItemDataRole.BackgroundRole:
            column = index.column()
            if column < 7:  # Columns 0-6 (CountryPrefix and band columns)
                value = super().data(index, Qt.ItemDataRole.DisplayRole)
                if value and isinstance(value, (int, float)) and value > 0:
                    return QBrush(QColor(44, 138, 44))  # Light green color
                elif value == 0:
                    return QBrush(QColor(155, 100, 100))  # Light red color
        return super().data(index, role)


class DXCCWindow(QDockWidget):
    message = pyqtSignal(dict)
    dbname = None
    db = None
    model = None
    pref = {}

    def __init__(self):
        super().__init__()
        self.active = False
        uic.loadUi(fsutils.APP_DATA_PATH / "dxcc_tracker.ui", self)
        self.setWindowTitle("DXCC Multiplier Tracker")
        self.load_pref()
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.tableView.verticalHeader().setVisible(False)

    def setActive(self, mode: bool):
        self.active = bool(mode)

    def update_model(self):
        self.model = CustomSqlModel(self)
        query = QSqlQuery(self.db)
        query.prepare(
            f"""
            SELECT CountryPrefix,
                SUM(CASE WHEN Band = 1.8 THEN 1 ELSE 0 END) AS '160m',
                SUM(CASE WHEN Band = 3.5 THEN 1 ELSE 0 END) AS '80m',
                SUM(CASE WHEN Band = 7.0 THEN 1 ELSE 0 END) AS '40m',
                SUM(CASE WHEN Band = 14.0 THEN 1 ELSE 0 END) AS '20m',
                SUM(CASE WHEN Band = 21.0 THEN 1 ELSE 0 END) AS '15m',
                SUM(CASE WHEN Band = 28.0 THEN 1 ELSE 0 END) AS '10m',
                COUNT(*) AS Total
            FROM DXLOG where ContestNR = {self.pref.get('contest', 1)} 
            GROUP BY CountryPrefix
            ORDER BY Total DESC
            """
        )
        if not query.exec():
            print("Query failed:", query.lastError().text())
        else:
            self.model.setQuery(query)
            headers = ["DXCC", "160m", "80m", "40m", "20m", "15m", "10m", "Total"]
            for i, header in enumerate(headers):
                self.model.setHeaderData(i, Qt.Orientation.Horizontal, header)
            self.tableView.setModel(self.model)
            self.tableView.resizeColumnsToContents()
            self.tableView.resizeRowsToContents()

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

        self.db.setDatabaseName(f"{self.dbname}")
        if not self.db.open():
            print("Error: Could not open database")
            return
        self.setWindowTitle(
            f"DXCC Tracker - {self.pref.get('current_database', 'ham.db')}"
        )

    def msg_from_main(self, msg):
        """"""
        if msg.get("cmd", "") in ("UPDATELOG", "CONTACTCHANGED", "DELETED"):
            ...
            self.update_model()
        if msg.get("cmd", "") == "NEWDB":
            ...
            self.load_new_db()
            self.update_model()
