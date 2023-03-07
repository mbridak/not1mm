#!/usr/bin/env python3
"""
K6GTE Contest logger
Email: michael.bridak@gmail.com
GPL V3
"""

# pylint: disable=too-many-lines
# pylint: disable=invalid-name
# pylint: disable=no-member
# pylint: disable=no-name-in-module
# pylint: disable=c-extension-no-member
# pylint: disable=unused-import

from math import radians, sin, cos, atan2, sqrt, asin, pi
import sys
import socket
import os
import logging
import threading
import uuid
import queue
import time
from itertools import chain

from json import dumps, loads, JSONDecodeError
from datetime import datetime, timedelta
from pathlib import Path
from shutil import copyfile

import requests

try:
    from not1mm.lib.database import DataBase
    from not1mm.lib.version import __version__
except ModuleNotFoundError:
    from lib.database import DataBase
    from lib.version import __version__


class main:
    """test"""

    def __init__(self):
        # create the DB
        # self.db = DataBase("file::memory:?cache=shared")
        self.db = DataBase("testdb.db", ".")
        self.db_object = None

    def run(self):
        """run"""
        # Set persistent values for contact
        # self.db.empty_contact["app"] = "K6GTELogger"
        self.db.empty_contact["StationPrefix"] = "K6GTE"
        self.db.empty_contact["Operator"] = "K6GTE"
        self.db.empty_contact["ContestName"] = "CQWWCW"
        self.db.empty_contact["ContestNR"] = "1"
        # self.db.empty_contact["StationName"] = "20M CW"

        # get clean contact object with persistent changes from above
        self.db_object = self.db.get_empty()

        # Make changes to save to the DB
        self.db_object["ID"] = uuid.uuid4().hex
        self.db_object["TS"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.db_object["Band"] = 14.0
        self.db_object["QSXFreq"] = 14030.0
        self.db_object["Freq"] = 14030.0
        self.db_object["CountryPrefix"] = "K"
        self.db_object["Continent"] = "NA"
        self.db_object["SNT"] = "599"
        self.db_object["SentNr"] = 1
        self.db_object["RCV"] = "599"
        self.db_object["NR"] = 37
        self.db_object["GridSquare"] = "DM13at"
        self.db_object["Sect"] = "ORG"
        self.db_object["QTH"] = "Their Home"
        self.db_object["Name"] = "Russ"
        self.db_object["Power"] = "100"
        self.db_object["Points"] = 2
        self.db_object["Call"] = "K5TUX"
        self.db_object["Mode"] = "CW"

        # Save the contact to the DB
        self.db.log_contact(self.db_object)
        print(f"\nSaved Data:\n{self.db.fetch_all_contacts_asc()}\n\n")

        # save changes
        self.db_object["QSXFreq"] = 14027.0
        self.db_object["Freq"] = 14027.0
        self.db.change_contact(self.db_object)
        print(f"\nUpdated Data:\n{self.db.fetch_all_contacts_asc()}\n\n")

        # get unique id of record
        # uniqid = self.db.get_unique_id(1)
        # print(f"Unique ID: {uniqid}")

        # fetch descending
        print(f"\nSorted Descending Data:\n{self.db.fetch_all_contacts_desc()}\n\n")

        # fetch last record
        print(f"\nGet last contact:\n{self.db.fetch_last_contact()}\n\n")

        # fetch all dirty
        # print(f"\nGet all marked dirty:\n{self.db.fetch_all_dirty_contacts()}\n\n")

        # fetch all dirty
        print(f"\nDeleting Contact:\n{self.db.delete_contact(1)}\n\n")


logger = logging.getLogger("__main__")
handler = logging.StreamHandler()
formatter = logging.Formatter(
    datefmt="%H:%M:%S",
    fmt="[%(asctime)s] %(levelname)s %(module)s - %(funcName)s Line %(lineno)d:\n%(message)s",
)
handler.setFormatter(formatter)
logger.addHandler(handler)

if Path("./debug").exists():
    # if True:
    logger.setLevel(logging.DEBUG)
    logger.debug("debugging on")
else:
    logger.setLevel(logging.WARNING)
    logger.warning("debugging off")

if __name__ == "__main__":
    app = main()
    app.run()
