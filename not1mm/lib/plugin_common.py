"""Common function(s) for all contest plugins"""

import logging
import datetime
import re
import uuid
import adif_io

from decimal import Decimal
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QDialog, QPushButton, QProgressDialog
from PyQt6.QtCore import QCoreApplication, Qt

from not1mm.lib.ham_utility import get_adif_band, get_not1mm_band, get_not1mm_band_xlog
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)


def online_score_xml(self):
    """generate online xml"""

    mults = self.contest.get_mults(self)
    the_mults = ""
    for thing in mults:
        the_mults += (
            f'<mult band="total" mode="ALL" type="{thing}">{mults.get(thing,0)}</mult>'
        )

    the_points = self.contest.just_points(self)

    the_date_time = datetime.datetime.now(datetime.timezone.utc).isoformat(" ")[:19]
    assisted = self.contest_settings.get("AssistedCategory", "")
    bands = self.contest_settings.get("BandCategory", "")
    modes = self.contest_settings.get("ModeCategory", "")
    if modes in ["SSB+CW", "SSB+CW+DIGITAL"]:
        modes = "MIXED"
    xmiter = self.contest_settings.get("TransmitterCategory", "")
    ops = self.contest_settings.get("OperatorCategory", "")
    overlay = self.contest_settings.get("OverlayCategory", "")
    power = self.contest_settings.get("PowerCategory", "")

    the_xml = (
        '<?xml version="1.0"?>'
        "<dynamicresults>"
        f"<contest>{self.contest.cabrillo_name}</contest>"
        f'<call>{self.station.get("Call", "")}</call>'
        # <ops>NR9Q</ops>
        f'<class power="{power}" assisted = "{assisted}" transmitter="{xmiter}" ops="{ops}" bands="{bands}" mode="{modes}" overlay="{overlay}"></class>'
        f"<club>{self.station.get('Club', '')}</club>"
        "<soft>Not1MM</soft>"
        f"<version>{__version__}</version>"
        "<qth>"
        # <dxcccountry>K</dxcccountry>
        f"<cqzone>{self.station.get('CQZone','')}</cqzone>"
        f"<iaruzone>{self.station.get('IARUZone','')}</iaruzone>"
        f"<arrlsection>{self.station.get('ARRLSection', '')}</arrlsection>"
        f"<stprvoth>{self.station.get('State','')}</stprvoth>"
        f"<grid6>{self.station.get('GridSquare','')}</grid6>"
        "</qth>"
        "<breakdown>"
        f'<qso band="total" mode="ALL">{self.contest.show_qso(self)}</qso>'
        f"{the_mults}"
        f'<point band="total" mode="ALL">{the_points}</point>'
        "</breakdown>"
        f"<score>{self.contest.calc_score(self)}</score>"
        f"<timestamp>{the_date_time}</timestamp>"
        "</dynamicresults>"
    )
    return the_xml


def get_points(self):
    """Return raw points before mults"""
    result = self.database.fetch_points()
    if result:
        if result.get("Points", 0) is not None:
            return int(result.get("Points", 0))
    return 0


def gen_adif(self, cabrillo_name: str, contest_id=""):
    """
    Creates an ADIF file of the contacts made.
    """
    now = datetime.datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    station_callsign = self.station.get("Call", "").upper()
    filename = (
        str(Path.home()) + "/" + f"{station_callsign}_{cabrillo_name}_{date_time}.adi"
    )
    log = self.database.fetch_all_contacts_asc()
    try:
        with open(filename, "w", encoding="utf-8", newline="") as file_descriptor:
            print("Not1MM ADIF export", end="\r\n", file=file_descriptor)
            print("<ADIF_VER:5>3.1.5", end="\r\n", file=file_descriptor)
            print("<EOH>", end="\r\n", file=file_descriptor)
            for contact in log:
                hiscall = contact.get("Call", "")
                hisname = contact.get("Name", "")
                the_date_and_time = contact.get("TS", "")
                themode = contact.get("Mode", "")
                if themode in ("CW", "CW-U", "CW-L", "CW-R", "CWR"):
                    themode = "CW"
                if cabrillo_name in ("CQ-WW-RTTY", "WEEKLY-RTTY"):
                    themode = "RTTY"
                frequency = str(Decimal(str(contact.get("Freq", 0))) / 1000)
                band = get_adif_band(Decimal(str(contact.get("Freq", 0))) / 1000)
                sentrst = contact.get("SNT", "")
                rcvrst = contact.get("RCV", "")
                sentnr = str(contact.get("SentNr", "0"))
                rcvnr = str(contact.get("NR", "0"))
                grid = contact.get("GridSquare", "")
                pfx = contact.get("CountryPrefix", "")
                comment = contact.get("Comment", "")
                loggeddate = the_date_and_time[:10]
                loggedtime = (
                    the_date_and_time[11:13]
                    + the_date_and_time[14:16]
                    + the_date_and_time[17:20]
                )
                print(
                    f"<QSO_DATE:{len(''.join(loggeddate.split('-')))}:d>"
                    f"{''.join(loggeddate.split('-'))}",
                    end="\r\n",
                    file=file_descriptor,
                )

                try:
                    print(
                        f"<TIME_ON:{len(loggedtime)}>{loggedtime}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                except TypeError:
                    ...

                try:
                    print(
                        f"<STATION_CALLSIGN:{len(station_callsign)}>{station_callsign}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                except TypeError:
                    ...

                try:
                    print(
                        f"<CALL:{len(hiscall)}>{hiscall.upper()}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                except TypeError:
                    ...

                try:
                    if len(hisname):
                        print(
                            f"<NAME:{len(hisname)}>{hisname.title()}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                except TypeError:
                    ...

                try:
                    if themode in ("USB", "LSB"):
                        print(
                            f"<MODE:3>SSB\r\n<SUBMODE:{len(themode)}>{themode}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                    else:
                        print(
                            f"<MODE:{len(themode)}>{themode}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                except TypeError:
                    ...

                try:
                    print(
                        f"<BAND:{len(band)}>{band}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                except TypeError:
                    ...

                try:
                    print(
                        f"<FREQ:{len(frequency)}>{frequency}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                except TypeError:
                    ...

                try:
                    print(
                        f"<RST_SENT:{len(sentrst)}>{sentrst}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                except TypeError:
                    ...

                try:
                    print(
                        f"<RST_RCVD:{len(rcvrst)}>{rcvrst}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                except TypeError:
                    ...

                try:
                    if cabrillo_name in ("WFD", "ARRL-FD", "ARRL-FIELD-DAY"):
                        sent = self.contest_settings.get("SentExchange", "")
                        if sent:
                            print(
                                f"<STX_STRING:{len(sent)}>{sent.upper()}",
                                end="\r\n",
                                file=file_descriptor,
                            )
                    elif cabrillo_name in ("ICWC-MST"):
                        sent = (
                            f'{self.contest_settings.get("SentExchange", "")} {sentnr}'
                        )
                        if sent:
                            print(
                                f"<STX_STRING:{len(sent)}>{sent.upper()}",
                                end="\r\n",
                                file=file_descriptor,
                            )
                    elif sentnr != "0":
                        print(
                            f"<STX_STRING:{len(sentnr)}>{sentnr}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                except TypeError:
                    ...

                # SRX STRING, Contest dependent
                try:
                    # ----------Medium Speed Test------------
                    if cabrillo_name in ("ICWC-MST"):
                        rcv = f"{hisname.upper()} {contact.get('NR', '')}"
                        if len(rcv) > 1:
                            print(
                                f"<SRX_STRING:{len(rcv)}>{rcv.upper()}",
                                end="\r\n",
                                file=file_descriptor,
                            )
                    # ----------Field Days------------
                    elif cabrillo_name in ("WFD", "ARRL-FD", "ARRL-FIELD-DAY"):
                        rcv = (
                            f"{contact.get('Exchange1', '')} {contact.get('Sect', '')}"
                        )
                        if len(rcv) > 1:
                            print(
                                f"<SRX_STRING:{len(rcv)}>{rcv.upper()}",
                                end="\r\n",
                                file=file_descriptor,
                            )
                    # ------------CQ 160---------------
                    elif cabrillo_name in ("CQ-160-CW", "CQ-160-SSB", "WEEKLY-RTTY"):
                        rcv = f"{contact.get('Exchange1', '')}"
                        if len(rcv) > 1:
                            print(
                                f"<SRX_STRING:{len(rcv)}>{rcv.upper()}",
                                end="\r\n",
                                file=file_descriptor,
                            )
                    # --------------K1USN-SST-----------
                    elif cabrillo_name == "K1USN-SST":
                        rcv = f"{contact.get('Name', '')} {contact.get('Sect', '')}"
                        if len(rcv) > 1:
                            print(
                                f"<SRX_STRING:{len(rcv)}>{rcv.upper()}",
                                end="\r\n",
                                file=file_descriptor,
                            )
                    # ------------CQ-WW-DX-RTTY---------
                    elif cabrillo_name == "CQ-WW-RTTY":
                        rcv = f"{str(contact.get('ZN', '')).zfill(2)} {contact.get('Exchange1', 'DX')}"
                        if len(rcv) > 1:
                            print(
                                f"<SRX_STRING:{len(rcv)}>{rcv.upper()}",
                                end="\r\n",
                                file=file_descriptor,
                            )
                    elif rcvnr != "0":
                        print(
                            f"<SRX_STRING:{len(rcvnr)}>{rcvnr}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                except TypeError:
                    ...

                try:
                    result = re.match(
                        "[A-R][A-R]([0-9][0-9][A-X][A-X])*([0-9][0-9])?",
                        grid,
                        re.IGNORECASE,
                    )
                    grid = ""
                    if result:
                        grid = result.group()

                    if len(grid[:8]) > 1:
                        print(
                            f"<GRIDSQUARE:{len(grid[:8])}>{grid[:8]}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                except TypeError:
                    ...

                try:
                    if len(pfx) > 0:
                        print(
                            f"<PFX:{len(pfx)}>{pfx}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                except TypeError:
                    ...

                try:
                    if len(contest_id) > 1:
                        print(
                            f"<CONTEST_ID:{len(contest_id)}>{contest_id}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                except TypeError:
                    ...

                try:
                    if len(comment):
                        print(
                            f"<COMMENT:{len(comment)}>{comment}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                except TypeError:
                    ...

                print("<EOR>", end="\r\n", file=file_descriptor)
                print("", end="\r\n", file=file_descriptor)
            self.show_message_box(f"ADIF saved to: {filename}")
    except IOError as error:
        self.show_message_box(f"Error saving ADIF file: {error}")


def imp_adif(self):
    """
    Imports an ADIF file into the current contest.
    """

    filename = self.filepicker("other")
    if not filename:
        return
    logger.debug(f"Selected file '{filename}' to import from")

    # read in content in binary mode (in case of illegal characters)
    try:
        with open(filename, "rb") as file:
            file_content = file.read()
    except Exception as e:
        self.show_message_box(f"Error: {e}")
        return

    # filter out anything beyond 7-bit ASCII
    ascii_content = str("")
    for b in file_content:
        if b < 128:
            ascii_content = ascii_content + chr(b)

    qsos_raw, adif_header = adif_io.read_from_string(ascii_content)
    qsos_sorted = sorted(qsos_raw, key=adif_io.time_on)

    num_qsos = len(qsos_sorted)
    logger.debug(f"Found {num_qsos} QSOs to import")
    self.show_message_box(f"Found {num_qsos} QSOs in\n'{filename}'.")
    if num_qsos == 0:
        return

    self.progress_dialog = QProgressDialog("Validating...", "Cancel", 0, num_qsos, self)
    self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
    # using .show() breaks modality - just start updating

    q_num = 0
    contacts = []
    dupes = 0

    for q in qsos_sorted:
        QCoreApplication.processEvents()
        if self.progress_dialog.wasCanceled():
            self.progress_dialog.close()
            self.show_message_box("Cancelling import.")
            return

        this_contact = self.database.get_empty()

        try:
            temp = adif_io.time_on(q)
            this_contact["TS"] = temp.strftime("%Y-%m-%d %H:%M:%S")
        except KeyError:
            logger.debug("Date/time not found in QSO #{q_num+1}")
            self.progress_dialog.close()
            self.show_message_box(
                f"Date/time not found in QSO #{q_num+1}.\nImport cancelled."
            )
            return

        if q.get("CALL"):
            this_contact["Call"] = q.get("CALL")
        else:
            logger.debug("Callsign not found in QSO #{q_num+1}")
            self.progress_dialog.close()
            self.show_message_box(
                f"Callsign not found in QSO #{q_num+1}.\nImport cancelled."
            )
            return

        # ADIF freq is in MHz, not1mm is in kHz
        if q.get("FREQ"):
            this_contact["Freq"] = float(q.get("FREQ")) * 1000.0
        else:
            logger.debug("Frequency not found in QSO #{q_num+1}")
            self.progress_dialog.close()
            self.show_msgbox(
                f"Valid Frequency not found in QSO #{q_num+1}.\nImport cancelled."
            )
            return

        if q.get("QSXFREQ"):
            this_contact["QSXFreq"] = float(q.get("QSXFREQ")) * 1000.0
        else:
            this_contact["QSXFreq"] = 0.0

        if q.get("MODE"):
            this_contact["Mode"] = q.get("MODE")
        elif q.get("SUBMODE"):
            this_contact["Mode"] = q.get("SUBMODE")
        else:
            logger.debug("Mode not found in QSO #{q_num+1}")
            self.progress_dialog.close()
            self.show_message_box(
                f"Valid Mode not found in QSO #{q_num+1}.\nImport cancelled."
            )
            return

        this_contact["ContestName"] = self.contest.name

        if q.get("SNT"):
            this_contact["SNT"] = q.get("SNT")
        elif q.get("RST_SENT"):
            this_contact["SNT"] = q.get("RST_SENT")

        if q.get("RCV"):
            this_contact["RCV"] = q.get("RCV")
        elif q.get("RST_RCVD"):
            this_contact["RCV"] = q.get("RST_RCVD")

        if q.get("COUNTRYPREFIX"):
            this_contact["CountryPrefix"] = q.get("COUNTRYPREFIX")
        elif q.get("PFX"):
            this_contact["CountryPrefix"] = q.get("PFX")

        if q.get("STATIONPREFIX"):
            this_contact["StationPrefix"] = q.get("STATIONPREFIX")

        if q.get("QTH"):
            this_contact["QTH"] = q.get("QTH")

        if q.get("NAME"):
            this_contact["Name"] = q.get("NAME")

        if q.get("COMMENT"):
            this_contact["Comment"] = q.get("COMMENT")

        if q.get("NR"):
            this_contact["NR"] = q.get("NR")

        if q.get("SECT"):
            this_contact["Sect"] = q.get("SECT")
        elif q.get("ARRL_SECT"):
            this_contact["Sect"] = q.get("ARRL_SECT")

        QCoreApplication.processEvents()

        if q.get("PREC"):
            this_contact["Prec"] = q.get("PREC")

        if q.get("CK"):
            this_contact["CK"] = q.get("CK")

        if q.get("ZN"):
            this_contact["ZN"] = q.get("ZN")
        elif q.get("CQZ"):
            this_contact["ZN"] = q.get("CQZ")

        if q.get("SENTNR"):
            this_contact["SentNr"] = q.get("SENTNR")

        if q.get("POINTS"):
            this_contact["Points"] = q.get("POINTS")
        elif q.get("APP_N1MM_POINTS"):
            this_contact["Points"] = q.get("APP_N1MM_POINTS")

        if q.get("APP_N1MM_MULT1"):
            this_contact["IsMultiplier1"] = q.get("APP_N1MM_MULT1")

        if q.get("APP_N1MM_MULT2"):
            this_contact["IsMultiplier2"] = q.get("APP_N1MM_MULT2")

        if q.get("POWER"):
            this_contact["Power"] = q.get("POWER")
        elif q.get("TX_PWR"):
            this_contact["Power"] = q.get("TX_PWR")

        # ADIF Band is in Meters (eg, "20m"), not1mm is in (float) MHz
        # xlog does not export a Band field, so Band should not be mandatory
        # 1st attempt: ADIF style like "18m"
        temp = str(q.get("BAND"))
        temp = get_not1mm_band(temp.lower())
        # 2nd attempt: no Band field, so take a Freq like "18.160" and double-convert
        temp2 = get_adif_band(float(q.get("FREQ")))  # returns like "18m"
        temp3 = get_not1mm_band(temp2.lower())  # returns like "18.068"
        # 3rd attempt: abbreviated Freq like "18" (ie, from xlog)
        temp4 = get_not1mm_band_xlog(q.get("FREQ"))
        if temp != 0.0:
            this_contact["Band"] = temp
        elif temp3 != 0.0:
            this_contact["Band"] = temp3
        elif temp4 != 0.0:
            this_contact["Band"] = temp4
        else:
            # Well, we tried.
            this_contact["Band"] = 0.0

        if q.get("WPXPREFIX"):
            this_contact["WPXPrefix"] = q.get("WPXPREFIX")

        if q.get("EXCHANGE1"):
            this_contact["Exchange1"] = q.get("EXCHANGE1")
        elif q.get("CLASS"):
            this_contact["Exchange1"] = q.get("CLASS")
        elif q.get("APP_N1MM_EXCHANGE1"):
            this_contact["Exchange1"] = q.get("APP_N1MM_EXCHANGE1")

        if q.get("RADIONR"):
            this_contact["RadioNR"] = q.get("RADIONR")
        elif q.get("APP_N1MM_RADIONR"):
            this_contact["RadioNR"] = q.get("APP_N1MM_RADIONR")
        else:
            this_contact["RadioNR"] = 1

        this_contact["ContestNR"] = self.pref.get("contest", "0")

        if q.get("ISMULTIPLIER3"):
            this_contact["isMultiplier3"] = q.get("ISMULTIPLIER3")
        elif q.get("APP_N1MM_MULT3"):
            this_contact["isMultiplier3"] = q.get("APP_N1MM_MULT3")

        if q.get("MISCTEXT"):
            this_contact["MiscText"] = q.get("MISCTEXT")

        if q.get("ISRUNQSO"):
            this_contact["IsRunQSO"] = q.get("ISRUNQSO")

        if q.get("CONTACTTYPE"):
            this_contact["ContactType"] = q.get("CONTACTTYPE")

        QCoreApplication.processEvents()

        if q.get("RUN1RUN2"):
            this_contact["Run1Run2"] = q.get("RUN1RUN2")
        elif q.get("APP_N1MM_RUN1RUN2"):
            this_contact["Run1Run2"] = q.get("APP_N1MM_RUN1RUN2")
        else:
            this_contact["Run1Run2"] = 1

        if q.get("GRIDSQUARE"):
            this_contact["GridSquare"] = q.get("GRIDSQUARE")

        if q.get("OPERATOR"):
            this_contact["Operator"] = q.get("OPERATOR")
        elif q.get("STATION_CALLSIGN"):
            this_contact["Operator"] = q.get("STATION_CALLSIGN")

        if q.get("CONTINENT"):
            this_contact["Continent"] = q.get("CONTINENT")
        elif q.get("APP_N1MM_CONTINENT"):
            this_contact["Continent"] = q.get("APP_N1MM_CONTINENT")

        if q.get("ROVERLOCATION"):
            this_contact["RoverLocation"] = q.get("ROVERLOCATION")

        if q.get("RADIOINTERFACED"):
            this_contact["RadioInterfaced"] = q.get("RADIOINTERFACED")
        elif q.get("APP_N1MM_RADIOINTERFACED"):
            this_contact["RadioInterfaced"] = q.get("APP_N1MM_RADIOINTERFACED")

        if q.get("NETWORKEDCOMPNR"):
            this_contact["NetworkedCompNr"] = q.get("NETWORKEDCOMPNR")

        if q.get("NETBIOSNAME"):
            this_contact["NetBiosName"] = q.get("NETBIOSNAME")
        elif q.get("APP_N1MM_NETBIOSNAME"):
            this_contact["NetBiosName"] = q.get("APP_N1MM_NETBIOSNAME")
        elif q.get("N3FJP_COMPUTERNAME"):
            this_contact["NetBiosName"] = q.get("N3FJP_COMPUTERNAME")

        if q.get("ISORIGINAL"):
            this_contact["IsOriginal"] = q.get("ISORIGINAL")
        elif q.get("APP_N1MM_ISORIGINAL"):
            this_contact["IsOriginal"] = q.get("APP_N1MM_ISORIGINAL")

        this_contact["ID"] = uuid.uuid4().hex

        if q.get("CLAIMEDQSO"):
            this_contact["CLAIMEDQSO"] = q.get("CLAIMEDQSO")
        elif q.get("APP_N1MM_CLAIMEDQSO"):
            this_contact["CLAIMEDQSO"] = q.get("APP_N1MM_CLAIMEDQSO")

        # is this record a dupe?
        theTS = this_contact["TS"]
        thecall = this_contact["Call"]
        temp = self.database.exec_sql(
            f"select count(*) as isdupe from dxlog where TS = '{theTS}' and call = '{thecall}'"
        )
        if temp["isdupe"] > 0:
            dupes = dupes + 1
        else:
            contacts.append(this_contact.copy())

        this_contact.clear()
        q_num = q_num + 1
        self.progress_dialog.setValue(q_num)
        QCoreApplication.processEvents()

    # All ADIF records have now been mapped.
    # setting to max value forces progress_dialog to close
    self.progress_dialog.setValue(num_qsos)

    logger.debug(f"Found {dupes} duplicate records")
    if dupes > 0:
        self.show_message_box(
            f"NOTE: Found {dupes} duplicate records, which will not be saved."
        )

    # open new progress_dialog for Save progress.
    self.progress_dialog = QProgressDialog(
        "Saving...", "Cancel", 0, len(contacts), self
    )
    self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)

    saves = 0
    for my_contact in contacts:
        QCoreApplication.processEvents()
        if self.progress_dialog.wasCanceled():
            self.progress_dialog.close()
            self.show_message_box("Cancelling import in progress.")
            return

        self.database.log_contact(my_contact)

        saves = saves + 1
        self.progress_dialog.setValue(saves)
        QCoreApplication.processEvents()

    self.progress_dialog.setValue(len(contacts))  # forces close
    # update everything
    self.log_window.get_log()

    if self.actionStatistics.isChecked():
        self.statistics_window.get_run_and_total_qs()

    score = self.contest.calc_score(self)
    self.score.setText(str(score))

    mults = self.contest.show_mults(self)
    qsos = self.contest.show_qso(self)
    multstring = f"{qsos}/{mults}"
    self.mults.setText(multstring)

    logger.debug(f"Saved {saves} ADIF records to contest {self.contest.name}")
    self.show_message_box(f"Saved {saves} ADIF records to this contest.")
    return
