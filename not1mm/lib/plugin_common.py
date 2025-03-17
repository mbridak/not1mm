"""Common function(s) for all contest plugins"""

import datetime
from decimal import Decimal
from pathlib import Path
from not1mm.lib.ham_utility import get_adif_band
from not1mm.lib.version import __version__


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
            print("<ADIF_VER:5>2.2.0", end="\r\n", file=file_descriptor)
            print("<EOH>", end="\r\n", file=file_descriptor)
            for contact in log:
                hiscall = contact.get("Call", "")
                hisname = contact.get("Name", "")
                the_date_and_time = contact.get("TS", "")
                themode = contact.get("Mode", "")
                if themode in ("CWR", "CW-R"):
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
                    if cabrillo_name in ("WFD", "ARRL-FD"):
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
                    elif cabrillo_name in ("WFD", "ARRL-FD"):
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
                    if len(grid) > 1:
                        print(
                            f"<GRIDSQUARE:{len(grid)}>{grid}",
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
