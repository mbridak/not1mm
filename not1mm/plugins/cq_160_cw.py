"""CQ 160 CW plugin"""

# pylint: disable=invalid-name, c-extension-no-member, unused-import, line-too-long

import datetime
import logging
import platform

from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "ST/Prov or DX CQ Zone"

name = "CQ 160 CW"
cabrillo_name = "CQ-160-CW"
mode = "CW"  # CW SSB BOTH RTTY

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Snt",
    "Rcv",
    "PFX",
    "Exchange1",
    "M1",
    "PTS",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 1


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
    self.field3.hide()
    self.field4.show()
    # self.other_label.setText("SentNR")
    # self.field3.setAccessibleName("Sent Number")
    self.exch_label.setText("ST/Prov/CQ Zone")
    self.field4.setAccessibleName("Received Exchange")


def reset_label(self):  # pylint: disable=unused-argument
    """reset label after field cleared"""


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.field1.findChild(QtWidgets.QLineEdit),
        self.field1.findChild(QtWidgets.QLineEdit): self.field2.findChild(
            QtWidgets.QLineEdit
        ),
        self.field2.findChild(QtWidgets.QLineEdit): self.field4.findChild(
            QtWidgets.QLineEdit
        ),
        self.field3.findChild(QtWidgets.QLineEdit): self.field4.findChild(
            QtWidgets.QLineEdit
        ),
        self.field4.findChild(QtWidgets.QLineEdit): self.callsign,
    }


def set_tab_prev(self):
    """Set TAB Advances"""
    self.tab_prev = {
        self.callsign: self.field4.findChild(QtWidgets.QLineEdit),
        self.field1.findChild(QtWidgets.QLineEdit): self.callsign,
        self.field2.findChild(QtWidgets.QLineEdit): self.field1.findChild(
            QtWidgets.QLineEdit
        ),
        self.field3.findChild(QtWidgets.QLineEdit): self.field2.findChild(
            QtWidgets.QLineEdit
        ),
        self.field4.findChild(QtWidgets.QLineEdit): self.field2.findChild(
            QtWidgets.QLineEdit
        ),
    }


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.contest_settings.get("SentExchange", 0)
    self.contact["Exchange1"] = self.other_2.text()
    self.contact["IsMultiplier1"] = 0
    # check if mult
    if "/MM" in self.contact.get("Call", ""):
        return
    if self.contact["CountryPrefix"] == "K":
        # check unique state.
        query = f"select count(*) as count from dxlog where CountryPrefix = 'K' and Exchange1 = '{self.contact.get('Exchange1', '')}' and ContestNR = '{self.pref.get('contest', '0')}'"
        result = self.database.exec_sql(query)
        if result.get("count", 0) > 0:
            self.contact["IsMultiplier1"] = 0
        else:
            self.contact["IsMultiplier1"] = 1
        return
    if self.contact["CountryPrefix"] == "VE":
        # check unique province.
        query = f"select count(*) as count from dxlog where CountryPrefix = 'VE' and Exchange1 = '{self.contact.get('Exchange1', '')}' and ContestNR = '{self.pref.get('contest', '0')}'"
        result = self.database.exec_sql(query)
        if result.get("count", 0) > 0:
            self.contact["IsMultiplier1"] = 0
        else:
            self.contact["IsMultiplier1"] = 1
        return
    # check all others
    query = f"select count(*) as count from dxlog where CountryPrefix = '{self.contact.get('CountryPrefix', '')}' and ContestNR = '{self.pref.get('contest', '0')}'"
    result = self.database.exec_sql(query)
    if result.get("count", 0) > 0:
        self.contact["IsMultiplier1"] = 0
    else:
        self.contact["IsMultiplier1"] = 1
    return


def predupe(self):  # pylint: disable=unused-argument
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""


def points(self):
    """Calc point"""
    # Maritime Mobile
    if "/MM" in self.contact.get("Call", ""):
        return 5

    result = self.cty_lookup(self.station.get("Call", ""))
    if result:
        for item in result.items():
            mycountry = item[1].get("entity", "")
            mycontinent = item[1].get("continent", "")
    result = self.cty_lookup(self.contact.get("Call", ""))
    if result:
        for item in result.items():
            entity = item[1].get("entity", "")
            continent = item[1].get("continent", "")

            # Both in same country
            if mycountry.upper() == entity.upper():
                return 2

            # Same Continent
            if mycontinent == continent:
                return 5

            # Different Continent
            return 10
    return 0


def show_mults(self):
    """Return display string for mults"""
    result = self.database.fetch_mult1_count()
    count = result.get("count", 0)
    return count


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
        result = self.database.fetch_mult1_count()
        mults = int(result.get("count", 0))
        return contest_points * mults
    return 0


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "CQ-160-CW")


def cabrillo(self):
    """Generates Cabrillo file. Maybe."""
    # https://www.cw160.com/cabrillo.htm
    logger.debug("******Cabrillo*****")
    logger.debug("Station: %s", f"{self.station}")
    logger.debug("Contest: %s", f"{self.contest_settings}")
    now = datetime.datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = (
        str(Path.home())
        + "/"
        + f"{self.station.get('Call', '').upper()}_{cabrillo_name}_{date_time}.log"
    )
    logger.debug("%s", filename)
    log = self.database.fetch_all_contacts_asc()
    try:
        with open(filename, "w", encoding="ascii") as file_descriptor:
            print("START-OF-LOG: 3.0", end="\r\n", file=file_descriptor)
            print(
                f"CREATED-BY: Not1MM v{__version__}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"CONTEST: {cabrillo_name}",
                end="\r\n",
                file=file_descriptor,
            )
            if self.station.get("Club", ""):
                print(
                    f"CLUB: {self.station.get('Club', '').upper()}",
                    end="\r\n",
                    file=file_descriptor,
                )
            print(
                f"CALLSIGN: {self.station.get('Call','')}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"LOCATION: {self.station.get('ARRLSection', '')}",
                end="\r\n",
                file=file_descriptor,
            )

            print(
                f"CATEGORY-OPERATOR: {self.contest_settings.get('OperatorCategory','')}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"CATEGORY-ASSISTED: {self.contest_settings.get('AssistedCategory','')}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"CATEGORY-BAND: {self.contest_settings.get('BandCategory','')}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"CATEGORY-MODE: {self.contest_settings.get('ModeCategory','')}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"CATEGORY-TRANSMITTER: {self.contest_settings.get('TransmitterCategory','')}",
                end="\r\n",
                file=file_descriptor,
            )
            if self.contest_settings.get("OverlayCategory", "") != "N/A":
                print(
                    f"CATEGORY-OVERLAY: {self.contest_settings.get('OverlayCategory','')}",
                    end="\r\n",
                    file=file_descriptor,
                )
            print(
                f"GRID-LOCATOR: {self.station.get('GridSquare','')}",
                end="\r\n",
                file=file_descriptor,
            )

            print(
                f"CATEGORY-POWER: {self.contest_settings.get('PowerCategory','')}",
                end="\r\n",
                file=file_descriptor,
            )

            print(
                f"CLAIMED-SCORE: {calc_score(self)}",
                end="\r\n",
                file=file_descriptor,
            )
            ops = f"@{self.station.get('Call','')}"
            list_of_ops = self.database.get_ops()
            for op in list_of_ops:
                ops += f", {op.get('Operator', '')}"
            print(
                f"OPERATORS: {ops}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"NAME: {self.station.get('Name', '')}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"ADDRESS: {self.station.get('Street1', '')}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"ADDRESS-CITY: {self.station.get('City', '')}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"ADDRESS-STATE-PROVINCE: {self.station.get('State', '')}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"ADDRESS-POSTALCODE: {self.station.get('Zip', '')}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"ADDRESS-COUNTRY: {self.station.get('Country', '')}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"EMAIL: {self.station.get('Email', '')}",
                end="\r\n",
                file=file_descriptor,
            )
            for contact in log:
                the_date_and_time = contact.get("TS", "")
                themode = contact.get("Mode", "")
                if themode == "LSB" or themode == "USB":
                    themode = "PH"
                frequency = str(int(contact.get("Freq", "0"))).rjust(5)

                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                print(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SNT', '')).ljust(3)} "
                    f"{str(contact.get('SentNr', '')).ljust(6)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('RCV', '')).ljust(3)} "
                    f"{str(contact.get('Exchange1', '')).ljust(6)}",
                    end="\r\n",
                    file=file_descriptor,
                )
            print("END-OF-LOG:", end="\r\n", file=file_descriptor)
        self.show_message_box(f"Cabrillo saved to: {filename}")
    except IOError as exception:
        logger.critical("cabrillo: IO error: %s, writing to %s", exception, filename)
        self.show_message_box(f"Error saving Cabrillo: {exception} {filename}")
        return


def trigger_update(self):
    """Triggers the log window to update."""
    cmd = {}
    cmd["cmd"] = "UPDATELOG"
    cmd["station"] = platform.node()
    self.multicast_interface.send_as_json(cmd)


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""
    all_contacts = self.database.fetch_all_contacts_asc()
    for contact in all_contacts:
        time_stamp = contact.get("TS", "")
        if contact.get("CountryPrefix", "") == "K":
            query = f"select count(*) as count from dxlog where TS < '{time_stamp}' and CountryPrefix = 'K' and Exchange1 = '{contact.get('Exchange1', '')}' and ContestNR = '{self.pref.get('contest', '0')}'"
            result = self.database.exec_sql(query)
            if result.get("count", 0) == 0:
                contact["IsMultiplier1"] = 1
            else:
                contact["IsMultiplier1"] = 0
            self.database.change_contact(contact)
            continue
        if contact.get("CountryPrefix", "") == "VE":
            query = f"select count(*) as count from dxlog where TS < '{time_stamp}' and CountryPrefix = 'VE' and Exchange1 = '{contact.get('Exchange1', '')}' and ContestNR = '{self.pref.get('contest', '0')}'"
            result = self.database.exec_sql(query)
            if result.get("count", 0) == 0:
                contact["IsMultiplier1"] = 1
            else:
                contact["IsMultiplier1"] = 0
            self.database.change_contact(contact)
            continue
        query = f"select count(*) as count from dxlog where TS < '{time_stamp}' and CountryPrefix = '{contact.get('CountryPrefix', '')}' and ContestNR = '{self.pref.get('contest', '0')}'"
        result = self.database.exec_sql(query)
        if result.get("count", 0) == 0:
            contact["IsMultiplier1"] = 1
        else:
            contact["IsMultiplier1"] = 0
        self.database.change_contact(contact)
    trigger_update(self)
