import pytest
from not1mm.plugins import ca_qso_party
from types import SimpleNamespace


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


# Rule: a California station works everyone and counts the states and
# provinces it is sent (its first county contact being California), while a
# station elsewhere counts only the California counties it works and scores
# nothing for a non-CA to non-CA contact.
def _ctx(state, exchange, dupe=0):
    return SimpleNamespace(
        station={"State": state},
        contact={"Exchange1": exchange, "Mode": "CW"},
        contact_is_dupe=dupe,
    )


@pytest.mark.parametrize(
    "state, exchange, expected",
    [
        ("CA", "SCLA", "CA"),
        ("CA", "SBER", "CA"),
        ("CA", "WA", "WA"),
        ("CA", "BC", "BC"),
        ("CA", "DX", None),
        ("CA", "", None),
        ("CT", "SCLA", "SCLA"),
        ("CT", "SDIE", "SDIE"),
        ("CT", "WA", None),
        ("CT", "DX", None),
    ],
)
def test_multiplier_key(state, exchange, expected):
    assert ca_qso_party.multiplier_key(_ctx(state, exchange), exchange) == expected


@pytest.mark.parametrize(
    "state, exchange, expected",
    [
        ("CA", "SCLA", 3),
        ("CA", "WA", 3),
        ("CA", "DX", 3),
        ("CT", "SCLA", 3),
        ("CT", "WA", 0),
        ("CT", "DX", 0),
    ],
)
def test_points(state, exchange, expected):
    assert ca_qso_party.points(_ctx(state, exchange)) == expected


def test_a_duplicate_scores_nothing():
    assert ca_qso_party.points(_ctx("CA", "SCLA", dupe=1)) == 0
