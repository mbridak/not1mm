import datetime
import logging

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDockWidget, QTableWidgetItem

from not1mm import fsutils
from not1mm.lib.database import DataBase
from not1mm.lib.i18n import load_ui
from not1mm.lib.preferences import Preferences

logger = logging.getLogger(__name__)


class StatsWindow(QDockWidget):
    """The stats window. Shows something important."""

    message = pyqtSignal(dict)
    dbname = None
    pref = {}  # noqa: RUF012
    poll_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        milliseconds=1000
    )
    statisticswindow_closed = pyqtSignal()

    def __init__(self, action):
        super().__init__()
        self.action = action
        self.active: bool = False
        self.load_pref()
        self.dbname: str = fsutils.USER_DATA_PATH / self.pref.get(
            "current_database", "ham.db"
        )
        self.database: DataBase = DataBase(self.dbname, fsutils.APP_DATA_PATH)
        self.database.current_contest = self.pref.get("contest", 0)
        load_ui(self, fsutils.APP_DATA_PATH / "statistics.ui")

    def msg_from_main(self, packet):
        """Process messages from the main window."""
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

        if packet.get("cmd", "") in (
            "CONTACTCHANGED",
            "UPDATELOG",
            "DELETE",
            "DELETED",
        ):
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
        self.pref = Preferences.data()

    def _set_cell(self, row: int, col: int, value, none_as: str = "0") -> None:
        """Put a right-aligned value in the table."""
        item = QTableWidgetItem(str(value).replace("None", none_as))
        item.setTextAlignment(0x0002)
        self.tableWidget.setItem(row, col, item)

    def get_run_and_total_qs(self):
        """get numbers"""
        if self.active is False:
            return
        contest = self.database.current_contest
        self.tableWidget.clear()
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tableWidget.setColumnCount(10)
        self.tableWidget.setHorizontalHeaderLabels(
            ["BAND", "QSO", "CALLS", "CW", "PH", "DI", "WPX", "CTY", "ZN", "PTS"]
        )
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.tableWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection
        )

        mode_case = (
            "CASE WHEN Mode IN ('LSB','USB','SSB','FM','AM') THEN 'PH' "
            "WHEN Mode IN ('CW','CW-U','CW-L','CW-R','CWR') THEN 'CW' "
            "WHEN Mode IN ('FT8','FT4','RTTY','PSK31','FSK441','MSK144','JT65','JT9','Q65') THEN 'DI' "
            "ELSE 'OTHER' END"
        )

        query = f"select DISTINCT(Band) as band from DXLOG where ContestNR = {contest} ORDER BY band DESC;"
        bands = self.database.exec_sql_mult(query)
        self.tableWidget.setRowCount(len(bands) + 1)
        row = 0
        for band in bands:
            query = (
                "select count(*) as qs, "
                "count(DISTINCT(WPXPrefix)) as wpx, "
                "count(DISTINCT(Call)) as calls, "
                "count(DISTINCT(NULLIF(CountryPrefix, ''))) as countries, "
                "count(DISTINCT(NULLIF(ZN, 0))) as zones, "
                "sum(Points) as points "
                f"from DXLOG where ContestNR = {contest} and Band = '{band['band']}';"
            )
            result = self.database.exec_sql(query)
            self._set_cell(row, 0, band.get("band", ""), none_as="")
            self._set_cell(row, 1, result.get("qs", "0"))
            self._set_cell(row, 2, result.get("calls", "0"))
            self._set_cell(row, 6, result.get("wpx", "0"))
            self._set_cell(row, 7, result.get("countries", "0"))
            self._set_cell(row, 8, result.get("zones", "0"))
            self._set_cell(row, 9, result.get("points", "0"))

            query = (
                "select sum(sortedmode.mode == 'CW') as CW, "
                "sum(sortedmode.mode == 'PH') as PH, "
                "sum(sortedmode.mode == 'DI') as DI "
                f"from (select {mode_case} mode from DXLOG "
                f"where ContestNR = {contest} and Band = '{band['band']}') as sortedmode;"
            )
            result = self.database.exec_sql(query)
            self._set_cell(row, 3, result.get("CW", "0"))
            self._set_cell(row, 4, result.get("PH", "0"))
            self._set_cell(row, 5, result.get("DI", "0"))
            row += 1

        # TOTAL row (multipliers counted per band, same as the existing WPX total)
        query = (
            "select count(*) as qs, "
            "count(DISTINCT(Call)) as calls, "
            "count(DISTINCT(WPXPrefix || ':' || Band)) as wpx, "
            "count(DISTINCT(CASE WHEN CountryPrefix != '' THEN CountryPrefix || ':' || Band END)) as countries, "
            "count(DISTINCT(CASE WHEN ZN > 0 THEN ZN || ':' || Band END)) as zones, "
            "sum(Points) as points "
            f"from DXLOG where ContestNR = {contest};"
        )
        result = self.database.exec_sql(query)
        self._set_cell(row, 0, "TOTAL")
        self._set_cell(row, 1, result.get("qs", "0"))
        self._set_cell(row, 2, result.get("calls", "0"))
        self._set_cell(row, 6, result.get("wpx", "0"))
        self._set_cell(row, 7, result.get("countries", "0"))
        self._set_cell(row, 8, result.get("zones", "0"))
        self._set_cell(row, 9, result.get("points", "0"))

        query = (
            "select sum(sortedmode.mode == 'CW') as CW, "
            "sum(sortedmode.mode == 'PH') as PH, "
            "sum(sortedmode.mode == 'DI') as DI "
            f"from (select {mode_case} mode from DXLOG "
            f"where ContestNR = {contest}) as sortedmode;"
        )
        result = self.database.exec_sql(query)
        self._set_cell(row, 3, result.get("CW", "0"))
        self._set_cell(row, 4, result.get("PH", "0"))
        self._set_cell(row, 5, result.get("DI", "0"))

        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.resizeRowsToContents()

    def closeEvent(self, event) -> None:
        self.action.setChecked(False)
        self.statisticswindow_closed.emit()
        event.accept()


if __name__ == "__main__":
    print("This is not a program.\nTry Again.")
