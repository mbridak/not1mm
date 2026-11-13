"""WIA Remembrance Day Contest plugin

Find rules at: https://www.wia.org.au/members/contests/rdcontest/

160m and up, CW/phone/digital.  A contact is worth one point, two on 160m and
two on 23cm and above, doubled on CW and RTTY, and all contacts logged between
0100 and 0600 local time score triple.  There is no multiplier.  A station may
be worked once per band every three hours, where FM counts as SSB and RTTY as
CW for the window.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

import datetime

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import band_mhz_of
from not1mm.lib.plugin_common import contest_time

# Rule 4: on CW and RTTY, whatever the band, the contact scores double.
_DOUBLE_POINT_MODES = (
    "CW",
    "CW-U",
    "CW-L",
    "CWR",
    "RTTY",
    "RTTY-R",
    "LSB-D",
    "USB-D",
    "AM-D",
    "FM-D",
    "DIGI-U",
    "DIGI-L",
    "DIG",
    "RTTYR",
    "PKTLSB",
    "PKTUSB",
    "FSK",
    "PKT",
)

# Cabrillo knows five modes; this sponsor calls the soundcard modes RY.
_CABRILLO_RY = (
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


def date_string_difference(date_str1, date_str2):
    """Difference between two UTC timestamps, as ``%H%M``."""
    date_format = "%Y-%m-%d %H:%M:%S"

    # Both stamps are UTC as logged; astimezone() on a naive datetime would
    # read them as local time and shift the difference by the local offset.
    dt1 = datetime.datetime.strptime(date_str1, date_format)
    dt2 = datetime.datetime.strptime(date_str2, date_format)
    diff = abs(dt1 - dt2)

    total_seconds = int(diff.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}{minutes:02d}"


def _dupe_mode(mode: str) -> str:
    """Group a mode the way rule 9.3a groups them for the three-hour window.

    FM and SSB count as one mode, and CW and RTTY count as another.
    """
    mode = str(mode).upper()
    if mode in ("LSB", "USB", "SSB", "FM", "AM"):
        return "PH"
    if mode.startswith("CW") or mode.startswith("RTTY"):
        return "CW"
    return mode


class Contest(ContestBase):
    """The WIA Remembrance Day Contest."""

    DisplayName = "WIA REMEMBRANCE"
    CabrilloName = "WIA-REMEMBRANCE"
    Mode = "BOTH"
    DupeType = 5  # once per band, per mode group, every three hours
    EXCHANGE_HINT = "Years Licenced"
    SOAPBOX_HINT = """ 
Exchange: A valid exchange consists of RS(T) followed by a number as follows:

a. For a single operator, the number of years you have been a licenced Ham. For example, if this is your 1st year as a ham then you will sign RS(T) 001. Round off to the nearest whole number. All zeros are not accepted.

b. For a multi-op or club station, the number of licenced years of the longest licenced Amateur present at the start of the contest.

A station may be worked once per band every three hours.  FM counts as SSB and RTTY counts as CW, so the call does stay lit as a dupe across those pairs.
"""
    DefaultContestExchange = "#"
    # 160m and the non-WARC HF bands, 23cm, and every band above it.
    Bands = (
        1.8,
        3.5,
        7,
        14,
        21,
        28,
        1296.0,
        2300.0,
        3300.0,
        5650.0,
        10000.0,
        24000.0,
        47000.0,
        75500.0,
        119980.0,
        134000.0,
        241000.0,
        300000.0,
    )
    # Only the sent years and the received years are used; other_1 (field3) is
    # hidden.
    EntryFields = ("field1", "field2", "field4")
    FrameText = ("", "Sent", "Years Licenced")
    AccessibleNames = ("", "", "Sent", "Years Licenced")
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "PTS",
    ]

    def points(self):
        """Rule 6: one point, plus 160m and 23cm, doubled, and the window."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        score = 1
        band = band_mhz_of(parent.contact.get("Band", 0))
        if band == 1.8:
            score += 1
        if band >= 1240.0:
            score += 1
        if parent.contact.get("Mode", "") in _DOUBLE_POINT_MODES:
            score *= 2
        # Rule 5: a contact between 0100 and 0600 local time scores triple.
        # The contact's own time is used so that a re-scored log is judged
        # against the clock it was logged on.
        local = (
            contest_time(parent)
            .replace(tzinfo=datetime.timezone.utc)
            .astimezone()
        )
        if 100 <= int(local.strftime("%H%M")) <= 600:
            score *= 3
        return score

    def set_contact_vars(self):
        """The exchange: the sent years, and the received years in ``NR``."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text().upper()
        parent.contact["NR"] = parent.other_2.text().upper()

        parent.contact["IsMultiplier1"] = 0
        parent.contact["IsMultiplier2"] = 0

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplierN``."""

    def get_mults(self):
        """The score page wants the (always zero) multiplier count."""
        return {"state": self.show_mults()}

    def specific_contest_check_dupe(self, call: str) -> dict:
        """Rule 9.3a: the same call within three hours, per band and mode group.

        FM and SSB count as one mode and CW and RTTY as another, so a station
        worked on FM is a duplicate if it is then worked on SSB inside the
        window.
        """
        parent = self.parent
        mode_group = _dupe_mode(parent.radio_state.get("mode", ""))
        query = (
            "select TS from DXLOG where Band = ? and Call = ? and ContestNR = ? and "
            "CASE WHEN Mode IN ('LSB','USB','SSB','FM','AM') THEN 'PH' "
            "WHEN Mode like 'CW%' or Mode like 'RTTY%' THEN 'CW' ELSE Mode END = ? "
            "order by TS DESC;"
        )
        result = parent.database.exec_sql(
            query,
            (
                parent.contact.get("Band", ""),
                call,
                parent.pref.get("contest", "0"),
                mode_group,
            ),
        )
        if result:
            log_dt = result.get("TS", False)
            if log_dt is not False:
                # The window is measured back from the contact's own time, not
                # the wall clock.
                date_time = contest_time(parent).strftime("%Y-%m-%d %H:%M:%S")
                delta = date_string_difference(log_dt, date_time)
                if int(delta) < 300:
                    return {"isdupe": True}
        return {"isdupe": False}

    def cabrillo_mode(self, mode: str) -> str:
        """CW, PH or RY, as the sponsor spells them."""
        if mode in ("CW-U", "CW-L", "CW-R", "CWR"):
            return "CW"
        if mode in ("LSB", "USB", "FM"):
            return "PH"
        if str(mode).strip() in _CABRILLO_RY:
            return "RY"
        return mode

    def cabrillo_qso_line(self, contact):
        """The Remembrance line: both serials zero-padded to three digits."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} "
            f"{self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{str(contact.get('SentNr', '0')).rjust(3, '0').ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{str(contact.get('NR', '')).rjust(3, '0').ljust(6)}"
        )

    def populate_history_info_line(self):
        """Show the history info for the typed call."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Exch1', '')}, "
                f"{result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")
