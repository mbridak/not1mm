"""CQ WPX RTTY plugin.

Find rules at: https://cqwpxrtty.com/rules.htm

Presented by CQ Magazine, 0000 UTC Saturday to 2359 UTC Sunday in September.
    Bands:      80, 40, 20, 15, 10m
    Exchange:   RST + serial number (the received one is what fldigi reports)
    Work:       once per band
    QSO points: 3 per 20/15/10m contact with another continent,
                6 per 80/40m contact with another continent,
                2 or 4 for the same continent but another country,
                and 1 or 2 for the same country, depending on the band.
    Multipliers: prefixes, counted once for the whole contest
    Cabrillo:   CQ-WPX-RTTY

Differs from the CW and SSB WPX contests in its scoring, in feeding the
receive field from fldigi rather than from the rig, and in sending the ESM
macros through fldigi instead of the function keys.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

import logging

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

logger = logging.getLogger(__name__)


class Contest(ContestBase):
    """CQ WPX, RTTY."""

    DisplayName = "CQ WPX RTTY"
    CabrilloName = "CQ-WPX-RTTY"
    Mode = "RTTY"
    EXCHANGE_HINT = "#"
    ADIFContestID = "CQ-WPX-RTTY"
    SendsRTCScore = True
    SupportsFT8 = True
    advance_on_space = [True, True, True, True, True]
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "WPX",
        "M1",
        "PTS",
    ]

    def set_contact_vars(self):
        """RST and serial number, sent and received, plus the prefix flag."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = parent.other_2.text()
        if parent.contact.get("WPXPrefix", ""):
            result = parent.database.fetch_wpx_exists(
                parent.contact.get("WPXPrefix", "")
            )
            if result.get("wpx_count", ""):
                parent.contact["IsMultiplier1"] = 0
            else:
                parent.contact["IsMultiplier1"] = 1

    def points(self):
        """Points for the contact being logged.

        Contact points:
        - Different-country contacts within any continent (not just North
          America) get 2 or 4 points
        - Same-country contacts get 1 or 2 points depending on the band
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        result = parent.cty_lookup(parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            my_country = item.get("entity", "")
            my_continent = item.get("continent", "")
        result = parent.cty_lookup(parent.contact.get("Call", ""))
        band = int(int(float(parent.contact.get("Freq", 0))) / 1000)
        if result is not None:
            item = result.get(next(iter(result)))
            their_country = item.get("entity", "")
            their_continent = item.get("continent", "")

            # Different continent
            if my_continent != their_continent:
                if band in [28, 21, 14]:
                    return 3
                return 6

            # Both in same country: rule V.B.3 pays one point on 28/21/14 MHz
            # and two points on 7 and 3.5 MHz.
            if my_country.upper() == their_country.upper():
                if band in [28, 21, 14]:
                    return 1
                return 2

            if band in [28, 21, 14]:
                return 2
            return 4
        # Something wrong
        return 0

    def show_mults(self):
        """Return display string for mults"""
        result = self.parent.database.fetch_wpx_count()
        if result:
            return int(result.get("wpx_count", 0))
        return 0

    def calc_score(self):
        """Total score is total QSO points times total mults."""
        parent = self.parent
        result = parent.database.fetch_points()
        if result is not None:
            score = result.get("Points", "0")
            if score is None:
                score = "0"
            result = parent.database.fetch_wpx_count()
            return int(score) * int(result.get("wpx_count", 0))
        return 0

    def recalculate_mults(self):
        """Recalculates multipliers after change in logged qso."""
        parent = self.parent
        for contact in parent.database.fetch_all_contacts_asc():
            parent.contact = contact
            contact["Points"] = self.points()
            result = parent.database.fetch_wpx_exists_before_me(
                contact.get("WPXPrefix", ""), contact.get("TS", "")
            )
            if result.get("wpx_count", 1) == 0:
                contact["IsMultiplier1"] = 1
            else:
                contact["IsMultiplier1"] = 0
            parent.database.change_contact(contact)

    def get_mults(self):
        """Get mults for RTC XML"""
        return {"wpxprefix": self.show_mults()}

    def ft8_handler(self, packet: dict):
        """Log a QSO reported by WSJT-X or fldigi over UDP.

        WSJT-X sends ``STATION_CALLSIGN``/``SRX_STRING``; fldigi sends
        ``STX``/``SRX`` for the serials.  Both end up in the usual fields and
        the contact is saved without the operator touching anything.
        """
        parent = self.parent
        logger.debug("%s", f"{packet=}")
        parent.callsign.setText(packet.get("CALL"))
        parent.contact["Call"] = packet.get("CALL", "")
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Exchange1"] = f"{packet.get('STATE', '')}".strip()
        parent.contact["ZN"] = packet.get("CQZ", "")
        parent.contact["Mode"] = packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["Band"] = get_logged_band(
            str(int(float(packet.get("FREQ", "0.0")) * 1000000))
        )
        logger.debug("%s", f"{parent.contact=}")
        parent.other_1.setText(f"{packet.get('STX', '')}".strip())
        parent.other_2.setText(f"{packet.get('SRX', '')}".strip())
        parent.save_contact()

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine, sending the macros through fldigi.

        Both the sent and the received serial are part of the exchange here, so
        entering either one counts, and the macro text is handed to fldigi
        rather than typed into the function keys.
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
                elif parent.other_1.text().isnumeric() and parent.other_2.text().isalpha():
                    self._resend_corrected_call(buttons_to_send)
                    parent.make_button_green(parent.esm_dict["QRZ"])
                    buttons_to_send.append(parent.esm_dict["QRZ"])
                    buttons_to_send.append("LOGIT")
                else:
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])

            if with_enter is True and bool(len(buttons_to_send)):
                self._send_macros_through_fldigi(
                    buttons_to_send, clear_call_sent=True
                )
        else:
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["MYCALL"])
                    buttons_to_send.append(parent.esm_dict["MYCALL"])

            elif parent.current_widget in ["other_1", "other_2"]:
                if parent.other_2.text() == "" or parent.other_1.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                elif parent.other_1.text().isnumeric() and parent.other_2.text().isalpha():
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")
                else:
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])

            if with_enter is True and bool(len(buttons_to_send)):
                self._send_macros_through_fldigi(buttons_to_send)

    def _send_macros_through_fldigi(self, buttons_to_send, clear_call_sent=False):
        """Log the contact and send the queued macros as one fldigi string."""
        parent = self.parent
        sendstring = ""
        for button in buttons_to_send:
            if not button:
                continue
            if button == "LOGIT":
                parent.save_contact()
                if clear_call_sent:
                    parent.esm_call_sent = ""
                continue
            if button == parent.esm_dict.get("HISCALL"):
                parent.esm_call_sent = parent.callsign.text()
            sendstring = f"{sendstring}{parent.process_macro(button.toolTip())} "
        parent.fldigi_util.send_string(sendstring)
