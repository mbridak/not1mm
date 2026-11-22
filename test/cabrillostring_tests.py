"""N1MM's CabrilloString: parsing and the QSO line it lays out."""

from __future__ import annotations

import pytest

from not1mm.lib.cabrillostring import (
    CabrilloStringError,
    parse_cabrillostring,
    qso_line,
)

CONTACT = {
    "TS": "2026-08-01 07:12:00",
    "Freq": 3512.5,
    "Mode": "CW",
    "StationPrefix": "K6GTE",
    "SNT": "599",
    "SentNr": "001",
    "Call": "K1ABC",
    "RCV": "599",
    "NR": "012",
    "Sect": "ORG",
    "MiscText": "m",
}


def line(text, contact=None, sent_exchange=""):
    return qso_line(
        parse_cabrillostring(text),
        contact or CONTACT,
        my_call="K6GTE",
        mode="CW",
        sent_exchange=sent_exchange,
    )


def test_parse_pairs():
    parsed = parse_cabrillostring("SNT, 4, SentNr, 4, CallSign, 13")
    assert [(field.name, field.width) for field in parsed.fields] == [
        ("SNT", 4),
        ("SentNr", 4),
        ("CallSign", 13),
    ]
    assert parsed.unknown == ()


def test_the_standard_line():
    text = "SNT, 4, SentNr, 4, CallSign, 13, RCV, 4, RcvNr, 4"
    expected = (
        "QSO:  3512 CW 2026-08-01 0712 "
        + "K6GTE".ljust(13)
        + "599 "
        + "001 "
        + "K1ABC".ljust(13)
        + "599 "
        + "012 "
    )
    assert line(text) == expected


def test_space_pads():
    assert line("CallSign, 5, Space, 3, RCV, 4").endswith("K1ABC" + "   " + "599 ")


def test_the_spellings_real_files_use():
    # SENT, Sect, Misc and the SntExchPart2 typo appear in the gallery.
    parsed = parse_cabrillostring("SENT, 4, Sect, 4, Misc, 2, SntExchPart2, 4")
    assert [field.name for field in parsed.fields] == [
        "SNT",
        "Sect",
        "MiscText",
        "SentExchPart2",
    ]
    assert parsed.unknown == ()


def test_sent_exchange_and_its_parts():
    text = "SentExch, 8, SentExchPart1, 4, SentExchPart2, 6, SentExchPart3, 3"
    result = line(text, sent_exchange="001 NA123")
    assert result.endswith("001 NA12" + "001 " + "NA123 " + "   ")


def test_an_unknown_field_is_blank_and_reported():
    parsed = parse_cabrillostring("SNT, 4, LastExch, 3, CallSign, 5")
    assert parsed.unknown == ("LastExch",)
    result = qso_line(parsed, CONTACT, my_call="K6GTE", mode="CW", sent_exchange="")
    assert result.endswith("599 " + "   " + "K1ABC")


def test_an_odd_list_is_an_error():
    with pytest.raises(CabrilloStringError):
        parse_cabrillostring("SNT, 4, SentNr")


def test_a_width_must_be_a_number():
    with pytest.raises(CabrilloStringError):
        parse_cabrillostring("SNT, four")


def test_values_are_truncated_to_the_width():
    assert line("CallSign, 3").endswith("K1A")
