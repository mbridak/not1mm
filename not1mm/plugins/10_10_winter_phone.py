"""10 10 winter phone plugin

Find rules at: https://www.ten-ten.org/qso-party-rules

The exchange is a name, a 10-10 number and an SPC, all typed into one field.
Two points when there is a 10-10 number, one otherwise, and no multipliers.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    """10 10 winter phone."""

    DisplayName = "10 10 WINTER PHONE"
    CabrilloName = "10-10-WINTER-PHONE"
    Mode = "SSB"
    DupeType = 1  # once per contest
    EXCHANGE_HINT = "Name + 10-10# + SPC"
    SendsRTCScore = True
    Bands = (28,)
    # The entry window hides other_1; the whole exchange goes in other_2, whose
    # spaces are significant, so advance_on_space is deliberately not set.
    EntryFields = ("field1", "field2", "field4")
    FrameText = ("SNT", "", "Name 1010# SPC")
    AccessibleNames = ("RST Sent", "", "", "Name 10 10 # SPC")
    TabOrder = ("callsign", "sent", "receive", "other_2")

    def validate(self):
        """The exchange is a name, a 10-10 number and an SPC."""
        exchange = self.parent.other_2.text().upper().split()
        return (
            len(exchange) == 3
            and exchange[0].isalpha()
            and exchange[1].isdigit()
            and exchange[2].isalpha()
        )

    def set_contact_vars(self):
        """The whole exchange in NR, the name split out, and a validity check."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)
        exchange = parent.other_2.text().upper().split()
        if len(exchange) == 3:
            parent.contact["Name"] = exchange[0]
            parent.contact["Comment"] = self.DisplayName
        if not self.validate():
            parent.show_message_box("The exchange was invalid.")

    def points(self):
        """Two points with a 10-10 number, one without.

        The exchange logged is read rather than the entry field: an imported or
        re-scored log leaves the field empty and every contact would score zero.
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        exchange = str(parent.contact.get("NR", "")).upper().split()
        if len(exchange) != 3:
            exchange = parent.other_2.text().upper().split()
        if len(exchange) == 3:
            try:
                if int(exchange[1]) > 0:
                    return 2
                return 1
            except ValueError:
                ...
        return 0
