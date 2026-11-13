"""IARU Region 1 Field Day (SSB)

Status:            Active
Geographic Focus:  Europe
Participation:     Worldwide
Mode:              CW
Bands:             160, 80, 40, 20, 15, 10m
Classes:           (see your national society rules)
Exchange:          RST + Serial No.
E-mail logs to:    (none)
Upload log at:     https://dxhf2.darc.de/~fdcwlog/upload.cgi?form=referat&lang=en
Mail logs to:      (none)
Find rules at:     https://www.darc.de/der-club/referate/conteste/iaru-region-1-fieldday/en/

Scoring:
  Fixed station to fixed station: 0 points.
  For contacts with:
    fixed stations in Europe: 2 points
    fixed stations outside Europe: 3 points
    portable stations in Europe: 4 points
    portable stations outside Europe: 6 points

Each station may be contacted only once per band.  Portable stations only
count as portable if they sign "/p", "/m", "/mm", or "/am".

Multipliers: ONE for each WAE country / DXCC entity worked on each band.
"""

from not1mm.lib.contest import ContestBase

# Rule: a station is portable when it signs one of these.
PORTABLE_SUFFIXES = ("/P", "/M", "/MM", "/AM")


def format_received_serial(value):
    """Render a received serial for the Cabrillo QSO line.

    The received number is the exchange an IARU R1 Field Day contact carries;
    a zero is written ``000`` so the column does not collapse to one character.
    """
    if value is None:
        return ""

    serial = str(value).strip()
    return "000" if serial == "0" else serial


class Contest(ContestBase):
    """IARU Region 1 Field Day, SSB."""

    DisplayName = "IARU FIELDDAY R1 DARC SSB"
    CabrilloName = "FD SSB"
    Mode = "SSB"
    EXCHANGE_HINT = "#"
    DupeType = 2  # once per band
    SendsRTCScore = True
    # A WAE country / DXCC entity once per band.
    NumMults = 1
    Multiplier1Name = "CountryPrefix"
    MultSqlString = "CountryPrefix"
    IsMult1Per = 1
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
        "PTS",
    ]

    def mult_sql(self, slot):
        """A contact without a country is not a multiplier.

        An imported log need not carry ``COUNTRYPREFIX``, and the module's live
        marking skipped such a contact while its replay did not -- so the
        column and the count disagreed.  Excluding the empty value makes the
        count, the marking and the score agree.
        """
        if slot == 1:
            return "NULLIF(CountryPrefix, '')"
        return super().mult_sql(slot)

    def set_contact_vars(self):
        """Contest Specific"""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = parent.other_2.text()
        if parent.contact.get("CountryPrefix", ""):
            self.mark_multipliers()

    def prefill(self):
        """Fill SentNR"""
        serial_nr = str(self.parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(self.parent.other_1.text()) == 0:
            self.parent.other_1.setText(serial_nr)

    def points(self):
        """Calc point

        fixed stations in Europe: 2 points
        fixed stations outside Europe: 3 points
        portable stations in Europe: 4 points
        portable stations outside Europe: 6 points
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        their_portable = False
        im_portable = False
        their_continent = parent.contact.get("Continent", "")
        the_call = parent.contact.get("Call", "").upper()

        if the_call.endswith(PORTABLE_SUFFIXES):
            their_portable = True
        if parent.station.get("Call", "").endswith(PORTABLE_SUFFIXES):
            im_portable = True

        if not im_portable and not their_portable:
            return 0

        if their_continent:
            if their_portable:
                if their_continent == "EU":
                    return 4
                return 6
            if their_continent == "EU":
                return 2
            return 3

        # Something wrong
        return 0

    def recalculate_mults(self):
        """Recalculate points and multipliers after a change in the log.

        The score is the sum of the ``Points`` column, and a contact's points
        depend on whether it is a duplicate, so the replay recomputes them --
        the base's replay only marks multipliers.  The country is marked the
        first time it appears on a band, as the module's own query did.
        """
        parent = self.parent
        worked = set()
        seen = set()
        for contact in parent.database.fetch_all_contacts_asc():
            parent.contact = contact
            key = (contact.get("Call", ""), contact.get("Band", ""))
            parent.contact_is_dupe = 1 if key in worked else 0
            worked.add(key)
            contact["Points"] = self.points()
            country = self.mult_value(1, contact)
            mult_key = (country, contact.get("Band", ""))
            contact["IsMultiplier1"] = 1 if country and mult_key not in seen else 0
            if country:
                seen.add(mult_key)
            parent.database.change_contact(contact)

    def cabrillo_qso_line(self, contact):
        """One ``QSO:`` line, with a zero received serial written ``000``."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{str(contact.get('SentNr', '')).ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{format_received_serial(contact.get('NR', '')).ljust(6)}"
        )
