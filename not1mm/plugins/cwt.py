"""CWT plugin

Find rules at: https://cwops.org/cwops-tests/

160-10m, once per band.  The exchange is the member's name and their member
number (or "CWA" for a non-member); each callsign worked is a multiplier once
for the contest.
"""

import logging

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

logger = logging.getLogger(__name__)


class Contest(ContestBase):
    """CWops Test (CWT)."""

    DisplayName = "CWT"
    CabrilloName = "CW-OPS"
    Mode = "CW"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "Name + Member No./'CWA'"
    DupeType = 2  # once per band
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    SupportsFT8 = True
    SendsRTCScore = True
    # The reports are hidden; only the two exchange fields are shown.
    EntryWindowInfo = ("NameText", 855, "RcvNrText", 625)
    QsoErrorString = "NameText_Any_not_Empty, RcvNrText_Any_not_Empty"
    FrameText = ("Name", "Number or State")
    AccessibleNames = (
        "Name",
        "Number or State",
    )
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
    PointsPerContact = 1
    # Each callsign once for the contest.
    NumMults = 1
    Multiplier1Name = "Calls"
    MultSqlString = "CallSign"
    IsMult1Per = 4

    def set_contact_vars(self):
        """The member's name and number; the sent exchange is a setting."""
        parent = self.parent
        parent.contact["SNT"] = self.report_default()
        parent.contact["RCV"] = self.report_default()
        parent.contact["Name"] = parent.fields.NameText.text().upper()
        parent.contact["NR"] = (
            parent.fields.NameText.text().upper()
            + " "
            + parent.fields.RcvNrText.text().upper()
        )
        parent.contact["SentNr"] = parent.contest_settings.get(
            "SentExchange", ""
        ).upper()
        self.mark_multipliers()

    def prefill(self):
        """Nothing to fill: the sent exchange is a fixed setting."""

    def predupe(self):
        """Recall the name and number from an earlier CWT QSO."""
        parent = self.parent
        if parent.fields.NameText.text() == "" and parent.fields.RcvNrText.text() == "":
            call = parent.callsign.text().upper()
            result = parent.database.exec_sql(
                "select NR from dxlog where Call = ? and ContestName = 'CWOPS-CWT' "
                "order by TS desc;",
                (call,),
            )
            if result:
                parts = str(result.get("NR", "")).upper().split()
                if len(parts) == 2:
                    parent.fields.NameText.setText(parts[0])
                    parent.fields.RcvNrText.setText(parts[1])

    def ft8_handler(self, the_packet: dict):
        """Process a logged QSO packet from WSJT-X or FlDigi."""
        parent = self.parent
        their_name = the_packet.get("NAME", "").upper()
        their_nr = (
            the_packet.get("SRX_STRING", "") or the_packet.get("SRX", "")
        ).upper()
        parent.callsign.setText(the_packet.get("CALL", ""))
        parent.fields.NameText.setText(their_name)
        parent.fields.RcvNrText.setText(their_nr)
        parent.contact["Call"] = the_packet.get("CALL", "")
        parent.contact["SNT"] = self.report_default()
        parent.contact["RCV"] = self.report_default()
        parent.contact["Name"] = their_name
        parent.contact["NR"] = f"{their_name} {their_nr}"
        parent.contact["Mode"] = the_packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(
            float(the_packet.get("FREQ", "0.0")) * 1000, 2
        )
        parent.contact["Band"] = get_logged_band(
            str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.save_contact()

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
        """Fill the exchange from the call history file, if it has one."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.fields.NameText.text() == "":
                parent.fields.NameText.setText(f"{result.get('Name', '')}")
            if parent.fields.RcvNrText.text() == "":
                parent.fields.RcvNrText.setText(f"{result.get('Exch1', '')}")
