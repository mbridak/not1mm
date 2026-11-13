"""CQ World-Wide VHF Contest

Find rules at: https://cqww-vhf.com/rules/

50 MHz and 144 MHz, once per band.  The exchange is the four-character grid
locator; the multiplier is each grid worked once per band, and a rover counts
the grids again from each new location -- which is why the sent grid is part of
the key.  The digital weekend is a separate Cabrillo contest name.
"""

import logging

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

logger = logging.getLogger(__name__)

# The digital modes the sponsor writes as DG.
DIGITAL_MODES = (
    "FT8",
    "FT4",
    "MSK144",
    "Q65",
    "FSK441",
    "JT65",
    "JT9",
    "PSK31",
    "BPSK31",
    "PSK63",
    "BPSK63",
    "PSK125",
    "BPSK125",
)


def normalize_grid(text: str) -> str:
    """Extract a valid 4-character Maidenhead grid locator from text.

    A valid locator is two letters, two digits, e.g. EM15.
    Longer locators are truncated to their 4-character field designator.
    """

    candidate = text.upper().strip().split()[0] if text.strip() else ""
    if len(candidate) >= 4:
        candidate = candidate[:4]
    if len(candidate) == 4 and candidate[:2].isalpha() and candidate[2:].isdigit():
        return candidate
    return ""


def validate_exchange(text: str) -> bool:
    """Return True if the text contains a valid 4-character grid."""

    return normalize_grid(text) != ""


def points_for_band(band) -> int:
    """Return QSO points for a band. 6m = 1 point, 2m = 2 points.

    ``band`` may be the stored MHz float, its string form, or the legacy plain
    band number, because the live logging path and the database disagree on the
    representation.
    """

    if band in ("50.0", "6", 50.0):
        return 1
    if band in ("144.0", "2", 144.0):
        return 2
    return 0


def contest_name_for(contest_settings: dict) -> str:
    """Return the correct Cabrillo contest name based on the mode category.

    The digital weekend uses CQ-VHF-DIGI, everything else CQ-VHF-SSBCW.
    """

    mode_category = contest_settings.get("ModeCategory", "")
    return "CQ-VHF-DIGI" if mode_category == "DIGITAL" else "CQ-VHF-SSBCW"


def category_mode(mode_category: str) -> str:
    """Map not1mm mode category to a valid Cabrillo CATEGORY-MODE value.

    Valid entries for the CQ WW VHF robot are: SSB CW DG FM MIXED.
    """

    mapping = {
        "CW": "CW",
        "SSB": "SSB",
        "FM": "FM",
        "DIGITAL": "DG",
        "SSB+CW": "MIXED",
        "SSB+CW+DIGITAL": "MIXED",
        "RTTY": "DG",
        "PSK": "DG",
    }
    return mapping.get(mode_category.upper(), mode_category)


class Contest(ContestBase):
    """CQ World-Wide VHF Contest."""

    DisplayName = "CQ WW VHF"
    CabrilloName = "CQ-VHF-SSBCW"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "4-character grid square"
    SOAPBOX_HINT = "CQ WW VHF - Exchange is your 4 digit gridsquare"
    DupeType = 5  # the contest decides: once per call, band and sent grid
    SupportsFT8 = True
    LocationFallback = "DX"
    # Only the sent and received grids are used; the RSTs are hidden.
    EntryFields = ("field3", "field4")
    FrameText = ("SNT", "Sent Grid", "Grid")
    AccessibleNames = ("RST Sent", "", "Sent Grid", "Gridsquare")
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "SentNr",
        "RcvNr",
        "PTS",
    ]
    # A grid once per band, and again from each new rover location, so the sent
    # grid joins the received grid in the key.
    NumMults = 1
    Multiplier1Name = "Grid"
    MultSqlString = "NR"
    IsMult1Per = 1

    def mult_sql(self, slot):
        """The grid pair as SQL, for counting the log.

        Only a text ``NR`` is a grid; a numeric one is not a multiplier.
        """
        if slot == 1:
            return "CASE WHEN typeof(NR) = 'text' THEN NR || ':' || SentNr END"
        return super().mult_sql(slot)

    def mult_value(self, slot, contact):
        """The received grid and the sent grid, for the key."""
        if slot == 1:
            grid = contact.get("NR", "")
            if not isinstance(grid, str) or not grid:
                return None
            return f"{grid}:{contact.get('SentNr', '')}"
        return super().mult_value(slot, contact)

    def get_mults(self):
        """The score page wants the grid-square id."""
        return {"gridsquare": self.show_mults()}

    def recalculate_mults(self):
        """No marks: the multipliers are counted from the log (see show_mults)."""

    def points(self):
        """1 point on 6m, 2 on 2m, nothing elsewhere."""
        if self.parent.contact_is_dupe > 0:
            return 0
        return points_for_band(self.parent.contact.get("Band", ""))

    def set_contact_vars(self):
        """The grids; neither RST is used."""
        parent = self.parent
        parent.contact["SNT"] = ""
        parent.contact["RCV"] = ""
        parent.contact["NR"] = normalize_grid(parent.other_2.text())
        parent.contact["SentNr"] = normalize_grid(parent.other_1.text())

    def validate(self):
        """Validate the exchange entry."""
        return validate_exchange(self.parent.other_2.text())

    def specific_contest_check_dupe(self, call):
        """A dupe is the same call on the same band from the same grid.

        A rover counts the grids again from each new location, so the sent
        grid is part of the dupe rule too.
        """
        parent = self.parent
        band = parent.contact.get("Band", "")
        sentnr = parent.RoverLocation or parent.contest_settings.get("SentExchange", "")
        result = parent.database.exec_sql(
            "select count(*) as dupe from dxlog where ContestNR = ? "
            "and Call = ? and Band = ? and SentNr = ?;",
            (parent.database.current_contest, call, band, str(sentnr).upper()),
        )
        return {"isdupe": bool(result and result.get("dupe", 0) > 0)}

    def predupe(self):
        """Put the sent grid (the rover location, or the set exchange) in."""
        parent = self.parent
        if parent.RoverLocation:
            parent.other_1.setText(str(parent.RoverLocation))
        else:
            parent.other_1.setText(
                str(parent.contest_settings.get("SentExchange", "")).upper()
            )

    def prefill(self):
        """Nothing to fill: :meth:`predupe` writes the sent grid."""

    def cabrillo_contest_name(self):
        """The digital weekend has its own Cabrillo contest name."""
        return contest_name_for(self.parent.contest_settings)

    def cabrillo_category_mode(self):
        """The CQ WW VHF robot's CATEGORY-MODE spelling."""
        return category_mode(self.parent.contest_settings.get("ModeCategory", ""))

    def cabrillo_mode(self, mode: str) -> str:
        """The VHF QSO mode codes: CW, PH, FM, RY and DG."""
        if mode in DIGITAL_MODES:
            return "DG"
        if mode == "AM":
            return "PH"
        return super().cabrillo_mode(mode)

    def cabrillo_qso_line(self, contact):
        """The VHF line: frequency to the MHz, and no RST."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", 0) / 1000)).rjust(4)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SentNr', '')).ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('NR', '')).ljust(6)}"
        )

    def ft8_handler(self, the_packet: dict):
        """Log an FT8 packet as a contact, as the module's handler did."""
        parent = self.parent
        parent.callsign.setText(the_packet.get("CALL"))
        parent.contact["Call"] = the_packet.get("CALL", "")
        my_grid = the_packet.get("MY_GRIDSQUARE", "")
        if my_grid:
            my_grid = normalize_grid(my_grid)
        their_grid = the_packet.get("GRIDSQUARE", "")
        if their_grid:
            their_grid = normalize_grid(their_grid)
        parent.contact["NR"] = their_grid
        parent.contact["SentNr"] = my_grid
        if the_packet.get("SUBMODE"):
            parent.contact["Mode"] = the_packet.get("SUBMODE", "ERR")
        else:
            parent.contact["Mode"] = the_packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(
            float(the_packet.get("FREQ", "0.0")) * 1000, 2
        )
        parent.contact["Band"] = get_logged_band(
            str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.contact["SNT"] = ""
        parent.contact["RCV"] = ""
        parent.other_1.setText(my_grid)
        parent.other_2.setText(their_grid)
        parent.save_contact()

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine: the grid is the exchange."""
        parent = self.parent
        if new_focused_widget is not None:
            parent.current_widget = parent.inputs_dict.get(new_focused_widget)

        for a_button in (
            parent.esm_dict["CQ"],
            parent.esm_dict["EXCH"],
            parent.esm_dict["QRZ"],
            parent.esm_dict["AGN"],
            parent.esm_dict["HISCALL"],
            parent.esm_dict["MYCALL"],
            parent.esm_dict["QSOB4"],
        ):
            if a_button is not None:
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

            elif parent.current_widget in ("other_2",):
                if not validate_exchange(parent.other_2.text()):
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                else:
                    # A corrected call has to go out again before the QSO is
                    # wiped, or the other station logs the wrong callsign.
                    if (
                        parent.pref.get("esm_send_corrected_call")
                        and parent.esm_call_sent
                        and parent.callsign.text() != parent.esm_call_sent
                    ):
                        parent.make_button_green(parent.esm_dict["HISCALL"])
                        buttons_to_send.append(parent.esm_dict["HISCALL"])
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

            elif parent.current_widget in ("other_2",):
                if not validate_exchange(parent.other_2.text()):
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

    def populate_history_info_line(self):
        """Show the call history entry for the callsign being typed."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('Loc1', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Check call history DB for available data."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Loc1', '')}")
