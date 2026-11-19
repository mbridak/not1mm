import pytest
from not1mm.plugins import darc_schwaben


@pytest.mark.parametrize(
    "callsign, dok, expected_points",
    [
        ("DL0YLT", "YLT", 10),
        ("DK0SQ", "SQ", 10),
        ("DL1ABC", "YLT", 10),
        ("DL1ABC", "SQ", 10),
        ("DL0T", "T01", 10),
        ("DF0T", "T18", 10),
        ("DK0T", "T99", 10),
        ("DN1T", "T05", 10),
        ("DN2JOE", "Z30", 10),
        ("DL1MGR", "T01", 5),
        ("DF3MT", "Z30", 5),
        ("DG1WSK", "T25", 5),
        ("DL2BER", "B01", 1),
        ("K6GTE", "001", 1),
        ("K6GTE", "NM", 1),
        ("F4HVV", "002", 1),
    ],
)
def test_get_points_for_contact(callsign, dok, expected_points):
    assert darc_schwaben.get_points_for_contact(callsign, dok) == expected_points


@pytest.mark.parametrize(
    "exchange_input, expected_dok, expected_grid",
    [
        ("T01", "T01", ""),
        ("T01 JN58ZZ", "T01", "JN58ZZ"),
        ("JN58ZZ T01", "T01", "JN58ZZ"),
        ("001 JN58FG", "001", "JN58FG"),
        ("NM", "NM", ""),
        ("Z30", "Z30", ""),
    ],
)
def test_parse_exchange(exchange_input, expected_dok, expected_grid):
    dok, grid = darc_schwaben.parse_exchange(exchange_input)
    assert dok == expected_dok
    assert grid == expected_grid
