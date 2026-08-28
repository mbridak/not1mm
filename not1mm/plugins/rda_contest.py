"""Russian District Award (RDA) Contest plugin.

Status:            Active
Geographic Focus:  Russia
Participation:     Worldwide
Mode:              CW, SSB
Bands:             160, 80, 40, 20, 15, 10m (no WARC)
Classes:           Single Op All Band (EUR / ASR / World, MIX/CW/SSB, HP/LP)
                   Multi-Op All Band
                   Field (C1/C2, Russian only)
Exchange:          Russian stations: RS(T) + RDA district code (e.g. TB02)
                   non-Russian stations: RS(T) + Serial No. starting at 001
Work stations:     Once per band per mode (dupe)
QSO Points:
                   Russian stations:
                      1 pt QSO with Russia on your continent
                      2 pts QSO with Russia on another continent
                      3 pts QSO with a different country on your continent
                     10 pts QSO with a DX entity from the official C1/C2 list
                      5 pts QSO with another continent
                   Non-Russian stations:
                     10 pts QSO with a Russian station
                   Kaliningrad (R2F/UA2) is a separate DXCC entity, but points
                   for QSOs with Kaliningrad are counted as for European Russia.
Multipliers:       Russian stations: each DXCC country once + each RDA district once
                   Non-Russian stations: each RDA district once
Score Calculation: Total score = total QSO points x total multipliers
Find rules at:     https://www.rdaward.org/rdac.htm (RDA CONTEST)
Cabrillo name:     RDAC
"""

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member, unused-import

import datetime
import logging
from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, imp_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

assert QtWidgets
assert imp_adif
assert online_score_xml

EXCHANGE_HINT = "# or RDA code"
SOAPBOX_HINT = "RDA Contest - Exchange: RS(T) + serial (non-RU) or RDA district code (RU)"

# Primary prefixes assigned to Russian stations by the country file.
# UA = European Russia, UA9 = Asiatic Russia, UA2 = Kaliningrad.
RUSSIA_PREFIXES = ("UA", "UA9", "UA2")

# Entity names used by the country file (cty.json / CTY).
RUSSIA_ENTITIES = ("European Russia", "Asiatic Russia", "Kaliningrad")

# Official C1/C2 list of rare DX entities that earn 10 points for a cross
# continent QSO from a Russian station.  Populate this set from the current
# year's rules; the values change from year to year.
SPECIAL_DX = {
    # "Vatican",
    # "Banaba Island",
}

name = "RDA Contest"
cabrillo_name = "RDAC"
mode = "BOTH"  # CW SSB BOTH RTTY

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Mode",
    "SentNr",
    "RcvNr",
    "Exchange1",
    "M1",
    "M2",
    "PTS",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 3


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
    self.exch_label.setText(QtWidgets.QApplication.translate("ContestPlugin", "Serial or RDA"))
    self.field4.setAccessibleName("Serial Number or Russian RDA district")


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
    """Set Shift-TAB Advances"""
    self.tab_prev = {
        self.callsign: self.other_2,
        self.sent: self.callsign,
        self.receive: self.sent,
        self.other_1: self.receive,
        self.other_2: self.other_1,
    }


def is_russian_prefix(prefix: str) -> bool:
    """Return True if the country prefix belongs to a Russian station."""
    return prefix.upper() in RUSSIA_PREFIXES


def country_mult_prefix(prefix: str) -> str:
    """Return a single grouping key for DXCC country multipliers.

    European and Asiatic Russia are one DXCC country so they share one
    country multiplier.  Kaliningrad is a separate DXCC entity.
    """
    prefix = prefix.upper()
    if prefix in ("UA", "UA9"):
        return "R"
    return prefix


def my_station_is_russian(self) -> bool:
    """Return True if the operating station is located in Russia."""
    result = self.cty_lookup(self.station.get("Call", ""))
    if result is None:
        return False
    item = result.get(next(iter(result)))
    if item.get("entity", "") in RUSSIA_ENTITIES:
        return True
    return False


def _his_prefix(self) -> str:
    """Resolve the worked station's primary prefix from the contact."""
    countryprefix = self.contact.get("CountryPrefix", "")
    if not countryprefix:
        result = self.cty_lookup(self.contact.get("Call", ""))
        if result:
            item = result.get(next(iter(result)))
            countryprefix = item.get("primary_pfx", "")
    return countryprefix


def _my_sent_exchange(self) -> str:
    """The exchange this station transmits.

    Russian stations send their fixed RDA district code, configured in the
    contest "Sent Exchange" field.  Non-Russian stations send a running
    serial number instead.
    """
    if my_station_is_russian(self):
        rda = str(self.contest_settings.get("SentExchange", "")).strip()
        if rda:
            return rda.upper()
    serial_nr = str(self.current_sn).zfill(3)
    if serial_nr == "None":
        serial_nr = "001"
    return serial_nr


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = _my_sent_exchange(self)
    self.contact["NR"] = self.other_2.text().upper()
    self.contact["IsMultiplier1"] = 0
    self.contact["IsMultiplier2"] = 0

    if self.contact_is_dupe > 0:
        return

    countryprefix = _his_prefix(self)
    rda_code = self.contact.get("NR", "")

    # RDA district multiplier (collected from Russian stations)
    if is_russian_prefix(countryprefix) and rda_code:
        query = (
            "select count(*) as mult_count from dxlog where "
            "ContestNR = ? and NR = ? and CountryPrefix in ('UA', 'UA9', 'UA2');"
        )
        result = self.database.exec_sql(
            query, (self.pref.get("contest", "1"), rda_code)
        )
        if result.get("mult_count", 0) == 0:
            self.contact["IsMultiplier1"] = 1

    # DXCC country multiplier (Russian stations only)
    if my_station_is_russian(self):
        call = self.contact.get("Call", "")
        if "/MM" not in call.upper():
            mult_prefix = country_mult_prefix(countryprefix)
            rows = self.database.exec_sql_mult(
                "select CountryPrefix from dxlog where ContestNR = ? and "
                "Call not like '%/MM%';",
                (self.pref.get("contest", "1"),),
            )
            seen = {country_mult_prefix(row.get("CountryPrefix", "")) for row in rows}
            if mult_prefix not in seen:
                self.contact["IsMultiplier2"] = 1


def predupe(self):  # pylint: disable=unused-argument
    """called after callsign entered"""


def prefill(self):
    """Fill sent exchange field"""
    if len(self.other_1.text()) == 0:
        self.other_1.setText(_my_sent_exchange(self))


def points(self):
    """Calc point"""
    if self.contact_is_dupe > 0:
        return 0

    call = self.contact.get("Call", "")

    mycountry = ""
    mycontinent = ""
    hiscountry = ""
    hiscontinent = ""

    result = self.cty_lookup(self.station.get("Call", ""))
    if result is not None:
        item = result.get(next(iter(result)))
        mycountry = item.get("entity", "")
        mycontinent = item.get("continent", "")

    result = self.cty_lookup(call)
    if result is not None:
        item = result.get(next(iter(result)))
        hiscountry = item.get("entity", "")
        hiscontinent = item.get("continent", "")

    if not hiscountry:
        return 0

    his_is_russian = hiscountry in RUSSIA_ENTITIES
    my_is_russian = mycountry in RUSSIA_ENTITIES

    if my_is_russian:
        # Russian station
        if his_is_russian:
            if mycontinent == hiscontinent:
                return 1  # QSO with Russia on your continent
            return 2  # QSO with Russia on another continent
        if mycontinent == hiscontinent:
            return 3  # QSO with a different country on your continent
        if hiscountry in SPECIAL_DX:
            return 10  # QSO with a DX entity from the C1/C2 list
        return 5  # QSO with another continent

    # Non-Russian station
    if his_is_russian:
        return 10  # QSO with Russian station
    return 0


def show_mults(self, rtc=None):
    """Return display string for mults"""
    mult_rda = 0  # RDA districts
    mult_country = 0  # DXCC countries (Russian stations only)

    query = (
        "select count(DISTINCT NR) as mult_count from dxlog "
        "where ContestNR = ? and CountryPrefix in ('UA', 'UA9', 'UA2') and NR != '';"
    )
    result = self.database.exec_sql(query, (self.database.current_contest,))
    if result:
        mult_rda = int(result.get("mult_count", 0))

    if my_station_is_russian(self):
        query = (
            "select count(DISTINCT(CASE WHEN CountryPrefix in ('UA', 'UA9') "
            "THEN 'R' ELSE CountryPrefix END)) as mult_count "
            "from dxlog where ContestNR = ? and Call not like '%/MM%';"
        )
        result = self.database.exec_sql(query, (self.database.current_contest,))
        if result:
            mult_country = int(result.get("mult_count", 0))

    if rtc is not None:
        return (mult_country, mult_rda)
    return mult_rda + mult_country


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
        contest_points = int(score)
        mults = show_mults(self)
        return contest_points * mults
    return 0


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "RDAC")


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """"""
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def cabrillo(self, file_encoding):
    """Generates Cabrillo file. Maybe."""
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
            if self.contest_settings.get("OverlayCategory", "") != "N/A":
                output_cabrillo_line(
                    f"CATEGORY-OVERLAY: {self.contest_settings.get('OverlayCategory','')}",
                    "\r\n",
                    file_descriptor,
                    file_encoding,
                )
            output_cabrillo_line(
                f"GRID-LOCATOR: {self.station.get('GridSquare','')}",
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
    """Recalculates multipliers after change in logged qso."""
    all_contacts = self.database.fetch_all_contacts_asc()

    for contact in all_contacts:
        countryprefix = contact.get("CountryPrefix", "")
        if not countryprefix:
            result = self.cty_lookup(contact.get("Call", ""))
            if result:
                item = result.get(next(iter(result)))
                countryprefix = item.get("primary_pfx", "")

        rda_code = contact.get("NR", "")

        contact["IsMultiplier1"] = 0
        contact["IsMultiplier2"] = 0

        if is_russian_prefix(countryprefix) and rda_code:
            query = (
                "select count(*) as mult_count from dxlog where TS < ? and "
                "NR = ? and CountryPrefix in ('UA', 'UA9', 'UA2') and ContestNR = ?;"
            )
            result = self.database.exec_sql(
                query,
                (
                    contact.get("TS", ""),
                    rda_code,
                    self.pref.get("contest", "1"),
                ),
            )
            if result.get("mult_count", 0) == 0:
                contact["IsMultiplier1"] = 1

        if my_station_is_russian(self):
            if "/MM" not in contact.get("Call", "").upper():
                mult_prefix = country_mult_prefix(countryprefix)
                query = (
                    "select CountryPrefix from dxlog where TS < ? and "
                    "Call not like '%/MM%' and ContestNR = ?;"
                )
                rows = self.database.exec_sql_mult(
                    query,
                    (
                        contact.get("TS", ""),
                        self.pref.get("contest", "1"),
                    ),
                )
                seen = {country_mult_prefix(row.get("CountryPrefix", "")) for row in rows}
                if mult_prefix not in seen:
                    contact["IsMultiplier2"] = 1

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
        self.esm_dict["CQ"],
        self.esm_dict["EXCH"],
        self.esm_dict["QRZ"],
        self.esm_dict["AGN"],
        self.esm_dict["HISCALL"],
        self.esm_dict["MYCALL"],
        self.esm_dict["QSOB4"],
    ]:
        if a_button is not None:
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

        elif self.current_widget in ["other_1", "other_2"]:
            if self.other_1.text() == "" or self.other_2.text() == "":
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])
            else:
                self.make_button_green(self.esm_dict["QRZ"])
                buttons_to_send.append(self.esm_dict["QRZ"])
                buttons_to_send.append("LOGIT")

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

        elif self.current_widget in ["other_1", "other_2"]:
            if self.other_1.text() == "" or self.other_2.text() == "":
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])
            else:
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append(self.esm_dict["EXCH"])
                buttons_to_send.append("LOGIT")

        if with_enter is True and bool(len(buttons_to_send)):
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        self.save_contact()
                        continue
                    self.process_function_key(button)


def populate_history_info_line(self):
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(
            f"{result.get('Call', '')}, {result.get('Exch1', '')}, {result.get('UserText','...')}"
        )
    else:
        self.history_info.setText("")


def check_call_history(self):
    """"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText','')}")
        if self.other_2.text() == "":
            self.other_2.setText(f"{result.get('Exch1', '')}")


def get_mults(self):
    """Get mults for RTC XML"""
    mults = {}
    mults["country"], mults["rda"] = show_mults(self, rtc=True)
    return mults


def just_points(self):
    """Get points for RTC XML"""
    return get_points(self)