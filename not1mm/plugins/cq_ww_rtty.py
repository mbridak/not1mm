"""CQ World-Wide DX Contest, RTTY

Find rules at: https://www.cqwwrtty.com/rules.htm

80-10m, once per band.  A contact inside a country is worth 1 point, 2 within
a continent and 3 across continents.  A W/VE station sends its state or VE
area beside the zone, and the multipliers are each US state or VE area, each
DXCC country and each CQ zone, all once per band.
"""

import logging

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

logger = logging.getLogger(__name__)

# The modes the sponsor wants written as RY; the rest of the Cabrillo mode
# table is the base's.
RTTY_MODES = (
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
)


class Contest(ContestBase):
    """CQ World-Wide DX Contest, RTTY."""

    DisplayName = "CQ WW RTTY"
    CabrilloName = "CQ-WW-RTTY"
    Mode = "RTTY"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "CQ Zone + (state/VE area)"
    SOAPBOX_HINT = """If you are outside North America, In your station settings, set the ARRL Section to DX.

Please make sure you set the Mode to RTTY Above."""
    DupeType = 2  # once per band
    SendsRTCScore = True
    SupportsFT8 = True
    # The reports, the zone in the first extra field and the state/VE area in
    # the second, so a call lookup goes to the zone.
    FrameText = ("SNT", "CQ Zone", "State/Prov")
    AccessibleNames = ("RST Sent", "", "C Q Zone", "U S State or Providence")
    NextField = "other_1"
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "ZN",
        "Exchange1",
        "PTS",
    ]
    # Each country, each W/VE state or VE area, and each zone, once per band.
    NumMults = 3
    Multiplier1Name = "Country"
    MultSqlString = "CountryPrefix"
    IsMult1Per = 1
    Multiplier2Name = "State/VE area"
    MultSqlString2 = "Exchange"
    IsMult2Per = 1
    Multiplier3Name = "CQ Zone"
    MultSqlString3 = "CQZONE"
    IsMult3Per = 1

    def points(self):
        """3 across continents, 2 within one, 1 inside a country."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        mine = parent.cty_lookup(parent.station.get("Call", ""))
        if mine is None:
            return 0
        item = mine.get(next(iter(mine)))
        mycountry = item.get("entity", "")
        mycontinent = item.get("continent", "")
        theirs = parent.cty_lookup(parent.contact.get("Call", ""))
        if theirs is not None:
            item = theirs.get(next(iter(theirs)))
            entity = item.get("entity", "")
            continent = item.get("continent", "")
            if mycountry.upper() == entity.upper():
                return 1
            if mycontinent == continent:
                return 2
            return 3
        return 0

    def mult_value(self, slot, contact):
        """The country, the W/VE QTH, and the zone."""
        if slot == 1:
            call = str(contact.get("Call", "")).upper()
            if call.endswith("/MM") or call.startswith("MM/"):
                return None
            prefix = contact.get("CountryPrefix", "")
            if prefix == "I" and call[:3] in ("IG9", "IH9"):
                prefix = call[:3]
            return prefix
        if slot == 2:
            # Alaska and Hawaii are country multipliers only, never QTH ones.
            qth = str(contact.get("Exchange1", "")).upper().strip()
            if not qth or qth == "DX" or qth in ("AK", "HI"):
                return None
            return qth
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same keys as SQL, for counting the log."""
        if slot == 1:
            return (
                "CASE WHEN Call LIKE '%/MM' OR Call LIKE 'MM/%' THEN NULL "
                "WHEN CountryPrefix = 'I' "
                "AND upper(substr(Call, 1, 3)) IN ('IG9', 'IH9') "
                "THEN upper(substr(Call, 1, 3)) "
                "ELSE CountryPrefix END"
            )
        if slot == 2:
            return (
                "CASE WHEN upper(trim(Exchange1)) "
                "IN ('', 'DX', 'AK', 'HI') THEN NULL "
                "ELSE upper(trim(Exchange1)) END"
            )
        return super().mult_sql(slot)

    def get_mults(self):
        """The score page's two rows: countries (with the QTHs) and zones.

        The count is the same as the module's; splitting the QTHs into a
        ``state`` row of their own is the score-breakdown work, not this.
        """
        return {
            "country": self._mult_count(1) + self._mult_count(2),
            "zone": self._mult_count(3),
        }

    def prefill(self):
        """Fill the zone from a call lookup."""
        parent = self.parent
        if len(parent.other_1.text()) == 0:
            parent.other_1.setText(str(parent.contact.get("ZN", "")))

    def set_contact_vars(self):
        """The reports, the zone, the state/VE area and the sent exchange."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["ZN"] = parent.other_1.text()
        parent.contact["Exchange1"] = parent.other_2.text() or "DX"
        sent = parent.contest_settings.get("SentExchange", 0)
        if " " in str(sent):
            parent.contact["SentNr"] = sent
        else:
            parent.contact["SentNr"] = f"{sent} DX"

    def recalculate_mults(self):
        """No marks: the multipliers are counted from the log (see show_mults)."""

    def cabrillo_mode(self, mode: str) -> str:
        """The digital modes the sponsor spells RY."""
        if mode.strip() in RTTY_MODES:
            return "RY"
        return super().cabrillo_mode(mode)

    def cabrillo_qso_line(self, contact):
        """The RTTY line: zone and state/VE area in place of the serial."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        exchange1 = contact.get("Exchange1", "")
        if exchange1 == "":
            exchange1 = "DX"
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{str(contact.get('SentNr', '')).ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{str(contact.get('ZN', '')).zfill(2)} "
            f"{str(exchange1).ljust(2)}"
        )

    def ft8_handler(self, the_packet: dict):
        """Log an FT8 packet as a contact, as the module's handler did."""
        parent = self.parent
        logger.debug(f"{the_packet=}")
        parent.callsign.setText(the_packet.get("CALL"))
        parent.contact["Call"] = the_packet.get("CALL", "")
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Exchange1"] = f"{the_packet.get('STATE', '')}".strip()
        parent.contact["ZN"] = the_packet.get("CQZ", "")
        parent.contact["Mode"] = the_packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(
            float(the_packet.get("FREQ", "0.0")) * 1000, 2
        )
        parent.contact["Band"] = get_logged_band(
            str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.other_1.setText(str(the_packet.get("CQZ", "ERR")))
        parent.other_2.setText(f"{the_packet.get('STATE', '')}".strip())
        parent.save_contact()

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine: the zone and, inside North America, the QTH.

        The RTTY macros go to fldigi as one string, and a W/VE station has to
        send its state as well as the zone, so this is not the base's machine.
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
                needs_qth = (
                    parent.contact.get("Continent", "") == "NA"
                    and parent.other_2.text() == ""
                )
                if needs_qth or parent.other_1.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                elif parent.other_1.text().isnumeric() and (
                    parent.other_2.text().isalpha()
                    or parent.contact.get("Continent", "") != "NA"
                ):
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
                sendstring = ""
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            continue
                        sendstring = f"{sendstring}{parent.process_macro(button.toolTip())} "
                parent.fldigi_util.send_string(sendstring)

    def populate_history_info_line(self):
        """Show the call history entry for the callsign being typed."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('CQZone', '')}, "
                f"{result.get('State', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Fill the zone and the state/VE area from the call history entry."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_1.text() == "":
                parent.other_1.setText(f"{result.get('CQZone', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('State', '')}")
