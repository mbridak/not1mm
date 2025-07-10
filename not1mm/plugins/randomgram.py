"""RandomGram plugin"""

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member, unused-import

import logging
import os

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)
EXCHANGE_HINT = ""
name = "RandomGram"
cabrillo_name = "RANDOMGRAM"
mode = "CW"  # CW SSB BOTH RTTY
columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 4

rgGroupsPath = os.path.join(os.path.expanduser("~"), "rg.txt")
try:
    with open(rgGroupsPath, "r") as f:
        rgGroups = f.readlines()
except:
    rgGroups = []


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
    self.snt_label.setText("SNT")
    self.field1.setAccessibleName("RST Sent")
    self.other_label.setText("SentRG")
    self.field3.setAccessibleName("Sent RandomGram")
    self.exch_label.setText("RcvRG")
    self.field4.setAccessibleName("Received RandomGram")


def reset_label(self):
    """reset label after field cleared"""


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.sent,
        self.sent: self.receive,
        self.receive: self.other_1,
        self.other_1: self.other_2,
        self.other_2: self.callsign,
    }


def set_tab_prev(self):
    """Set TAB Advances"""
    self.tab_prev = {
        self.callsign: self.other_2,
        self.sent: self.callsign,
        self.receive: self.sent,
        self.other_1: self.receive,
        self.other_2: self.other_1,
    }


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["Comment"] = self.other_2.text()
    self.contact["SentNr"] = self.other_1.text()
    self.contact["NR"] = self.other_2.text()


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""
    qso_count = show_qso(self)
    if len(rgGroups) <= qso_count:
        return

    nextRG = rgGroups[qso_count]
    if len(nextRG) > 0:
        self.other_1.setText(nextRG)


def points(self):
    """Calc point"""
    return 2


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


def process_esm(self, new_focused_widget=None, with_enter=False):
    """ESM State Machine"""

    # self.pref["run_state"]

    # -----===== Assigned F-Keys =====-----
    # self.esm_dict["CQ"]
    # self.esm_dict["EXCH"]
    # self.esm_dict["QRZ"]
    # self.esm_dict["AGN"]
    # self.esm_dict["HISCALL"]
    # self.esm_dict["MYCALL"]
    # self.esm_dict["QSOB4"]

    # ----==== text fields ====----
    # self.callsign
    # self.sent
    # self.receive
    # self.other_1
    # self.other_2

    if new_focused_widget is not None:
        self.current_widget = self.inputs_dict.get(new_focused_widget)

    # print(f"checking esm {self.current_widget=} {with_enter=} {self.pref.get("run_state")=}")

    for a_button in [
        self.F1,
        self.F2,
        self.F3,
        self.F4,
        self.F5,
        self.F6,
        self.F7,
        self.F8,
        self.F9,
        self.F10,
        self.F11,
        self.F12,
    ]:
        self.restore_button_color(a_button)

    buttons_to_send = []

    if self.pref.get("run_state"):
        if self.current_widget == "callsign":
            if len(self.callsign.text()) < 3:
                self.make_button_green(self.esm_dict["CQ"])
                buttons_to_send.append(self.esm_dict["CQ"])
            elif len(self.callsign.text()) > 2:
                self.make_button_green(self.esm_dict["HISCALL"])
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append(self.esm_dict["HISCALL"])
                buttons_to_send.append(self.esm_dict["EXCH"])

        #        elif self.current_widget in ["other_1", "other_2"]:
        #            if self.other_2.text() == "" and self.other_1.text() == "":
        #                self.make_button_green(self.esm_dict["AGN"])
        #                buttons_to_send.append(self.esm_dict["AGN"])
        #            else:
        #                self.make_button_green(self.esm_dict["QRZ"])
        #                buttons_to_send.append(self.esm_dict["QRZ"])
        #                buttons_to_send.append("LOGIT")

        elif self.current_widget in ["other_1", "other_2"]:
            buttons_to_send.append("LOGIT")

        if with_enter is True and bool(len(buttons_to_send)):
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        self.save_contact()
                        continue
                    self.process_function_key(button)
    else:
        if self.current_widget == "callsign":
            if len(self.callsign.text()) > 2:
                self.make_button_green(self.esm_dict["MYCALL"])
                buttons_to_send.append(self.esm_dict["MYCALL"])

        #        elif self.current_widget in ["other_1", "other_2"]:
        #            if self.other_2.text() == "" and self.other_1.text() == "":
        #                self.make_button_green(self.esm_dict["AGN"])
        #                buttons_to_send.append(self.esm_dict["AGN"])
        #            else:
        #                self.make_button_green(self.esm_dict["EXCH"])
        #                buttons_to_send.append(self.esm_dict["EXCH"])
        #                buttons_to_send.append("LOGIT")

        elif self.current_widget in ["other_1", "other_2"]:
            buttons_to_send.append("LOGIT")

        if with_enter is True and bool(len(buttons_to_send)):
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        self.save_contact()
                        continue
                    self.process_function_key(button)


def populate_history_info_line(self):
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(
            f"{result.get('Call', '')}, {result.get('Name', '')}, {result.get('UserText','...')}"
        )
    else:
        self.history_info.setText("")


def check_call_history(self):
    """"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText','')}")
        if self.other_1.text() == "":
            self.other_1.setText(f"{result.get('Name', '')}")
