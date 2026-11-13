"""John Moyle Memorial Field Day (WIA-JMMFD)

Find rules at: https://www.wia.org.au/members/contests/johnmoyle/
Upload logs at: https://vklogchecker.com

160m to 10m and 50 MHz and up.  The exchange is RST and a serial number.  A
station may be worked once per band, per mode group and per three-hour block
(eight blocks from 0100 UTC); phone is one point and CW two, and only a
contact with a VK, ZL or P2 station at one end scores.  Each new VK/ZL/P2
prefix is a multiplier once per band, per mode group and per block.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

import datetime

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import calculate_wpx_prefix, get_logged_band
from not1mm.lib.plugin_common import contest_time

_PHONE_MODES = ("LSB", "USB", "SSB", "FM", "AM")

# primary_pfx for Australia, New Zealand and Papua New Guinea (cty.json maps
# VK/VL/VJ/VI/AX -> VK and ZL/ZM/ZK -> ZL).  Only these stations give mults and
# DX stations may only claim points for them.
_OCEANIA_COUNTRY_PREFIXES = ("VK", "ZL", "P2")

_OCEANIA_ENTITIES = ("Australia", "New Zealand", "Papua New Guinea")

# The frequency column the sponsor's log checker expects, by band.
_CABRILLO_FREQ = {
    "1.8": "1800",
    "3.5": "3500",
    "7.0": "7000",
    "14.0": "14000",
    "21.0": "21000",
    "28.0": "28000",
    "50.0": "50",
    "70.0": "70",
    "144.0": "144",
    "222.0": "222",
    "432.0": "432",
    "902.0": "902",
    "1296.0": "1.2G",
    "2300.0": "2.3G",
    "3300.0": "3.4G",
    "5650.0": "5.7G",
    "10000.0": "10G",
    "24000.0": "24G",
    "47000.0": "47G",
    "75500.0": "75G",
    "119980.0": "122G",
    "134000.0": "134G",
    "241000.0": "241G",
}


def _band_from_contact(contact: dict) -> str:
    """Return the canonical DXLOG band value (e.g. '7.0') for a contact."""
    band = str(contact.get("Band", ""))
    if not band or band == "0.0":
        freq = contact.get("Freq", 0)
        if freq:
            band = get_logged_band(str(float(freq) * 1_000_000))
    return str(float(band))


def _mode_group(mode: str) -> str:
    """Group a radio mode into PH, CW or OTHER per the JMMFD rules."""
    if mode in _PHONE_MODES:
        return "PH"
    if str(mode).startswith("CW"):
        return "CW"
    return "OTHER"


def _block_from_ts(ts: str) -> int:
    """Return the 3-hour block (0-7) for a UTC timestamp string.

    Blocks start at 0100 UTC: 0100-0400 is block 0, 2200-0100 is block 7.
    """
    if len(ts) < 13:
        return 0
    hour = int(ts[11:13])
    if hour < 1:
        return 7
    return (hour - 1) // 3


def _block_boundaries(now: datetime.datetime) -> tuple:
    """Return the (start, end) UTC datetimes of the current 3-hour block."""
    if now.hour < 1:
        block_start = (now - datetime.timedelta(days=1)).replace(
            hour=22, minute=0, second=0, microsecond=0
        )
        block_end = now.replace(hour=1, minute=0, second=0, microsecond=0)
    else:
        block = (now.hour - 1) // 3
        block_start = now.replace(hour=1 + 3 * block, minute=0, second=0, microsecond=0)
        block_end = block_start + datetime.timedelta(hours=3)
    return block_start, block_end


class Contest(ContestBase):
    """John Moyle Memorial Field Day."""

    DisplayName = "John Moyle Field Day"
    CabrilloName = "WIA-JMMFD"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "#"
    # A station may be worked once per band, per mode group and per block.
    DupeType = 5
    SendsRTCScore = True
    Bands = (
        1.8,
        3.5,
        7,
        14,
        21,
        28,
        50,
        70,
        144,
        222,
        432,
        902,
        1296,
        2300,
        3300,
        5650,
        10000,
        24000,
        47000,
        75500,
        119980,
        134000,
        241000,
    )
    DefaultContestExchange = "#"
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
    # Each VK/ZL/P2 prefix, once per band, per mode group and per block.  The
    # key itself is the CASE in mult_sql()/mult_value() below.
    NumMults = 1
    Multiplier1Name = "WPXPrefix"
    MultSqlString = "WPXPrefix"
    IsMult1Per = 1  # once per band (the mode group and block are in the key)

    def _is_oceania_entity(self, call: str) -> bool:
        """True when *call* belongs to a VK, ZL or P2 (Oceania) entity."""
        result = self.parent.cty_lookup(call)
        if result is None:
            return False
        try:
            item = result.get(next(iter(result)))
        except (StopIteration, AttributeError):
            return False
        return item.get("entity", "") in _OCEANIA_ENTITIES

    def mult_sql(self, slot: int):
        """The prefix key: per band, mode group and three-hour block.

        Blocks run from 0100 UTC, and the hour before 0100 is the last block of
        the previous day.  An empty prefix is not a multiplier: the module's
        replay already skipped it, while its count did not test for it.
        """
        if slot != 1:
            return super().mult_sql(slot)
        return (
            "CASE WHEN CountryPrefix IN ('VK','ZL','P2') AND WPXPrefix <> '' "
            "AND (Mode IN ('LSB','USB','SSB','FM','AM') OR Mode LIKE 'CW%') "
            "THEN WPXPrefix || ':' || "
            "CASE WHEN Mode IN ('LSB','USB','SSB','FM','AM') THEN 'PH' ELSE 'CW' END "
            "|| ':' || "
            "CASE WHEN CAST(substr(TS,12,2) AS INTEGER) < 1 THEN 7 "
            "ELSE (CAST(substr(TS,12,2) AS INTEGER) - 1) / 3 END END"
        )

    def mult_value(self, slot: int, contact):
        """The same key as :meth:`mult_sql`, from a logged row or a spot."""
        if slot != 1:
            return super().mult_value(slot, contact)
        if contact.get("CountryPrefix", "") not in _OCEANIA_COUNTRY_PREFIXES:
            return None
        prefix = contact.get("WPXPrefix", "")
        group = _mode_group(contact.get("Mode", ""))
        if not prefix or group == "OTHER":
            return None
        return f"{prefix}:{group}:{_block_from_ts(contact.get('TS', ''))}"

    def set_contact_vars(self):
        """The exchange, the block the contact belongs to, and its multiplier."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = parent.other_2.text()
        # Record the three-hour block on the contact; the log editor shows it.
        parent.contact["MiscText"] = str(_block_from_ts(parent.contact.get("TS", "")))
        self.mark_multipliers()

    def prefill(self):
        """Fill SentNR with the next serial number.

        Single Op and Multi-Single run the serial consecutively across all
        bands.  Multi Op restarts at 001 on each band.
        """
        parent = self.parent
        operator_category = parent.contest_settings.get("OperatorCategory", "")
        if operator_category in ("MULTI-OP", "MULTI-TWO"):
            result = parent.database.exec_sql(
                "select max(SentNR) + 1 as serial_nr from DXLOG "
                "where ContestNR = ? and Band = ?;",
                (parent.pref.get("contest", "1"), _band_from_contact(parent.contact)),
            )
            serial_nr = str(result.get("serial_nr", "1")).zfill(3)
        else:
            serial_nr = str(parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(parent.other_1.text()) == 0:
            parent.other_1.setText(serial_nr)

    def points(self):
        """Phone is one point and CW two; only an Oceania contact scores.

        Only VK, ZL and P2 stations give points, and a station outside Oceania
        can only claim points for contacts with them.
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        mode_group = _mode_group(parent.contact.get("Mode", ""))
        if mode_group == "OTHER":
            return 0
        if parent.contact.get(
            "CountryPrefix", ""
        ) not in _OCEANIA_COUNTRY_PREFIXES and not self._is_oceania_entity(
            parent.station.get("Call", "")
        ):
            return 0
        return 2 if mode_group == "CW" else 1

    def recalculate_mults(self):
        """Recompute the points, the block and the multiplier in log order.

        An imported log carries neither prefix and has no dupe decisions, so
        cty fills the prefixes and the contact's own (call, band, mode group,
        block) decides the dupe.  The score is the sum of the ``Points``
        column, so it has to be worked out again here.
        """
        parent = self.parent
        database = parent.database
        worked = set()
        seen = set()
        for contact in database.fetch_all_contacts_asc():
            parent.contact = contact
            result = parent.cty_lookup(contact.get("Call", ""))
            if result is not None:
                item = result.get(next(iter(result)))
                contact["CountryPrefix"] = item.get("primary_pfx", "")
                contact["WPXPrefix"] = calculate_wpx_prefix(contact.get("Call", ""))

            band = str(contact.get("Band", ""))
            block = _block_from_ts(contact.get("TS", ""))
            contact["MiscText"] = str(block)
            key = (
                contact.get("Call", ""),
                band,
                _mode_group(contact.get("Mode", "")),
                block,
            )
            parent.contact_is_dupe = 1 if key in worked else 0
            worked.add(key)

            contact["Points"] = self.points()
            value = self.mult_value(1, contact)
            if contact["Points"] > 0 and value and value not in seen:
                contact["IsMultiplier1"] = 1
                seen.add(value)
            else:
                contact["IsMultiplier1"] = 0
            database.change_contact(contact)

    def specific_contest_check_dupe(self, call: str) -> dict:
        """A call is a dupe on this band and mode group inside the same block."""
        parent = self.parent
        mode_group = _mode_group(parent.radio_state.get("mode", ""))
        if mode_group == "OTHER":
            return {"isdupe": False}

        # The block is the one the contact was logged in, so a re-scored or
        # imported log is checked against its own clock and not the wall clock.
        block_start, block_end = _block_boundaries(contest_time(parent))
        result = parent.database.exec_sql(
            """
            select count(*) as isdupe from dxlog where
            Call = ?
            and Band = ?
            and ContestNR = ?
            and TS >= ?
            and TS < ?
            and CASE WHEN Mode IN ('LSB','USB','SSB','FM','AM') THEN 'PH'
                     WHEN Mode like 'CW%' THEN 'CW'
                     ELSE 'OTHER' END = ?
            ;""",
            (
                call,
                parent.contact.get("Band", ""),
                parent.pref.get("contest", "0"),
                block_start.strftime("%Y-%m-%d %H:%M:%S"),
                block_end.strftime("%Y-%m-%d %H:%M:%S"),
                mode_group,
            ),
        )
        if result:
            return result
        return {"isdupe": False}

    def cabrillo_mode(self, mode: str) -> str:
        """FM is a phone contact here, as the module wrote it."""
        if mode == "FM":
            return "PH"
        return super().cabrillo_mode(mode)

    def cabrillo_qso_line(self, contact):
        """The JMMFD line: the sponsor's frequency token and padded serials."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        band = _band_from_contact(contact)
        frequency = _CABRILLO_FREQ.get(
            band, str(round(contact.get("Freq", "0"))).rjust(5)
        )
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{str(contact.get('SentNr', '0')).rjust(3, '0').ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{str(contact.get('NR', '0')).rjust(3, '0').ljust(6)}"
        )
