"""Trans-Tasman Low-Band Contest

Find rules at: https://www.wia.org.au/members/contests/transtasman/
Upload logs at: https://www.vklogchecker.com/

160, 80 and 40m, SSB/CW/digital.  Only contacts with a VK or ZL station at one
end count, and they are worth one point.  A station may be worked once per
band, per mode group and per two-hour block (three blocks from 0800 UTC), and
each different VK/ZL prefix counts once per band per block.  The score is the
contacts in each block times the prefixes worked in that block, summed over
the three blocks.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

import datetime

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import calculate_wpx_prefix, get_logged_band
from not1mm.lib.plugin_common import contest_time

_PHONE_MODES = ("LSB", "USB", "SSB", "FM", "AM")

# Prefixes used by stations operating within Australia or New Zealand and
# their external territories (eg VK9, VK0, ZK, ZM). cty.json maps the entities
# but not all external territories to a VK/ZL primary_pfx, so match the WPX
# prefix instead. The contest counts e.g. VK9 once, not per island.
_VK_ZL_PREFIXES = ("VK", "ZL", "ZK", "ZM")


def _band_from_contact(contact: dict) -> str:
    """Return the canonical DXLOG band value (e.g. '7.0') for a contact."""
    band = str(contact.get("Band", ""))
    if not band or band == "0.0":
        freq = contact.get("Freq", 0)
        if freq:
            band = get_logged_band(str(float(freq) * 1_000_000))
    return str(float(band))


def _mode_group(mode: str) -> str:
    """Group a radio mode into PH, CW or DIGI per the contest rules.

    SSB, CW and Digital (RTTY/PSK) are the three allowed mode classes.
    """
    if mode in _PHONE_MODES:
        return "PH"
    if str(mode).startswith("CW"):
        return "CW"
    return "DIGI"


def _block_from_ts(ts: str) -> int:
    """Return the 2-hour block (0-2) for a UTC timestamp string.

    Blocks run 0800-1000, 1000-1200 and 1200-1400 UTC.
    """
    if len(ts) < 13:
        return 0
    hour = int(ts[11:13])
    if hour < 8:
        return 0
    if hour > 13:
        return 2
    return (hour - 8) // 2


def _block_boundaries(now: datetime.datetime) -> tuple:
    """Return the (start, end) UTC datetimes of the current 2-hour block."""
    if now.hour < 8:
        block = 0
    elif now.hour > 13:
        block = 2
    else:
        block = (now.hour - 8) // 2
    block_start = now.replace(hour=8 + 2 * block, minute=0, second=0, microsecond=0)
    block_end = block_start + datetime.timedelta(hours=2)
    return block_start, block_end


def _is_vk_zl_prefix(wpx: str) -> bool:
    """Return True if a WPX prefix belongs to a VK or ZL station.

    Covers mainland VK/ZL calls and their external territories (VK9, VK0, ZK,
    ZM). ZK and ZM are New Zealand prefixes that cty.json maps to ZL.
    """
    return wpx.startswith(_VK_ZL_PREFIXES)


def _block_sql_expr() -> str:
    """SQL expression deriving the 2-hour block from a DXLOG TS value."""
    return (
        "CASE WHEN CAST(substr(TS,12,2) AS INTEGER) < 8 THEN 0 "
        "WHEN CAST(substr(TS,12,2) AS INTEGER) > 13 THEN 2 "
        "ELSE (CAST(substr(TS,12,2) AS INTEGER) - 8) / 2 END"
    )


def _vk_zl_wpx_filter(alias: str = "") -> str:
    """SQL WHERE fragment restricting a column to VK/ZL prefixes."""
    col = "WPXPrefix"
    if alias:
        col = f"{alias}.WPXPrefix"
    return (
        f"({col} like 'VK%' or {col} like 'ZL%' "
        f"or {col} like 'ZK%' or {col} like 'ZM%')"
    )


class Contest(ContestBase):
    """Trans-Tasman Low-Band Contest."""

    DisplayName = "Trans Tasman"
    CabrilloName = "WIA-TRANS TASMAN"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "#"
    SOAPBOX_HINT = "This has not been tested. Good Luck."
    # Rule: a station can be worked once per band per mode per 2-hour block.
    DupeType = 5
    Bands = (1.8, 3.5, 7)
    SendsRTCScore = True
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
    # A VK/ZL prefix, once per band per block.  The block is part of the key,
    # so it is in the expression rather than the "per" columns.
    NumMults = 1
    Multiplier1Name = "WPXPrefix"
    MultSqlString = "WPXPrefix"
    IsMult1Per = 1

    def prefill(self):
        """Fill SentNR with next serial number.

        Single Op runs the serial consecutively across all bands. Multi Op
        (multi-multi per the rules) restarts at 001 on each band.
        """
        parent = self.parent
        operator_category = parent.contest_settings.get("OperatorCategory", "")
        if operator_category == "SINGLE-OP":
            serial_nr = str(parent.current_sn).zfill(3)
        else:
            result = parent.database.exec_sql(
                "select max(SentNR) + 1 as serial_nr from DXLOG "
                "where ContestNR = ? and Band = ?;",
                (parent.pref.get("contest", "1"), _band_from_contact(parent.contact)),
            )
            serial_nr = str(result.get("serial_nr", "1")).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(parent.other_1.text()) == 0:
            parent.other_1.setText(serial_nr)

    def points(self):
        """All valid VK/ZL contacts are worth one point.

        Points are only awarded for contacts between two VK or ZL stations.
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        if not _is_vk_zl_prefix(parent.contact.get("WPXPrefix", "")):
            return 0
        my_wpx = calculate_wpx_prefix(parent.station.get("Call", ""))
        if not _is_vk_zl_prefix(my_wpx):
            return 0
        return 1

    def set_contact_vars(self):
        """The reports, the two serials and the block; then the multiplier."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = parent.other_2.text()

        # stash the 2-hour block so a replay does not have to reparse the time.
        parent.contact["MiscText"] = str(_block_from_ts(parent.contact.get("TS", "")))

        self.mark_multipliers()

    def mult_sql(self, slot):
        """The VK/ZL prefix and its block, as SQL."""
        if slot == 1:
            return (
                f"CASE WHEN {_vk_zl_wpx_filter()} "
                f"THEN WPXPrefix || ':' || {_block_sql_expr()} END"
            )
        return super().mult_sql(slot)

    def mult_value(self, slot, contact):
        """The same key in Python, for a contact or a spot."""
        if slot == 1:
            wpx = contact.get("WPXPrefix", "")
            if not _is_vk_zl_prefix(wpx):
                return None
            return f"{wpx}:{_block_from_ts(contact.get('TS', ''))}"
        return super().mult_value(slot, contact)

    def specific_contest_check_dupe(self, call):
        """Return dict with isdupe True if the call was worked on this band and
        mode-group in the current 2-hour block."""
        parent = self.parent
        mode = parent.radio_state.get("mode", "")
        mode_group = _mode_group(mode)

        band = parent.contact.get("Band", "")
        # The block is the one the contact was logged in, so a re-scored or
        # imported log is checked against its own clock and not the wall clock.
        block_start, block_end = _block_boundaries(contest_time(parent))

        query = """
            select count(*) as isdupe from dxlog where
            Call = ?
            and Band = ?
            and ContestNR = ?
            and TS >= ?
            and TS < ?
            and CASE WHEN Mode IN ('LSB','USB','SSB','FM','AM') THEN 'PH'
                     WHEN Mode like 'CW%' THEN 'CW'
                     ELSE 'DIGI' END = ?
            ;"""

        result = parent.database.exec_sql(
            query,
            (
                call,
                band,
                parent.pref.get("contest", "0"),
                block_start.strftime("%Y-%m-%d %H:%M:%S"),
                block_end.strftime("%Y-%m-%d %H:%M:%S"),
                mode_group,
            ),
        )
        if result:
            return result
        return {"isdupe": False}

    def show_qso(self):
        """Return qso count (only VK/ZL contacts score in this contest)."""
        parent = self.parent
        query = f"""
            select count(*) as qsos
            from DXLOG
            where ContestNR = ?
            and {_vk_zl_wpx_filter()};
            """
        result = parent.database.exec_sql(query, (parent.pref.get("contest", "0"),))
        if result:
            return int(result.get("qsos", 0))
        return 0

    def calc_score(self):
        """Return calculated score.

        For each of the three 2-hour blocks: contacts in that block multiplied
        by the number of different prefixes worked on each band in that block,
        summed over the blocks.  Only a contact that scored is one of those
        contacts - a duplicate is not, so it is counted out here.
        """
        contacts = self.parent.database.fetch_all_contacts_asc()
        qso_count = {}
        mult_count = {}
        for contact in contacts:
            wpx = contact.get("WPXPrefix", "")
            if not _is_vk_zl_prefix(wpx) or not contact.get("Points", 0):
                continue
            block = _block_from_ts(contact.get("TS", ""))
            qso_count[block] = qso_count.get(block, 0) + 1
            mult_count.setdefault(block, set()).add((contact.get("Band", ""), wpx))
        score = 0
        for block in (0, 1, 2):
            score += qso_count.get(block, 0) * len(mult_count.get(block, ()))
        return score

    def recalculate_mults(self):
        """Rescore and mark an imported log.

        The points and the multiplier are both read from WPXPrefix, which an
        imported ADIF does not have to carry, so it is filled from cty.  The
        duplicate has to be worked out here too: the score reads the Points
        column, and a duplicate is worth nothing.
        """
        parent = self.parent
        seen = set()
        seen_mult = set()
        for contact in parent.database.fetch_all_contacts_asc():
            parent.contact = contact
            result = parent.cty_lookup(contact.get("Call", ""))
            if result is not None:
                item = result.get(next(iter(result)))
                contact["CountryPrefix"] = item.get("primary_pfx", "")
                contact["WPXPrefix"] = calculate_wpx_prefix(contact.get("Call", ""))

            time_stamp = contact.get("TS", "")
            band = str(contact.get("Band", ""))
            contact["MiscText"] = str(_block_from_ts(time_stamp))

            key = (
                contact.get("Call", ""),
                band,
                _mode_group(contact.get("Mode", "")),
                _block_from_ts(time_stamp),
            )
            parent.contact_is_dupe = 1 if key in seen else 0
            seen.add(key)

            contact["Points"] = self.points()

            value = self.mult_value(1, contact)
            mult_key = (value, band)
            contact["IsMultiplier1"] = (
                0 if value in (None, "") or mult_key in seen_mult else 1
            )
            seen_mult.add(mult_key)
            parent.database.change_contact(contact)

    def cabrillo_mode(self, mode: str) -> str:
        """The sponsor's mode groups: phone is written ``PH``, digital as Cabrillo says.

        The module grouped SSB, AM and FM with the phone modes -- and anything
        that was not CW, RTTY or PSK as well.  The base knows only
        ``LSB``/``USB`` as phone, and it is the base that writes RTTY ``RY``
        (the standing rule) and the PSK sub-codes ``PS``/``PM``/``PO``, so both
        are spelled out here.
        """
        if mode.startswith("CW"):
            return "CW"
        if mode.startswith("RTTY"):
            return "RY"
        if mode.startswith(("PSK", "BPSK")):
            return super().cabrillo_mode(mode)
        return "PH"

    def cabrillo_qso_line(self, contact):
        """The serials are printed three digits wide, from the integer column."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
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
