#!/usr/bin/env python3
"""
not1mm Contest logger
Email: michael.bridak@gmail.com
GPL V3
Class: RTCService
Purpose: Service to post 'real time' scores.
"""

# pylint: disable=unused-import, c-extension-no-member, no-member, invalid-name, too-many-lines
# pylint: disable=logging-fstring-interpolation, line-too-long, no-name-in-module

import datetime
import logging
import os
from json import loads

import requests
from requests.auth import HTTPBasicAuth

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QEventLoop

import not1mm.fsutils as fsutils

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
        if os.path.exists(fsutils.CONFIG_FILE):
            with open(fsutils.CONFIG_FILE, "rt", encoding="utf-8") as file_descriptor:
                return loads(file_descriptor.read())
