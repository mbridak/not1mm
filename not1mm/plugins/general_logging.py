"""General Logging plugin"""

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member, unused-import

import logging

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, get_points
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)
EXCHANGE_HINT = ""
name = "General Logging"
cabrillo_name = "General-Logging"
mode = "BOTH"  # CW SSB BOTH RTTY
columns = [0, 1, 2, 3, 4, 16, 17]
columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Mode",
    "Snt",
    "Rcv",
    "Name",
    "Comment",
]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 4


def init_contest(self):
    """setup plugin"""
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_1


def interface(self):
    """Setup user interface"""
    self.field1.show()
    self.field2.show()
    self.field3.show()
    self.field4.show()
    self.snt_label.setText("SNT")
    self.field1.setAccessibleName("RST Sent")
    label = self.field3.findChild(QtWidgets.QLabel)
    label.setText("Name")
    self.field3.setAccessibleName("Name")
    label = self.field4.findChild(QtWidgets.QLabel)
    label.setText("Comment")
    self.field4.setAccessibleName("Comment")


def reset_label(self):
    """reset label after field cleared"""


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
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["Name"] = self.other_1.text()
    self.contact["Comment"] = self.other_2.text()


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""


def points(self):
    """Calc point"""


def show_mults(self):
    """Return display string for mults"""


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score"""
    result = self.database.fetch_points()


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name)


def cabrillo(self, file_encoding):
    """Generates Cabrillo file. Maybe."""


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""
