"""RSGB Commonwealth (BERU) Contest plugin"""

# pylint: disable=invalid-name, c-extension-no-member, unused-import

# Commonwealth (BERU) Contest
#  	Status:	Active
#  	Geographic Focus:	Commonwealth countries and territories
#  	Participation:	Commonwealth countries and territories
#  	Awards:	Commonwealth countries and territories
#  	Mode:	CW
#  	Bands:	80, 40, 20, 15, 10m
#  	Classes:	Single Op (12/24)(Assisted/Unassisted)(Low/High)
# Single Op Remote (12/24)
# Single Op QRP (Assisted/Unassisted)
# Multi-Op
# HQ
#  	Max power:	High: >100 watts
# Low: 100 watts
# QRP: 5 watts
#  	Exchange:	RST + Serial No.
#  	QSO Points:	5 points per QSO with same continent
# 10 points per QSO with different continent
# 20 additional points for each of first three QSOs with a Commonwealth Area or HQ station per band
#  	Multipliers:	(none)
#  	Score Calculation:	Total score = total QSO points
#  	Upload log at:	http://www.rsgbcc.org/cgi-bin/hfenter.pl
#  	Mail logs to:	(none)
#  	Find rules at:	https://www.rsgbcc.org/hf/rules/2025/rcwc.shtml
#  	Cabrillo name:	RSGB-COMMONWEALTH
#  	Cabrillo name aliases:	RSGB-BERU


import datetime
import logging
import re

from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, imp_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "Serial No."

name = "RSGB Commonwealth BERU"
cabrillo_name = "RSGB-COMMONWEALTH"
mode = "CW"  # CW SSB BOTH RTTY
# columns = [0, 1, 2, 3, 4, 5, 6, 17, 15]
columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
    "M2",
    "PTS",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 2

# The seven UK home nations / crown dependencies listed in rule 4(d).
# Contacts between any two of these areas score nothing unless the
# distant station is an HQ station.
HOME_NATIONS = frozenset(
    (
        "England",
        "Northern Ireland",
        "Scotland",
        "Wales",
        "Isle of Man",
        "Jersey",
        "Guernsey",
    )
)

# DXCC entity names as they appear in data/cty.json, covering the
# RSGB Commonwealth Call Areas list:
# https://www.rsgbcc.org/hf/information/codes.shtml
COMMONWEALTH_ENTITIES = frozenset(
    (
        # United Kingdom, Crown Dependencies and Overseas Territories
        "England",
        "Scotland",
        "Wales",
        "Northern Ireland",
        "Isle of Man",
        "Jersey",
        "Guernsey",
        "Gibraltar",
        "Bermuda",
        "Anguilla",
        "Montserrat",
        "British Virgin Islands",
        "Turks & Caicos Islands",
        "Cayman Islands",
        "Falkland Islands",
        "South Georgia Island",
        "South Sandwich Islands",
        "South Shetland Islands",
        "South Orkney Islands",
        "Pitcairn Island",
        "Ducie Island",
        "St. Helena",
        "Ascension Island",
        "Tristan da Cunha & Gough",
        "Chagos Islands",
        # Europe
        "Malta",
        "Cyprus",
        "UK Base Areas on Cyprus",
        # Asia
        "India",
        "Andaman & Nicobar Is.",
        "Lakshadweep Islands",
        "Pakistan",
        "Bangladesh",
        "Sri Lanka",
        "Singapore",
        "West Malaysia",
        "East Malaysia",
        "Maldives",
        "Brunei Darussalam",
        "Spratly Islands",
        # Africa
        "South Africa",
        "Pr. Edward & Marion Is.",
        "Kingdom of Eswatini",
        "Lesotho",
        "Malawi",
        "Tanzania",
        "Nigeria",
        "Togo",
        "Uganda",
        "Kenya",
        "Ghana",
        "Sierra Leone",
        "Zambia",
        "Rwanda",
        "Botswana",
        "The Gambia",
        "Mozambique",
        "Namibia",
        "Gabon",
        "Cameroon",
        "Agalega & St. Brandon",
        "Mauritius",
        "Rodriguez Island",
        "Seychelles",
        # Americas
        "Canada",
        "Sable Island",
        "St. Paul Island",
        "Jamaica",
        "Barbados",
        "Trinidad & Tobago",
        "Antigua & Barbuda",
        "Belize",
        "St. Kitts & Nevis",
        "St. Lucia",
        "St. Vincent",
        "Dominica",
        "Grenada",
        "Bahamas",
        "Guyana",
        # Oceania
        "Australia",
        "Heard Island",
        "Macquarie Island",
        "Cocos (Keeling) Islands",
        "Christmas Island",
        "Lord Howe Island",
        "Mellish Reef",
        "Norfolk Island",
        "Willis Island",
        "New Zealand",
        "Chatham Islands",
        "Kermadec Islands",
        "N.Z. Subantarctic Is.",
        "Fiji",
        "Rotuma Island",
        "Conway Reef",
        "Papua New Guinea",
        "Nauru",
        "Tonga",
        "Samoa",
        "Niue",
        "North Cook Islands",
        "South Cook Islands",
        "Tuvalu",
        "Western Kiribati",
        "Central Kiribati",
        "Eastern Kiribati",
        "Banaba Island",
        "Tokelau Islands",
        "Temotu Province",
        "Solomon Islands",
        "Vanuatu",
    )
)

# Call area extraction for countries that contain multiple call areas.
CANADA_CALLAREA_RE = re.compile(r"^(V[EOY][0-9])")
AUSTRALIA_CALLAREA_RE = re.compile(r"^(VK9[CLMNWX]|VK[0-9])")
SOUTHAFRICA_CALLAREA_RE = re.compile(r"^(ZS[0-8])")
NEWZEALAND_CALLAREA_RE = re.compile(r"^(ZL[0-9])")

HQ_EXCHANGE_RE = re.compile(r"\bHQ\b", re.IGNORECASE)

# Portable markers that don't indicate the operating location,
# mirroring lib.ham_utility.calculate_wpx_prefix.
PORTABLE_SUFFIXES = [
    "M",
    "MM",
    "P",
    "QRP",
    "A",
    "J",
    "LH",
    "LGT",
    "LS",
    "NLD",
    "T",
    "R",
    "TR",
]


def init_contest(self):
    """setup plugin"""
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_2


def interface(self):
    """Setup user interface"""
    self.field1.show()
    self.field2.show()
    self.field3.show()
    self.field4.show()
    self.snt_label.setText("SNT")
    self.field1.setAccessibleName("RST Sent")
    self.other_label.setText(QtWidgets.QApplication.translate("ContestPlugin", "SentNR"))
    self.field3.setAccessibleName("Sent Number")
    self.exch_label.setText(QtWidgets.QApplication.translate("ContestPlugin", "RcvNR"))
    self.field4.setAccessibleName("Received Number")


def reset_label(self):  # pylint: disable=unused-argument
    """reset label after field cleared"""


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.sent,
        self.sent: self.receive,
        self.receive: self.other_1,
        self.other_1: self.other_2,
        self.other_2: self.callsign,
    }


def set_tab_prev(self):
    """Set TAB Advances"""
    self.tab_prev = {
        self.callsign: self.other_2,
        self.sent: self.callsign,
        self.receive: self.sent,
        self.other_1: self.receive,
        self.other_2: self.other_1,
    }


def get_base_call(call: str) -> str:
    """
    Return the callsign identifying the operating location, stripping
    portable markers and preferring a portable prefix (VE3/G4ABC -> VE3).

    Parameters
    ----------
    call : str
    The callsign to reduce to its base form.

    Returns
    -------
    str
    The base callsign.
    """

    base_call = str(call).upper().strip()
    if not base_call:
        return ""
    for suffix in PORTABLE_SUFFIXES:
        base_call = re.sub("/" + suffix + "$", "", base_call)
    if "/" in base_call:
        parts = [part for part in base_call.split("/") if part]
        with_digit = [
            part
            for part in parts
            if any(char.isdigit() for char in part) and any(char.isalpha() for char in part)
        ]
        if len(with_digit) > 1:
            return min(with_digit, key=len)
        if with_digit:
            return with_digit[0]
        if parts:
            return max(parts, key=len)
        return ""
    return base_call


def is_hq_station(exchange: str) -> bool:
    """
    Determine if the received exchange indicates an HQ station.
    HQ stations identify by sending 'HQ' after their serial number.

    Parameters
    ----------
    exchange : str
    The received exchange string.

    Returns
    -------
    bool
    True if 'HQ' appears as a standalone token.
    """

    return bool(HQ_EXCHANGE_RE.search(str(exchange)))


def get_entity_info(self, call: str) -> dict | None:
    """
    Look up DXCC entity information for a callsign.

    Parameters
    ----------
    call : str
    The callsign to look up.

    Returns
    -------
    dict or None
    Entity information from cty data, None when not found.
    """

    result = self.cty_lookup(get_base_call(call))
    if result is None:
        return None
    try:
        return result.get(next(iter(result)))
    except StopIteration:
        return None


def get_commonwealth_area(self, call: str) -> str | None:
    """
    Return an identifier for the Commonwealth Call Area of a callsign.
    Countries containing multiple call areas are identified by their
    call area prefix, everything else by its DXCC entity name.

    Parameters
    ----------
    call : str
    The callsign to identify.

    Returns
    -------
    str or None
    The call area identifier, None when it can't be determined.
    """

    base_call = get_base_call(call)
    for pattern in (
        CANADA_CALLAREA_RE,
        AUSTRALIA_CALLAREA_RE,
        SOUTHAFRICA_CALLAREA_RE,
        NEWZEALAND_CALLAREA_RE,
    ):
        match = pattern.match(base_call)
        if match:
            return match.group(1)
    entity_info = get_entity_info(self, base_call)
    if entity_info is not None:
        return entity_info.get("entity")
    return None


def scoring_info(self) -> dict | None:
    """
    Gather all information needed to score the current contact.

    Returns
    -------
    dict or None
    A dict with keys eligible, same_continent, hq_station.
    Returns None when either callsign cannot be resolved to an entity.
    """

    their_exchange = str(self.contact.get("NR", ""))
    hq_station = is_hq_station(their_exchange)

    my_info = get_entity_info(self, self.station.get("Call", ""))
    their_info = get_entity_info(self, self.contact.get("Call", ""))
    if my_info is None or their_info is None:
        logger.debug("scoring_info: unable to resolve %s", self.contact.get("Call", ""))
        return None

    my_continent = my_info.get("continent", "")
    their_continent = their_info.get("continent", "")
    their_entity = their_info.get("entity", "")

    my_area = get_commonwealth_area(self, self.station.get("Call", ""))
    their_area = get_commonwealth_area(self, self.contact.get("Call", ""))

    eligible = hq_station or their_entity in COMMONWEALTH_ENTITIES

    # Rule 4(b): no contacts within your own call area.
    # Rule 4(e): HQ stations may be contacted even in your own call area.
    if my_area is not None and my_area == their_area and not hq_station:
        eligible = False

    # Rule 4(d): QSOs between the seven home nations don't count,
    # unless the distant station is an HQ station.
    if (
        not hq_station
        and my_area in HOME_NATIONS
        and their_area in HOME_NATIONS
    ):
        eligible = False

    return {
        "eligible": eligible,
        "same_continent": my_continent == their_continent,
        "hq_station": hq_station,
    }


def bonus_count_before_me(self) -> int:
    """
    Return the number of earlier contacts in this contest that were
    flagged as earning a Commonwealth Call Area bonus on this band.

    Parameters
    ----------
    None

    Returns
    -------
    int
    The count of flagged bonus contacts before this one on this band.
    """

    band = float(self.contact.get("Band", 0))
    time_stamp = self.contact.get("TS", "")
    query = (
        "select count(*) as bonus_count from dxlog "
        f"where Band={band} and IsMultiplier2=1 "
        f"and TS < '{time_stamp}' "
        f"and ContestNR = {self.pref.get('contest', '1')};"
    )
    result = self.database.exec_sql(query)
    return int(result.get("bonus_count", 0))


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.other_1.text()
    self.contact["NR"] = self.other_2.text()
    self.contact["IsMultiplier1"] = 0
    info = scoring_info(self)
    if info is not None and info["eligible"]:
        # IsMultiplier2 marks a contact earning one of the three
        # per-band Commonwealth Call Area bonuses.
        if bonus_count_before_me(self) < 3:
            self.contact["IsMultiplier2"] = 1
        else:
            self.contact["IsMultiplier2"] = 0
    else:
        self.contact["IsMultiplier2"] = 0


def predupe(self):  # pylint: disable=unused-argument
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""
    serial_nr = str(self.current_sn).zfill(3)
    if serial_nr == "None":
        serial_nr = "001"
    if len(self.other_1.text()) == 0:
        self.other_1.setText(serial_nr)


def points(self):
    """Calc point"""

    if self.contact_is_dupe > 0:
        return 0

    info = scoring_info(self)
    if info is None or not info["eligible"]:
        return 0

    if info["same_continent"]:
        contact_points = 5
    else:
        contact_points = 10

    # Rule 8(c): 20 additional points for each of the first three
    # contacts with a Commonwealth Call Area on each band.
    if int(self.contact.get("IsMultiplier2", 0)) == 1:
        contact_points += 20
    return contact_points


def show_mults(self):
    """Return display string for mults"""
    return 0


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score"""
    result = self.database.fetch_points()
    if result is not None:
        score = result.get("Points", "0")
        if score is None:
            score = "0"
        return int(score)
    return 0


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "RSGB-BERU")


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """"""
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def cabrillo(self, file_encoding):
    """Generates Cabrillo file. Maybe."""
    # https://www.rsgbcc.org/hf/rules/Cabrillo/Cabrillo-Information.shtml
    logger.debug("******Cabrillo*****")
    logger.debug("Station: %s", f"{self.station}")
    logger.debug("Contest: %s", f"{self.contest_settings}")
    now = datetime.datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = (
        str(Path.home())
        + "/"
        + f"{self.station.get('Call', '').upper().replace('/','-')}_{cabrillo_name}_{date_time}.log"
    )
    logger.debug("%s", filename)
    log = self.database.fetch_all_contacts_asc()
    try:
        with open(filename, "w", encoding=file_encoding, newline="") as file_descriptor:
            output_cabrillo_line(
                "START-OF-LOG: 3.0",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CREATED-BY: Not1MM v{__version__}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CONTEST: {cabrillo_name}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            if self.station.get("Club", ""):
                output_cabrillo_line(
                    f"CLUB: {self.station.get('Club', '').upper()}",
                    "\r\n",
                    file_descriptor,
                    file_encoding,
                )
            output_cabrillo_line(
                f"CALLSIGN: {self.station.get('Call','')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"LOCATION: {self.station.get('ARRLSection', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-OPERATOR: {self.contest_settings.get('OperatorCategory','')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-ASSISTED: {self.contest_settings.get('AssistedCategory','')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-BAND: {self.contest_settings.get('BandCategory','')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            mode = self.contest_settings.get("ModeCategory", "")
            if mode in ["SSB+CW", "SSB+CW+DIGITAL"]:
                mode = "MIXED"
            output_cabrillo_line(
                f"CATEGORY-MODE: {mode}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-TRANSMITTER: {self.contest_settings.get('TransmitterCategory','')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-POWER: {self.contest_settings.get('PowerCategory','')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )

            output_cabrillo_line(
                f"CLAIMED-SCORE: {calc_score(self)}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            ops = ""
            list_of_ops = self.database.get_ops()
            for op in list_of_ops:
                ops += f"{op.get('Operator', '')}, "
            if self.station.get("Call", "") not in ops:
                ops += f"@{self.station.get('Call','')}"
            else:
                ops = ops.rstrip(", ")
            output_cabrillo_line(
                f"OPERATORS: {ops}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"NAME: {self.station.get('Name', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS: {self.station.get('Street1', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS-CITY: {self.station.get('City', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS-STATE-PROVINCE: {self.station.get('State', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS-POSTALCODE: {self.station.get('Zip', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS-COUNTRY: {self.station.get('Country', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"EMAIL: {self.station.get('Email', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            for contact in log:
                the_date_and_time = contact.get("TS", "")
                themode = contact.get("Mode", "")
                if themode in ("CW-U", "CW-L", "CW-R", "CWR"):
                    themode = "CW"
                if themode == "LSB" or themode == "USB":
                    themode = "PH"
                frequency = str(round(contact.get("Freq", "0"))).rjust(5)

                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                output_cabrillo_line(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SNT', '')).ljust(3)} "
                    f"{str(contact.get('SentNr', '')).ljust(6)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('RCV', '')).ljust(3)} "
                    f"{str(contact.get('NR', '')).ljust(6)}",
                    "\r\n",
                    file_descriptor,
                    file_encoding,
                )
            output_cabrillo_line("END-OF-LOG:", "\r\n", file_descriptor, file_encoding)
        self.show_message_box(f"Cabrillo saved to: {filename}")
    except IOError as exception:
        logger.critical("cabrillo: IO error: %s, writing to %s", exception, filename)
        self.show_message_box(f"Error saving Cabrillo: {exception} {filename}")
        return


def recalculate_mults(self):
    """Recalculates multipliers and bonuses after change in logged qso."""
    all_contacts = self.database.fetch_all_contacts_asc()
    bonus_counts = {}
    self.contact_is_dupe = 0
    for contact in all_contacts:
        self.contact = contact
        info = scoring_info(self)
        earns_bonus = 0
        if info is not None and info["eligible"]:
            band = float(contact.get("Band", 0))
            count = bonus_counts.get(band, 0)
            if count < 3:
                earns_bonus = 1
            bonus_counts[band] = count + 1
        contact["IsMultiplier1"] = 0
        contact["IsMultiplier2"] = earns_bonus
        contact["Points"] = points(self)
        self.database.change_contact(contact)


def process_esm(self, new_focused_widget=None, with_enter=False):
    """ESM State Machine"""

    # self.pref["run_state"]

    # -----===== Assigned F-Keys =====-----
    # self.esm_dict["CQ"]
    # self.esm_dict["EXCH"]
    # self.esm_dict["QRZ"]
    # self.esm_dict["AGN"]
    # self.esm_dict["HISCALL"]
    # self.esm_dict["MYCALL"]
    # self.esm_dict["QSOB4"]

    # ----==== text fields ====----
    # self.callsign
    # self.sent
    # self.receive
    # self.other_1
    # self.other_2

    if new_focused_widget is not None:
        self.current_widget = self.inputs_dict.get(new_focused_widget)

    for a_button in [
        self.F1,
        self.F2,
        self.F3,
        self.F4,
        self.F5,
        self.F6,
        self.F7,
        self.F8,
        self.F9,
        self.F10,
        self.F11,
        self.F12,
    ]:
        self.restore_button_color(a_button)

    buttons_to_send = []

    if self.pref.get("run_state"):
        if self.current_widget == "callsign":
            if len(self.callsign.text()) < 3:
                self.make_button_green(self.esm_dict["CQ"])
                buttons_to_send.append(self.esm_dict["CQ"])
            elif len(self.callsign.text()) > 2:
                self.make_button_green(self.esm_dict["HISCALL"])
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append(self.esm_dict["HISCALL"])
                buttons_to_send.append(self.esm_dict["EXCH"])

        elif self.current_widget == "other_2":
            if self.other_2.text() == "":
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])
            elif self.other_2.text().isnumeric():
                self.make_button_green(self.esm_dict["QRZ"])
                buttons_to_send.append(self.esm_dict["QRZ"])
                buttons_to_send.append("LOGIT")
            else:
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])

        if with_enter is True and bool(len(buttons_to_send)):
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        self.save_contact()
                        continue
                    self.process_function_key(button)
    else:
        if self.current_widget == "callsign":
            if len(self.callsign.text()) > 2:
                self.make_button_green(self.esm_dict["MYCALL"])
                buttons_to_send.append(self.esm_dict["MYCALL"])

        elif self.current_widget == "other_2":
            if self.other_2.text() == "":
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])
            elif self.other_2.text().isnumeric():
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append(self.esm_dict["EXCH"])
                buttons_to_send.append("LOGIT")
            else:
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])

        if with_enter is True and bool(len(buttons_to_send)):
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        self.save_contact()
                        continue
                    self.process_function_key(button)


def get_mults(self):
    """Get mults for RTC XML"""
    mults = {}
    return mults


def just_points(self):
    """Get points for RTC XML"""
    return get_points(self)
