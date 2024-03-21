#!/usr/bin/env python3

import os
import sys
import subprocess
from pathlib import Path

from appdata import AppDataPaths

WORKING_PATH = Path(os.path.dirname(os.path.abspath(__file__)))

MODULE_PATH = WORKING_PATH
APP_DATA_PATH = MODULE_PATH / "data"

_app_paths = AppDataPaths(name='not1mm')
_app_paths.setup()

LOG_FILE = _app_paths.get_log_file_path(name='appplication.log')
_DATA_PATH = Path(_app_paths.app_data_path)

if os.environ.get("XDG_DATA_HOME", None):
    _DATA_PATH = Path(os.environ.get("XDG_DATA_HOME"))
    LOG_FILE = _DATA_PATH / 'application.log'

USER_DATA_PATH = _DATA_PATH
CONFIG_PATH = USER_DATA_PATH
CONFIG_FILE = CONFIG_PATH / "not1mm.json"

DARK_STYLESHEET = ""

def openFileWithOS(file):
    if sys.platform == 'win32':
        os.startfile(file)
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', file])
    else:
        subprocess.Popen(['xdg-open', file])
        #os.system(f"xdg-open {fsutils.USER_DATA_PATH / macro_file}")
