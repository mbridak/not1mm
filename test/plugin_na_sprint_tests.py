"""Tests for the NA Sprint CW/RTTY plugins."""

# pylint: disable=redefined-outer-name, protected-access

import datetime
import json
import uuid
from pathlib import Path

import pytest

import not1mm
from not1mm.lib.database import DataBase
from not1mm.plugins import na_sprint_cw, na_sprint_rtty

CTY = json.loads(
    (Path(not1mm.__file__).parent / "data" / "cty.json").read_text(encoding="utf-8")
)


def cty_lookup(callsign: str):
    """Same algorithm as MainWindow.cty_lookup."""
    callsign = callsign.upper()
    for count in reversed(range(len(callsign))):
        searchitem = callsign[: count + 1]
        result = {key: val for key, val in CTY.items() if key == searchitem}
        if not result:
            continue
        if result.get(searchitem).get("exact_match"):
            if searchitem == callsign:
                return result
            continue
        return result
    return None


class FakeLineEdit:
    """Stands in for a QLineEdit."""

    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text

    def setText(self, text):  # pylint: disable=invalid-name
        self._text = text


class Harness:
    """Just enough of MainWindow for the plugin."""

    def __init__(self, plugin, tmp_path, mycall="K0RX"):
        self.plugin = plugin
        self.contest = plugin
        self.ctyfile = CTY
        self.cty_lookup = cty_lookup
        self.database = DataBase(
            str(tmp_path / "t.db"),
            Path(not1mm.__file__).parent / "data",
            current_contest=1,
        )
        self.station = {"Call": mycall, "Name": "Dave", "State": "MN"}
        self.contest_settings = {"SentExchange": "DAVE MN"}
        self.callsign = FakeLineEdit()
        self.sent = FakeLineEdit("599")
        self.receive = FakeLineEdit("599")
        self.other_1 = FakeLineEdit()
        self.other_2 = FakeLineEdit()
        self.exch_label = FakeLineEdit()
        self.contact = {}
        self.contact_is_dupe = 0
        self.radio_state = {"vfoa": 14040000}
        self.pref = {"run_state": False}
        self.serial = 0
        self.ts = datetime.datetime(2026, 9, 13, 0, 0, 0)

    def log(self, call, exch, band="14.0", freq=14040.0, run=False):
        """Mimic MainWindow.save_contact()."""
        self.serial += 1
        self.ts += datetime.timedelta(minutes=1)
        self.callsign.setText(call)
        self.other_1.setText(str(self.serial))
        self.other_2.setText(exch)
        continent, pfx = na_sprint_cw._entity(self, call)
        dupe = self.database.exec_sql(
            "select count(*) as c from dxlog where Call = ? and Band = ? and ContestNR = 1;",
            (call, band),
        )["c"]
        self.contact_is_dupe = dupe
        self.contact = self.database.empty_contact.copy()
        self.contact.update(
            {
                "TS": self.ts.isoformat(" "),
                "Call": call,
                "Band": band,
                "Freq": freq,
                "Mode": self.plugin.mode,
                "ContestName": self.plugin.cabrillo_name,
                "ContestNR": 1,
                "StationPrefix": self.station["Call"],
                "Continent": continent,
                "CountryPrefix": pfx,
                "IsRunQSO": run,
                "ID": uuid.uuid4().hex,
            }
        )
        self.plugin.set_contact_vars(self)
        self.contact["Points"] = self.plugin.points(self)
        self.database.log_contact(self.contact)
        return dict(self.contact)


@pytest.fixture
def h(tmp_path):
    return Harness(na_sprint_cw, tmp_path)


@pytest.mark.parametrize(
    "exch, call, expected",
    [
        ("154 RICK NC", "N6TR", ("154", "RICK", "NC", "N6TR")),
        ("RICK NC 154", "N6TR", ("154", "RICK", "NC", "N6TR")),
        ("0154 RICK NC", "N6TR", ("154", "RICK", "NC", "N6TR")),
        # correction typed after a call-history prefill
        ("RICK NC 154 BOB", "N6TR", ("154", "BOB", "NC", "N6TR")),
        ("RICK NC 154 OR", "N6TR", ("154", "RICK", "OR", "N6TR")),
        ("12 TREE OR 13", "K7GM", ("13", "TREE", "OR", "K7GM")),
        # names that are also state codes
        ("5 AL TX", "W5XX", ("5", "AL", "TX", "W5XX")),
        ("5 AL", "W5XX", ("5", "", "AL", "W5XX")),
        ("5 AL AL", "W5XX", ("5", "AL", "AL", "W5XX")),
        # aliases
        ("7 JOE NF", "VO1AA", ("7", "JOE", "NL", "VO1AA")),
        ("7 JOE PQ", "VE2AA", ("7", "JOE", "QC", "VE2AA")),
        # DX
        ("33 HANS DX", "DL1AA", ("33", "HANS", "DX", "DL1AA")),
        # other NA countries
        ("9 JUAN XE", "XE1AA", ("9", "JUAN", "XE", "XE1AA")),
        ("9 JOSE KP4", "KP4AA", ("9", "JOSE", "KP4", "KP4AA")),
        ("9 PEPE CO", "CO8LY", ("9", "PEPE", "CO", "CO8LY")),
        # callsign correction in the exchange field
        ("K7GM 122 TREE OR", "K7GN", ("122", "TREE", "OR", "K7GM")),
        ("", "N6TR", ("", "", "", "N6TR")),
    ],
)
def test_split_exchange(h, exch, call, expected):
    _, pfx = na_sprint_cw._entity(h, call)
    assert na_sprint_cw.split_exchange(h, exch, call, pfx) == expected


@pytest.mark.parametrize(
    "call, sect, expected",
    [
        ("N6TR", "NC", "NC"),
        ("K7GM", "OR", "OR"),
        ("VE3AA", "ON", "ON"),
        ("VO1AA", "NL", "NL"),
        ("N6TR", "ZZ", ""),  # bad location from a W station: no mult
        ("KH6AA", "HI", "HI"),
        ("KH6AA", "KH6", "HI"),
        ("KL7AA", "AK", "AK"),
        ("KL7AA", "", "AK"),
        ("XE1AA", "XE", "C-XE"),
        ("HI8AA", "HI", "HI"),  # sent a state code: counts as sent
        ("HI8AA", "DR", "C-HI"),  # Dominican Republic, not Hawaii
        ("KP4AA", "PR", "C-KP4"),
        ("VP9AA", "VP9", "C-VP9"),
        ("OX3AA", "OX", "C-OX"),
        ("FP5AA", "FP", "C-FP"),
        ("4U1UN", "NY", "NY"),
        ("DL1AA", "DX", ""),
        ("JA1AA", "DX", ""),
    ],
)
def test_mult_key(h, call, sect, expected):
    continent, pfx = na_sprint_cw._entity(h, call)
    assert na_sprint_cw.mult_key(sect, continent, pfx) == expected


def test_scoring_and_mults(h):
    q = h.log("N6TR", "1 RICK NC")
    assert (q["Points"], q["IsMultiplier1"], q["Sect"]) == (1, 1, "NC")
    # same state, different station: no new mult
    q = h.log("W4AA", "2 BOB NC")
    assert (q["Points"], q["IsMultiplier1"]) == (1, 0)
    # same station, new band: points, but NC not a new mult (mults are per contest)
    q = h.log("N6TR", "3 RICK NC", band="7.0", freq=7040.0)
    assert (q["Points"], q["IsMultiplier1"]) == (1, 0)
    # dupe on the same band
    q = h.log("N6TR", "4 RICK NC")
    assert q["Points"] == 0
    # 15m is not a Sprint band
    q = h.log("K1AA", "5 JIM MA", band="21.0", freq=21040.0)
    assert (q["Points"], q["IsMultiplier1"]) == (0, 0)
    # DX: point for an NA station, no mult
    q = h.log("DL1AA", "6 HANS DX")
    assert (q["Points"], q["IsMultiplier1"]) == (1, 0)
    # NA country mult
    q = h.log("XE1AA", "7 JUAN XE")
    assert (q["Points"], q["IsMultiplier1"], q["Exchange1"]) == (1, 1, "C-XE")
    # 1500 MA later on a valid band is now a mult
    q = h.log("K1BB", "8 SUE MA")
    assert q["IsMultiplier1"] == 1

    assert na_sprint_cw.show_qso(h) == 8
    assert na_sprint_cw.show_mults(h) == 3  # NC, C-XE, MA
    assert na_sprint_cw.calc_score(h) == 6 * 3


def test_non_na_station_only_scores_na(tmp_path):
    h = Harness(na_sprint_cw, tmp_path, mycall="DL1ZZ")
    assert h.log("N6TR", "1 RICK NC")["Points"] == 1
    assert h.log("G3AA", "2 JOHN DX")["Points"] == 0
    assert h.log("KH6AA", "3 AKI HI")["Points"] == 1  # KH6 counts as NA


def test_recalculate_matches_live(h):
    for call, exch, band in [
        ("N6TR", "1 RICK NC", "14.0"),
        ("N6TR", "2 RICK NC", "14.0"),
        ("N6TR", "3 RICK NC", "7.0"),
        ("XE1AA", "4 JUAN XE", "7.0"),
        ("K1AA", "5 JIM MA", "21.0"),
        ("K1BB", "6 SUE MA", "3.5"),
    ]:
        h.log(call, exch, band=band)
    live = [
        (c["Call"], c["Points"], c["IsMultiplier1"], c["Exchange1"])
        for c in h.database.fetch_all_contacts_asc()
    ]
    # wipe what live logging computed and recalc from scratch
    h.database.exec_sql_commit(
        "update dxlog set Points = 0, IsMultiplier1 = 0, Exchange1 = '';"
    )
    h.log_window = None
    na_sprint_cw.recalculate_mults(h)
    recalc = [
        (c["Call"], c["Points"], c["IsMultiplier1"], c["Exchange1"])
        for c in h.database.fetch_all_contacts_asc()
    ]
    assert recalc == live
    assert na_sprint_cw.show_mults(h) == 3


def test_qsy_rule(h):
    na_sprint_cw._after_log(h, was_run=True, freq_khz=14040.0)
    h.radio_state["vfoa"] = 14040500  # moved only 0.5 kHz
    assert na_sprint_cw.qsy_needed(h)
    h.radio_state["vfoa"] = 14041000  # moved 1 kHz
    assert not na_sprint_cw.qsy_needed(h)
    # an S&P QSO means we now own that frequency
    na_sprint_cw._after_log(h, was_run=False, freq_khz=14041.0)
    h.radio_state["vfoa"] = 14041000
    assert not na_sprint_cw.qsy_needed(h)


def test_cabrillo(h, tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    h.log("N6TR", "154 RICK NC", freq=14041.7)
    h.log("DL1AA", "33 HANS DX", band="7.0", freq=7031.2)
    h.database.get_ops = lambda: []
    messages = []
    h.show_message_box = messages.append
    na_sprint_cw.cabrillo(h, "ascii")
    log = next(tmp_path.glob("K0RX_NA-SPRINT-CW_*.log")).read_bytes().decode()
    assert "CONTEST: NA-SPRINT-CW\r\n" in log
    assert "LOCATION: MN\r\n" in log
    assert "CATEGORY-MODE: CW\r\n" in log
    assert (
        "QSO: 14042 CW 2026-09-13 0001 K0RX             1 DAVE       MN  "
        "N6TR           154 RICK       NC\r\n"
    ) in log
    assert (
        "QSO:  7031 CW 2026-09-13 0002 K0RX             2 DAVE       MN  "
        "DL1AA           33 HANS       DX\r\n"
    ) in log


def test_rtty_identity(tmp_path):
    h = Harness(na_sprint_rtty, tmp_path)
    assert na_sprint_rtty.cabrillo_name == "NA-SPRINT-RTTY"
    assert na_sprint_rtty.mode == "RTTY"
    assert na_sprint_rtty.dupe_type == 2
    q = h.log("N6TR", "1 RICK NC")
    assert (q["Points"], q["IsMultiplier1"]) == (1, 1)


def test_rtty_udp_adif(tmp_path):
    h = Harness(na_sprint_rtty, tmp_path)
    saved = {}

    def save_contact():
        na_sprint_rtty.set_contact_vars(h)
        saved.update(h.contact)

    h.save_contact = save_contact
    na_sprint_rtty.set_self(h)
    na_sprint_rtty.ft8_handler(
        {
            "CALL": "N6TR",
            "MODE": "RTTY",
            "FREQ": "14.085000",
            "NAME": "RICK",
            "STATE": "NC",
            "SRX": "154",
            "STX": "12",
        }
    )
    assert (saved["Call"], saved["NR"], saved["Name"], saved["Sect"]) == (
        "N6TR",
        "154",
        "RICK",
        "NC",
    )
    assert saved["SentNr"] == "12"
    assert saved["Band"] == "14.0"
