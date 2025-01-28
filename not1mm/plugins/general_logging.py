"""General Logging plugin"""

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member, unused-import

import logging

from PyQt6 import QtWidgets

from not1mm.lib.ham_utility import get_logged_band
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
    self.other_label.setText("Name")
    self.field3.setAccessibleName("Name")
    self.exch_label.setText("Comment")
    self.field4.setAccessibleName("Comment")


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


def set_self(the_outie):
    """..."""
    globals()["ALTEREGO"] = the_outie


def ft8_handler(the_packet: dict):
    """Process FT8 QSO packets
    FT8
    {
        'CALL': 'KE0OG',
        'GRIDSQUARE': 'DM10AT',
        'MODE': 'FT8',
        'RST_SENT': '',
        'RST_RCVD': '',
        'QSO_DATE': '20210329',
        'TIME_ON': '183213',
        'QSO_DATE_OFF': '20210329',
        'TIME_OFF': '183213',
        'BAND': '20M',
        'FREQ': '14.074754',
        'STATION_CALLSIGN': 'K6GTE',
        'MY_GRIDSQUARE': 'DM13AT',
        'CONTEST_ID': 'ARRL-FIELD-DAY',
        'SRX_STRING': '1D UT',
        'CLASS': '1D',
        'ARRL_SECT': 'UT'
    }
    FlDigi
    {
        'FREQ': '7.029500',
        'CALL': 'DL2DSL',
        'MODE': 'RTTY',
        'NAME': 'BOB',
        'QSO_DATE': '20240904',
        'QSO_DATE_OFF': '20240904',
        'TIME_OFF': '212825',
        'TIME_ON': '212800',
        'RST_RCVD': '599',
        'RST_SENT': '599',
        'BAND': '40M',
        'COUNTRY': 'FED. REP. OF GERMANY',
        'CQZ': '14',
        'STX': '000',
        'STX_STRING': '1D ORG',
        'CLASS': '1D',
        'ARRL_SECT': 'DX',
        'TX_PWR': '0',
        'OPERATOR': 'K6GTE',
        'STATION_CALLSIGN': 'K6GTE',
        'MY_GRIDSQUARE': 'DM13AT',
        'MY_CITY': 'ANAHEIM, CA',
        'MY_STATE': 'CA'
    }

    """
    # print(f"\n{the_packet=}\n")
    if ALTEREGO is not None:
        ALTEREGO.callsign.setText(the_packet.get("CALL"))
        ALTEREGO.contact["Call"] = the_packet.get("CALL", "")
        ALTEREGO.contact["SNT"] = the_packet.get("RST_SENT", "59")
        ALTEREGO.contact["RCV"] = the_packet.get("RST_RCVD", "59")
        my_grid = the_packet.get("MY_GRIDSQUARE", "")
        if my_grid:
            if len(my_grid) > 4:
                my_grid = my_grid[:4]
        their_grid = the_packet.get("GRIDSQUARE", "")
        if their_grid:
            ALTEREGO.contact["GridSquare"] = their_grid
        if the_packet.get("SUBMODE"):
            ALTEREGO.contact["Mode"] = the_packet.get("SUBMODE", "ERR")
        else:
            ALTEREGO.contact["Mode"] = the_packet.get("MODE", "ERR")
        ALTEREGO.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)
        ALTEREGO.contact["QSXFreq"] = round(
            float(the_packet.get("FREQ", "0.0")) * 1000, 2
        )
        ALTEREGO.contact["Band"] = get_logged_band(
            str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
        )
        ALTEREGO.save_contact()
