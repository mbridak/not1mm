"""ARRL plugin"""

# pylint: disable=invalid-name, unused-argument, unused-variable

import logging
from pathlib import Path
from PyQt5 import QtWidgets
from not1mm.lib.version import __version__

logger = logging.getLogger("__main__")

name = "ARRL Sweepstakes CW"
cabrillo_name = "ARRL-SWEEPSTAKES-CW"
mode = "CW"  # CW SSB BOTH RTTY
columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
    "CK",
    "Prec",
    "Sect",
    "M1",
    "PTS",
]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 1


def init_contest(self):
    """setup plugin"""
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_2


def interface(self):
    """Setup user interface"""
    self.field1.show()
    self.field2.show()
    self.field3.show()
    self.field4.show()
    label = self.field3.findChild(QtWidgets.QLabel)
    label.setText("SentNR")
    label = self.field4.findChild(QtWidgets.QLabel)
    label.setText("sn prec ck sec")


def reset_label(self):
    """reset label after field cleared"""
    self.exch_label.setText("sn prec ck sec")


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.field1.findChild(QtWidgets.QLineEdit),
        self.field1.findChild(QtWidgets.QLineEdit): self.field2.findChild(
            QtWidgets.QLineEdit
        ),
        self.field2.findChild(QtWidgets.QLineEdit): self.field3.findChild(
            QtWidgets.QLineEdit
        ),
        self.field3.findChild(QtWidgets.QLineEdit): self.field4.findChild(
            QtWidgets.QLineEdit
        ),
        self.field4.findChild(QtWidgets.QLineEdit): self.callsign,
    }


def set_tab_prev(self):
    """Set TAB Advances"""
    self.tab_prev = {
        self.callsign: self.field4.findChild(QtWidgets.QLineEdit),
        self.field1.findChild(QtWidgets.QLineEdit): self.callsign,
        self.field2.findChild(QtWidgets.QLineEdit): self.field1.findChild(
            QtWidgets.QLineEdit
        ),
        self.field3.findChild(QtWidgets.QLineEdit): self.field2.findChild(
            QtWidgets.QLineEdit
        ),
        self.field4.findChild(QtWidgets.QLineEdit): self.field3.findChild(
            QtWidgets.QLineEdit
        ),
    }


def set_contact_vars(self):
    """Contest Specific"""
    sn, prec, ck, sec, call = parse_exchange(self)
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.other_1.text()
    self.contact["NR"] = sn
    self.contact["Prec"] = prec
    self.contact["CK"] = ck
    self.contact["Sect"] = sec
    self.contact["Call"] = call
    result = self.database.fetch_sect_exists(sec)
    if result.get("sect_count"):
        self.contact["IsMultiplier1"] = 0
    else:
        self.contact["IsMultiplier1"] = 1


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""
    result = self.database.get_serial()
    serial_nr = str(result.get("serial_nr", "1"))
    if serial_nr == "None":
        serial_nr = "1"
    field = self.field3.findChild(QtWidgets.QLineEdit)
    if len(field.text()) == 0:
        field.setText(serial_nr)


def points(self):
    """Calc point"""
    return 2


def show_mults(self):
    """Return display string for mults"""
    sql = f"select count(DISTINCT(Sect)) as mults from dxlog where ContestNR = {self.database.current_contest};"
    result = self.database.exec_sql(sql)
    return int(result.get("mults", 0))


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def get_points(self):
    """Return raw points before mults"""
    result = self.database.fetch_points()
    logger.debug("%s", f"{result}")
    if result:
        points = result.get("Points", "0")
        if points is None:
            return 0
        return int(result.get("Points", "0"))
    return 0


def calc_score(self):
    """Return calculated score"""
    points = get_points(self)
    mults = show_mults(self)
    return points * mults


def adif(self):
    """
    Creates an ADIF file of the contacts made.
    """


def cabrillo(self):
    """Generates Cabrillo file. Maybe."""


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""
    all_contacts = self.database.fetch_all_contacts_asc()
    for contact in all_contacts:
        time_stamp = contact.get("TS")
        sec = contact.get("Sect")
        result = self.database.fetch_sect_exists_before_me(sec, time_stamp)
        sect_count = result.get("sect_count", 1)
        if sect_count == 0:
            contact["IsMultiplier1"] = 1
        else:
            contact["IsMultiplier1"] = 0
        self.database.change_contact(contact)


def parse_exchange(self):
    """Parse exchange..."""
    exchange = self.other_2.text()
    exchange = exchange.upper()
    sn = ""
    prec = ""
    ck = ""
    sec = ""
    call = self.callsign.text()

    for tokens in exchange.split():
        text = ""
        numb = ""
        print(f"'{tokens}'")
        if tokens.isdigit():
            print(f"{tokens} is digits")
            if sn == "":
                sn = tokens
            else:
                ck = tokens
            continue
        elif tokens.isalpha():
            print(f"{tokens} is alpha")
            if len(tokens) == 1:
                prec = tokens
            else:
                sec = tokens
            continue
        elif tokens.isalnum():
            print("isalnum")
            if tokens[:1].isalpha():
                print(f"{tokens} is callsign")
                call = tokens
                continue
            for i, c in enumerate(tokens):
                if c.isalpha():
                    text = tokens[i:]
                    numb = tokens[:i]
                    print(f"{tokens[:i]} {tokens[i:]}")
                    break
            if len(text) == 1:
                prec = text
                sn = numb
            else:
                sec = text
                ck = numb
    label = f"sn:{sn} p:{prec} cl:{call} ck:{ck} sec:{sec}"
    self.exch_label.setText(label)
    return (sn, prec, ck, sec, call)
