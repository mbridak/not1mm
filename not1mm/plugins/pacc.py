"""Dutch PACC Contest

Find rules at: https://veron.nl/vereniging/commissies-en-werkgroepen/traffic-bureau/

160m through 10m, CW and SSB, once per band and mode.  A Dutch station sends
its province, everyone else a serial number.  A Dutch entrant scores one point
for every contact; a foreign entrant only for the Dutch stations it works.

A Dutch entrant counts each DXCC country once per band and mode, a foreign
entrant each Dutch province (which is why the serial a non-Dutch station sends
is not a multiplier).

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

import logging

from not1mm.lib.contest import ContestBase
from not1mm.lib.fields import DEFAULT_ENTRY_WINDOW

logger = logging.getLogger(__name__)

PROV_SEC = [
    "DR",
    "FL",
    "FR",
    "GD",
    "GR",
    "LB",
    "NB",
    "NH",
    "OV",
    "UT",
    "ZH",
    "ZL",
]

# PROV_SEC as a SQL list, for the multiplier key.
PROVINCE_LIST = ", ".join(f"'{province}'" for province in PROV_SEC)


def _is_pa(parent, call) -> bool:
    """True when the callsign belongs to a Dutch station."""
    result = parent.cty_lookup(call)
    if not result:
        return False
    item = result.get(next(iter(result)), {})
    return item.get("entity", "") == "Netherlands"


class Contest(ContestBase):
    """Dutch PACC Contest."""

    DisplayName = "PACC"
    CabrilloName = "PACC"
    Mode = "BOTH"
    EXCHANGE_HINT = "# or Province"
    DupeType = 3  # once per band and mode
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    SendsRTCScore = True
    # The reports, our serial or province, and theirs.
    EntryWindowInfo = DEFAULT_ENTRY_WINDOW
    QsoErrorString = "SntNrText_Any_not_Empty, RcvNrText_Any_not_Empty"
    FrameText = ("SNT", "RCV", "SentNR", "Prov or SN")
    AccessibleNames = (
        "RST Sent",
        "",
        "Sent Number",
        "Province code or Serial Number",
    )
    # The country for a Dutch entrant, the provinces for everyone else.
    NumMults = 1
    Multiplier1Name = "State"
    MultSqlString = "NR"
    IsMult1Per = 3

    def im_dutch(self) -> bool:
        """True when the entrant is a Dutch station."""
        return _is_pa(self.parent, self.parent.station.get("Call", ""))

    def points(self):
        """One point, but a foreign entrant only scores the Dutch contacts."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        if self.im_dutch():
            return 1
        if _is_pa(parent, parent.contact.get("Call", "")):
            return 1
        return 0

    def mult_value(self, slot, contact):
        """The country for a Dutch entrant, the province for everyone else."""
        if slot == 1:
            if self.im_dutch():
                return contact.get("CountryPrefix", "")
            province = contact.get("NR")
            return province if province in PROV_SEC else None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same side-dependent key as SQL, for counting the log."""
        if slot == 1:
            if self.im_dutch():
                return "CountryPrefix"
            return f"CASE WHEN NR IN ({PROVINCE_LIST}) THEN NR END"
        return super().mult_sql(slot)

    def set_contact_vars(self):
        """The reports and the exchange; this contest marks no multipliers."""
        parent = self.parent
        parent.contact["SNT"] = parent.fields.SNTText.text()
        parent.contact["RCV"] = parent.fields.RCVText.text()
        parent.contact["NR"] = parent.fields.RcvNrText.text().upper()
        parent.contact["SentNr"] = parent.fields.SntNrText.text()

    def recalculate_mults(self):
        """Nothing to mark: the count comes from the log, not the M column."""

    def populate_history_info_line(self):
        """Show what call history knows about the station."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Sect', '')}, "
                f"{result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the province from call history."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.fields.RcvNrText.text() == "":
                parent.fields.RcvNrText.setText(f"{result.get('Sect', '')}")
