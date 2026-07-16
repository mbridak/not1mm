#!/usr/bin/env python3
"""
not1mm Contest logger
Email: michael.bridak@gmail.com
GPL V3
Class: RTCService
Purpose: Service to post 'real time' scores.
"""

import datetime
import logging

import requests
from PyQt6.QtCore import QEventLoop, QObject, QThread, pyqtSignal
from requests.auth import HTTPBasicAuth

from not1mm.lib.preferences import Preferences

logger = logging.getLogger(__name__)


class RTCService(QObject):
    """The Real Time Score Reporting Service class."""

    rtc_callback: pyqtSignal = pyqtSignal(dict)
    delta: int = 2  # two minutes
    poll_time: datetime.datetime = datetime.datetime.now() + datetime.timedelta(
        minutes=delta
    )
    time_to_quit: bool = False
    xml: str = ""

    def __init__(self):
        super().__init__()
        self.pref = self.get_settings()
        self.delta = self.pref.get("rtc_interval", 2)

    def run(self) -> None:
        """Send score xml object to rtc scoring site."""
        while not self.time_to_quit:
            # if self.pref.get("send_rtc_scores", False) is True:
            if datetime.datetime.now() > self.poll_time:
                response = ""
                self.poll_time = datetime.datetime.now() + datetime.timedelta(
                    minutes=self.delta
                )
                if len(self.xml):
                    headers = {"Content-Type": "text/xml"}
                    try:
                        result = requests.post(
                            self.pref.get("rtc_url", ""),
                            data=self.xml,
                            headers=headers,
                            auth=HTTPBasicAuth(
                                self.pref.get("rtc_user", ""),
                                self.pref.get("rtc_pass", ""),
                            ),
                            timeout=30,
                        )
                        response = f"{result.status_code}|{result.reason}|{result.text}"
                    except requests.exceptions.Timeout:
                        response = "RTC post timeout."
                    except requests.exceptions.RequestException as e:
                        response = f"An RTC post error occurred: {e}"
                else:
                    response = "No XML data"
                try:
                    self.rtc_callback.emit({"result": response})
                except QEventLoop:
                    ...
            QThread.msleep(1)

    def get_settings(self) -> dict:
        """Get the settings."""
        return Preferences.data()
