#!/usr/bin/env python3
"""
Single source of truth for reading and writing not1mm.json.

Exposes a Preferences class:
    Preferences.load() -> reads file, merges over _defaults, populates _data
    Preferences.data() -> live reference to the in-memory dict
    Preferences.save() -> atomic write of _data
"""

import logging
import os
from json import dumps, loads
from json.decoder import JSONDecodeError
from pathlib import Path

import not1mm.fsutils as fsutils

logger = logging.getLogger("preferences")


class Preferences:
    _path: Path = fsutils.CONFIG_FILE
    _data: dict = {}
    _defaults: dict = {
        "sounddevice": "default",
        "useqrz": False,
        "lookupusername": "username",
        "lookuppassword": "password",
        "run_state": True,
        "command_buttons": False,
        "cw_macros": True,
        "bands_modes": True,
        "bands": ["160", "80", "40", "20", "15", "10"],
        "current_database": "ham.db",
        "contest": "",
        "multicast_group": "239.1.1.1",
        "multicast_port": 2239,
        "interface_ip": "0.0.0.0",
        "send_rtc_scores": False,
        "rtc_url": "",
        "rtc_user": "",
        "rtc_pass": "",
        "rtc_interval": 2,
        "send_n1mm_packets": False,
        "n1mm_station_name": "20M CW Tent",
        "n1mm_operator": "Bernie",
        "n1mm_radioport": "127.0.0.1:12060",
        "n1mm_contactport": "127.0.0.1:12060",
        "n1mm_lookupport": "127.0.0.1:12060",
        "n1mm_scoreport": "127.0.0.1:12060",
        "usehamdb": False,
        "usehamqth": False,
        "cloudlog": False,
        "cloudlogapi": "",
        "cloudlogurl": "",
        "CAT_ip": "127.0.0.1",
        "userigctld": False,
        "useflrig": False,
        "cwip": "127.0.0.1",
        "cwport": 6789,
        "cwtype": 0,
        "useserver": False,
        "im_the_master": False,
        "CAT_port": 4532,
        "cluster_server": "dxc.nc7j.com",
        "cluster_port": 7373,
        "cluster_filter": "Set DX Filter SpotterCont=NA",
        "cluster_mode": "OPEN",
        "cluster_expire": 1,
        "logwindow": False,
        "bandmapwindow": False,
        "checkwindow": False,
        "vfowindow": False,
        "ratewindow": False,
        "statisticswindow": False,
        "darkmode": True,
    }

    @classmethod
    def load(cls) -> dict:
        """Read the prefs file, merge over defaults, populate _data.

        Pure stdlib + logger. Never touches Qt.
        Missing file -> write defaults, return them.
        Parse error  -> log critical, return defaults.
        """
        if os.path.exists(cls._path):
            try:
                with open(cls._path, "rt", encoding="utf-8") as file_descriptor:
                    raw = loads(file_descriptor.read())
                    cls._data = {**cls._defaults, **raw}
            except (JSONDecodeError, ValueError, TypeError) as exc:
                logger.critical("Error parsing %s: %s", cls._path, exc)
                cls._data = cls._defaults.copy()
        else:
            logger.info("No preference file. Writing a new one to %s.", cls._path)
            cls._data = cls._defaults.copy()
            cls.save()
        return cls._data

    @classmethod
    def data(cls) -> dict:
        """Live reference to the in-memory dict. Mutations are visible to all callers."""
        return cls._data

    @classmethod
    def save(cls) -> None:
        """Atomic write: tmp file then os.replace()."""
        path = Path(cls._path)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            with open(tmp_path, "wt", encoding="utf-8") as file_descriptor:
                file_descriptor.write(dumps(cls._data, indent=4))
            os.replace(tmp_path, path)
        except (IOError, TypeError, ValueError) as exc:
            logger.critical("writepreferences: %s", exc)
