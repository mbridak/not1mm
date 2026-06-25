"""TA VHF UHF Contest"""

import logging
from not1mm.lib.ham_utility import distance
from not1mm.lib.plugin_common import gen_adif, get_points
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "# + 6char grid"

name = "TA VHF UHF"
mode = "BOTH"
cabrillo_name = "TA-VHF-UHF"

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
    "Exchange1",
    "PTS",
]

advance_on_space = [True, True, True, True, False]
dupe_type = 3


def init_contest(self):
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_2

def reset_label(self):
    pass

def predupe(self):
    pass  

def interface(self):
    self.field1.show()   # callsign
    self.field2.show()   # sent RST
    self.field3.show()   # receive RST
    self.field4.show()   # exchange field

    self.snt_label.setText("SNT")
    self.other_label.setText("SNTNR")
    self.exch_label.setText("RCV NR + GRID")

    self.sent.setText("599")
    self.receive.setText("599")

    self.sent.setReadOnly(True)
    self.receive.setReadOnly(True)

def set_tab_next(self):
    self.tab_next = {
        self.callsign: self.sent,
        self.sent: self.receive,
        self.receive: self.other_1,
        self.other_1: self.other_2,
        self.other_2: self.callsign,
    }


def set_tab_prev(self):
    self.tab_prev = {
        self.callsign: self.other_2,
        self.sent: self.callsign,
        self.receive: self.sent,
        self.other_1: self.receive,
        self.other_2: self.other_1,
    }

def parse_exchange(self):
    exchange = self.other_2.text().upper().split()

    sn = ""
    grid = ""

    for t in exchange:
        if t.isdigit() and sn == "":
            sn = t
        elif len(t) == 6 and t.isalnum():
            grid = t

    return sn, grid

def set_contact_vars(self):
    sn, grid = parse_exchange(self)

    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()

    self.contact["NR"] = sn
    self.contact["Exchange1"] = grid

    self.contact["SentNr"] = self.other_1.text()

    try:
        next_sn = int(self.current_sn) + 1
        self.other_1.setText(str(next_sn).zfill(3))
    except:
        pass

def prefill(self):
    serial_nr = str(self.current_sn).zfill(3)

    if self.other_1.text() == "":
        self.other_1.setText(serial_nr)

def points(self):
    if self.contact_is_dupe > 0:
        return 0

    band = self.contact.get("Band", "")
    their_grid = self.contact.get("Exchange1", "")

    km = distance(self.station.get("GridSquare", ""), their_grid)

    mult = {
        "50": 1,
        "144": 2,
        "432": 3,
    }.get(str(band), 1)

    return max(1, int(km * mult))


def show_mults(self, rtc=None):
    return 0


def show_qso(self):
    result = self.database.fetch_qso_count()
    return int(result.get("qsos", 0)) if result else 0


def calc_score(self):
    result = self.database.fetch_points()
    if result:
        return int(result.get("Points", 0) or 0)
    return 0


def adif(self):
    gen_adif(self, cabrillo_name)


def recalculate_mults(self):
    pass
