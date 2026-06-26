"""TA VHF UHF Contest"""

import logging
from not1mm.lib.ham_utility import distance
from not1mm.lib.plugin_common import gen_adif, get_points
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "# + 6char grid"

name = "TA VHF UHF"
mode = "BOTH"
cabrillo_name = "TA-VHF-UHF"

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
    "Exchange1",
    "PTS",
]

advance_on_space = [True, True, True, True, False]
dupe_type = 3


def init_contest(self):
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_2


def reset_label(self):
    pass


def predupe(self):
    pass


def interface(self):
    self.field1.show()  # callsign
    self.field2.show()  # sent RST
    self.field3.show()  # receive RST
    self.field4.show()  # exchange field

    self.snt_label.setText("SNT")
    self.other_label.setText("SNTNR")
    self.exch_label.setText("RCV NR + GRID")

    self.sent.setText("59")
    self.receive.setText("59")

    self.sent.setReadOnly(True)
    self.receive.setReadOnly(True)


def set_tab_next(self):
    self.tab_next = {
        self.callsign: self.sent,
        self.sent: self.receive,
        self.receive: self.other_1,
        self.other_1: self.other_2,
        self.other_2: self.callsign,
    }


def set_tab_prev(self):
    self.tab_prev = {
        self.callsign: self.other_2,
        self.sent: self.callsign,
        self.receive: self.sent,
        self.other_1: self.receive,
        self.other_2: self.other_1,
    }


def parse_exchange(self):
    exchange = self.other_2.text().upper().split()

    sn = ""
    grid = ""

    for t in exchange:
        if t.isdigit() and sn == "":
            sn = t
        elif len(t) == 6 and t.isalnum():
            grid = t

    return sn, grid


def set_contact_vars(self):
    sn, grid = parse_exchange(self)

    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()

    self.contact["NR"] = sn
    self.contact["Exchange1"] = grid

    self.contact["SentNr"] = self.other_1.text()

    try:
        next_sn = int(self.current_sn) + 1
        self.other_1.setText(str(next_sn).zfill(3))
    except:
        pass


def prefill(self):
    serial_nr = str(self.current_sn).zfill(3)

    if self.other_1.text() == "":
        self.other_1.setText(serial_nr)


def points(self):
    if self.contact_is_dupe > 0:
        return 0

    band = self.contact.get("Band", "")
    their_grid = self.contact.get("Exchange1", "")

    km = distance(self.station.get("GridSquare", ""), their_grid)

    mult = {
        "50": 1,
        "144": 2,
        "432": 3,
    }.get(str(band), 1)

    return max(1, int(km * mult))


def show_mults(self, rtc=None):
    return 0


def show_qso(self):
    result = self.database.fetch_qso_count()
    return int(result.get("qsos", 0)) if result else 0


def calc_score(self):
    result = self.database.fetch_points()
    if result:
        return int(result.get("Points", 0) or 0)
    return 0


def adif(self):
    gen_adif(self, cabrillo_name)


def edi(self, parent=None):
    from pathlib import Path
    import datetime
    from not1mm.lib.ham_utility import distance
    import logging

    logger = logging.getLogger(__name__)

    def get_station_field(*keys, default=""):
        for key in keys:
            val = self.station.get(key)
            if val:
                return val
        return default

    log = self.database.fetch_all_contacts_asc()
    if not log:
        logger.info("No QSOs to export")
        return

    my_call = get_station_field("Call", "Callsign", "MyCall", default="MYCALL")
    my_grid = get_station_field("GridSquare", "Grid", default="AA00AA")
    operator_name = get_station_field(
        "OperatorName", "Operator", "Name", default="Operator"
    )
    address = get_station_field("Address", "Adr1", default="")
    city = get_station_field("City", "Locality", default="")
    country = get_station_field("Country", "CountryName", default="Turkey")
    email = get_station_field("Email", "eMail", default="")
    contest_name = "TA 50_144_430 Contest"

    timestamps = []
    for q in log:
        ts = q.get("Timestamp", "")
        if ts:
            try:
                dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                timestamps.append(dt)
            except:
                pass
    if timestamps:
        start_date = min(timestamps).strftime("%Y%m%d")
        end_date = max(timestamps).strftime("%Y%m%d")
    else:
        start_date = datetime.datetime.now().strftime("%Y%m%d")
        end_date = start_date

    date_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = Path.home() / f"{my_call}_{cabrillo_name}_{date_time}.edi"

    bands = {}
    for q in log:
        band = q.get("Band", "")
        bands.setdefault(band, []).append(q)

    output_lines = []

    for band, band_qsos in bands.items():
        band_qsos.sort(key=lambda x: x.get("Timestamp", ""))
        band_display = f"{int(float(band))} MHz"
        band_code = "6"

        header = [
            "[REG1TEST;1]",
            f"TName={contest_name}",
            f"TDate={start_date};{end_date}",
            f"PCall={my_call}",
            f"PWWLo={my_grid}",
            "PExch=001",
            f"PAdr1={address}",
            "PAdr2=",
            "PSect=SINGLE-OP",
            f"PBand={band_display}",
            "PClub=",
            f"RName={operator_name}",
            f"RCall={my_call}",
            f"RAdr1={address}",
            "RAdr2=",
            "RPoCo=",
            f"RCity={city}",
            f"RCoun={country}",
            "RPhon=",
            f"RHBBS={email}",
            "MOpe1=",
            "MOpe2=",
            "STXEq=",
            "SPowe=",
            "SRXEq=",
            "SAnte=",
            "SAntH=;",
        ]

        total_qsos = len(band_qsos)
        total_points = 0
        dx_list = []

        for q in band_qsos:
            grid = q.get("Exchange1", "")
            if grid and len(grid) >= 4:
                dist = distance(my_grid, grid)
            else:
                dist = 0
            mult = {"50": 1, "144": 2, "432": 3}.get(str(band), 1)
            pts = max(1, int(dist * mult))
            total_points += pts
            if dist > 500:
                dx_list.append(f"{q.get('Call', '')};{grid};{int(dist)}")

        summary = [
            f"CQSOs={total_qsos};1",
            f"CQSOP={total_points}",
            "CWWLs=0;0;1",
            "CWWLB=0",
            "CExcs=0;0;1",
            "CExcB=0",
            f"CDXCs={len(dx_list)};0;1",
            "CDXCB=0",
            f"CToSc={total_points}",
            f"CODXC={';;'.join(dx_list)}",
            "[Remarks]",
            "",
            f"[QSORecords;{total_qsos}]",
        ]

        qso_lines = []
        for q in band_qsos:
            ts = q.get("Timestamp", "")
            try:
                dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                date_str = dt.strftime("%y%m%d")
                time_str = dt.strftime("%H%M")
            except:
                date_str = start_date[-6:]
                time_str = "0000"

            call = q.get("Call", "")
            sent_rst = q.get("Sent", "59")
            sent_nr = str(int(q.get("SentNr", "001"))).zfill(3)
            rcv_rst = q.get("Rcv", "59")
            rcv_nr = str(int(q.get("RcvNr", "001"))).zfill(3)
            grid = q.get("Exchange1", "")
            if grid and len(grid) >= 4:
                dist = int(distance(my_grid, grid))
            else:
                dist = 0

            line = f"{date_str};{time_str};{call};{band_code};{sent_rst};{sent_nr};{rcv_rst};{rcv_nr};;{grid};{dist};;;;"
            qso_lines.append(line)

        output_lines.extend(header)
        output_lines.extend(summary)
        output_lines.extend(qso_lines)

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    logger.info(f"EDI saved to {filename}")


def recalculate_mults(self):
    pass
