from PyQt6.QtWidgets import QMainWindow, QTableView
from PyQt6.QtSql import QSqlDatabase, QSqlQueryModel, QSqlQuery
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtCore import Qt
from PyQt6 import uic
import not1mm.fsutils as fsutils
import os

class CustomSqlModel(QSqlQueryModel):
    def data(self, index, role):
        if role == Qt.ItemDataRole.BackgroundRole:
            column = index.column()
            if column < 7:  # Columns 0-6 (CountryPrefix and band columns)
                value = super().data(index, Qt.ItemDataRole.DisplayRole)
                if value and isinstance(value, (int, float)) and value > 0:
                    return QBrush(QColor(144, 238, 144))  # Light green color
                elif value == 0:
                    return QBrush(QColor(255, 200, 200))  # Light red color
        return super().data(index, role)

class DXCCTrackerWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(fsutils.APP_DATA_PATH / "dxcc_tracker.ui", self)
        self.setWindowTitle("DXCC Multiplier Tracker")
        self.tableView.verticalHeader().setVisible(False)
        
        # Connect to the local database
        db_path = os.path.join(os.path.dirname(__file__), "cqww_se0i.db") ### Should be changed to "current_database"
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName(db_path)
        if not self.db.open():
            print("Error: Could not open database")
            return

        self.model = CustomSqlModel(self)
        self.update_model()
        self.tableView.setModel(self.model)

    def update_model(self):
        query = QSqlQuery(self.db)
        query.prepare("""
        SELECT CountryPrefix,
            SUM(CASE WHEN Band = 1.8 THEN 1 ELSE 0 END) AS '160m',
            SUM(CASE WHEN Band = 3.5 THEN 1 ELSE 0 END) AS '80m',
            SUM(CASE WHEN Band = 7.0 THEN 1 ELSE 0 END) AS '40m',
            SUM(CASE WHEN Band = 14.0 THEN 1 ELSE 0 END) AS '20m',
            SUM(CASE WHEN Band = 21.0 THEN 1 ELSE 0 END) AS '15m',
            SUM(CASE WHEN Band = 28.0 THEN 1 ELSE 0 END) AS '10m',
            COUNT(*) AS Total
        FROM DXLOG
        GROUP BY CountryPrefix
        ORDER BY Total DESC
        """)
        if not query.exec():
            print("Query failed:", query.lastError().text())
        else:
            self.model.setQuery(query)
            headers = ["DXCC", "160m", "80m", "40m", "20m", "15m", "10m", "Total"]
            for i, header in enumerate(headers):
                self.model.setHeaderData(i, Qt.Orientation.Horizontal, header)
