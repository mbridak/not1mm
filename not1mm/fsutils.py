#!/usr/bin/env python3

"""
fsutils.py: Filesystem utilities for not1mm.
@kyleboyle
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

from appdata import AppDataPaths

WORKING_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = WORKING_PATH
APP_DATA_PATH = MODULE_PATH / "data"
DATA_PATH = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
DATA_PATH += "/not1mm"
USER_DATA_PATH = Path(DATA_PATH)
_CONFIG_PATH = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
_CONFIG_PATH += "/not1mm"
CONFIG_PATH = Path(_CONFIG_PATH)
CONFIG_FILE = CONFIG_PATH / "not1mm.json"
LOG_FILE = USER_DATA_PATH / "not1mm_debug.log"

# Create directories if they do not exist on Linux systems
if platform.system() not in ["Windows", "Darwin"]:
    Path(CONFIG_PATH).mkdir(parents=True, exist_ok=True)
    Path(USER_DATA_PATH).mkdir(parents=True, exist_ok=True)

# Define and create directories if they do not exist on Windows or Mac systems
if platform.system() in ["Windows", "Darwin"]:
    _app_paths = AppDataPaths(name="not1mm")
    _app_paths.setup()
    LOG_FILE = _app_paths.get_log_file_path(name="appplication.log")
    _DATA_PATH = Path(_app_paths.app_data_path)
    USER_DATA_PATH = _DATA_PATH
    CONFIG_PATH = USER_DATA_PATH
    CONFIG_FILE = CONFIG_PATH / "not1mm.json"


def openFileWithOS(file):
    """Open a file with the default program for that OS."""
    if sys.platform == "win32":
        os.startfile(file)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", file])
    else:
        subprocess.Popen(["xdg-open", file])
