"""
IARU HF World Championship  IARU-HF

Exchange:       IARU HQ: RS(T) + IARU Society
                Non-HQ: RS(T) + ITU Zone No.

Work stations:  Once per band per mode

QSO Points:     1 point per QSO with same zone or with HQ stations
                3 points per QSO with different zone on same continent
                5 points per QSO with different zone on different continent

Multipliers:    Each ITU zone once per band
                Each IARU HQ and each IARU official once per band
"""

# pylint: disable=invalid-name, unused-argument, unused-variable

import datetime
import logging

from decimal import Decimal
from pathlib import Path

from PyQt5 import QtWidgets
from not1mm.lib.version import __version__

logger = logging.getLogger("__main__")

name = "IARU HF"
cabrillo_name = "IARU-HF"
mode = "BOTH"  # CW SSB BOTH RTTY

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Mode",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
    "PTS",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 3

OFFICIAL_STATIONS = []


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
    label = self.field4.findChild(QtWidgets.QLabel)
    label.setText("ITU Zone")
    self.field4.setAccessibleName("I T U Zone")


def reset_label(self):
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
        self.field3.findChild(QtWidgets.QLineEdit): self.callsign,
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
    self.contact["ZN"] = self.other_2.text()
    self.contact["NR"] = self.other_2.text()
    self.contact["SentNr"] = self.contest_settings.get("SentExchange", 0)


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill ITU Zone"""
    if len(self.other_2.text()) == 0:
        self.other_2.setText(str(self.contact.get("ZN", "")))
    self.other_1.setText(str(self.contest_settings.get("SentExchange", 0)))


def points(self):
    """
    QSO Points: 1 point per QSO with same zone or with HQ stations
                3 points per QSO with different zone on same continent
                5 points per QSO with different zone on different continent
    """

    result = self.cty_lookup(self.station.get("Call", ""))
    if result:
        for item in result.items():
            mycontinent = item[1].get("continent", "")
    our_itu = int(self.station.get("IARUZone", 0))

    try:
        their_itu = int(self.contact.get("ZN", 0))
    except ValueError:
        return 1
    if our_itu == their_itu:
        return 1
    if self.contact["Continent"] == mycontinent:
        return 3
    return 5


def show_mults(self):
    """Return display string for mults"""
    result1 = self.database.fetch_zn_band_mode_count()
    if result1:
        return int(result1.get("zbm_count", 0))
    return 0


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def get_points(self):
    """Return raw points before mults"""
    result = self.database.fetch_points()
    if result:
        return int(result.get("Points", 0))
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
    """
    Creates an ADIF file of the contacts made.
    """
    now = datetime.datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = (
        str(Path.home())
        + "/"
        + f"{self.station.get('Call').upper()}_{cabrillo_name}_{date_time}.adi"
    )
    log = self.database.fetch_all_contacts_asc()
    try:
        with open(filename, "w", encoding="utf-8") as file_descriptor:
            print("<ADIF_VER:5>2.2.0", end="\r\n", file=file_descriptor)
            print("<EOH>", end="\r\n", file=file_descriptor)
            for contact in log:
                hiscall = contact.get("Call", "")
                hisname = contact.get("Name", "")
                the_date_and_time = contact.get("TS")
                # band = contact.get("Band")
                themode = contact.get("Mode")
                frequency = str(Decimal(str(contact.get("Freq", 0))) / 1000)
                sentrst = contact.get("SNT", "")
                rcvrst = contact.get("RCV", "")
                sentnr = str(contact.get("SentNr", "0"))
                rcvnr = str(contact.get("NR", "0"))
                grid = contact.get("GridSquare", "")
                comment = contact.get("Comment", "")
                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                print(
                    f"<QSO_DATE:{len(''.join(loggeddate.split('-')))}:d>"
                    f"{''.join(loggeddate.split('-'))}",
                    end="\r\n",
                    file=file_descriptor,
                )
                print(
                    f"<TIME_ON:{len(loggedtime)}>{loggedtime}",
                    end="\r\n",
                    file=file_descriptor,
                )
                print(
                    f"<CALL:{len(hiscall)}>{hiscall.upper()}",
                    end="\r\n",
                    file=file_descriptor,
                )
                if len(hisname):
                    print(
                        f"<NAME:{len(hisname)}>{hisname.title()}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                print(
                    f"<MODE:{len(themode)}>{themode}", end="\r\n", file=file_descriptor
                )
                # print(
                #     f"<BAND:{len(band + 'M')}>{band + 'M'}",
                #     end="\r\n",
                #     file=file_descriptor,
                # )
                try:
                    print(
                        f"<FREQ:{len(frequency)}>{frequency}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                except TypeError:
                    pass  # This is bad form... I can't remember why this is in a try block

                print(
                    f"<RST_SENT:{len(sentrst)}>{sentrst}",
                    end="\r\n",
                    file=file_descriptor,
                )
                print(
                    f"<RST_RCVD:{len(rcvrst)}>{rcvrst}",
                    end="\r\n",
                    file=file_descriptor,
                )
                if sentnr != "0":
                    print(
                        f"<STX_STRING:{len(sentnr)}>{sentnr}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                if rcvnr != "0":
                    print(
                        f"<SRX_STRING:{len(rcvnr)}>{rcvnr}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                if len(grid) > 1:
                    print(
                        f"<GRIDSQUARE:{len(grid)}>{grid}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                if len(comment):
                    print(
                        f"<COMMENT:{len(comment)}>{comment}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                print("<EOR>", end="\r\n", file=file_descriptor)
                print("", end="\r\n", file=file_descriptor)
    except IOError:
        ...


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
        + f"{self.station.get('Call').upper()}_{cabrillo_name}_{date_time}.log"
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
            print(
                "OPERATORS: ",
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
                    f"{str(contact.get('ZN', '')).ljust(6)}",
                    end="\r\n",
                    file=file_descriptor,
                )
            print("END-OF-LOG:", end="\r\n", file=file_descriptor)
    except IOError as exception:
        logger.critical("cabrillo: IO error: %s, writing to %s", exception, filename)
        return


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""
