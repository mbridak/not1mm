import pytest
from not1mm.plugins import wag

@pytest.mark.parametrize(
        "rcvd_string, expected_district",
        [
            ("L16", "L"),
            ("O15", "O"),
            ("BCC", "B"),
            ("75DARC", "D"),
            ("RTA", "R"),
            ("50HSK", "H"),
            ("60U10", "U"),
            ("HAM25", "H"),
            ("x30", "x"),
            ("1525BK", "B"),
            ("2025", None),
            ("003", None),
            ("", None),
        ],
)

def test_get_district(rcvd_string, expected_district):
    assert wag.get_district(rcvd_string) == expected_district