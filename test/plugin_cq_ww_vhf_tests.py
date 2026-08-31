import pytest
from not1mm.plugins import cq_ww_vhf


@pytest.mark.parametrize(
    "band, expected_points",
    [
        ("50.0", 1),
        ("6", 1),
        ("144.0", 2),
        ("2", 2),
        ("432.0", 0),
        ("20.0", 0),
        ("", 0),
    ],
)
def test_points_for_band(band, expected_points):
    assert cq_ww_vhf.points_for_band(band) == expected_points


@pytest.mark.parametrize(
    "text, expected_grid",
    [
        ("EM15", "EM15"),
        ("em15", "EM15"),
        ("FN31BL", "FN31"),
        (" EM15 ", "EM15"),
        ("JN58", "JN58"),
        ("EM1", ""),
        ("1234", ""),
        ("ABCD", ""),
        ("", ""),
    ],
)
def test_normalize_grid(text, expected_grid):
    assert cq_ww_vhf.normalize_grid(text) == expected_grid


@pytest.mark.parametrize(
    "text, valid",
    [
        ("EM15", True),
        ("fn31bl", True),
        ("EM1", False),
        ("", False),
        ("N0GRD", False),
    ],
)
def test_validate_exchange(text, valid):
    assert cq_ww_vhf.validate_exchange(text) is valid


@pytest.mark.parametrize(
    "mode_category, expected_name",
    [
        ("CW", "CQ-VHF-SSBCW"),
        ("SSB", "CQ-VHF-SSBCW"),
        ("SSB+CW", "CQ-VHF-SSBCW"),
        ("DIGITAL", "CQ-VHF-DIGI"),
        ("", "CQ-VHF-SSBCW"),
    ],
)
def test_cabrillo_contest_name(mode_category, expected_name):
    settings = {"ModeCategory": mode_category}
    assert cq_ww_vhf.cabrillo_contest_name(settings) == expected_name


@pytest.mark.parametrize(
    "mode_category, expected_mode",
    [
        ("CW", "CW"),
        ("SSB", "SSB"),
        ("DIGITAL", "DG"),
        ("RTTY", "DG"),
        ("PSK", "DG"),
        ("SSB+CW", "MIXED"),
        ("SSB+CW+DIGITAL", "MIXED"),
    ],
)
def test_cabrillo_mode(mode_category, expected_mode):
    assert cq_ww_vhf.cabrillo_mode(mode_category) == expected_mode
