"""WAG - Worked All Germany plugin, by DL6CQ.

Find rules at: https://www.darc.de/der-club/referate/conteste/wag-contest/regeln/

Only the parts that differ from :mod:`not1mm.lib.contest` are here.  WAG is the
contest UDC cannot describe: the points depend on where the *operator* is (a DL
station gets 1/3/5, an outsider 3 for a DL station and 0 for anything else),
and so does the multiplier (a DXCC entity seen from DL, a German district seen
from outside).  So ``points()`` and ``mult_value()`` stay methods; the counting,
the score and the marking all come from the base.
"""

import logging
import re

from not1mm.lib.contest import ContestBase

logger = logging.getLogger(__name__)


class Contest(ContestBase):
    """Worked All Germany."""

    DisplayName = "WAG"
    CabrilloName = "WAG"
    Mode = "BOTH"
    DupeType = 3  # once per band and mode
    EXCHANGE_HINT = "DOK/NM or #"
    SendsRTCScore = True
    Bands = (3.5, 7, 14, 21, 28)
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "M1",
        "PTS",
    ]
    # The exchange labels and screen-reader names differ from the base default.
    FrameText = ("SNT", "DOK/# Sent", "DOK/# RCVD")
    AccessibleNames = ("", "", "RST Sent", "DOK/NM or Number")
    # Multiplier 1 is the DXCC entity from DL and the district from outside;
    # either way it counts once per band and mode.  The key is a method.
    NumMults = 1
    Multiplier1Name = "CountryPrefix"
    MultSqlString = "CountryPrefix"
    IsMult1Per = 3
    is_german = False

    def init_contest(self):
        """Set up the entry window, then work out which side of WAG we are on."""
        super().init_contest()
        result = self.parent.cty_lookup(self.parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            self.is_german = item.get("primary_pfx", "") == "DL"
        logger.debug("Contest station is DL: %s", self.is_german)

    def points(self):
        """Points for the contact being logged: 1/3/5 from DL, 3 or 0 outside."""
        if self.parent.contact_is_dupe > 0:
            return 0

        contact = self.parent.contact
        if not self.is_german and contact.get("CountryPrefix", "") == "DL":
            return 3
        if not self.is_german:
            return 0
        if contact.get("CountryPrefix", "") == "DL":
            return 1
        if contact.get("Continent", "") == "EU":
            return 3
        return 5

    def mult_value(self, slot: int, contact):
        """The multiplier key: the DXCC entity from DL, else the district.

        The district is the first *letter* of the received DOK (a special DOK
        like ``60CHILD`` is district ``C``), and ``NM`` -- a DL non-member --
        does not count at all.  From outside DL only a DL station is a
        multiplier.
        """
        if self.is_german:
            return contact.get("CountryPrefix", "")
        if contact.get("CountryPrefix", "") != "DL":
            return None
        dok = str(contact.get("NR", "")).upper()
        if dok == "NM" or not dok:
            return None
        return get_district(dok)

    def show_mults(self):
        """The number of multipliers is the number of marked contacts.

        The key is not a SQL expression (the district is a letter inside the
        received exchange), so the log cannot be counted by a query; the marks
        :meth:`recalculate_mults` leaves are the count.
        """
        result = self.parent.database.fetch_mult_count(1)
        return int(result.get("count", 0)) if result else 0

    def set_contact_vars(self):
        """Set the exchange, and mark the multiplier the contact is worth."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text()
        parent.contact["SentNr"] = parent.other_1.text()

        dok = parent.contact["NR"].upper()
        dxcc = parent.contact.get("CountryPrefix", "")
        band = parent.contact.get("Band", "")
        district = get_district(dok)

        # Multiplier: non-DL worked DL, by district.
        if dxcc == "DL" and not isinstance(dok, int) and dok != "NM" and not self.is_german:
            query = (
                f"select count(*) as dok_count from dxlog where 1=1 "
                f"and NR like '{district}%' "
                f"and Band = '{band}' "
                f"and ContestNR = {parent.pref.get('contest', '1')};"
            )
            logger.debug(query)
            result = parent.database.exec_sql(query)
            logger.debug(result)
            count = int(result.get("dok_count", 0))
            if count == 0:
                parent.contact["IsMultiplier1"] = 1
            else:
                parent.contact["IsMultiplier1"] = 0

        # Multiplier: DL worked any station, by DXCC entity.
        if self.is_german:
            query = (
                f"select count(*) as dxcc_count from dxlog where 1=1 "
                f"and CountryPrefix = '{dxcc}' "
                f"and Band = '{band}' "
                f"and ContestNR = {parent.pref.get('contest', '1')};"
            )
            logger.debug(query)
            result = parent.database.exec_sql(query)
            logger.debug(result)
            count = int(result.get("dxcc_count", 0))
            if count == 0:
                parent.contact["IsMultiplier1"] = 1
            else:
                parent.contact["IsMultiplier1"] = 0

    def predupe(self):
        """Warn when a non-DL station tries to work something that is not DL."""
        parent = self.parent
        dxcc = parent.contact.get("CountryPrefix", "")
        if not self.is_german and dxcc != "DL":
            logger.debug("DL only in WAG!")
            parent.dupe_indicator.setText("DL stations only!")
            parent.dupe_indicator.show()

    def prefill(self):
        """Fill the sent exchange, and the received one from call history."""
        parent = self.parent
        sent_exchange_setting = parent.contest_settings.get("SentExchange", "")
        if sent_exchange_setting.strip() == "#":
            result = parent.database.get_serial()
            serial_nr = str(result.get("serial_nr", "1")).zfill(3)
            if serial_nr == "None":
                serial_nr = "001"
            if len(parent.other_1.text()) == 0:
                parent.other_1.setText(serial_nr)
        else:
            parent.other_1.setText(sent_exchange_setting)

        if parent.other_2.text() == "":
            call = parent.callsign.text().upper()
            query = (
                f"select NR from dxlog where Call = '{call}' "
                f"and ContestName = '{self.CabrilloName}' order by ts desc;"
            )
            logger.debug(query)
            result = parent.database.exec_sql(query)
            logger.debug("%s", f"{result}")
            if result and isinstance(result.get("NR", ""), str):
                parent.other_2.setText(str(result.get("NR", "")))

    def reset_label(self):
        """Put the dupe indicator back after it was used for a warning."""
        self.parent.dupe_indicator.setText("Dupe!")

    def after_recalculate_mults(self):
        """Refresh the log window after a rescore."""
        cmd = {"cmd": "UPDATELOG"}
        if self.parent.log_window:
            self.parent.log_window.msg_from_main(cmd)

    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Exch1', '')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the received exchange from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                # Strip leading whitespace for the case that historyfile is not
                # well formatted, f.e. CA0LL, DOK instead of CA0LL,DOK
                parent.other_2.setText(f"{result.get('Exch1', '').lstrip()}")

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        Both exchange fields count as "the exchange" here, so entering either
        one finishes the contact.
        """
        parent = self.parent
        if new_focused_widget is not None:
            parent.current_widget = parent.inputs_dict.get(new_focused_widget)

        for a_button in (
            parent.F1,
            parent.F2,
            parent.F3,
            parent.F4,
            parent.F5,
            parent.F6,
            parent.F7,
            parent.F8,
            parent.F9,
            parent.F10,
            parent.F11,
            parent.F12,
        ):
            parent.restore_button_color(a_button)

        buttons_to_send = []

        if parent.pref.get("run_state"):
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) < 3:
                    parent.make_button_green(parent.esm_dict["CQ"])
                    buttons_to_send.append(parent.esm_dict["CQ"])
                    parent.esm_call_sent = ""
                elif len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["HISCALL"])
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["HISCALL"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])

            elif parent.current_widget in ["other_1", "other_2"]:
                if parent.other_2.text() == "" or parent.other_1.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                else:
                    # If the operator corrected a busted callsign after the
                    # exchange was already sent, resend the corrected call
                    # ahead of the QRZ/TU macro so the other station logs the
                    # right callsign before the QSO is wiped.
                    self._resend_corrected_call(buttons_to_send)
                    parent.make_button_green(parent.esm_dict["QRZ"])
                    buttons_to_send.append(parent.esm_dict["QRZ"])
                    buttons_to_send.append("LOGIT")

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            parent.esm_call_sent = ""
                            continue
                        if button == parent.esm_dict.get("HISCALL"):
                            parent.esm_call_sent = parent.callsign.text()
                        parent.process_function_key(button)
        else:
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["MYCALL"])
                    buttons_to_send.append(parent.esm_dict["MYCALL"])

            elif parent.current_widget in ["other_1", "other_2"]:
                if parent.other_2.text() == "" or parent.other_1.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                else:
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            continue
                        parent.process_function_key(button)


def get_district(dok):
    """The first letter of a DOK: WAG's district multiplier.

    A special DOK (``60CHILD``) is counted by its first *letter*, so
    ``60CHILD`` is district ``C``.
    """
    district = re.search(r"[A-Za-z]", dok)
    return district.group(0) if district else None
