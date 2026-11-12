"""NAQP RTTY plugin

Find rules at: https://www.ncjweb.com/NAQP-Rules.pdf

160-10m, once per band.  A North American station is 1 point and an NA operator
scores every contact; a non-NA operator scores only NA contacts.  Each US state
and DC, each VE province/territory and each other North American country is a
multiplier once per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
import logging

from not1mm.lib.ham_utility import get_logged_band

# NAQP and the Sprint share one multiplier taxonomy: US states plus DC, the 13
# VE provinces/territories, and other North American countries keyed
# "C-<prefix>" so that a country prefix cannot collide with a state
# abbreviation (the Dominican Republic's HI against Hawaii's HI).  Reuse the
# Sprint's tables rather than keeping a second copy.
from not1mm.plugins.na_sprint_cw import _entity, mult_key

# A North American station is "defined by the ARRL DXCC List, with the addition
# of Hawaii".  cty.dat files Hawaii (KH6) under Oceania, so the exception has
# to be made explicitly - na_sprint_cw.py does the same.
NA_FORCED_PREFIXES = ("KH6",)

logger = logging.getLogger(__name__)


def _is_na(parent, call) -> bool:
    """Return True if `call` counts as a North American station."""
    result = parent.cty_lookup(call)
    if result is not None:
        item = result.get(next(iter(result)))
        if item.get("continent", "") == "NA":
            return True
        return item.get("primary_pfx", "") in NA_FORCED_PREFIXES
    return False


class Contest(ContestBase):
    """North American QSO Party, RTTY."""

    DisplayName = "NAQP RTTY"
    CabrilloName = "NAQP-RTTY"
    Mode = "RTTY"
    EXCHANGE_HINT = "Name or Name + SPC"
    DupeType = 2  # once per band
    SendsRTCScore = True
    SupportsFT8 = True
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    # Only the name and the location are used; the RSTs are hidden.
    EntryFields = ("field3", "field4")
    FrameText = ("SNT", "Name", "State")
    AccessibleNames = ("RST Sent", "", "Name", "State")
    # The module focused the name field after a lookup, not the location.
    NextField = "other_1"
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Name",
        "Sect",
        "M1",
        "PTS",
    ]
    # Exchange1 carries the normalised key -- Sect keeps the raw location for
    # the Cabrillo line -- and each key counts once per band.
    NumMults = 1
    Multiplier1Name = "Exchange"
    MultSqlString = "Exchange"
    IsMult1Per = 1

    def mult_sql(self, slot):
        """The normalised key as SQL, with an empty one -- a "DX" -- not counted."""
        if slot != 1:
            return super().mult_sql(slot)
        return "NULLIF(Exchange1, '')"

    def points(self):
        """1 point when either end of the contact is in North America."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        if _is_na(parent, parent.station.get("Call", "")) or _is_na(
            parent, parent.contact.get("Call", "")
        ):
            return 1
        return 0

    def _multiplier_key(self, contact):
        """The normalised key for a contact's raw location."""
        parent = self.parent
        continent, pfx = _entity(parent, contact.get("Call", ""))
        if not pfx:
            continent = contact.get("Continent", "")
            pfx = contact.get("CountryPrefix", "")
        return mult_key(contact.get("Sect", ""), continent, pfx)

    def set_contact_vars(self):
        """The received exchange, and the multiplier it is worth."""
        parent = self.parent
        contact = parent.contact
        contact["SNT"] = parent.sent.text()
        contact["RCV"] = parent.receive.text()
        contact["Name"] = parent.other_1.text().upper()
        contact["Sect"] = parent.other_2.text().upper()
        contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)
        contact["Exchange1"] = self._multiplier_key(contact)
        self.mark_multipliers()

    def recalculate_mults(self):
        """Recompute the key and mark the first scoring contact of each.

        An imported log carries neither Exchange1 nor the entity of the call,
        so the key is rebuilt from Sect and cty first; the module only marked a
        contact that scored a point.
        """
        database = self.parent.database
        seen = set()
        for contact in database.fetch_all_contacts_asc():
            key = self._multiplier_key(contact)
            band = contact.get("Band", "")
            contact["Exchange1"] = key
            if key and contact.get("Points", 0) == 1 and (key, band) not in seen:
                contact["IsMultiplier1"] = 1
            else:
                contact["IsMultiplier1"] = 0
            seen.add((key, band))
            database.change_contact(contact)
        self.after_recalculate_mults()

    def after_recalculate_mults(self):
        """Refresh the log window, as the module's replay did."""
        cmd = {}
        cmd["cmd"] = "UPDATELOG"
        if self.parent.log_window:
            self.parent.log_window.msg_from_main(cmd)

    def prefill(self):
        """Nothing to prefill: other_1 is the name, not the sent serial."""

    def cabrillo_qso_line(self, contact):
        """The NAQP line: the operator's name/location, then the received pair."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SentNr', '')).upper()} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('Name', '')).ljust(11)} "
            f"{str(contact.get('Sect', '')).ljust(5)}"
        )

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        A North American station sends a name *and* a location, so both fields
        have to be copied before the contact is finished; a station elsewhere
        sends only a name, which is the first field.
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

            elif parent.current_widget in ("other_1", "other_2"):
                continent = parent.contact.get("Continent")
                if parent.other_1.text() == "" or (
                    parent.other_2.text() == "" and continent == "NA"
                ):
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                elif (
                    parent.other_1.text().isalpha()
                    and parent.other_2.text().isalpha()
                    and continent == "NA"
                ):
                    self._resend_corrected_call(buttons_to_send)
                    parent.make_button_green(parent.esm_dict["QRZ"])
                    buttons_to_send.append(parent.esm_dict["QRZ"])
                    buttons_to_send.append("LOGIT")
                elif parent.other_1.text().isalpha() and continent != "NA":
                    self._resend_corrected_call(buttons_to_send)
                    parent.make_button_green(parent.esm_dict["QRZ"])
                    buttons_to_send.append(parent.esm_dict["QRZ"])
                    buttons_to_send.append("LOGIT")
                else:
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])

            if with_enter is True and bool(len(buttons_to_send)):
                sendstring = ""
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            parent.esm_call_sent = ""
                            continue
                        if button == parent.esm_dict.get("HISCALL"):
                            parent.esm_call_sent = parent.callsign.text()
                        sendstring = f"{sendstring}{parent.process_macro(button.toolTip())} "
                parent.fldigi_util.send_string(sendstring)
        else:
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["MYCALL"])
                    buttons_to_send.append(parent.esm_dict["MYCALL"])

            elif parent.current_widget in ("other_1", "other_2"):
                continent = parent.contact.get("Continent")
                if parent.other_1.text() == "" or (
                    parent.other_2.text() == "" and continent == "NA"
                ):
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                elif (
                    parent.other_1.text().isalpha()
                    and parent.other_2.text().isalpha()
                    and continent == "NA"
                ):
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")
                elif parent.other_1.text().isalpha() and continent != "NA":
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")
                else:
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])

            if with_enter is True and bool(len(buttons_to_send)):
                sendstring = ""
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            continue
                        sendstring = f"{sendstring}{parent.process_macro(button.toolTip())} "
                parent.fldigi_util.send_string(sendstring)

    def cabrillo_mode(self, mode):
        """The sponsor's digital sub-modes are all RTTY; the rest is the base's."""
        if mode.strip() in (
            "RTTY",
            "RTTY-R",
            "LSB-D",
            "USB-D",
            "AM-D",
            "FM-D",
            "DIGI-U",
            "DIGI-L",
            "RTTYR",
            "PKTLSB",
            "PKTUSB",
        ):
            return "RY"
        return super().cabrillo_mode(mode)

    def ft8_handler(self, packet: dict):
        """Log a QSO reported by WSJT-X or fldigi over UDP.

        Both send a name and a location, and fldigi puts the received one in
        ``SRX_STRING``.
        """
        parent = self.parent
        parent.callsign.setText(packet.get("CALL"))
        parent.contact["Call"] = packet.get("CALL", "")
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.other_1.setText(f"{packet.get('NAME', '')}".strip())
        parent.other_2.setText(f"{packet.get('SRX_STRING', '')}".strip())
        parent.contact["ZN"] = packet.get("CQZ", "")
        parent.contact["Mode"] = packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["Band"] = get_logged_band(
            str(int(float(packet.get("FREQ", "0.0")) * 1000000))
        )
        logger.debug("%s", f"{parent.contact=}")
        parent.save_contact()

    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('State', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the name and location from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_1.text() == "":
                parent.other_1.setText(f"{result.get('Name', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('State', '')}")
