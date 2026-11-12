"""His Maj. King of Spain Contest, CW

Find rules at: https://concursos.ure.es/en/s-m-el-rey-de-espana-cw/bases/

160m-10m, once per band.  A Spanish station sends its province and everyone
else a serial; an EA-to-EA contact is 2 points, an EA-to-outside one 1 and an
outside-to-EA one 3.  Each EA province, each entity and the King's special
station EF0F are multipliers once per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase

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
# 'SMR' and 'HQ' are not provinces: they are the special stations, and each is
# a multiplier of its own.
EA_PROVINCES = frozenset(
    (
        "AV", "BU", "C", "LE", "LO", "LU", "O", "OU", "P", "PO", "S", "SA",
        "SG", "SO", "VA", "ZA",
        "BI", "HU", "NA", "SS", "TE", "VI", "Z",
        "B", "GI", "L", "T",
        "BA", "CC", "CR", "CU", "GU", "M", "TO",
        "A", "AB", "CS", "MU", "V",
        "IB",
        "AL", "CA", "CO", "GR", "H", "J", "MA", "SE",
        "GC", "TF",
        "CE", "ML",
    )
)


class Contest(ContestBase):
    """His Maj. King of Spain Contest, CW."""

    DisplayName = "His Maj. King of Spain Contest, CW"
    CabrilloName = "EA-MAJESTAD-CW"
    Mode = "CW"
    EXCHANGE_HINT = "Province or #"
    DupeType = 2  # work each band once
    SendsRTCScore = True
    Bands = (1.8, 3.5, 7, 14, 21, 28)
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
        """The three multiplier counts: provinces, entities and EF0F.

        The rules make them three different things -- a province keyed on the
        received exchange, a country keyed on the callsign, and the King's
        station counted once per band -- so the counting stays the module's
        queries rather than one ``MultSqlString``.
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

        # The King of Spain's special station, EF0F, counts once per band; it
        # sends SMR in place of a province.
        result = database.exec_sql(
            "select count(DISTINCT(Band)) as mult_count "
            f"from dxlog where Call like 'EF0F%' and ContestNR = {database.current_contest};"
        )
        special = int(result.get("mult_count", 0)) if result else 0

        return provinces_count, entities, special

    def show_mults(self):
        """Each province, each entity and EF0F, once per band."""
        provinces, entities, special = self._mult_breakdown()
        return provinces + special + entities

    def get_mults(self):
        """The online score feed's country/state split of the same numbers."""
        provinces, entities, special = self._mult_breakdown()
        return {"country": entities + special, "state": provinces}

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
        """Prefill the received province from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Exch1', '')}")
