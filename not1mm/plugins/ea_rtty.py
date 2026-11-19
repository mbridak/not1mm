"""EA RTTY Contest

Find rules at: https://concursos.ure.es/en/eartty/bases/

80m-10m, once per band.  A Spanish station sends its province and everyone else
a serial; an EA-to-EA contact is 2 points, an EA-to-outside one 1 and an
outside-to-EA one 3.  Each EA province, each entity, each USA/VE/JA/VK call area
and the EA4URE special station are multipliers once per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

# cty.dat's primary prefixes for Spain, in the spelling the rules use.
EA_PREFIXES = ("EA", "EA1", "EA2", "EA3", "EA4", "EA5", "EA6", "EA7", "EA8", "EA9")

# The Spanish provinces the rules count, grouped by call area (see the rules):
# EA1: AV, BU, C, LE, LO, LU, O, OU, P, PO, S, SA, SG, SO, VA, ZA
# EA2: BI, HU, NA, SS, TE, VI, Z
# EA3: B, GI, L, T
# EA4: BA, CC, CR, CU, GU, M, TO
# EA5: A, AB, CS, MU, V
# EA6: IB
# EA7: AL, CA, CO, GR, H, J, MA, SE
# EA8: GC, TF
# EA9: CE, ML
# 'HQ' is not a province: it is EA4URE, a multiplier of its own.
EA_PROVINCES = frozenset(
    (
        "AV",
        "BU",
        "C",
        "LE",
        "LO",
        "LU",
        "O",
        "OU",
        "P",
        "PO",
        "S",
        "SA",
        "SG",
        "SO",
        "VA",
        "ZA",
        "BI",
        "HU",
        "NA",
        "SS",
        "TE",
        "VI",
        "Z",
        "B",
        "GI",
        "L",
        "T",
        "BA",
        "CC",
        "CR",
        "CU",
        "GU",
        "M",
        "TO",
        "A",
        "AB",
        "CS",
        "MU",
        "V",
        "IB",
        "AL",
        "CA",
        "CO",
        "GR",
        "H",
        "J",
        "MA",
        "SE",
        "GC",
        "TF",
        "CE",
        "ML",
    )
)

# "The call areas of USA, Canada, Japan, and Australia": cty.dat's primary
# prefixes for those countries, including the US areas it reports as entities
# of their own - Alaska (KL), Hawaii (KH0-KH9) and the Caribbean and Pacific
# possessions (KP1-KP5).
CALL_AREA_PREFIXES = frozenset(
    (
        "K",
        "KL",
        "KH0",
        "KH1",
        "KH2",
        "KH3",
        "KH4",
        "KH5",
        "KH6",
        "KH7",
        "KH8",
        "KH9",
        "KP1",
        "KP2",
        "KP3",
        "KP4",
        "KP5",
        "VE",
        "VK",
        "JA",
    )
)


def _call_area(contact) -> str:
    """Return the call area digit for a contact.

    The WPX prefix carries it when the log has one, otherwise the first digit
    of the callsign is the area for the four countries in question - which
    matters for logs imported without a prefix, where the empty string would
    otherwise pass for an area.
    """
    for source in (contact.get("WPXPrefix", ""), contact.get("Call", "")):
        for char in str(source).upper():
            if char.isdigit():
                return char
    return ""


class Contest(ContestBase):
    """EA RTTY Contest."""

    DisplayName = "EA RTTY"
    CabrilloName = "EARTTY"
    Mode = "RTTY"
    EXCHANGE_HINT = "Province or #"
    DupeType = 2  # work each band once
    SendsRTCScore = True
    SupportsFT8 = True
    Bands = (3.5, 7, 14, 21, 28)
    FrameText = ("SNT", "SentNR", "Prov or SN")
    AccessibleNames = ("RST Sent", "", "Sent Number", "Province or Serial Number")

    def points(self):
        """Two points inside EA, three into it and one otherwise."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        me = None
        him = None

        result = parent.cty_lookup(parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            me = item.get("primary_pfx", "")

        result = parent.cty_lookup(parent.contact.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            him = item.get("primary_pfx", "")

        if me is not None and him is not None:
            if me in EA_PREFIXES and him in EA_PREFIXES:
                return 2
            if me in EA_PREFIXES:
                return 1
            if him in EA_PREFIXES:
                return 3
        return 1

    def _mult_breakdown(self) -> tuple:
        """The four multiplier counts: provinces, entities, areas, EA4URE.

        The rules make them four different things -- a province keyed on the
        received exchange, a country keyed on the callsign, an area keyed on
        the prefix's digit, and the EA4URE station counted once per band -- so
        the counting stays the module's queries rather than one
        ``MultSqlString``.
        """
        parent = self.parent
        database = parent.database

        # Each entity once per band.
        result = database.exec_sql(
            "select count(DISTINCT(CountryPrefix || ':' || Band)) as mult_count "
            f"from dxlog where ContestNR = {database.current_contest};"
        )
        entities = int(result.get("mult_count", 0)) if result else 0

        # Each EA province once per band.
        provinces = ",".join(f"'{province}'" for province in sorted(EA_PROVINCES))
        result = database.exec_sql(
            "select count(DISTINCT(NR || ':' || Band)) as mult_count "
            f"from dxlog where ContestNR = {database.current_contest} "
            f"and upper(NR) in ({provinces});"
        )
        provinces_count = int(result.get("mult_count", 0)) if result else 0

        # Each USA, VE, JA or VK call area once per band.  The US areas
        # include Alaska, Hawaii and the other areas cty.dat reports as
        # entities of their own.
        areas = set()
        for contact in database.fetch_all_contacts_asc():
            pfx = contact.get("CountryPrefix", "")
            if pfx not in CALL_AREA_PREFIXES:
                continue
            area = _call_area(contact)
            if area:
                areas.add((pfx, area, contact.get("Band", "")))
        dx = len(areas)

        # Each QSO with EA4URE once per band.
        result = database.exec_sql(
            "select count(DISTINCT(Band)) as mult_count "
            f"from dxlog where Call = 'EA4URE' and ContestNR = {database.current_contest};"
        )
        ea4ure = int(result.get("mult_count", 0)) if result else 0

        return provinces_count, entities, dx, ea4ure

    def show_mults(self):
        """Each province, entity, call area and EA4URE, once per band."""
        provinces, entities, dx, ea4ure = self._mult_breakdown()
        return provinces + dx + ea4ure + entities

    def get_mults(self):
        """The online score feed's country/state split of the same numbers."""
        provinces, entities, dx, ea4ure = self._mult_breakdown()
        return {"country": entities + dx + ea4ure, "state": provinces}

    def calc_score(self):
        """Points times multipliers, both summed from the log."""
        return self.just_points() * self.show_mults()

    def recalculate_mults(self):
        """Nothing to mark: the multipliers are counted from the log.

        The module never wrote ``IsMultiplierN`` and its replay was empty, so
        the column stays unmarked and the score keeps its own queries.
        """

    def set_contact_vars(self):
        """The sent province/serial and the received province/serial."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.other_1.text()

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine, with the RTTY HISCALL not re-sending the exchange."""
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

            elif parent.current_widget == "other_2":
                if parent.other_2.text() == "":
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
                        if button == parent.esm_dict["HISCALL"]:
                            parent.esm_call_sent = parent.callsign.text()
                            parent.process_function_key(button, rttysendrx=False)
                            continue
                        parent.process_function_key(button)
        else:
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["MYCALL"])
                    buttons_to_send.append(parent.esm_dict["MYCALL"])

            elif parent.current_widget == "other_2":
                if parent.other_2.text() == "":
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

    def ft8_handler(self, packet):
        """Log a QSO reported by WSJT-X or fldigi over UDP."""
        parent = self.parent
        parent.callsign.setText(packet.get("CALL"))
        parent.contact["Call"] = packet.get("CALL", "")
        parent.contact["SNT"] = packet.get("RST_SENT", "599")
        parent.contact["RCV"] = packet.get("RST_RCVD", "599")

        sent_string = packet.get("STX_STRING", "")
        if sent_string != "":
            parent.contact["SentNr"] = sent_string
            parent.other_1.setText(str(sent_string))
        else:
            parent.contact["SentNr"] = packet.get("STX", "000")
            parent.other_1.setText(str(packet.get("STX", "000")))

        rx_string = packet.get("SRX_STRING", "")
        if rx_string != "":
            parent.contact["NR"] = rx_string
            parent.other_2.setText(str(rx_string))
        else:
            parent.contact["NR"] = packet.get("SRX", "000")
            parent.other_2.setText(str(packet.get("SRX", "000")))

        parent.contact["Mode"] = packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["Band"] = get_logged_band(
            str(int(float(packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.save_contact()

    def populate_history_info_line(self):
        """Show the call history entry for the callsign being typed."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('State', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the received province from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('State', '')}")
