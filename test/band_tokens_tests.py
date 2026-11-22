"""One band token, two spellings: metre names and numeric MHz.

UDC itself is inconsistent: ``PointsPerContact`` writes ``160m``, ``70cm``,
while ``PointsMultByBand`` writes ``1.8``, ``3.5``, ``420``.  The shared
reader accepts both, so a new field does not have to pick a camp.
"""

from __future__ import annotations

import pytest

from not1mm.lib.ham_utility import parse_band


@pytest.mark.parametrize(
    "token,mhz",
    [
        ("160m", 1.8),
        ("80m", 3.5),
        ("40m", 7.0),
        ("20m", 14.0),
        ("15m", 21.0),
        ("10m", 28.0),
        ("6m", 50.0),
        ("4m", 70.0),
        ("2m", 144.0),
        ("1.25m", 222.0),
        ("70cm", 432.0),
        ("33cm", 902.0),
        ("23cm", 1296.0),
        ("13cm", 2300.0),
        ("9cm", 3300.0),
        ("6cm", 5650.0),
        ("3cm", 10_000.0),
        ("6mm", 47_000.0),
        ("160M", 1.8),  # case-insensitive
    ],
)
def test_band_names(token, mhz):
    assert parse_band(token) == mhz


@pytest.mark.parametrize(
    "token,mhz",
    [
        ("1.8", 1.8),
        ("3.5", 3.5),
        ("7", 7.0),
        ("14", 14.0),
        ("21", 21.0),
        ("28", 28.0),
        ("50", 50.0),
        ("70", 70.0),
        ("144", 144.0),
        ("222", 222.0),
        ("902", 902.0),
        ("2300", 2300.0),
        ("3300", 3300.0),
        ("5650", 5650.0),
        ("10000", 10_000.0),
        ("24000", 24_000.0),
        ("47000", 47_000.0),
    ],
)
def test_numeric_mhz(token, mhz):
    assert parse_band(token) == mhz


def test_n1mm_microwave_frequencies_land_on_our_bands():
    # N1MM's PointsMultByBand names 420 and 1240; not1mm's canonical values
    # are 432 (70cm) and 1296 (23cm).
    assert parse_band("420") == 432.0
    assert parse_band("432") == 432.0
    assert parse_band("1240") == 1296.0
    assert parse_band("1296") == 1296.0


def test_a_frequency_inside_a_band_resolves_to_the_band():
    assert parse_band("7.05") == 7.0
    assert parse_band("3.6") == 3.5
    assert parse_band("145.5") == 144.0


def test_a_bare_number_is_a_metre_name_first():
    # UDC files write the band as a metre number without the unit
    # (SameContinent+80), so 10 is 10m and 40 is 40m, not their MHz values.
    assert parse_band("10") == 28.0
    assert parse_band("10m") == 28.0
    assert parse_band("40") == 7.0
    assert parse_band("40m") == 7.0
    assert parse_band("60") == 5.0
    assert parse_band("80") == 3.5
    assert parse_band("160") == 1.8


def test_the_numeric_reading_of_the_overlapping_numbers():
    # 5, 10, 40 and 60 are both a metre name and a frequency; the metre name
    # wins, and the numeric spelling needs a decimal point.
    assert parse_band("5") == 54.0  # 5m
    assert parse_band("5.0") == 5.0  # 60m
    assert parse_band("10") == 28.0  # 10m
    assert parse_band("10.0") == 10.0  # 30m
    assert parse_band("40") == 7.0  # 40m
    assert parse_band("40.0") == 40.0  # 8m
    assert parse_band("60") == 5.0  # 60m
    assert parse_band("60.0") == 54.0  # 5m


@pytest.mark.parametrize("token", ["", "banana", "0", "-7", "3.5m", "75mc"])
def test_unknown_tokens_are_zero(token):
    assert parse_band(token) == 0.0
