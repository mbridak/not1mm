"""JIDX PH Contest

Status:            Active
Geographic Focus:  Japan
Participation:     Worldwide
Mode:              CW
Bands:             160, 80, 40, 20, 15, 10m
Exchange:          JA: RST + Prefecture No.
                   non-JA: RST + CQ Zone No.
Work stations:     Once per band
QSO Points:        4 points per JA-DX QSO on 160m
                   2 points per JA-DX QSO on 80m
                   1 point per JA-DX QSO on 40, 20, 15m
                   2 points per JA-DX QSO on 10m
Multipliers:       JA Stations: DXCC countries and CQ zones once per band
                   non-JA Stations: JA prefectures plus JD1/O, JD1/MT, JD1/OT
                   once per band
Find rules at:     http://www.jidx.org/jidxrule-e.html
Cabrillo name:     JIDX-SSB
"""

from not1mm.lib.contest import ContestBase, output_cabrillo_line
from not1mm.lib.plugin_common import get_points
from not1mm.lib.version import __version__


def _is_ja(parent, call) -> bool:
    """True when the callsign belongs to a Japanese station."""
    result = parent.cty_lookup(call)
    if not result:
        return False
    item = result.get(next(iter(result)), {})
    return item.get("entity", "") == "Japan"


class Contest(ContestBase):
    """JIDX PH Contest."""

    DisplayName = "JIDX PH"
    CabrilloName = "JIDX-SSB"
    Mode = "SSB"
    EXCHANGE_HINT = "Prefecture or CQ Zone"
    DupeType = 2  # once per band
    SendsRTCScore = True
    Bands = (1.8, 3.5, 7, 14, 21, 28)
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
    # Each prefecture (the JA station's number) once per band, and only a
    # contact that scored carries one.
    NumMults = 1
    Multiplier1Name = "Prefecture"
    MultSqlString = "NR"
    IsMult1Per = 1

    def mult_value(self, slot, contact):
        """The received number, as the log stores it.

        ``NR`` is an INTEGER column, so a logged contact carries an int while
        the entry field carries text; converting here keeps the live existence
        check comparing like with like.  Whether the contact scored is the SQL
        key's business (see :meth:`mult_sql`), so the bandmap can still answer
        for a spot.
        """
        if slot != 1:
            return super().mult_value(slot, contact)
        try:
            return int(str(contact.get("NR", "")).strip())
        except (TypeError, ValueError):
            return None

    def mult_sql(self, slot):
        """Only a scoring contact's prefecture counts (rule 6)."""
        if slot == 1:
            return "CASE WHEN Points > 0 THEN NR END"
        return super().mult_sql(slot)

    def set_contact_vars(self):
        """Contest Specific"""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = parent.other_2.text()
        # A JA-JA or DX-DX contact scores nothing, so it carries no multiplier;
        # the base's marking cannot see that, because Points is set after this.
        if self.points() > 0 and parent.contact.get("NR", ""):
            self.mark_multipliers()
        else:
            parent.contact["IsMultiplier1"] = 0

    def points(self):
        """Calc point"""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        # Rule 5: only contacts between a JA station and a DX station score.
        # JA-JA and DX-DX contacts are worth no points and no multiplier.
        if _is_ja(parent, parent.station.get("Call", "")) == _is_ja(
            parent, parent.contact.get("Call", "")
        ):
            return 0

        pts = {
            1: 4,
            3: 2,
            7: 1,
            14: 1,
            21: 1,
            28: 2,
        }
        mhz = int(int(float(parent.contact.get("Freq", 0))) / 1000)
        return pts.get(mhz, 0)

    def recalculate_mults(self):
        """Recalculates multipliers after change in logged qso."""
        parent = self.parent
        seen = set()
        for contact in parent.database.fetch_all_contacts_asc():
            # One multiplier per prefecture per band (rule 6).  A contact that
            # scores nothing - a duplicate, or a DX-DX contact - carries none.
            key = (str(contact.get("NR", "")), str(contact.get("Band", "")))
            if (contact.get("Points") or 0) > 0 and key not in seen:
                seen.add(key)
                contact["IsMultiplier1"] = 1
            else:
                contact["IsMultiplier1"] = 0
            parent.database.change_contact(contact)

    def get_mults(self):
        """Get mults for RTC XML"""
        return {"country": self.show_mults()}

    def _category(self) -> str:
        """The one ``CATEGORY:`` token JIDX asks for."""
        settings = self.parent.contest_settings
        category = ""
        band = settings.get("BandCategory", "")
        if settings.get("OperatorCategory", "") == "SINGLE-OP":
            if band == "ALL":
                category = "AB"
            if band == "10M":
                category = "28"
            if band == "15M":
                category = "21"
            if band == "20M":
                category = "14"
            if band == "40M":
                category = "7"
            if band == "80M":
                category = "3.5"
            if band == "160M":
                category = "1.8"
            if settings.get("PowerCategory", "") in ("LOW", "QRP"):
                category += "L"
        else:
            if settings.get("TransmitterCategory", "") == "ONE":
                category = "MOP1"
            else:
                category = "MOP2"
        return category

    def _cabrillo_header(self, file_descriptor, file_encoding):
        """JIDX's own header: a one-line category and a score breakdown."""
        parent = self.parent
        station = parent.station
        settings = parent.contest_settings

        def line(text):
            output_cabrillo_line(text, "\r\n", file_descriptor, file_encoding)

        result = parent.cty_lookup(station.get("Call", ""))
        mycountry = ""
        if result is not None:
            item = result.get(next(iter(result)))
            mycountry = item.get("entity", "")

        qsos = parent.database.fetch_qso_count().get("qsos", 0)
        raw_points = get_points(parent)
        mults = self.show_mults()

        line("START-OF-LOG: 2.0")
        line(f"CONTEST: {self.CabrilloName}")
        if station.get("Club", ""):
            line(f"CLUB: {station.get('Club', '').upper()}")
        line(f"CALLSIGN: {station.get('Call', '')}")
        line(f"CATEGORY: {self._category()}")
        line(f"CLAIMED-SCORE: {self.calc_score()} ({qsos}-{raw_points}-{mults})")
        ops = ""
        for op in parent.database.get_ops():
            ops += f"{op.get('Operator', '')}, "
        if station.get("Call", "") not in ops:
            ops += f"@{station.get('Call', '')}"
        else:
            ops = ops.rstrip(", ")
        line(f"OPERATORS: {ops}")
        line(f"CREATED-BY: Not1MM v{__version__}")
        line(f"ENTITY: {mycountry}")
        line(f"NAME: {station.get('Name', '')}")
        line(f"ADDRESS: {station.get('Street1', '')}")
        line(f"ADDRESS-CITY: {station.get('City', '')}")
        line(f"ADDRESS-STATE-PROVINCE: {station.get('State', '')}")
        line(f"ADDRESS-POSTALCODE: {station.get('Zip', '')}")
        line(f"ADDRESS-COUNTRY: {station.get('Country', '')}")
        line(f"EMAIL: {station.get('Email', '')}")
        line(f"SENTNR: {settings.get('SentExchange', '')}")
