"""Common function(s) for all contest plugins"""

import datetime
import re
import uuid
import adif_io

from decimal import Decimal
from pathlib import Path
from not1mm.lib.ham_utility import get_adif_band, get_not1mm_band
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
    try:
        qsos_raw, adif_header = adif_io.read_from_file(filename)
        qsos_sorted = sorted(qsos_raw, key = adif_io.time_on)
    except FileNotFoundError as err:
        self.show_message_box(f"{err}")    
        return 
    num_qsos = len(qsos_sorted) 
    self.show_message_box(f"Found {num_qsos} QSOs in\n{filename}")

    # Read all records from ADIF file and map them to not1mm fields.
    # If a mandatory field is missing, abort mapping and skip import.
    q_num = 0
    contacts = [] 
    dupes = 0 
    
    for q in qsos_sorted:
        this_contact = self.database.get_empty()
        
        try:
            temp = adif_io.time_on(q)
            this_contact["TS"] = temp.strftime("%Y-%m-%d %H:%M:%S")
        except KeyError:
            self.show_message_box(f"Date/time not found in QSO #{q_num+1}.\nImport cancelled.")
            return
            
        try:
            this_contact["Call"] = q["CALL"]
        except KeyError:
            self.show_message_box(f"Callsign not found in QSO #{q_num+1}.\nImport cancelled.")
            return
            
        # ADIF freq is in MHz, not1mm is in kHz
        try:
            this_contact["Freq"] = float(q["FREQ"]) * 1000.0 
        except (ValueError, TypeError, KeyError):
            self.show_message_box(f"Valid Frequency not found in QSO #{q_num+1}.\nImport cancelled.")
            return    
            
        this_contact["QSXFreq"] = ""
        
        try:
            temp = q["MODE"]
        except KeyError:
            temp = ""   
        try:
            temp2 = q["SUBMODE"]
        except KeyError:
            temp2 = ""   
        if temp:
            this_contact["Mode"] = temp
        elif temp2:
            this_contact["Mode"] = temp2
        else:
            self.show_message_box(f"Valid Mode not found in QSO #{q_num+1}.\nImport cancelled.")
            return
                
        this_contact["ContestName"] = self.contest.name
        
        try:
            this_contact["SNT"] = q["RST_SENT"]
        except KeyError:
            this_contact["SNT"] = ""
            
        try:
            this_contact["RCV"] = q["RST_RCVD"]
        except KeyError:
            this_contact["RCV"] = ""
            
        try:
            this_contact["CountryPrefix"] = q["PFX"]
        except KeyError:
            this_contact["CountryPrefix"] = ""
            
        this_contact["StationPrefix"] = ""
        this_contact["QTH"] = ""
        
        try:
            this_contact["Name"] = q["NAME"]
        except KeyError:
            this_contact["Name"] = ""
            
        try:        
            this_contact["Comment"] = q["COMMENT"]
        except KeyError:
            this_contact["Comment"] = ""
                
        this_contact["NR"] = 0
        
        try:
            this_contact["Sect"] = q["ARRL_SECT"]
        except KeyError:
            this_contact["Sect"] = ""
            
        this_contact["Prec"] = ""
        this_contact["CK"] = 0
        this_contact["ZN"] = 0
        
        try: 
            this_contact["SentNr"] = q["SENTNR"]
        except KeyError:
            this_contact["SentNr"] = ""

        try:
            this_contact["Points"] = q["APP_N1MM_POINTS"]
        except KeyError:
            this_contact["Points"] = ""

        try:
            this_contact["IsMultiplier1"] = q["APP_N1MM_MULT1"]
        except KeyError:    
            this_contact["IsMultiplier1"] = 0

        try:
            this_contact["IsMultiplier2"] = q["APP_N1MM_MULT2"]
        except KeyError:        
            this_contact["IsMultiplier2"] = 0
            
        this_contact["Power"] = 0
        
        # ADIF Band is in Meters (eg, "20m"), not1mm is in MHz
        try:
            temp = q["BAND"]
            temp = temp.lower()
            this_contact["Band"] = get_not1mm_band(temp)
        except KeyError:
            self.show_message_box(f"Valid Band not found in QSO #{q_num+1}.\nImport cancelled.")
            return

        try:
            this_contact["WPXPrefix"] = q["WPXPREFIX"]
        except KeyError:
            this_contact["WPXPrefix"] = ""
            
        try:
            temp = q["CLASS"]
        except KeyError:
            temp = ""
        try:                            
            temp2 = q["EXCHANGE1"]
        except KeyError:
            temp2 = ""
        try:
            temp3 = q["APP_N1MM_EXCHANGE1"]
        except KeyError:
            temp3 = ""
        this_contact["Exchange1"] = temp + temp2 + temp3
            
        this_contact["RadioNR"] = ""
        this_contact["ContestNR"] = self.pref.get("contest", "0")

        try:
            this_contact["isMultiplier3"] = q["APP_N1MM_MULT3"]
        except KeyError:
            this_contact["isMultiplier3"] = 0
            
        this_contact["MiscText"] = ""
        this_contact["IsRunQSO"] = ""
        this_contact["ContactType"] = ""

        try:
            this_contact["Run1Run2"] = q["APP_N1MM_RUN1RUN2"]
        except KeyError:    
            this_contact["Run1Run2"] = ""
        
        this_contact["GridSquare"] = ""
        
        try:
            temp = q["OPERATOR"]
        except KeyError:
            temp = ""
        if temp:
            this_contact["Operator"] = temp
        else:    
            try:
                temp = q["STATION_CALLSIGN"]
            except KeyError:
                temp = ""
            if temp:
                this_contact["Operator"] = temp
            else:
                this_contact["Operator"] = ""

        try:
            this_contact["Continent"] = q["APP_N1MM_CONTINENT"]
        except KeyError:    
            this_contact["Continent"] = ""
            
        this_contact["RoverLocation"] = ""
        this_contact["RadioInterfaced"] = ""
        this_contact["NetworkedCompNr"] = 1

        try:
            this_contact["NetBiosName"] = q["APP_N1MM_NETBIOSNAME"]
        except KeyError:
            this_contact["NetBiosName"] = ""

        this_contact["IsOriginal"] = 0
        this_contact["ID"] = uuid.uuid4().hex
        this_contact["CLAIMEDQSO"] = 1
        
       # is this record a dupe?
        theTS = this_contact["TS"]
        thecall = this_contact["Call"]
        temp = self.database.exec_sql(f"select count(*) as isdupe from dxlog where TS = '{theTS}' and call = '{thecall}'")
        if temp["isdupe"] > 0:
            dupes = dupes + 1
        else:
            contacts.append(this_contact.copy())
        this_contact.clear()
        q_num = q_num + 1
    
    # All ADIF records have now been mapped.
    if dupes > 0:
        self.show_message_box(f"NOTE: Found {dupes} duplicate records, which will not be saved.")
    saves = 0 
    for my_contact in contacts:
        self.database.log_contact(my_contact) 
        saves = saves + 1 
    if saves > 0:
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
    
    self.show_message_box(f"Saved {saves} ADIF records to this contest.")
        
    return 
