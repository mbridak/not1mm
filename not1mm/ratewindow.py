#!/usr/bin/env python3
"""
not1mm Contest logger
Email: michael.bridak@gmail.com
GPL V3
Class: RateWindow
Purpose: not sure yet
"""
# pylint: disable=no-name-in-module, unused-import, no-member, invalid-name, c-extension-no-member
# pylint: disable=logging-fstring-interpolation, line-too-long

import datetime
import logging
import os

from PyQt6 import uic
from PyQt6.QtWidgets import QDockWidget
from PyQt6.QtCore import pyqtSignal, QTimer

import not1mm.fsutils as fsutils
from not1mm.lib.database import DataBase

from json import loads
from json.decoder import JSONDecodeError

logger = logging.getLogger(__name__)


class RateWindow(QDockWidget):
    """The rate window. Shows something important."""

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

        uic.loadUi(fsutils.APP_DATA_PATH / "ratewindow.ui", self)
        self.timer = QTimer()
        self.timer.timeout.connect(self.get_run_and_total_qs)
        self.timer.start(1000)

    def msg_from_main(self, packet):
        """"""

        if packet.get("cmd", "") == "NEWDB":
            self.load_pref()
            self.dbname = fsutils.USER_DATA_PATH / self.pref.get(
                "current_database", "ham.db"
            )
            self.database = DataBase(self.dbname, fsutils.APP_DATA_PATH)
            self.database.current_contest = self.pref.get("contest", 0)

    def setActive(self, mode: bool):
        self.active = bool(mode)

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

        # last_hour
        # 10_last_qso
        # hundred_last_qso
        # since_lasthour_label since_lasthour
        # --------------------
        # time_on
        # time_off
        # --------------------
        # run_qso
        # sandp_qso
        # hour_run_qso
        # hour_sandp_qso
        # --------------------
        # avg_km
        # avg_pts
        # --------------------
        # time_by_mult
        # qso_counts
        # mult_counts
        # mult_worth
        # {'runs': 3, 'totalqs': 3}

        # WHERE datetime(timestamp) > datetime(current_timestamp, '-60 minutes')

        if not self.active or not self.isVisible():
            return
        # Get Q's in the 60 Minutes
        query = f"select (julianday(MAX(ts)) -  julianday(MIN(ts))) * 24 * 60 as timespan, count(*) as items from (select * from dxlog where ContestNR = {self.database.current_contest} and datetime(TS) > datetime(current_timestamp, '-60 minutes'));"
        result = self.database.exec_sql(query)
        if result.get("items", 0) < 1:
            self.last_hour.setText("--- Q/h")
        elif result.get("items", 0) == 1:
            self.last_hour.setText("1 Q/h")
        else:
            try:
                perhour = (60.0 / result.get("timespan", 60)) * result.get("items", 0)
                self.last_hour.setText(str(f"{perhour:.2f} Q/h"))
            except (ZeroDivisionError, TypeError):
                ...

        # Get Q's per hour rate of the last 10 QSO's
        query = f"SELECT (julianday(MAX(ts)) -  julianday(MIN(ts))) * 24 * 60 as timespan, count(*) as items FROM ( select * from DXLOG where ContestNR = {self.database.current_contest} ORDER by ts DESC limit 10);"
        result = self.database.exec_sql(query)
        if result.get("items", 0) < 10:
            self.ten_last_qso.setText("--- Q/h")
        else:
            try:
                perhour = (60.0 / result.get("timespan", 60)) * result.get("items", 0)
                self.ten_last_qso.setText(str(f"{perhour:.2f} Q/h"))
            except (ZeroDivisionError, TypeError):
                ...

        # Get Q's per hour rate of the last 100 QSO's
        query = f"SELECT (julianday(MAX(ts)) -  julianday(MIN(ts))) * 24 * 60 as timespan, count(*) as items FROM (select * from DXLOG where ContestNR = {self.database.current_contest} ORDER by ts DESC limit 100);"
        result = self.database.exec_sql(query)
        if result.get("items", 0) < 100:
            self.hundred_last_qso.setText("--- Q/h")
        else:
            try:
                perhour = (60.0 / result.get("timespan", 60)) * result.get("items", 0)
                self.hundred_last_qso.setText(str(f"{perhour:.2f} Q/h"))
            except (ZeroDivisionError, TypeError):
                ...

        # Get rate for the current hour
        query = f"SELECT strftime('%Y-%m-%d %H:00:00','now') as limit_stamp, strftime('%H00','now') as current_hour, count(*) as items FROM DXLOG where ContestNR = {self.database.current_contest} and datetime(TS) > limit_stamp;"
        result = self.database.exec_sql(query)

        self.since_lasthour_label.setText(
            f"Since {result.get('current_hour', '0000')}z:"
        )
        self.since_lasthour.setText(f"{result.get('items', '0')} QSO")

        # Get Run QSO's and S&P QSO's
        query = f"select sum(IsRunQSO) as runs, count(*) as totalqs from dxlog where ContestNR = {self.database.current_contest};"
        result = self.database.exec_sql(query)
        try:
            sandp = result.get("totalqs", 0) - result.get("runs", 0)
            self.run_qso.setText(f"{result.get('runs', 0)}")
            self.sandp_qso.setText(f"{sandp}")
        except TypeError:
            ...

        # Get runs for the current hour
        query = f"SELECT strftime('%Y-%m-%d %H:00:00','now') as limit_stamp, sum(IsRunQSO) as runs, count(*) as totalqs FROM DXLOG where ContestNR = {self.database.current_contest} and datetime(TS) > limit_stamp;"
        result = self.database.exec_sql(query)
        try:
            sandp = result.get("totalqs", 0) - result.get("runs", 0)
            self.hour_run_qso.setText(f"{result.get('runs', 0)}")
            self.hour_sandp_qso.setText(f"{sandp}")
        except TypeError:
            ...
