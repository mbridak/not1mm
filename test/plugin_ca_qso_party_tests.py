import pytest
from not1mm.plugins import ca_qso_party


@pytest.mark.parametrize(
    "text, expected",
    [
        ("SCLA", True),
        ("scla", True),
        ("ALAM", True),
        ("LANG", True),
        ("CCOS", True),
        ("MARN", True),
        ("MARP", True),
        ("SBAR", True),
        ("SMAT", True),
        ("YOLO", True),
        ("SCRU", True),
        ("SMAT", True),
        ("SCLA", True),
        ("XX", False),
        ("", False),
        ("ALAMX", False),
        ("ALAM  ", True),
    ],
)
def test_is_valid_ca_county(text, expected):
    assert ca_qso_party.is_valid_ca_county(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("CA", True),
        ("OR", True),
        ("NY", True),
        ("AB", True),
        ("BC", True),
        ("ON", True),
        ("QC", True),
        ("YT", True),
        ("DX", False),
        ("xx", False),
        ("", False),
        ("CAL", False),
        ("SCLA", False),
    ],
)
def test_is_valid_state_province(text, expected):
    assert ca_qso_party.is_valid_state_province(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("SCLA", True),
        ("ALAM", True),
        ("CA", True),
        ("OR", True),
        ("AB", True),
        ("DX", True),
        ("xx", False),
        ("", False),
        ("CAL", False),
        ("ALAMX", False),
    ],
)
def test_is_valid_exchange(text, expected):
    assert ca_qso_party.is_valid_exchange(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("scla", "SCLA"),
        ("  ca  ", "CA"),
        ("dx", "DX"),
        ("or", "OR"),
        (" alam ", "ALAM"),
    ],
)
def test_normalize_exchange(text, expected):
    assert ca_qso_party.normalize_exchange(text) == expected


@pytest.mark.parametrize(
    "mode, is_dupe, expected",
    [
        ("SSB", False, 3),
        ("LSB", False, 3),
        ("USB", False, 3),
        ("FM", False, 3),
        ("CW", False, 3),
        ("CW-U", False, 3),
        ("FT8", False, 3),
        ("SSB", True, 0),
        ("CW", True, 0),
    ],
)
def test_points_for_qso(mode, is_dupe, expected):
    assert ca_qso_party.points_for_qso(mode, is_dupe) == expected


def test_cabrillo_name():
    assert ca_qso_party.cabrillo_name == "CQP"


def test_dupe_type():
    assert ca_qso_party.dupe_type == 3
