"""ARRL Sep VHF"""

# Cabrillo name:	ARRL-VHF-SEP
# Cabrillo name aliases:	ARRL-VHF

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member

import datetime
import logging

from pathlib import Path
from PyQt5 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, get_points
from not1mm.lib.version import __version__

logger = logging.getLogger("__main__")

name = "ARRL VHF SEP"
mode = "BOTH"  # CW SSB BOTH RTTY
cabrillo_name = "ARRL-VHF-SEP"

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "SentNr",
    "RcvNr",
    "PTS",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 2


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
    label = self.field3.findChild(QtWidgets.QLabel)
    label.setText("SentNR")
    self.field3.setAccessibleName("Sent Grid")
    label = self.field4.findChild(QtWidgets.QLabel)
    label.setText("Grid")
    self.field4.setAccessibleName("Gridsquare")


def reset_label(self):
    """reset label after field cleared"""


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.field1.findChild(QtWidgets.QLineEdit),
        self.field1.findChild(QtWidgets.QLineEdit): self.field2.findChild(
            QtWidgets.QLineEdit
        ),
        self.field2.findChild(QtWidgets.QLineEdit): self.field3.findChild(
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
        self.field4.findChild(QtWidgets.QLineEdit): self.field3.findChild(
            QtWidgets.QLineEdit
        ),
    }


def validate(self):
    """doc"""
    # exchange = self.other_2.text().upper().split()
    # if len(exchange) == 3:
    #     if exchange[0].isalpha() and exchange[1].isdigit() and exchange[2].isalpha():
    #         return True
    # return False
    return True


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["NR"] = self.other_2.text().upper()
    self.contact["SentNr"] = self.other_1.text()


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill sentnr"""
    result = self.database.get_serial()
    serial_nr = str(result.get("serial_nr", "1"))
    if serial_nr == "None":
        serial_nr = "1"

    exchange = self.contest_settings.get("SentExchange", "").replace("#", serial_nr)
    field = self.field3.findChild(QtWidgets.QLineEdit)
    if len(field.text()) == 0:
        field.setText(exchange)


def points(self):
    """Calc point"""

    # QSO Points:	1 point per 50 or 144 MHz QSO
    # 2 points per 222 or 432 MHz QSO
    # 3 points per 902 or 1296 MHz QSO
    # 4 points per 2.3 GHz or higher QSO

    _band = self.contact.get("Band", "")
    if _band in ["50", "144"]:
        return 1
    if _band in ["222", "432"]:
        return 2
    if _band in ["902", "1296"]:
        return 3
    if _band in ["2300+"]:
        return 4
    return 0


def show_mults(self):
    """Return display string for mults"""
    # Multipliers:	Grid squares once per band

    dx = 0

    sql = (
        "select count(DISTINCT(NR || ':' || Band)) as mult_count "
        f"from dxlog where ContestNR = {self.database.current_contest} and typeof(NR) = 'text';"
    )
    result = self.database.exec_sql(sql)

    if result:
        dx = result.get("mult_count", 0)

    return dx


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score"""
    # Multipliers: Each US State + DC once per mode
    _points = get_points(self)
    _mults = show_mults(self)
    _power_mult = 1
    # if self.contest_settings.get("PowerCategory", "") == "QRP":
    #     _power_mult = 2
    return _points * _power_mult * _mults


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name)


def cabrillo(self):
    """Generates Cabrillo file. Maybe."""
    # https://www.cqwpx.com/cabrillo.htm
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
            # print(
            #     f"ARRL-SECTION: {self.pref.get('section', '')}",
            #     end="\r\n",
            #     file=file_descriptor,
            # )
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
            # print(
            #     f"CATEGORY: {None}",
            #     end="\r\n",
            #     file=file_descriptor,
            # )
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
                    f"{str(contact.get('NR', '')).ljust(6)}",
                    end="\r\n",
                    file=file_descriptor,
                )
            print("END-OF-LOG:", end="\r\n", file=file_descriptor)
    except IOError as exception:
        logger.critical("cabrillo: IO error: %s, writing to %s", exception, filename)
        return


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""
