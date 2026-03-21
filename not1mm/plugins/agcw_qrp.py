# coded and tested by Michael Hartje, DK5HH
# Version 20260318

"""
AGCW qrp, CW
Status:	Active
Member Focus:
Participation:	Worldwide
Awards:	Worldwide
Mode:	CW
Bands:
        80 m (3.510 – 3.560 kHz)
        40 m (7.010 – 7.040 kHz)
        20 m (14.000 – 14.060 kHz)
        15 m (21.000 – 21.070 kHz)
        10 m (28.000 – 28.070 kHz)
Classes:	VLP: Very Low Power = bis 1 W Output
            QRP: klassisch QRP = bis 5 W Output
            MP: moderate Power = bis 25 W Output
            QRO: über 25 W Output

Exchange:   RST+ fortlaufende 3-stellige QSO-Nummer (ab 001) Klasse AGCW-Nummer.
            Beispiel: 579 001 QRP 1537
            Nichtmitglieder geben statt der AGCW-Mitgliedsnummer “NM” für “No Member”.
            Beispiel: 599 027 MP NMember: RST + Serial No + / Mitgliedsnummer
            non-Member: RST + Serial No.

Work stations:	Once per band

QSO Points:	QRO <–> QRO: 0 Points
            QRO <–> QRP, MP, VLP: 2 Points
            MP <–> MP, QRP, VLP: 2 Points
            QRP <–> QRP, VLP: 3 Points
            VLP <–> VLP: 3 Points

Multipliers:	QSO with Member  once per band

Score Calculation:	Total score = total QSO points x total mults

Cabrillo name:	AGCW-QRP
Cabrillo name aliases:	AGCW-QRP

1. Objective	The AGCW-DL invites all radio amateurs to participate in the annual QRP CONTEST. The QRP CONTEST is to arouse and to promote the interest in all aspects of low power amateur radio communication. QRO stations who want to learn about these activities by contacting QRP stations are therefore also invited. They will be counted in a separate category.
2. Dates	Annually on the second Saturday in March from 1400 to 2000 UTC.
3. Bands	80m (3.510-3.560 kHz), 40m, 20m (14.000-14.060 kHz), 15m, 10m. The IARU Region 1 band plan must be adhered to!
4. Categories	VLP: Very Low Power = up to 1 W output
QRP: classic QRP = up to 5 W output
MP: moderate Power = up to 25 W output
QRO: more than 25 W output

In the contest-dialog set PowerCategory to High, Low or QRP but set exchange string for the
exchange text to the  (VLP, QRP, MD, QRO)


5. Operation

Only CW (A1A). Only single OP. Only one TX and RX or TRX is allowed to be operated simultaneously.  Each station may be worked once per band. The use of decoders or reader software is not allowed.

    CALL: CQ QRP TEST
    EXCHANGE:
    RST report plus a sequential 3-digit serial number (starting at 001) followed by category and AGCW-Membership-Number.  Example:599 003 qrp 1234
    Non-members have to send “NM” instead of the membership number. Example: 599 027 MP NM

6. Scoring

    QSO POINTS:
    QRO <–> QRO: 0 points
    QRO <–> QRP, MP, VLP: 2 points
    MP  <–> MP, QRP, VLP: 2 points
    QRP <–> QRP, VLP: 3 points
    VLP <–> VLP: 3 points
    MULTIPLIERS: Each contact with a member of AGCW is worth one multiplier per band.
    TOTAL SCORE: Sum of the QSO points of all bands multiplied with the sum of all multiplier points of all bands.
    Dupes do not count.


7. Awards	Participants can get their own certificate from our website a few weeks after the contest has finished.
At once the results are calculated participants get noticed thereof.

8. Log-Submission



Even short logs are welcome! Final results will be published later.

    LOGS: Please use only Logs in Cabrillo v2 or v3  format. The log should be *uploaded* (URL below) with the following file names: CALL.CBR (e.g. ON3ABC.CBR)
    Participants are requested to make themselves familiar with the Cabrillo specifications beforehand.



    Loglines (QSO-data) within the files must contain sets of fields strictly in this order:

    1. Frequency
    2. Mode (always CW)
    3. Date
    4. Time
    5. Own Call
    6. RST sent
    7. Exchange sent
    8. Other station’s call sign
    9. RST received
    10. Exchange received.

    RST and Exchange , e.g. 599 001 QRP 1234 or
    599 003 VLP NM

    A logging program was provided by ArComm and can be downloaded as freeware here:
    http://www.qslonline.de/hk/eigen/kontest.htm#hamagcwqrp
    Log Submission
    New from 2023: Submission exclusively via web upload on the page
    https://contest.agcw.de/qrpc/


    DEADLINE: Upload no later than March, 31.

Checklogs are welcome, also comments of the participants.
Publication of the claimed scores will be announced promptly after the deadline.
"""

import datetime
import logging
import platform
import re

from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, imp_adif, get_points, online_score_xml

from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "# pwr_class MemberNr"
SOAPBOX_HINT = """
Power classes are {VLP, QRP, MP, QRO}
MemberNr is AGCW-MemberNr or NM for Non Member.

For the Run exchange macro I’d put ’{SNT} # {EXCH}’"""


name = "AGCW QRP"
cabrillo_name = "AGCW-QRP"
mode = "CW"  # CW SSB BOTH RTTY

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Mode",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
    "M1",
    "M2",
    "PTS",
]

advance_on_space = [True, True, True, True, False]

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
    self.other_label.setText("Sent")
    self.other_1.setAccessibleName("Sent")
    self.exch_label.setText("SN Pwr MbrNr")
    self.other_2.setAccessibleName("Serial Number Power Class Member Number")


def reset_label(self):
    """reset label after field cleared"""


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.other_1,
        self.sent: self.other_1,
        self.receive: self.other_1,
        self.other_1: self.other_2,
        #        self.other_2: self.other_3,
        self.other_2: self.callsign,
    }


def set_tab_prev(self):
    """Set TAB Advances"""
    self.tab_prev = {
        self.callsign: self.other_2,
        self.sent: self.callsign,
        self.receive: self.callsign,
        self.other_1: self.callsign,
        self.other_2: self.other_1,
        #        self.other_3: self_other_2
    }


def set_contact_vars(self):
    """
    prepare both multipliers even when only 0ne is used
    """
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.other_1.text().upper() + self.contest_settings.get(
        "SentExchange", "xxx xxx"
    ).strip("#")
    self.contact["NR"] = self.other_2.text().upper().replace(" ", "/")

    self.contact["IsMultiplier1"] = 0
    self.contact["IsMultiplier2"] = 0

    band = self.contact.get("Band", "")

    if len(self.contact["NR"]) > 0:
        r_number, pwr_class, member = received_fields(self, self.contact["NR"])
        if member.isdigit():
            query = (
                f"select count(*) as member_count from dxlog where 1=1 "
                f"and Band = '{band}' "
                f"and ContestNR = {self.pref.get('contest', '1')};"
            )
            result = self.database.exec_sql(query)
            count = int(result.get("member_count", 0))
            if count == 0:
                self.contact["IsMultiplier2"] = 1
            else:
                self.contact["IsMultiplier2"] = 0


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""
    sent_sxchange_setting = self.contest_settings.get("SentExchange", "")
    if (len(sent_sxchange_setting) > 0) and (sent_sxchange_setting.find("#") >= 0):
        if self.current_sn is not None:
            serial_nr = str(self.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(self.other_1.text()) == 0:
            self.other_1.setText(serial_nr)
    else:
        self.other_1.setText(sent_sxchange_setting)


def received_fields(self, r_nr):
    """
    split the "received field" 003/VLP/1234
    """
    hs = r_nr.upper().replace("/", "")
    if len(hs) > 3:  # there could be a valid message inside
        pwr_class = re.findall("[A-Z]+[OP]", hs)[0]
        hr = hs.split(pwr_class)
        member = hr[1]
        r_number = hr[0]
    else:
        member = "NM"
        pwr_class = "QRO"
        r_number = "001"
    return r_number, pwr_class, member


def points(self):
    """
    from contest rules:
    QSO Points:
            QRO <–> QRO: 0 Points

            QRO <–> QRP, MP, VLP: 2 Points

            MP <–> MP, QRP, VLP: 2 Points

            QRP <–> QRP, VLP: 3 Points

            VLP <–> VLP: 3 Punkte1 point per QSO

    """
    # The Dialog offers QRP, Low, High for the powercategory
    # so we code it
    #    VLP and QRP will be coded as QRP,
    #    MP will be coded Low
    #    QRO will be coded as High

    mypowerclass = self.contest_settings.get("PowerCategory")

    if self.contact_is_dupe > 0:
        return 0
    pts = 2  # for qrp stns
    if len(self.contact["NR"]) > 0:
        r_number, pwr_class, member = received_fields(self, self.contact["NR"])
        pt_2 = {"QRO", "MP"}
        pt_3 = {"QRP", "VLP"}

        if pwr_class in pt_2:
            pts = 2
        if pwr_class in pt_3:
            pts = 3

        self.contact["NR"] = r_number + "/" + pwr_class + "/" + member
    # if both station QRO than pts=0
    if mypowerclass == "High" and pwr_class == QRO:
        pts = 0
    return pts


def show_mults(self, rtc=None):
    """Return display string for mults"""
    one = int(self.database.fetch_mult_count(1).get("count", 0))
    two = int(self.database.fetch_mult_count(2).get("count", 0))
    if rtc is not None:
        return (two, one)

    return one + two


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


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""

    all_contacts = self.database.fetch_all_contacts_asc()
    for contact in all_contacts:

        contact["IsMultiplier1"] = 0
        contact["IsMultiplier2"] = 0

        time_stamp = contact.get("TS", "")
        R_NR = contact.get("NR", "")
        dxcc = contact.get("CountryPrefix", "")
        band = contact.get("Band", "")
        r_nr, pwr_class, member = received_fields(self, R_NR)
        # print(r_nr, " . ", pwr_class, " . ",member)
        sumnr = r_nr + "/" + pwr_class + "/" + member
        if (member != "NM") and member.isdigit():
            query = (
                f"select count(*) as member_count from dxlog where  TS < '{time_stamp}' "
                f"and NR = '{sumnr}'"
                f"and Band = '{band}' "
                f"and ContestNR = {self.pref.get('contest', '1')};"
            )
            result = self.database.exec_sql(query)
            count = int(result.get("member_count", 0))
            if count == 0:
                contact["IsMultiplier1"] = 1

        # use the following code for other agcw-contests e.g happy new year contest
        """if dxcc:
            query = (
                f"select count(*) as dxcc_count from dxlog where TS < '{time_stamp}' "
                f"and CountryPrefix = '{dxcc}' "
                f"and Band = '{band}' "
                f"and ContestNR = {self.pref.get('contest', '1')};"
            )
            result = self.database.exec_sql(query)
            if not result.get("dxcc_count", ""):
                contact["IsMultiplier2"] = 1
        """
        self.database.change_contact(contact)
    cmd = {}
    cmd["cmd"] = "UPDATELOG"
    if self.log_window:
        self.log_window.msg_from_main(cmd)


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "AGCW-QRP")


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """"""
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def cabrillo(self, file_encoding):
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
            if self.contest_settings.get("Soapbox") != SOAPBOX_HINT:
                for l in self.contest_settings.get("Soapbox", "").splitlines():
                    output_cabrillo_line(
                        f"SOAPBOX: {l}",
                        "\r\n",
                        file_descriptor,
                        file_encoding,
                    )

            for contact in log:
                the_date_and_time = contact.get("TS", "")
                themode = contact.get("Mode", "")
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
                    f"{str(contact.get('NR', '')).ljust(6).replace('/',' ')}",
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

    # print(f"checking esm {self.current_widget=} {with_enter=} {self.pref.get("run_state")=}")

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

        elif self.current_widget == "other_2":
            if self.other_2.text() == "":
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

        elif self.current_widget == "other_2":
            if self.other_2.text() == "":
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


def get_mults(self):
    """Get mults for RTC XML"""
    mults = {}
    mults["country"], mults["state"] = show_mults(self, rtc=True)
    return mults


def just_points(self):
    """Get points for RTC XML"""
    return get_points(self)


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
