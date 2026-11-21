"""N1MM ``.sec`` section lists: parsing, discovery, and the shipped Section."""

from __future__ import annotations

import pytest

from not1mm.lib import sections
from not1mm.lib.sections import (
    SectionListError,
    parse_sec,
    parse_sec_text,
    sec_files,
)


def test_parse_a_type_line_and_codes():
    text = "\ufeffType=ARI_SEZ  SubType=\r\nA01\r\nA02\r\n\r\nB01\r\n"
    section = parse_sec_text(text, "ari")
    assert (section.name, section.subtype) == ("ARI_SEZ", "")
    assert section.codes == frozenset({"A01", "A02", "B01"})


def test_the_type_line_is_optional():
    section = parse_sec_text("aa\nbb\n", "mylist")
    assert section.name == "mylist"
    assert section.codes == frozenset({"AA", "BB"})


def test_a_file_without_codes_is_an_error():
    with pytest.raises(SectionListError):
        parse_sec_text("Type=EMPTY  SubType=\n", "empty")


def test_parse_a_file(tmp_path):
    path = tmp_path / "demo.sec"
    path.write_text("Type=DEMO SubType=REGION\nAA\nBB\n", encoding="ascii")
    section = parse_sec(path)
    assert section.name == "DEMO"
    assert section.subtype == "REGION"
    assert section.codes == frozenset({"AA", "BB"})
    assert section.path == path


def test_the_shipped_section_list():
    section = sections.load_sec("ARRL_RAC_Section")
    assert section is not None
    assert len(section.codes) == 85
    assert "ORG" in section
    assert "EB" in section
    assert (sections.BUNDLED_SEC_DIR / "ARRL_RAC_Section.sec").is_file()


def test_the_type_line_is_not_a_lookup_key():
    # The shipped file's Type is "Section"; that generic name must not load it.
    assert sections.load_sec("ARRL_RAC_Section") is not None
    assert sections.load_sec("Section") is None


def test_a_contest_drives_its_list_from_mult_window_type():
    from types import SimpleNamespace

    from not1mm.plugins import arrl_ss_cw

    ctx = SimpleNamespace(contact_is_dupe=0, contact={"Sect": "ORG"})
    contest = arrl_ss_cw.Contest(ctx)
    assert contest.MultWindowType == "ARRL_RAC_Section"
    assert "ORG" in contest._sections()
    assert contest.points() == 2
    assert contest.mult_value(1, {"Sect": "ORG"}) == "ORG"
    assert "'ORG'" in contest.mult_sql(1)

    ctx.contact["Sect"] = "ZZ"
    assert contest.points() == 0
    assert contest.mult_value(1, {"Sect": "ZZ"}) is None


def test_a_user_file_wins(monkeypatch, tmp_path):
    user = tmp_path / "sec"
    user.mkdir()
    (user / "demo.sec").write_text("Type=DEMO\nAA\n", encoding="ascii")
    monkeypatch.setattr(
        sections, "sec_directories", lambda: (sections.BUNDLED_SEC_DIR, user)
    )
    sections.clear_cache()
    assert sections.load_sec("demo").codes == frozenset({"AA"})
    assert sections.load_sec("DEMO").codes == frozenset({"AA"})
    # A Type that differs from the file name is metadata, not a lookup key.
    assert sections.load_sec("OTHER") is None


def test_a_user_file_overrides_the_bundled_one(monkeypatch, tmp_path):
    user = tmp_path / "sec"
    user.mkdir()
    (user / "ARRL_RAC_Section.sec").write_text("Type=Section\nZZ\n", encoding="ascii")
    monkeypatch.setattr(
        sections, "sec_directories", lambda: (sections.BUNDLED_SEC_DIR, user)
    )
    sections.clear_cache()
    assert sections.load_sec("ARRL_RAC_Section").codes == frozenset({"ZZ"})


def test_discovery_skips_a_missing_directory(monkeypatch, tmp_path):
    missing = tmp_path / "not-there"
    monkeypatch.setattr(
        sections, "sec_directories", lambda: (missing, sections.BUNDLED_SEC_DIR)
    )
    sections.clear_cache()
    assert "arrl_rac_section" in sec_files()
