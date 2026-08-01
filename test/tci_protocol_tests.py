import pytest

from not1mm.lib.tci_protocol import (
    bandwidth_from_filter_band,
    build_command,
    not1mm_mode_to_tci,
    parse_frame,
    split_frames,
    tci_mode_to_not1mm,
)


@pytest.mark.parametrize(
    "frame, expected",
    [
        ("vfo:0,0,14030000;", ("vfo", ["0", "0", "14030000"])),
        ("ready;", ("ready", [])),
        ("trx:0,true;", ("trx", ["0", "true"])),
        ("rx_filter_band:0,-500,500;", ("rx_filter_band", ["0", "-500", "500"])),
        ("  vfo:0,0,14030000;  ", ("vfo", ["0", "0", "14030000"])),
        ("VFO:0,0,14030000;", ("vfo", ["0", "0", "14030000"])),
        ("vfo:0,0,14030000", None),  # no terminator
        (";", None),
        ("", None),
        (":1,2;", None),  # empty command name
    ],
)
def test_parse_frame(frame, expected):
    assert parse_frame(frame) == expected


def test_split_frames_handles_multiple_commands_in_one_payload():
    payload = "device:AetherSDR;trx_count:1;ready;"
    assert split_frames(payload) == ["device:AetherSDR;", "trx_count:1;", "ready;"]


def test_split_frames_ignores_trailing_whitespace_fragment():
    assert split_frames("ready;\n") == ["ready;"]


@pytest.mark.parametrize(
    "args, expected",
    [
        (("vfo", 0, 0, 14030000), "vfo:0,0,14030000;"),
        (("modulation", 0, "cw"), "modulation:0,cw;"),
        (("trx", 0, "true"), "trx:0,true;"),
        (("cw_macros_speed", 25), "cw_macros_speed:25;"),
        (("stop",), "stop;"),
    ],
)
def test_build_command(args, expected):
    assert build_command(*args) == expected


def test_build_command_roundtrips_through_parse_frame():
    assert parse_frame(build_command("vfo", 0, 0, 14030000)) == (
        "vfo",
        ["0", "0", "14030000"],
    )


@pytest.mark.parametrize(
    "tci, not1mm",
    [
        ("cw", "CW"),
        ("cwr", "CWR"),
        ("lsb", "LSB"),
        ("usb", "USB"),
        ("digl", "DIGI-L"),
        ("digu", "DIGI-U"),
        ("rtty", "RTTY"),
        ("fm", "FM"),
        ("nfm", "NFM"),
        ("CW", "CW"),  # case insensitive
    ],
)
def test_tci_mode_to_not1mm(tci, not1mm):
    assert tci_mode_to_not1mm(tci) == not1mm


def test_fm_and_nfm_do_not_collide():
    """AetherSDR offers both; folding them together loses one on the way back."""
    assert tci_mode_to_not1mm("fm") != tci_mode_to_not1mm("nfm")


def test_tci_mode_to_not1mm_passes_through_unknown_modes_uppercased():
    assert tci_mode_to_not1mm("someNewMode") == "SOMENEWMODE"


@pytest.mark.parametrize(
    "not1mm, tci",
    [
        ("CW", "cw"),
        ("CWR", "cwr"),
        ("USB", "usb"),
        ("DIGI-L", "digl"),
        ("RTTY", "rtty"),  # native on AetherSDR, not remapped to digl
        ("FM", "fm"),
        ("NFM", "nfm"),
    ],
)
def test_not1mm_mode_to_tci(not1mm, tci):
    assert not1mm_mode_to_tci(not1mm) == tci


def test_mode_translation_roundtrips_for_every_known_tci_mode():
    from not1mm.lib.tci_protocol import TCI_TO_NOT1MM_MODE

    for tci in TCI_TO_NOT1MM_MODE:
        assert not1mm_mode_to_tci(tci_mode_to_not1mm(tci)) == tci


def test_cw_and_data_modes_match_radio_module_expectations():
    """Radio matches get_mode_list() against these lists by exact string."""
    from not1mm.radio import Radio

    assert tci_mode_to_not1mm("cw") in Radio.cw_list
    assert tci_mode_to_not1mm("digl") in Radio.rtty_list


@pytest.mark.parametrize(
    "low, high, expected",
    [
        ("-500", "500", "1000"),
        ("300", "2700", "2400"),
        ("500", "-500", "1000"),  # order independent
        ("0", "0", "0"),
        ("junk", "500", ""),
        ("", "", ""),
    ],
)
def test_bandwidth_from_filter_band(low, high, expected):
    assert bandwidth_from_filter_band(low, high) == expected
