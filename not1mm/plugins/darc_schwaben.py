"""DARC Schwaben Contest

Find rules at: https://www.darc.de/der-club/referate/conteste/allgemeine-contestregeln-darc-referat-conteste/

80m, 40m, 2m and 70cm, once per band and mode.  The exchange is RST and a DOK,
or a serial number for a station without one, plus a locator on VHF.  A contact
is worth 1 point, 5 for a station in district T or Z30, and 10 for the special
and club stations.  There are no multipliers: the score is the sum of the
points.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.fields import DEFAULT_ENTRY_WINDOW


def get_points_for_contact(callsign: str, dok: str) -> int:
    """Calculate QSO points based on callsign and DOK."""
    call = callsign.upper().strip()
    dok = dok.upper().strip()

    # Special DOK / callsigns DL0YLT or DK0SQ -> 10 points
    if call in ("DL0YLT", "DK0SQ") or dok in ("YLT", "SQ"):
        return 10

    # Extract district/dok:
    # Check if DOK belongs to District T (starts with T) or is Z30
    is_t_or_z30 = dok.startswith("T") or dok == "Z30"

    if is_t_or_z30:
        # Check if Training station (DN prefix)
        if call.startswith("DN"):
            return 10

        # Check if Club station (DA0, DF0, DK0, DL0, DP0, DR0 prefix)
        if any(
            call.startswith(pfx) for pfx in ("DA0", "DF0", "DK0", "DL0", "DP0", "DR0")
        ):
            return 10

        # Regular T or Z30 station -> 5 points
        return 5

    # Any other station -> 1 point
    return 1


def parse_exchange(exchange_text: str):
    """Parse exchange into DOK/NR and Grid locator if present."""
    tokens = exchange_text.upper().split()
    dok_or_nr = ""
    grid = ""
    for token in tokens:
        if len(token) in (4, 6) and token[:2].isalpha() and token[2:4].isdigit():
            grid = token
        elif not dok_or_nr:
            dok_or_nr = token
    if not dok_or_nr and exchange_text:
        dok_or_nr = exchange_text.strip()
    return dok_or_nr, grid


class Contest(ContestBase):
    """DARC Schwaben Contest."""

    DisplayName = "DARC SCHWABEN"
    CabrilloName = "Schwaben Contest"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "DOK/NM or # (+Locator for VHF)"
    DupeType = 3  # work each band/mode once
    # The exchange may carry a locator beside the DOK ("T01 JN58ZZ"), so a
    # space is part of it and does not advance the focus.
    advance_on_space = [True, True, True, True, False]
    # The DOK is the "sent" exchange and the received one, hence the labels.
    EntryWindowInfo = DEFAULT_ENTRY_WINDOW
    QsoErrorString = "SntNrText_Any_not_Empty, RcvNrText_Any_not_Empty"
    FrameText = ("SNT", "RCV", "DOK/# Sent", "DOK/# RCVD")
    AccessibleNames = ("RST Sent", "RST Received", "Sent DOK", "DOK/NM or Number")

    def points(self):
        """One point a contact, more for district T/Z30 and the clubs."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        return get_points_for_contact(
            parent.contact.get("Call", ""), parent.contact.get("NR", "")
        )

    def set_contact_vars(self):
        """The sent DOK/serial and the received DOK plus VHF locator."""
        parent = self.parent
        parent.contact["SNT"] = parent.fields.SNTText.text()
        parent.contact["RCV"] = parent.fields.RCVText.text()

        sent_text = parent.fields.SntNrText.text().upper().strip()
        rcvd_text = parent.fields.RcvNrText.text().upper().strip()

        rcvd_dok, rcvd_grid = parse_exchange(rcvd_text)

        parent.contact["SentNr"] = sent_text
        parent.contact["NR"] = rcvd_dok if rcvd_dok else rcvd_text
        if rcvd_grid:
            parent.contact["Exchange1"] = rcvd_grid

    def prefill(self):
        """Fill the sent exchange, then recall the station's last DOK."""
        parent = self.parent
        super().prefill()
        if parent.fields.RcvNrText.text():
            return
        call = parent.callsign.text().upper()
        result = parent.database.exec_sql(
            "select NR from dxlog where Call = ? and ContestName = ? "
            "order by ts desc;",
            (call, self.CabrilloName),
        )
        if result and isinstance(result.get("NR", ""), str):
            parent.fields.RcvNrText.setText(str(result.get("NR", "")))

    def cabrillo_mode(self, mode):
        """FM is a phone mode in this contest's Cabrillo log."""
        if mode == "FM":
            return "PH"
        return super().cabrillo_mode(mode)

    def cabrillo_qso_line(self, contact):
        """The exchange written with a locator beside the DOK, 12 wide."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)

        sent_ex = str(contact.get("SentNr", "")).strip()
        rcvd_ex = str(contact.get("NR", "")).strip()
        ex1 = str(contact.get("Exchange1", "")).strip()
        if ex1:
            rcvd_ex = f"{rcvd_ex} {ex1}".strip()

        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{sent_ex.ljust(12)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{rcvd_ex.ljust(12)}"
        )

    def recalculate_mults(self):
        """Rescore the log: the points are per contact, and a dupe is zero.

        The score is the sum of the ``Points`` column, so the replay has to put
        the values back after an import, and a duplicate has to stay at zero or
        it adds points it never earned.
        """
        parent = self.parent
        all_contacts = parent.database.fetch_all_contacts_asc()
        if not all_contacts:
            return
        worked = set()
        for contact in all_contacts:
            call = contact.get("Call", "")
            dok = contact.get("NR", "")
            key = (call, contact.get("Band", ""), contact.get("Mode", ""))
            if key in worked:
                contact["Points"] = 0
            else:
                contact["Points"] = get_points_for_contact(call, dok)
            worked.add(key)
            parent.database.change_contact(contact)

    def populate_history_info_line(self):
        """Show the call history entry for the callsign being typed."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('Exch1', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the received DOK from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.fields.RcvNrText.text() == "":
                parent.fields.RcvNrText.setText(f"{result.get('Exch1', '')}")
