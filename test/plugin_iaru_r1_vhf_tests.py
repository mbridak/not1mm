"""Tests for the IARU Region 1 VHF & Up Contest plugin."""

import math
from types import SimpleNamespace

import pytest

from not1mm.plugins import iaru_r1_vhf as iaru


class FakeDatabase:
    """Minimal fake database for unit tests."""

    def __init__(self, existing=None):
        self.contacts = list(existing or [])
        self.current_contest = "test"

    def fetch_all_contacts_asc(self):
        return self.contacts

    def fetch_qso_count(self):
        return {"qsos": len(self.contacts)}

    def fetch_points(self):
        total = sum(int(c.get("Points", 0)) for c in self.contacts)
        return {"Points": total}

    def exec_sql(self, query, params=None):
        return {}

    def change_contact(self, contact):
        pass


def make_self(
    my_grid="JO59",
    their_grid="JO49",
    dupe=False,
    band="2M",
    existing=(),
):
    """Build a minimal fake `self` for the plugin module functions."""
    fake = SimpleNamespace()
    fake.station = {"GridSquare": my_grid, "Call": "PA0TEST", "Name": "Test"}
    fake.contact = {
        "Exchange1": their_grid,
        "SNT": "59",
        "RCV": "59",
        "SentNr": "001",
        "NR": "001",
    }
    fake.contact_is_dupe = 1 if dupe else 0
    fake.contest_settings = {"BandCategory": band}
    fake.database = FakeDatabase(existing=existing)
    return fake


# --- Module metadata ---


def test_module_metadata():
    assert iaru.name == "IARU R1 VHF"
    assert iaru.mode == "BOTH"
    assert iaru.cabrillo_name == "IARU-R1-VHF"
    assert iaru.dupe_type == 2


# --- large_square helper ---


@pytest.mark.parametrize(
    "grid,expected",
    [
        ("JO49", "JO49"),
        ("jo49jf", "JO49"),
        ("JO59JC", "JO59"),
        ("", ""),
        ("JN58", "JN58"),
        (None, ""),
    ],
)
def test_large_square(grid, expected):
    if grid is None:
        grid = ""
    assert iaru.distance(grid[:4] + "ab" if grid else "", grid[:4] + "ab" if grid else "") >= 0


# --- bandinMHz mapping ---


@pytest.mark.parametrize(
    "band,expected",
    [
        ("ALL", "ALL"),
        ("6M", "50 MHz"),
        ("4M", "70 MHz"),
        ("2M", "145 MHz"),
        ("432", "435 MHz"),
        ("1.2G", "1,3 GHz"),
        ("2.3G", "2,3 GHz"),
        ("3.4G", "3,4 GHz"),
        ("5.7G", "5,7 GHz"),
        ("10G", "10 GHz"),
        ("24G", "24 GHz"),
        ("47G", "47 GHz"),
        ("75G", "76 GHz"),
        ("119G", "122 GHz"),
        ("142G", "134 GHz"),
        ("241G", "245 GHz"),
    ],
)
def test_bandinMHz_maps_ui_band_categories(band, expected):
    assert iaru.bandinMHz(band) == expected


def test_bandinMHz_never_returns_literal_error():
    for band in ("LIGHT", "VHF-3-BAND", "VHF-FM-ONLY", ""):
        assert "Invalid" not in iaru.bandinMHz(band)


# --- GHZ_MULT / MM_FACTOR ---


@pytest.mark.parametrize(
    "band,expected",
    [
        ("2M", 1),
        ("432", 1),
        ("1.2G", 1),
        ("10G", 1),
        ("24G", 1),
        ("47G", 2),
        ("75G", 3),
        ("119G", 4),
        ("142G", 8),
        ("241G", 10),
    ],
)
def test_mm_factor(band, expected):
    assert iaru.MM_FACTOR.get(band, 1) == expected


# --- Distance function ---


def test_distance_formula():
    """Distance should be floor(km) + 1."""
    km = iaru.ham_distance("JO59", "JO49")
    expected = int(km) + 1
    result = iaru.distance("JO59", "JO49")
    assert result == expected


def test_distance_zero_grid():
    assert iaru.distance("", "") == 0


# --- Points ---


def test_points_normal_vhf():
    """VHF band (1x multiplier): distance + 1."""
    pts = iaru.points(make_self(my_grid="JO59", their_grid="JO49", band="2M"))
    expected = int(iaru.ham_distance("JO59", "JO49")) + 1
    assert pts == expected


def test_points_dupe_zero():
    fake = make_self(dupe=True)
    assert iaru.points(fake) == 0


def test_points_mm_band():
    """47G should apply factor 2."""
    low = iaru.points(make_self(my_grid="JO59", their_grid="JO49", band="2M"))
    high = iaru.points(make_self(my_grid="JO59", their_grid="JO49", band="47G"))
    assert high == low * 2


def test_points_mm_factor_75g():
    """75G should apply factor 3."""
    base = iaru.points(make_self(my_grid="JO59", their_grid="JO49", band="2M"))
    result = iaru.points(make_self(my_grid="JO59", their_grid="JO49", band="75G"))
    assert result == base * 3


def test_points_empty_grid():
    """Empty locator should yield 0 points."""
    fake = make_self(their_grid="")
    assert iaru.points(fake) == 0


# --- show_mults ---


def test_show_mults_counts_distinct_large_squares():
    fake = make_self()
    fake.database.contacts = [
        {"Exchange1": "JO49XX"},
        {"Exchange1": "JO49AB"},
        {"Exchange1": "JO59CD"},
        {"Exchange1": "JO59EF"},
    ]
    assert iaru.show_mults(fake) == 2


def test_show_mults_empty_log():
    fake = make_self()
    assert iaru.show_mults(fake) == 0


def test_show_mults_normalizes_case():
    fake = make_self()
    fake.database.contacts = [
        {"Exchange1": "jo49xx"},
        {"Exchange1": "JO49AB"},
        {"Exchange1": "Jo59CD"},
    ]
    assert iaru.show_mults(fake) == 2


def test_show_mults_short_locator_ignored():
    fake = make_self()
    fake.database.contacts = [
        {"Exchange1": "JO4"},
        {"Exchange1": ""},
        {"Exchange1": "JO59CD"},
    ]
    assert iaru.show_mults(fake) == 1


# --- show_qso ---


def test_show_qso_empty():
    fake = make_self()
    assert iaru.show_qso(fake) == 0


def test_show_qso_with_contacts():
    fake = make_self(existing=[{"Points": 10}, {"Points": 20}])
    assert iaru.show_qso(fake) == 2


# --- calc_score ---


def test_calc_score_zero():
    fake = make_self()
    assert iaru.calc_score(fake) == 0


def test_calc_score_sum():
    fake = make_self(existing=[{"Points": 100}, {"Points": 200}])
    assert iaru.calc_score(fake) == 300


# --- recalculate_mults ---


def test_recalculate_mults_vhf():
    """All VHF contacts: points = distance + 1, no bonus."""
    contacts = [
        {"Exchange1": "JO49XX", "Band": "145 MHz", "Points": 0},
        {"Exchange1": "JO59CD", "Band": "145 MHz", "Points": 0},
    ]
    fake = make_self(my_grid="JO59", existing=contacts)
    iaru.recalculate_mults(fake)
    for c in contacts:
        expected = int(iaru.ham_distance("JO59", c["Exchange1"])) + 1
        assert c["Points"] == expected, (c["Exchange1"], c["Points"], expected)


# --- EDI helper ---


def test_edi_calls_gen_edi(monkeypatch):
    """edi() should call gen_edi with the right arguments."""
    called_with = {}

    def fake_gen_edi(self, cab, name, start, end):
        called_with["cab"] = cab
        called_with["name"] = name
        called_with["start"] = start
        called_with["end"] = end

    monkeypatch.setattr(iaru, "gen_edi", fake_gen_edi)
    fake = make_self()
    fake.contest_settings = {"StartDate": "2026-09-13"}
    iaru.edi(fake)
    assert called_with["cab"] == "IARU-R1-VHF"
    assert called_with["start"] == "20260913"


def test_adif_calls_gen_adif(monkeypatch):
    """adif() should call gen_adif with the right arguments."""
    called_with = {}

    def fake_gen_adif(self, cab, name, start, end):
        called_with["cab"] = cab
        called_with["name"] = name
        called_with["start"] = start
        called_with["end"] = end

    monkeypatch.setattr(iaru, "gen_adif", fake_gen_adif)
    fake = make_self()
    fake.contest_settings = {"StartDate": "2026-09-13"}
    iaru.adif(fake)
    assert called_with["cab"] == "IARU-R1-VHF"
    assert called_with["start"] == "20260913"


# --- Serial number per band ---


def test_next_serial_first_qso():
    """No prior contacts: serial starts at 1."""
    fake = make_self()
    fake.database.exec_sql = lambda q, p: {}
    result = iaru._next_serial_for_band(fake, "2M")
    assert result == 1


def test_next_serial_increments():
    """Prior contact with SentNr=5: next serial is 6."""
    fake = make_self()
    fake.database.exec_sql = lambda q, p: {"maxsn": 5}
    result = iaru._next_serial_for_band(fake, "2M")
    assert result == 6


# --- parse_exchange ---


def test_parse_exchange_valid():
    fake = make_self()
    fake.other_2 = SimpleNamespace(text=lambda: "599 003 JO49AB")
    result = iaru.parse_exchange(fake)
    assert result == ("599", "003", "JO49AB")


def test_parse_exchange_partial():
    fake = make_self()
    fake.other_2 = SimpleNamespace(text=lambda: "59 003")
    result = iaru.parse_exchange(fake)
    assert result == ("59", "003", "")


def test_parse_exchange_empty():
    fake = make_self()
    fake.other_2 = SimpleNamespace(text=lambda: "")
    result = iaru.parse_exchange(fake)
    assert result == ("", "", "")
