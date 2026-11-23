"""UDC discovery: the bundled and user directories, and the contest registry.

The shipped files are ``not1mm/data/udc/sk_memorial.udc`` and
``ok1wc.udc``; the tests point the user directory at a temporary one, so
nothing touches the real home directory.
"""

from __future__ import annotations

import pytest

from not1mm.lib import contest, parse_udc
from not1mm.lib.parse_udc import BUNDLED_UDC_DIR, udc_files

SHIPPED = BUNDLED_UDC_DIR / "sk_memorial.udc"

HEAD = """[Author]
AuthorName = Test
[File]
Revision = 1.0.0
[Contest]
Name = {name}
DisplayName = {display}
CabrilloName = {cabrillo}
Mode = CW
DupeType = 2
EntryWindowInfo = SNTText, 450, RCVText, 450, SntNrText, 625, RcvNrText, 625
FrameText = SNT RCV Sent Rcvd
"""


def udc_text(name: str, display: str | None = None, cabrillo: str | None = None) -> str:
    return HEAD.format(name=name, display=display or name, cabrillo=cabrillo or name)


@pytest.fixture(autouse=True)
def user_dir(monkeypatch, tmp_path):
    """Read the bundled files plus a temporary user directory."""
    directory = tmp_path / "udc"
    directory.mkdir()
    monkeypatch.setattr(
        parse_udc, "udc_directories", lambda: (BUNDLED_UDC_DIR, directory)
    )
    monkeypatch.setattr(contest, "_AVAILABLE", None)
    yield directory
    # available_contests() assigns the module global; monkeypatch restores the
    # value it saw, so the next test starts clean.


def write(directory, name: str, text: str):
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


# -- the shipped file ------------------------------------------------------


def test_the_package_ships_a_udc():
    assert SHIPPED.is_file()


def test_the_shipped_udc_parses_without_errors():
    udc = parse_udc.parse_udc(SHIPPED)
    assert udc.basename == "sk_memorial"
    errors = [issue for issue in parse_udc.validate_udc(udc) if issue.level == "error"]
    assert not errors


def test_the_shipped_udc_is_the_silent_key_memorial():
    contest_class = parse_udc.contest_from_udc(parse_udc.parse_udc(SHIPPED))
    assert contest_class.DisplayName == "Silent Key Memorial Contest"
    assert contest_class.CabrilloName == "SKMC"
    assert contest_class.Mode == "CW"
    assert contest_class.DupeType == 2
    assert contest_class.NumMults == 1
    assert contest_class.MultSqlString == "Exchange"
    assert contest_class.IsMultPer == 1
    assert contest_class.PointsPerContact == 1
    assert contest_class.EntryWindowInfo == (
        "SNTText",
        450,
        "SntNrText",
        625,
        "RCVText",
        450,
        "Exchange1Text",
        900,
    )
    assert contest_class.FrameText == ("SntRpt", "SntSK", "RcvRpt", "RcvSK")
    # Time, call, frequency and mode are always shown; LogInfo adds the rest.
    assert contest_class.LogInfo[:4] == [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq (KHz)",
        "Mode",
    ]
    assert "Exchange1" in contest_class.LogInfo


def test_the_shipped_udc_needs_nothing_unimplemented():
    contest_class = parse_udc.contest_from_udc(parse_udc.parse_udc(SHIPPED))
    assert contest_class.UdcUnimplemented == ()


# -- discovery -------------------------------------------------------------


def test_the_bundled_directory_is_read():
    assert udc_files()["sk_memorial"] == SHIPPED


def test_both_directories_are_read(user_dir):
    write(user_dir, "extra.udc", udc_text("EXTRA", "Extra Contest"))
    assert {"sk_memorial", "extra"} <= set(udc_files())


def test_a_user_file_wins_over_the_bundled_one(user_dir):
    mine = write(
        user_dir,
        "sk_memorial.udc",
        udc_text("SKMC", "My Silent Key Contest", "SKMC"),
    )
    assert udc_files()["sk_memorial"] == mine
    assert contest.contest_metadata("sk_memorial").DisplayName == (
        "My Silent Key Contest"
    )


def test_the_registry_includes_the_udc():
    infos = [info for info in contest.available_contests() if info.udc_path]
    assert [info.basename for info in infos] == ["ok1wc", "sk_memorial"]
    assert infos[1].display_name == "Silent Key Memorial Contest"
    assert infos[1].cabrillo_name == "SKMC"


def test_the_registry_still_has_the_plugins():
    assert any(info.udc_path is None for info in contest.available_contests())


def test_the_shipped_ok1wc_udc_is_the_memorial():
    path = udc_files()["ok1wc"]
    contest_class = parse_udc.contest_from_udc(parse_udc.parse_udc(path))
    assert contest_class.DisplayName == "OK1WC Memorial Contest"
    assert contest_class.CabrilloName == "MWC"
    assert contest_class.SendsRTCScore is True
    assert contest_class.EXCHANGE_HINT == "#"
    assert contest_class.Bands == (3.5, 7.0)
    assert contest_class.UdcUnimplemented == ()


def test_the_picker_lists_the_udc():
    assert (
        "Silent Key Memorial Contest (SKMC)",
        "sk_memorial",
    ) in contest.contest_picker_entries()


def test_a_udc_is_found_by_its_stem():
    for asked in ("sk_memorial", "SK_MEMORIAL"):
        contest_class = contest.contest_metadata(asked)
        assert contest_class is not None, asked
        assert contest_class.BaseName == "sk_memorial"
    # A display or Cabrillo name is not an identifier.
    assert contest.contest_metadata("Silent Key Memorial Contest") is None
    assert contest.contest_metadata("SKMC") is None


def test_load_contest_opens_a_udc():
    parent = object()
    loaded = contest.load_contest("sk_memorial", parent)
    assert loaded.parent is parent
    assert loaded.BaseName == "sk_memorial"
    assert loaded.DisplayName == "Silent Key Memorial Contest"


def test_two_files_with_the_same_name_are_two_contests(user_dir):
    write(user_dir, "pair-a.udc", udc_text("PAIR", "Pair A", "PAIR"))
    write(user_dir, "pair-b.udc", udc_text("PAIR", "Pair B", "PAIR"))
    a = contest.contest_metadata("pair-a")
    b = contest.contest_metadata("pair-b")
    assert a.BaseName == "pair-a"
    assert b.BaseName == "pair-b"
    assert a.UdcName == b.UdcName == "PAIR"
    assert a.DisplayName != b.DisplayName


def test_two_udcs_with_the_same_label_stay_apart(user_dir):
    # Same DisplayName and same CabrilloName: only the file name differs.
    write(user_dir, "twin-a.udc", udc_text("TWIN", "Twin Contest", "TWIN"))
    write(user_dir, "twin-b.udc", udc_text("TWIN", "Twin Contest", "TWIN"))
    labels = dict(
        (basename, label) for label, basename in contest.contest_picker_entries()
    )
    assert labels["twin-a"] == "Twin Contest (TWIN) [twin-a]"
    assert labels["twin-b"] == "Twin Contest (TWIN) [twin-b]"


def test_a_broken_udc_is_skipped_and_the_rest_survive(user_dir):
    write(
        user_dir,
        "broken.udc",
        udc_text("BROKEN", "Broken").replace("Mode = CW", "Mode = FM"),
    )
    labels = [basename for _label, basename in contest.contest_picker_entries()]
    assert "sk_memorial" in labels
    assert "broken" not in labels
    assert contest.contest_metadata("broken") is None


# -- the Cabrillo line -----------------------------------------------------


def test_the_shipped_udc_writes_its_exchange_on_the_cabrillo_line():
    loaded = contest.load_contest("sk_memorial", object())
    line = loaded.cabrillo_qso_line(
        {
            "TS": "2026-11-01 07:12:00",
            "Freq": 3512.5,
            "Mode": "CW",
            "StationPrefix": "HA6NA",
            "SNT": "599",
            "SentNr": "HA6NA",
            "Call": "YT7MM",
            "RCV": "599",
            "Exchange1": "YT7MM",
        }
    )
    assert line == (
        "QSO:  3512 CW 2026-11-01 0712 HA6NA         599 HA6NA  "
        "YT7MM         599 YT7MM "
    )


def test_a_udc_with_a_serial_box_still_writes_nr(user_dir):
    write(
        user_dir,
        "serial.udc",
        udc_text("SERIAL", "Serial Contest").replace(
            "SntNrText, 625, RcvNrText, 625", "RcvNrText, 625"
        ),
    )
    loaded = contest.load_contest("serial", object())
    line = loaded.cabrillo_qso_line(
        {
            "TS": "2026-11-01 07:12:00",
            "Freq": 7000.0,
            "Mode": "CW",
            "StationPrefix": "K6GTE",
            "SNT": "599",
            "SentNr": "001",
            "Call": "K1ABC",
            "RCV": "599",
            "NR": "042",
        }
    )
    assert line.endswith("599 042   ")  # the exchange column is six wide
