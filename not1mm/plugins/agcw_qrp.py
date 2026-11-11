"""AGCW QRP contest plugin

Find rules at: https://www.agcw.de/contest/qrp/qrp-c-engl/

80/40/20/15/10m, once per band.  The exchange is RST, a three-digit serial, a
power class (VLP, QRP, MP or QRO) and an AGCW member number, with "NM" for a
non-member.  The points depend on the two power classes and a member worked is
a multiplier once per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

import re

from not1mm.lib.contest import ContestBase, output_cabrillo_line


def received_fields(r_nr: str) -> tuple:
    """Split a received exchange into ``(serial, power class, member)``.

    The operator types it with spaces, ``set_contact_vars`` stores it with
    slashes, and the power class is the only thing that carries letters -- so
    it is found rather than assumed to be in a fixed position.
    """
    text = r_nr.upper().replace("/", "")
    if len(text) > 3:
        power_class = re.findall("[A-Z]+[OP]", text)[0]
        head, member = text.split(power_class)
        return head, power_class, member
    return "001", "QRO", "NM"


class Contest(ContestBase):
    """AGCW QRP."""

    DisplayName = "AGCW QRP"
    CabrilloName = "AGCW-QRP"
    Mode = "CW"
    EXCHANGE_HINT = "# pwr_class MemberNr"
    SOAPBOX_HINT = """
Power classes are {VLP, QRP, MP, QRO}
MemberNr is AGCW-MemberNr or NM for Non Member.

For the Run exchange macro I’d put ’{SNT} # {EXCH}’"""
    ADIFContestID = "AGCW-QRP"
    SendsRTCScore = True
    # other_2 holds "serial power member" with spaces; they are turned into
    # slashes as the contact is stored, so they must survive being typed.
    advance_on_space = [True, True, True, True, False]
    Bands = (3.5, 7, 14, 21, 28)
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
    # Only the labels and names the module set; snt_label is left alone.
    FrameText = ("", "Sent", "SN Pwr MbrNr")
    AccessibleNames = ("", "", "Sent", "Serial Number Power Class Member Number")
    # A member worked is the multiplier; the second one (a DXCC entity per
    # band) was declared for other AGCW contests and is never marked, so it is
    # reported to the score page as zero.
    NumMults = 1
    Multiplier1Name = "MiscText"
    MultSqlString = "Misc"
    IsMult1Per = 1

    def set_contact_vars(self):
        """The exchange, and the member the contact is worth."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text().upper() + (
            parent.contest_settings.get("SentExchange", "xxx xxx").strip("#")
        )
        parent.contact["NR"] = parent.other_2.text().upper().replace(" ", "/")
        self.mark_multipliers()

    def mult_value(self, slot, contact):
        """The multiplier key: the AGCW member number, per band.

        A non-member ("NM") is not a multiplier, and neither is a number that
        is not a member number.
        """
        member = received_fields(contact.get("NR", ""))[2]
        return member if member != "NM" and member.isdigit() else None

    def mark_multipliers(self):
        """Set ``IsMultiplier1`` on the contact being logged.

        The member number lives inside ``NR`` (as ``serial/class/member``), so
        the check is not a column the base can build a query from.
        """
        parent = self.parent
        contact = parent.contact
        member = received_fields(contact.get("NR", ""))[2]
        if member == "NM" or not member.isdigit():
            contact["IsMultiplier1"] = 0
            return
        result = parent.database.exec_sql(
            "select count(*) as count from dxlog where NR like ? and Band = ? "
            "and ContestNR = ?;",
            (f"%/%/{member}", contact.get("Band"), parent.pref.get("contest", "1")),
        )
        contact["IsMultiplier1"] = 0 if result.get("count", 0) else 1

    def show_mults(self):
        """The number of multipliers is the number of marked contacts."""
        result = self.parent.database.fetch_mult_count(1)
        return int(result.get("count", 0)) if result else 0

    def get_mults(self):
        """The score page is told about both multipliers, as it always was."""
        return {"country": 0, "state": self.show_mults()}

    def after_recalculate_mults(self):
        """Refresh the log window after a rescore."""
        cmd = {"cmd": "UPDATELOG"}
        if self.parent.log_window:
            self.parent.log_window.msg_from_main(cmd)

    def points(self):
        """Points for the contact being logged: the two power classes.

        Two points is the default (QRO or MP against QRP or VLP, or MP against
        anything); QRO against QRO scores nothing and QRP against QRP or VLP
        scores three.  The contest setup offers HIGH/LOW/QRP for the power
        category, so the entrant's class is QRO, MP or QRP.
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        my_power = str(parent.contest_settings.get("PowerCategory", "")).upper()
        power_class = "QRO"
        nr = parent.contact.get("NR", "")
        if len(nr) > 0:
            serial, power_class, member = received_fields(nr)
            parent.contact["NR"] = f"{serial}/{power_class}/{member}"
        if my_power == "HIGH" and power_class == "QRO":
            return 0
        if my_power == "QRP" and power_class in ("QRP", "VLP"):
            return 3
        return 2

    def _cabrillo_header(self, file_descriptor, file_encoding):
        """The standard header, then the operator's soapbox."""
        super()._cabrillo_header(file_descriptor, file_encoding)
        soapbox = self.parent.contest_settings.get("Soapbox", "")
        if soapbox != self.SOAPBOX_HINT:
            for line in soapbox.splitlines():
                output_cabrillo_line(
                    f"SOAPBOX: {line}", "\r\n", file_descriptor, file_encoding
                )

    def cabrillo_qso_line(self, contact):
        """The standard line, with the stored slashes shown as spaces.

        Only the received exchange field is touched: a call like ``DL1ABC/P``
        keeps its slash.
        """
        number = str(contact.get("NR", "")).ljust(6)
        line = super().cabrillo_qso_line(contact)
        return f"{line[: -len(number)]}{number.replace('/', ' ')}"

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
