"""IARU Region 1 Field Day: the portable scoring, the country multiplier and
the QSO line.

Reference:
  https://www.darc.de/der-club/referate/conteste/iaru-region-1-fieldday/en/
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from contest_harness import ContestHarness, DummyProgress, discover_cases

from not1mm.lib import plugin_common
from not1mm.lib.contest import load_contest
from not1mm.plugins.iaru_fieldday_r1_cw import Contest

PLUGINS = ["iaru_fieldday_r1_cw", "iaru_fieldday_r1_ssb"]


class Field:
    def __init__(self, value: str):
        self.value = value

    def text(self):
        return self.value


REPO = Path(__file__).resolve().parents[1]


def _database():
    from not1mm.lib.database import DataBase

    return DataBase(":memory:", REPO / "not1mm/data", current_contest=5)


def _ctx(my_call, his_call, continent="EU", dupe=0):
    contact = {"Call": his_call, "Continent": continent}
    return SimpleNamespace(
        contact_is_dupe=dupe,
        contact=contact,
        station={"Call": my_call},
    )


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "my_call,his_call,continent,expected",
    [
        # fixed to fixed is nothing, on either side
        ("DL1ABC", "DL2ABC", "EU", 0),
        ("DL1ABC", "K6GTE", "NA", 0),
        # a fixed entrant scores the portable stations
        ("DL1ABC", "DL3ABC/P", "EU", 4),
        ("DL1ABC", "W1AW/P", "NA", 6),
        # a portable entrant scores everyone
        ("DL2ABC/P", "DL2ABC", "EU", 2),
        ("DL2ABC/P", "K6GTE", "NA", 3),
        ("DL2ABC/P", "DL3ABC/P", "EU", 4),
        ("DL2ABC/P", "W1AW/P", "NA", 6),
        # "/m", "/mm" and "/am" are portable too
        ("DL1ABC", "DL3ABC/M", "EU", 4),
        ("DL1ABC", "DL3ABC/MM", "EU", 4),
        ("DL1ABC", "DL3ABC/AM", "EU", 4),
        # no continent: nothing to score
        ("DL1ABC", "DL3ABC/P", "", 0),
    ],
)
def test_points(plugin, my_call, his_call, continent, expected):
    assert load_contest(plugin, _ctx(my_call, his_call, continent)).points() == expected


@pytest.mark.parametrize("plugin", PLUGINS)
def test_a_duplicate_scores_nothing(plugin):
    assert load_contest(plugin, _ctx("DL1ABC", "DL3ABC/P", "EU", dupe=1)).points() == 0


@pytest.mark.parametrize(
    "plugin,name,cabrillo,mode",
    [
        ("iaru_fieldday_r1_cw", "IARU FIELDDAY R1 DARC CW", "FD CW", "CW"),
        ("iaru_fieldday_r1_ssb", "IARU FIELDDAY R1 DARC SSB", "FD SSB", "SSB"),
    ],
)
def test_class_metadata(plugin, name, cabrillo, mode):
    contest = load_contest(plugin, SimpleNamespace())
    assert contest.DisplayName == name
    assert contest.CabrilloName == cabrillo
    assert contest.Mode == mode
    # once per band
    assert contest.DupeType == 2
    # one WAE country / DXCC entity per band
    assert contest.NumMults == 1
    assert contest.IsMult1Per == 1
    assert contest._mult_columns(1) == ("Band",)
    assert "Mode" in contest.LogInfo
    assert contest.LogInfo[-2:] == ["M1", "PTS"]


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "contact,expected",
    [
        ({"CountryPrefix": "DL"}, "DL"),
        ({"CountryPrefix": "K"}, "K"),
        ({"CountryPrefix": ""}, ""),
    ],
)
def test_the_country_is_the_multiplier_key(plugin, contact, expected):
    assert load_contest(plugin, SimpleNamespace()).mult_value(1, contact) == expected


@pytest.mark.parametrize("plugin", PLUGINS)
def test_a_contact_without_a_country_is_not_counted(plugin):
    """An imported log need not carry COUNTRYPREFIX; the empty is no mult."""
    contest = load_contest(plugin, SimpleNamespace())
    assert contest.mult_sql(1) == "NULLIF(CountryPrefix, '')"
    assert contest._mult_columns(1) == ("Band",)


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "received_serial, expected",
    [
        pytest.param(0, "000", id="integer-zero"),
        pytest.param("0", "000", id="string-zero"),
        pytest.param("00", "00", id="string-zero"),
        pytest.param(" 0 ", "000", id="zero-with-whitespace"),
        pytest.param("000", "000", id="padded-zero"),
        pytest.param(None, "", id="none"),
        pytest.param("", "", id="empty"),
        pytest.param("   ", "", id="whitespace-only"),
        pytest.param(23, "23", id="integer-serial"),
        pytest.param("007", "007", id="leading-zeros"),
        pytest.param(" 23 ", "23", id="serial-with-whitespace"),
    ],
)
def test_cabrillo_formats_received_serials(plugin, received_serial, expected):
    report = "599" if plugin.endswith("cw") else "59"
    contact = {
        "TS": "2026-09-05 16:00:00",
        "Freq": 14000,
        "Mode": "CW" if plugin.endswith("cw") else "USB",
        "StationPrefix": "DM1ABC/P",
        "SNT": report,
        "SentNr": 0,
        "Call": "DL1AAA",
        "RCV": report,
        "NR": received_serial,
    }
    line = load_contest(plugin, SimpleNamespace()).cabrillo_qso_line(contact)
    assert line[-6:] == expected.ljust(6)
    # Placeholder formatting must not change the sent serial.
    assert line.split()[7] == "0"


def _insert(database, row_id, timestamp, call, prefix, band):
    database.exec_sql_commit(
        "INSERT INTO dxlog (ID, TS, Call, CountryPrefix, Band, ContestNR, Run1Run2, Continent) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (row_id, timestamp, call, prefix, band, 5, 0, "EU"),
    )


@pytest.mark.parametrize("plugin", PLUGINS)
def test_new_multiplier_is_scoped_to_band(plugin):
    database = _database()
    try:
        app = SimpleNamespace(
            contact={"CountryPrefix": "DL", "Band": 14.0},
            sent=Field("59"),
            receive=Field("59"),
            other_1=Field("001"),
            other_2=Field("001"),
            database=database,
        )
        contest = load_contest(plugin, app)

        contest.set_contact_vars()
        assert app.contact["IsMultiplier1"] == 1

        _insert(database, "ID0", "2026-09-01 16:00:00", "DL1AAA", "DL", 7.0)
        contest.set_contact_vars()
        assert app.contact["IsMultiplier1"] == 1

        _insert(database, "ID1", "2026-09-02 16:00:00", "ON1AAB", "ON", 7.0)
        contest.set_contact_vars()
        assert app.contact["IsMultiplier1"] == 1

        _insert(database, "ID2", "2026-09-03 16:00:00", "ON1AAC", "ON", 14.0)
        contest.set_contact_vars()
        assert app.contact["IsMultiplier1"] == 1

        _insert(database, "ID3", "2026-09-04 16:00:00", "DL1AAD", "DL", 14.0)
        contest.set_contact_vars()
        assert app.contact["IsMultiplier1"] == 0
    finally:
        database.conn.close()


@pytest.mark.parametrize("plugin", PLUGINS)
def test_recalculation_counts_same_entity_once_on_each_band(plugin):
    database = _database()
    try:
        _insert(database, "ID0", "2026-09-01 16:00:00", "DL1AAA", "DL", 7.0)
        _insert(database, "ID2", "2026-09-02 16:00:00", "ON1AAB", "ON", 7.0)
        _insert(database, "ID3", "2026-09-03 16:00:00", "DL1AAC", "DL", 7.0)
        _insert(database, "ID4", "2026-09-04 16:00:00", "ON1AAD", "ON", 14.0)
        _insert(database, "ID5", "2026-09-05 16:00:00", "ON1AAE", "ON", 14.0)
        _insert(database, "ID6", "2026-09-06 16:00:00", "DL1AAF", "DL", 14.0)

        app = SimpleNamespace(
            database=database,
            station={"Call": "DM1ABC/P"},
            contact_is_dupe=0,
        )
        load_contest(plugin, app).recalculate_mults()
        assert [
            item["IsMultiplier1"] for item in database.fetch_all_contacts_asc()
        ] == [1, 1, 0, 1, 0, 1]
    finally:
        database.conn.close()


def test_recalculation_recomputes_the_points():
    """A fixed entrant's log: the two fixed-to-fixed contacts score nothing."""
    database = _database()
    try:
        _insert(database, "ID0", "2026-09-01 16:00:00", "DL1AAA", "DL", 14.0)
        _insert(database, "ID1", "2026-09-02 16:00:00", "DL1AAB", "DL", 14.0)

        app = SimpleNamespace(
            database=database,
            station={"Call": "DL1ABC"},
            contact_is_dupe=0,
        )
        load_contest("iaru_fieldday_r1_cw", app).recalculate_mults()
        assert [
            item["Points"] for item in database.fetch_all_contacts_asc()
        ] == [0, 0]
    finally:
        database.conn.close()


def test_the_dxcc_lookup_is_scoped_to_band():
    """The database question the points and the multiplier both rely on."""
    database = _database()
    try:
        _insert(database, "ID0", "2026-09-05 16:00:00", "DL1AAA", "DL", 7.0)
        assert database.fetch_dxcc_band_exists("DL", 14.0) == {"dxcc_band_count": 0}
        assert database.fetch_dxcc_band_exists("DL", 7.0) == {"dxcc_band_count": 1}
        assert database.fetch_dxcc_exists_before_me_on_band(
            "DL", "2026-09-05 16:01:00", 7.0
        ) == {"dxcc_band_count": 1}
    finally:
        database.conn.close()


# -- the numbers the corpus cases produce --------------------------------------
CASES = {case.id: case for case in discover_cases()}


@pytest.fixture
def headless(monkeypatch, tmp_path):
    """Neutralise plugin_common's Qt bits, as the corpus runner does."""
    monkeypatch.setattr(plugin_common, "QProgressDialog", DummyProgress)
    monkeypatch.setattr(
        plugin_common.QCoreApplication, "processEvents", staticmethod(lambda: None)
    )
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    return tmp_path


def loaded(case_id, headless, monkeypatch):
    case = CASES[case_id]
    home = headless / f"{case.contest}-{case.name}"
    home.mkdir(parents=True, exist_ok=True)
    harness = ContestHarness(case.contest, case, home, monkeypatch)
    plugin_common.import_adif(harness)
    harness.score_log()
    return harness


@pytest.mark.parametrize(
    "case_id,mults,score",
    [
        ("iaru_fieldday_r1_cw/DL1ABC", 2, 20),
        ("iaru_fieldday_r1_cw/DL2ABC", 2, 30),
        ("iaru_fieldday_r1_ssb/DL1ABC", 2, 20),
        ("iaru_fieldday_r1_ssb/DL2ABC", 2, 30),
    ],
)
def test_country_count_and_score(case_id, mults, score, headless, monkeypatch):
    contest = loaded(case_id, headless, monkeypatch).contest
    assert contest.show_mults() == mults
    assert contest.get_mults() == {"country": mults}
    assert contest.calc_score() == score
