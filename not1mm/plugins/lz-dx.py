"""LZ DX Contest

Find rules at: https://lzdx.bfra.bg/rulesen.html

80-10m, once per band and mode.  An LZ station sends a two-letter district and
everyone else an ITU zone.  A Bulgarian contact is worth 10 points, one between
two LZ stations 1, another country on the same continent 1 and another
continent 3.  Every ITU zone counts once per band, plus the LZ districts for a
foreign entrant or the DXCC countries for an LZ one.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    """LZ DX Contest."""

    DisplayName = "LZ DX"
    CabrilloName = "LZ-DX"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "District or ITU-Zone"
    DupeType = 3  # once per band and mode
    Bands = (3.5, 7, 14, 21, 28)
    # The zone multiplier is the ITU zone, but the district lookup uses the
    # operator's IARU zone classification.
    ZoneType = "IARU"
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "M1",
        "M2",
        "PTS",
    ]
    # The hidden serial and the visible district or zone.
    EntryFields = ("field1", "field2", "field4")
    FrameText = ("", "Sent", "District/ITU")
    AccessibleNames = ("", "", "Sent", "District or ITU")
    # Every ITU zone once per band, plus the LZ districts for a foreign
    # entrant or the DXCC countries for an LZ one.
    NumMults = 2
    Multiplier1Name = "CQZONE"
    MultSqlString = "CQZONE"
    IsMult1Per = 1
    Multiplier2Name = "CountryPrefix"
    MultSqlString2 = "CountryPrefix"
    IsMult2Per = 1
    SendsRTCScore = True

    def _entity(self, call):
        """Return ``(entity, continent)`` for a callsign, or ``("", "")``."""
        result = self.parent.cty_lookup(call)
        if not result:
            return "", ""
        item = result.get(next(iter(result)), {})
        return item.get("entity", ""), item.get("continent", "")

    def _is_lz(self) -> bool:
        """True when the entrant is a Bulgarian station."""
        return self._entity(self.parent.station.get("Call", ""))[0] == "Bulgaria"

    def points(self):
        """10 points for an LZ station, 1 or 3 by continent otherwise."""
        parent = self.parent
        if parent.contact_is_dupe:
            return 0

        their_country, their_continent = self._entity(parent.contact.get("Call", ""))
        if not their_country:
            return 0

        # The entrant's own lookup can fail too; _entity guards that, where the
        # module left my_continent unbound and points() raised.
        my_country, my_continent = self._entity(parent.station.get("Call", ""))

        if my_country == "Bulgaria" and their_country == "Bulgaria":
            return 1
        if their_country == "Bulgaria":
            return 10
        if my_continent != their_continent:
            return 3
        return 1

    def mult_value(self, slot, contact):
        """A live ITU zone, or the district/country according to the entrant."""
        if slot == 1:
            zone = contact.get("ZN")
            try:
                return int(zone) if int(zone or 0) > 0 else None
            except (TypeError, ValueError):
                return None
        if slot == 2:
            if self._is_lz():
                country = contact.get("CountryPrefix")
                return country or None
            district = contact.get("NR")
            if (
                contact.get("CountryPrefix") == "LZ"
                and isinstance(district, str)
                and district != ""
            ):
                return district.upper()
            return None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same keys as SQL, for counting the log."""
        if slot == 1:
            return "CASE WHEN ZN > 0 THEN ZN END"
        if slot == 2:
            if self._is_lz():
                return "CASE WHEN CountryPrefix != '' THEN CountryPrefix END"
            return (
                "CASE WHEN CountryPrefix = 'LZ' AND typeof(NR) = 'text' "
                "AND NR <> '' THEN upper(NR) END"
            )
        return super().mult_sql(slot)

    def get_mults(self):
        """The score page's single row, as the module summed it."""
        return {"state": self.show_mults()}

    def set_contact_vars(self):
        """The reports and the exchange, then mark the two multipliers."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text().upper()
        parent.contact["NR"] = parent.other_2.text().upper()
        self.mark_multipliers()

    def after_recalculate_mults(self):
        """Refresh the log window after a rescore."""
        if self.parent.log_window:
            self.parent.log_window.msg_from_main({"cmd": "UPDATELOG"})

    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Exch1', '')}, "
                f"{result.get('UserText', '...')}"
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
                parent.other_2.setText(f"{result.get('Exch1', '')}")
