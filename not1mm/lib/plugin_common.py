"""Common function(s) for all contest plugins"""

import datetime
import logging
import re
import uuid
from decimal import Decimal
from pathlib import Path

import adif_io
from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QApplication, QDialog, QProgressDialog, QPushButton

from not1mm.lib.ham_utility import get_adif_band, get_not1mm_band
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

# Prevents unused warnings
assert QApplication
assert QDialog
assert QPushButton


def online_score_xml(self):
    """generate online xml"""

    mults = self.contest.get_mults(self)
    the_mults = ""
    for thing in mults:
        the_mults += (
            f'<mult band="total" mode="ALL" type="{thing}">{mults.get(thing, 0)}</mult>'
        )

    the_points = self.contest.just_points(self)

    the_date_time = datetime.datetime.now(datetime.UTC).isoformat(" ")[:19]
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
        f"<call>{self.station.get('Call', '')}</call>"
        # <ops>NR9Q</ops>
        f'<class power="{power}" assisted = "{assisted}" transmitter="{xmiter}" ops="{ops}" bands="{bands}" mode="{modes}" overlay="{overlay}"></class>'
        f"<club>{self.station.get('Club', '')}</club>"
        "<soft>Not1MM</soft>"
        f"<version>{__version__}</version>"
        "<qth>"
        # <dxcccountry>K</dxcccountry>
        f"<cqzone>{self.station.get('CQZone', '')}</cqzone>"
        f"<iaruzone>{self.station.get('IARUZone', '')}</iaruzone>"
        f"<arrlsection>{self.station.get('ARRLSection', '')}</arrlsection>"
        f"<stprvoth>{self.station.get('State', '')}</stprvoth>"
        f"<grid6>{self.station.get('GridSquare', '')}</grid6>"
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
    if result and result.get("Points", 0) is not None:
        return int(result.get("Points", 0))
    return 0


def gen_adif(self, cabrillo_name: str, contest_id=""):
    """
    Creates an ADIF file of the contacts made.
    """
    now = datetime.datetime.now(tz=datetime.UTC)
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    station_callsign = self.station.get("Call", "").upper().replace("/", "-")
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
                freq_mhz = Decimal(str(contact.get("Freq", 0))) / 1000
                frequency = str(freq_mhz)
                band = get_adif_band(freq_mhz)
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
                            f"{self.contest_settings.get('SentExchange', '')} {sentnr}"
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
                print(end="\r\n", file=file_descriptor)
            self.show_message_box(f"ADIF saved to: {filename}")
    except OSError as error:
        self.show_message_box(f"Error saving ADIF file: {error}")


def gen_edi(
    self,
    cabrillo_name: str,
    contest_name: str,
    start_date: str,
    end_date: str,
    band_display: str = "",
    qso_fmt=None,
    get_points=None,
    separator: str = "=",
):
    """Generate a REG1TEST EDI contest log file.

    Parameters
    ----------
    self :
        The main window instance providing ``self.station``,
        ``self.contest_settings``, ``self.database``, and
        ``self.show_message_box``.
    cabrillo_name : str
        Short contest identifier used in the output filename
        (e.g. ``"DARC VHF"``).
    contest_name : str
        Full contest name written into the ``TName`` header field.
    start_date, end_date : str
        Contest dates in ``YYYYMMDD`` format, written to ``TDate``.
    band_display : str, optional
        Human-readable band string for ``PBand``
        (e.g. ``"144 MHz"``).  Defaults to the value from
        ``BandCategory`` passed through the standard EDI band
        table, or ``"ALL"`` if unavailable.
    qso_fmt : callable, optional
        ``f(contact, mode_code, my_grid) -> str`` returning the
        semicolon-delimited QSO record line for *contact*.
        Defaults to the standard Region-1 record using the
        ``Points`` field already stored in the database.
    get_points : callable, optional
        ``f() -> int`` returning the claimed total QSO points.
        Defaults to summing the ``Points`` column via the
        database.
    separator : str, optional
        Character placed between EDI keywords and values.
        Defaults to ``"="`` per the REG1TEST specification.

    Data sources
    -------------
    **Station** (``self.station``)::

        Call, GridSquare, Name, Street1, Street2, Zip, City,
        Country, Club, Email, STXeq, SAnte, SAntH1

    **Contest settings** (``self.contest_settings``)::

        StartDate, OperatorCategory, BandCategory, PowerCategory

    **Database** (``self.database``)::

        fetch_all_contacts_asc(), fetch_qso_count(), fetch_points()

    The default ``qso_fmt`` reads the following keys from each
    contact dict returned by ``fetch_all_contacts_asc()``:

    TS, Call, Mode, SNT, SentNr, RCV, NR, Exchange1, Points
    """

    file_encoding = "ascii"

    # ── mode string → EDI numeric code ──────────────────────
    _mode_code = {
        "SSB": 1,
        "LSB": 1,
        "USB": 1,
        "CW": 2,
        "CWL": 2,
        "CWU": 2,
        "AM": 5,
        "FM": 6,
        "RTTY": 7,
        "SSTV": 8,
        "ATV": 9,
    }

    def _edi_mode_code(mode_str):
        """Map a mode string to an EDI mode code (default 0)."""
        return _mode_code.get(str(mode_str).upper(), 0)

    # ── default QSO record formatter ────────────────────────
    def _default_qso_fmt(contact, mode_code, _my_grid):
        the_ts = contact.get("TS", "")
        date_str = the_ts[2:4] + the_ts[5:7] + the_ts[8:10]
        time_str = the_ts[11:13] + the_ts[14:16]
        try:
            sent_nr = f"{int(str(contact.get('SentNr', '0')).split()[0]):03d}"
        except (TypeError, ValueError):
            sent_nr = "000"
        try:
            rcv_nr = f"{int(contact.get('NR', 0)):03d}"
        except (TypeError, ValueError):
            rcv_nr = "000"
        return (
            f"{date_str};"
            f"{time_str};"
            f"{contact.get('Call', '')};"
            f"{mode_code};"
            f"{contact.get('SNT', '')};"
            f"{sent_nr};"
            f"{contact.get('RCV', '')};"
            f"{rcv_nr};"
            f";"
            f"{contact.get('Exchange1', '')};"
            f"{contact.get('Points', '')};"
            f"; ; ; "
        )

    if qso_fmt is None:
        qso_fmt = _default_qso_fmt

    # ── default points getter ───────────────────────────────
    if get_points is None:

        def _default_get_points():
            result = self.database.fetch_points()
            if result is not None:
                score = result.get("Points", "0")
                if score is None:
                    score = "0"
                return int(score)
            return 0

        get_points = _default_get_points

    # ── retrieve data ───────────────────────────────────────
    log = self.database.fetch_all_contacts_asc()
    number_of_qsos = len(log)
    total_points = get_points()

    # Band display: caller-provided, else derive from settings
    if not band_display:
        band_cat = (
            self.contest_settings.get("BandCategory", "")
            if self.contest_settings
            else ""
        )
        band_display = _edi_band_table(band_cat)

    # ── build filename ──────────────────────────────────────
    now = datetime.datetime.now().astimezone()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    station_call = self.station.get("Call", "").upper().replace("/", "-")
    filename = (
        str(Path.home()) + "/" + f"{station_call}_{cabrillo_name}_{date_time}.edi"
    )

    logger.debug("EDI output: %s", filename)

    try:
        with open(filename, "w", encoding=file_encoding, newline="") as fh:

            def _out(line):
                """Write one EDI line encoded to ASCII with CR LF."""
                print(
                    line.encode(file_encoding, errors="ignore").decode(),
                    end="\r\n",
                    file=fh,
                )

            # ── header section ──────────────────────────────
            _out("[REG1TEST;1]")
            _out(f"TName{separator}{contest_name}")
            _out(f"TDate{separator}{start_date};{end_date}")
            _out(f"PCall{separator}{self.station.get('Call', '')}")
            _out(f"PWWLo{separator}{self.station.get('GridSquare', '')}")
            _out(f"PExch{separator}")
            _out(
                f"PAdr1{separator}"
                f"{self.station.get('Street1', '')}, "
                f"{self.station.get('Zip', '')}  "
                f"{self.station.get('City', '')}, "
                f"{self.station.get('Country', '')}"
            )
            _out(f"PAdr2{separator}")
            _out(
                f"PSect{separator}"
                f"{self.contest_settings.get('OperatorCategory', '') if self.contest_settings else ''}"
            )
            _out(f"PBand{separator}{band_display}")
            _out(f"PClub{separator}{self.station.get('Club', '').upper()}")
            _out(f"RName{separator}{self.station.get('Name', '')}")
            _out(f"RCall{separator}{self.station.get('Call', '')}")
            _out(f"RAdr1{separator}{self.station.get('Street1', '')}")
            _out(f"RAdr2{separator}{self.station.get('Street2', '')}")
            _out(f"RPoCo{separator}{self.station.get('Zip', '')}")
            _out(f"RCity{separator}{self.station.get('City', '')}")
            _out(f"RCoun{separator}{self.station.get('Country', '')}")
            _out(f"RPhon{separator}")
            _out(f"RHBBS{separator}{self.station.get('Email', '')}")
            _out(f"MOpe1{separator}")
            _out(f"MOpe2{separator}")
            _out(f"STXEq{separator}{self.station.get('STXeq', '')}")
            _out(
                f"SPowe{separator}"
                f"{self.contest_settings.get('PowerCategory', '') if self.contest_settings else ''}"
            )
            _out(f"SRXEq{separator}")
            _out(f"SAnte{separator}{self.station.get('SAnte', '')}")
            _out(f"SAntH{separator}{self.station.get('SAntH1', '')}")

            # ── summary section ─────────────────────────────
            _out(f"CQSOs{separator}{number_of_qsos};1")
            _out(f"CQSOP{separator}{total_points}")
            _out(f"CWWLs{separator}0;0;1")
            _out(f"CWWLB{separator}0")
            _out(f"CExcs{separator}0;0;1")
            _out(f"CExcB{separator}0")
            _out(f"CDXCs{separator}0;0;1")
            _out(f"CDXCB{separator}0")
            _out(f"CToSc{separator}{total_points}")
            _out(f"CODXC{separator}")
            _out("[Remarks]")
            _out(f"[QSORecords;{number_of_qsos}]")

            # ── QSO records ─────────────────────────────────
            my_grid = self.station.get("GridSquare", "")
            for contact in log:
                mode_code = _edi_mode_code(contact.get("Mode", ""))
                _out(qso_fmt(contact, mode_code, my_grid))

        self.show_message_box(f"EDI saved to: {filename}")
    except OSError as exception:
        logger.critical("EDI: IO error: %s, writing to %s", exception, filename)
        self.show_message_box(f"Error saving EDI: {exception} {filename}")


def _edi_band_table(band_category):
    """Map a not1mm BandCategory string to an EDI ``PBand`` value."""
    return {
        "ALL": "ALL",
        "160M": "1,8 MHz",
        "80M": "3,5 MHz",
        "40M": "7 MHz",
        "20M": "14 MHz",
        "15M": "21 MHz",
        "10M": "28 MHz",
        "6M": "50 MHz",
        "4M": "70 MHz",
        "2M": "144 MHz",
        "70cm": "432 MHz",
        "23cm": "1,3 GHz",
        "2.3G": "2,3 GHz",
        "3.4G": "3,4 GHz",
        "5.7G": "5,7 GHz",
        "10G": "10 GHz",
        "24G": "24 GHz",
        "47G": "47 GHz",
        "75G": "76 GHz",
        "119G": "120 GHz",
        "142G": "144 GHz",
        "241G": "248 GHz",
    }.get(band_category, band_category or "ALL")


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
    except OSError as e:
        self.show_message_box(f"Error: {e}")
        return

    # filter out anything beyond 7-bit ASCII
    ascii_content = ""
    for b in file_content:
        if b < 128:
            ascii_content = ascii_content + chr(b)

    qsos_raw, _adif_header = adif_io.read_from_string(ascii_content)
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
                f"Date/time not found in QSO #{q_num + 1}.\nImport cancelled."
            )
            return

        if q.get("CALL"):
            this_contact["Call"] = q.get("CALL")
        else:
            logger.debug("Callsign not found in QSO #{q_num+1}")
            self.progress_dialog.close()
            self.show_message_box(
                f"Callsign not found in QSO #{q_num + 1}.\nImport cancelled."
            )
            return

        freq_mhz = None
        if q.get("FREQ"):
            freq_mhz = float(q.get("FREQ"))
        elif q.get("BAND"):
            band_str = str(q.get("BAND")).lower()
            freq_mhz = get_not1mm_band(band_str)
            if freq_mhz == 0.0:
                freq_mhz = None

        if freq_mhz is None:
            logger.debug(f"Frequency not found in QSO #{q_num + 1}")
            self.progress_dialog.close()
            self.show_message_box(...)
            return

        this_contact["Freq"] = freq_mhz * 1000.0

        # ADIF Band is in Meters (eg, "20m"), not1mm is in (float) MHz
        # 1st attempt: ADIF style like "18m"
        if band := get_not1mm_band(str(q.get("BAND")).lower()):
            this_contact["Band"] = band
        else:
            # convert the QSO frequency to a not1mm band float (0.0 when invalid)
            band_name = get_adif_band(Decimal(str(freq_mhz)))
            this_contact["Band"] = get_not1mm_band(band_name)

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
                f"Valid Mode not found in QSO #{q_num + 1}.\nImport cancelled."
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
        elif q.get("SRX_STRING"):
            this_contact["NR"] = q.get("SRX_STRING")

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
        elif q.get("STX_STRING"):
            this_contact["SentNr"] = q.get("STX_STRING")

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
    self.contest.recalculate_mults(self)  # compute Points + IsMultiplier1 first
    self.log_window.get_log()  # then refresh log display with correct data

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
