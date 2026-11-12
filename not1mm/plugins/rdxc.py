"""Russian DX Contest (RDXC) plugin.

Status:            Active
Geographic Focus:  Worldwide
Participation:     Worldwide
Awards:            Worldwide
Mode:              CW, SSB
Bands:             160, 80, 40, 20, 15, 10m
Classes:           Single Op All Band (QRP/Low/High)
                   Single Op Single Band
                   Multi-Single
                   Multi-Two
                   Multi-Multi
Max power:         HP: >100 watts
                   LP: 100 watts
                   QRP: 5 watts
Exchange:          Russian stations: RS(T) + oblast code
                   non-Russian stations: RS(T) + Serial No.
Work stations:     Once per band per mode
QSO Points:        Russian stations:
                     2 pts QSO with Russia on your continent
                     5 pts QSO with Russia on another continent
                     3 pts QSO with different country on your continent
                     5 pts QSO with another continent
                   Non-Russian stations:
                     10 pts QSO with Russian station
                     2 pts QSO with your own country
                     3 pts QSO with different country on your continent
                     5 pts QSO with another continent
                     5 pts QSO with /MM station
Multipliers:       Each Russian oblast once per band
                   Each country (DXCC + WAE) once per band
Score Calculation: Total score = total QSO points x total mults
Find rules at:     https://www.rdxc.org/rules_eng
Cabrillo name:     RDXC
"""

import logging

from not1mm.lib.contest import ContestBase

logger = logging.getLogger(__name__)

# Primary prefixes assigned to Russian stations by the country file.
# UA = European Russia, UA9 = Asiatic Russia, UA2 = Kaliningrad.
RUSSIA_PREFIXES = ("UA", "UA9", "UA2")

# Rule 7.3: Kaliningrad (UA2F), Franz Josef Land (RI1FJ) and the Russian
# Antarctic stations (RI1AN) each count as a separate DXCC entity *and* a
# separate oblast. cty.dat gives Franz Josef Land the prefix R1FJ and files the
# Antarctic calls under the generic Antarctica entity, so they are recognised
# by callsign rather than by CountryPrefix.
SPECIAL_RUSSIAN_PREFIXES = ("R1FJ", "RI1FJ", "RI1AN")

# The Russian prefixes as a SQL list, for the oblast key.
RUSSIA_PREFIX_LIST = ", ".join(f"'{prefix}'" for prefix in RUSSIA_PREFIXES)

# ... and the rule 7.3 calls, as a SQL condition.
SPECIAL_RUSSIAN_SQL = " OR ".join(
    f"Call LIKE '{prefix}%'" for prefix in SPECIAL_RUSSIAN_PREFIXES
)


def is_russian_prefix(prefix: str) -> bool:
    """Return True if the country prefix belongs to a Russian station."""
    return prefix.upper() in RUSSIA_PREFIXES


def is_russian_station(countryprefix: str, call: str) -> bool:
    """Return True for a Russian station, including the rule 7.3 specials."""
    if is_russian_prefix(countryprefix):
        return True
    return str(call).upper().startswith(SPECIAL_RUSSIAN_PREFIXES)


def country_mult_prefix(prefix: str) -> str:
    """Return the country multiplier key for a country prefix.

    Rule 9 uses the DXCC entity list, where European Russia (UA) and Asiatic
    Russia (UA9) are separate countries, as is Kaliningrad (UA2).
    """
    return prefix.upper()


class Contest(ContestBase):
    """Russian DX Contest."""

    DisplayName = "RDXC"
    CabrilloName = "RDXC"
    Mode = "BOTH"
    EXCHANGE_HINT = "# or Oblast"
    DupeType = 3  # once per band and mode
    SendsRTCScore = True
    # The reports, our exchange (a serial or an oblast code) and the received
    # one.
    FrameText = ("SNT", "SentNR", "Serial or Oblast")
    AccessibleNames = (
        "RST Sent",
        "",
        "Sent Number",
        "Serial Number or Russian Oblast",
    )
    # Each Russian oblast once per band, and each country once per band.
    NumMults = 2
    Multiplier1Name = "Oblast"
    MultSqlString = "NR"
    IsMult1Per = 1
    Multiplier2Name = "CountryPrefix"
    MultSqlString2 = "CountryPrefix"
    IsMult2Per = 1
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "M1",
        "M2",
        "PTS",
    ]

    def his_prefix(self, contact) -> str:
        """The worked station's prefix, from the contact or from cty."""
        countryprefix = contact.get("CountryPrefix", "")
        if not countryprefix:
            result = self.parent.cty_lookup(contact.get("Call", ""))
            if result:
                item = result.get(next(iter(result)))
                countryprefix = item.get("primary_pfx", "")
        return countryprefix

    def mult_value(self, slot, contact):
        """An oblast from a Russian station, and every country, once a band."""
        if slot == 1:
            if "/MM" in str(contact.get("Call", "")).upper():
                return None  # rule 7.4: maritime mobile is no multiplier
            if not is_russian_station(
                self.his_prefix(contact), contact.get("Call", "")
            ):
                return None
            return contact.get("NR") or None
        if slot == 2:
            if "/MM" in str(contact.get("Call", "")).upper():
                return None
            return country_mult_prefix(self.his_prefix(contact)) or None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same two keys as SQL, for counting the log."""
        if slot == 1:
            return (
                "CASE WHEN NR <> '' AND Call NOT LIKE '%/MM%' AND "
                f"(CountryPrefix IN ({RUSSIA_PREFIX_LIST}) OR "
                f"{SPECIAL_RUSSIAN_SQL}) THEN NR END"
            )
        if slot == 2:
            return "CASE WHEN Call NOT LIKE '%/MM%' THEN CountryPrefix END"
        return super().mult_sql(slot)

    def get_mults(self):
        """The score page's two rows, under the names this contest used."""
        return {"country": self._mult_count(2), "oblast": self._mult_count(1)}

    def set_contact_vars(self):
        """Contest Specific"""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["IsMultiplier1"] = 0
        parent.contact["IsMultiplier2"] = 0
        if parent.contact_is_dupe == 0:
            self.mark_multipliers()

    def prefill(self):
        """Fill SentNR"""
        serial_nr = str(self.parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(self.parent.other_1.text()) == 0:
            self.parent.other_1.setText(serial_nr)

    def points(self):
        """Calc point"""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        call = parent.contact.get("Call", "")
        if call.upper().endswith("/MM"):
            return 5

        mycountry = ""
        mycontinent = ""
        hiscountry = ""
        hiscontinent = ""

        result = parent.cty_lookup(parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            mycountry = item.get("entity", "")
            mycontinent = item.get("continent", "")

        result = parent.cty_lookup(call)
        if result is not None:
            item = result.get(next(iter(result)))
            hiscountry = item.get("entity", "")
            hiscontinent = item.get("continent", "")

        if not hiscountry:
            return 0

        his_is_russian = hiscountry in (
            "European Russia",
            "Asiatic Russia",
            "Kaliningrad",
        )

        if mycountry in ("European Russia", "Asiatic Russia", "Kaliningrad"):
            # Russian station
            if his_is_russian:
                if mycontinent == hiscontinent:
                    return 2  # QSO with Russia on your continent
                return 5  # QSO with Russia on another continent
            if mycontinent == hiscontinent:
                return 3  # QSO with a different country on your continent
            return 5  # QSO with another continent

        # Non-Russian station
        if his_is_russian:
            return 10  # QSO with Russian station
        if mycountry == hiscountry:
            return 2  # QSO with your own country
        if mycontinent == hiscontinent:
            return 3  # QSO with a different country on your continent
        return 5  # QSO with another continent

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        The exchange is our serial or oblast *and* theirs, so both entry fields
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
                f"{result.get('Call', '')}, {result.get('Exch1', '')}, "
                f"{result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the received oblast from call history."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Exch1', '')}")
