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
    """The RTC Service class."""

    poll_callback = pyqtSignal(dict)
    delta = 2  # two minutes
    poll_time = datetime.datetime.now() + datetime.timedelta(minutes=delta)
    time_to_quit = False
    xml = ""

    def __init__(self):
        super().__init__()
        self.pref = self.get_settings()
        self.delta = self.pref.get("rtc_interval", 2)

    def run(self) -> None:
        """Send score xml object to rtc scoring site."""
        while not self.time_to_quit:
            # if self.pref.get("send_rtc_scores", False) is True:
            if datetime.datetime.now() > self.poll_time:
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
                        print(f"{self.xml=}\n{result=}\n{result.text}")
                    except requests.exceptions.Timeout:
                        print("RTC post timeout.")
                    except requests.exceptions.RequestException as e:
                        print(f"An RTC post error occurred: {e}")
                else:
                    print("No XML data")
                try:
                    self.poll_callback.emit({"success": True})
                except QEventLoop:
                    ...
            QThread.msleep(1)

    def get_settings(self) -> dict:
        """Get the settings."""
        if os.path.exists(fsutils.CONFIG_FILE):
            with open(fsutils.CONFIG_FILE, "rt", encoding="utf-8") as file_descriptor:
                return loads(file_descriptor.read())
