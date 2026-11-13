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
    FrameText = ("SNT", "SentNR", "Prov or SN")
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
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.other_1.text()

    def recalculate_mults(self):
        """Nothing to mark: the count comes from the log, not the M column."""

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        The exchange is our serial or province *and* theirs, so both fields
        have to be filled before the contact is finished.
        """
        parent = self.parent
        if new_focused_widget is not None:
            parent.current_widget = parent.inputs_dict.get(new_focused_widget)

        for a_button in (
            parent.F1,
            parent.F2,
            parent.F3,
            parent.F4,
            parent.F5,
            parent.F6,
            parent.F7,
            parent.F8,
            parent.F9,
            parent.F10,
            parent.F11,
            parent.F12,
        ):
            parent.restore_button_color(a_button)

        buttons_to_send = []
        if parent.pref.get("run_state"):
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) < 3:
                    parent.make_button_green(parent.esm_dict["CQ"])
                    buttons_to_send.append(parent.esm_dict["CQ"])
                    parent.esm_call_sent = ""
                elif len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["HISCALL"])
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["HISCALL"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])

            elif parent.current_widget in ("other_1", "other_2"):
                if parent.other_1.text() == "" or parent.other_2.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                else:
                    self._resend_corrected_call(buttons_to_send)
                    parent.make_button_green(parent.esm_dict["QRZ"])
                    buttons_to_send.append(parent.esm_dict["QRZ"])
                    buttons_to_send.append("LOGIT")

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            parent.esm_call_sent = ""
                            continue
                        if button == parent.esm_dict.get("HISCALL"):
                            parent.esm_call_sent = parent.callsign.text()
                        parent.process_function_key(button)
        else:
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["MYCALL"])
                    buttons_to_send.append(parent.esm_dict["MYCALL"])

            elif parent.current_widget in ("other_1", "other_2"):
                if parent.other_1.text() == "" or parent.other_2.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                else:
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            continue
                        parent.process_function_key(button)

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
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Sect', '')}")
