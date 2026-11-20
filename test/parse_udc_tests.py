"""The UDC reader: parsing, validation, and the contest factory.

The field-by-field reference is ``UDC-FIELDS.md`` next to the repository.
"""

from __future__ import annotations

import pytest

from not1mm.lib.contest import ContestBase
from not1mm.lib.parse_udc import (
    CONTEST_KEYS,
    KNOWN_KEYS,
    Udc,
    UdcError,
    contest_from_udc,
    load_udc,
    parse_udc,
    parse_udc_text,
    validate_udc,
)

MINIMAL = """
[Author]
AuthorName = Test
Callsign = K6GTE
[File]
Revision = 1.0.0
Description = A test contest
[Contest]
Name = TEST
DisplayName = Test Contest
CabrilloName = TEST
Mode = CW
DupeType = 2
EntryWindowInfo = SNTText, 450, RCVText, 450, SntNrText, 625, RcvNrText, 625
FrameText = SNT RCV Sent Rcvd
"""


def udc_for(text: str, source: str = "test") -> Udc:
    return parse_udc_text(text, source)


def issues(udc: Udc, level: str = "error") -> list:
    return [issue for issue in validate_udc(udc) if issue.level == level]


def messages(udc: Udc, level: str = "warning") -> str:
    return "\n".join(str(issue) for issue in issues(udc, level))


# -- parsing ---------------------------------------------------------------


def test_parse_sections_and_values():
    text = "\ufeff[Author]\r\nAuthorName=K6GTE\r\n[File]\r\nRevision =1.0.0\r\n"
    text += "[Contest]\r\nName =TEST\r\nDisplayName = Test Contest\r\n"
    udc = udc_for(text)
    assert udc.section("Author") == {"AuthorName": "K6GTE"}
    assert udc.section("File") == {"Revision": "1.0.0"}
    assert udc.get("name") == "TEST"
    assert udc.get("displayname") == "Test Contest"
    assert udc.display_name == "Test Contest"


def test_parse_file_uses_the_stem(tmp_path):
    path = tmp_path / "my-contest.udc"
    path.write_text(MINIMAL, encoding="utf-8")
    udc = parse_udc(path)
    assert udc.source == "my-contest"
    assert udc.path == path


def test_parse_file_decodes_a_windows_1252_file(tmp_path):
    path = tmp_path / "latin.udc"
    path.write_bytes(MINIMAL.replace("Test", "Tëst").encode("cp1252"))
    assert parse_udc(path).display_name == "Tëst Contest"


def test_parse_file_reports_a_missing_file(tmp_path):
    with pytest.raises(UdcError):
        parse_udc(tmp_path / "nope.udc")


def test_a_file_without_a_contest_section_is_an_error():
    with pytest.raises(UdcError):
        udc_for("[Author]\nAuthorName = x\n")


def test_box_names_are_case_insensitive():
    # SARLRTTY.udc writes "SntText"; N1MM names are not case-sensitive.
    udc = udc_for(MINIMAL.replace("SNTText", "SntText"))
    assert contest_from_udc(udc).EntryWindowInfo[0] == "SNTText"
    assert not issues(udc)


def test_itu_is_accepted_without_a_warning():
    # The zones are ITU zones; N1MM's help calls them IARU.
    udc = udc_for(MINIMAL + "ZoneType = ITU\n")
    assert contest_from_udc(udc).ZoneType == "IARU"
    assert "ZoneType" not in messages(udc)


def test_digital_is_accepted_as_a_mode():
    # FT4/FT8 files say DIGITAL; the documented set stops at RTTY.
    udc = udc_for(MINIMAL.replace("Mode = CW", "Mode = DIGITAL"))
    assert contest_from_udc(udc).Mode == "DIGITAL"
    assert not issues(udc)


def test_a_value_list_where_a_section_header_belongs_is_ignored():
    # WIA_VHFUHF.udc pastes "[AllowableTime, CompareToSecond, ...]" inside
    # [Contest]; the keys after it must stay in [Contest].
    udc = udc_for(
        MINIMAL + "[AllowableTime, CompareToSecond, InfoStatus]\n" "IsMultPer = 1\n"
    )
    assert udc.get("IsMultPer") == "1"
    assert not issues(udc)
    assert "not a section header" in messages(udc)


def test_unknown_keys_and_sections_are_kept_and_warned():
    text = MINIMAL + "\nFancyNewThing = 42\n[Extra]\nWhatever = yes\n"
    udc = udc_for(text)
    assert udc.get("FancyNewThing") == "42"
    assert udc.section("Extra") == {"Whatever": "yes"}
    warning = messages(udc)
    assert "unknown key 'FancyNewThing'" in warning
    assert "unknown section [Extra]" in warning


def test_a_repeated_key_keeps_the_first_non_empty_value():
    # ARIRTTY.UDC has "IsMultPer =1" and, from the editor's defaults, an empty
    # "IsMultPer =" further down.  N1MM's docs say nothing about duplicates;
    # the rule here is that an empty repeat never erases the value.
    udc = udc_for(MINIMAL + "IsMultPer = 1\nIsMultPer =\n")
    assert udc.get("IsMultPer") == "1"
    assert "repeats empty; keeping '1'" in messages(udc)


def test_arrlttys_empty_repeat_does_not_erase_the_value():
    udc = udc_for(MINIMAL + "IsMultPer = 1\nIsMultPer =\nIsMultPer =\n")
    assert udc.get("IsMultPer") == "1"


def test_a_repeated_key_with_two_values_keeps_the_first():
    udc = udc_for(MINIMAL + "ZoneType = CQ\nZoneType = IARU\n")
    assert udc.get("ZoneType") == "CQ"
    assert "keeping 'CQ', ignoring 'IARU'" in messages(udc)


def test_a_value_after_an_empty_one_is_used():
    udc = udc_for(MINIMAL + "IsWorkable =\nIsWorkable = MyCountryOnly\n")
    assert udc.get("IsWorkable") == "MyCountryOnly"
    assert "had no value; using 'MyCountryOnly'" in messages(udc)


def test_the_template_spelling_of_the_time_multipliers_is_accepted():
    udc = udc_for(MINIMAL + "PointMultAtTimeGMT = 0000, 0600, 2\n")
    assert udc.get("PointsMultAtTimeGMT") == "0000, 0600, 2"


def test_comments_and_blank_lines_are_skipped():
    udc = udc_for("; a comment\n\n" + MINIMAL + "\n# another\n")
    assert udc.get("Name") == "TEST"
    assert not udc.warnings


# -- validation ------------------------------------------------------------


def test_a_valid_file_has_no_errors():
    assert not issues(udc_for(MINIMAL))


def test_the_name_is_required():
    udc = udc_for(MINIMAL.replace("Name = TEST\n", ""))
    assert "Name" in [issue.key for issue in issues(udc)]


def test_bad_enumeration_values_are_errors():
    udc = udc_for(
        MINIMAL.replace("Mode = CW", "Mode = FM").replace(
            "DupeType = 2", "DupeType = 9"
        )
    )
    keys = [issue.key for issue in issues(udc)]
    assert keys == ["Mode", "DupeType"]


def test_an_unshapeable_entry_window_is_an_error():
    udc = udc_for(MINIMAL.replace("SNTText, 450", "SNTText, 450, RCVText"))
    assert "EntryWindowInfo" in [issue.key for issue in issues(udc)]


def test_an_unknown_box_is_an_error():
    udc = udc_for(MINIMAL.replace("SntNrText, 625", "SntNrText, 625, BogusText, 100"))
    assert "unknown box 'BogusText'" in messages(udc, "error")


def test_an_odd_log_info_is_an_error():
    udc = udc_for(MINIMAL + "LogInfo = SentReport, 500, SentNr\n")
    assert "LogInfo" in [issue.key for issue in issues(udc)]


def test_a_bad_multiplier_kind_is_a_warning():
    udc = udc_for(MINIMAL + "MultSqlString = Comment\nNumMults = 1\n")
    assert "not a multiplier kind" in messages(udc)


def test_a_non_documented_multiplier_spelling_is_accepted_and_warned_about():
    # "Country" is what some sample files say; the documentation says
    # "CountryPrefix".  Read it, but say so.
    udc = udc_for(MINIMAL + "NumMults = 1\nMultSqlString = Country\n")
    contest = contest_from_udc(udc)
    assert contest.MultSqlString == "CountryPrefix"
    assert "not the documented spelling" in messages(udc)


def test_declared_multipliers_without_a_key_are_warned_about():
    udc = udc_for(MINIMAL + "NumMults = 1\n")
    assert "no MultSqlString has a key" in messages(udc)


# -- the factory -----------------------------------------------------------


def test_the_factory_maps_the_identity():
    udc = udc_for(MINIMAL)
    contest = contest_from_udc(udc)
    assert issubclass(contest, ContestBase)
    assert contest.DisplayName == "Test Contest"
    assert contest.CabrilloName == "TEST"
    assert contest.ContestName == "test"  # the source, not the UDC Name
    assert contest.UdcName == "TEST"
    assert contest.Mode == "CW"
    assert contest.DupeType == 2
    assert contest.ZoneType == "CQ"


def test_mixed_case_and_missing_values_use_the_udc_defaults():
    text = MINIMAL.replace("Mode = CW", "Mode = Both").replace("DupeType = 2", "")
    udc = udc_for(text)
    contest = contest_from_udc(udc)
    assert contest.Mode == "BOTH"
    assert contest.DupeType == 2  # UDC's default
    assert contest.ZoneType == "CQ"


def test_the_factory_keeps_the_entry_window():
    contest = contest_from_udc(udc_for(MINIMAL))
    assert contest.EntryWindowInfo == (
        "SNTText",
        450,
        "RCVText",
        450,
        "SntNrText",
        625,
        "RcvNrText",
        625,
    )
    assert contest.FrameText == ("SNT", "RCV", "Sent", "Rcvd")


def test_a_missing_entry_window_gets_the_standard_boxes():
    udc = udc_for(MINIMAL.replace("EntryWindowInfo =", "#EntryWindowInfo ="))
    contest = contest_from_udc(udc)
    assert len(contest.EntryWindowInfo) == 8
    assert "standard four boxes" in messages(udc)


def test_a_short_frame_text_is_padded_with_blank_labels():
    udc = udc_for(MINIMAL.replace("FrameText = SNT RCV Sent Rcvd", "FrameText = SNT"))
    assert contest_from_udc(udc).FrameText == ("SNT", "", "", "")


def test_the_factory_maps_the_multipliers():
    text = MINIMAL + "NumMults = 2\nMultiplier1Name = Sect\n"
    text += "MultSqlString = Section\nMultSqlString2 = Country\nIsMultPer = 1\n"
    contest = contest_from_udc(udc_for(text))
    assert contest.NumMults == 2
    assert contest.MultSqlString == "Section"
    assert contest.MultSqlString2 == "CountryPrefix"
    assert contest.IsMultPer == 1
    assert contest.IsMult1Per == 1


def test_a_multiplier_slot_can_have_its_own_counting():
    text = MINIMAL + "NumMults = 2\nMultiplier1Name = Grid\nMultiplier2Name = Cty\n"
    text += "MultSqlString = Grid\nMultSqlString2 = CountryPrefix\n"
    text += "IsMultPer = 4\nIsMult1Per = 1\n"
    contest = contest_from_udc(udc_for(text))
    assert contest.IsMult1Per == 1
    assert contest.IsMult2Per == 4


def test_a_declared_multiplier_without_a_key_does_not_count():
    # calc_score() multiplies by the multiplier count, so a "multiplier" with
    # no key would score the whole contest zero.
    contest = contest_from_udc(udc_for(MINIMAL + "NumMults = 1\n"))
    assert contest.NumMults == 0


def test_n_a_is_no_multiplier():
    contest = contest_from_udc(udc_for(MINIMAL + "NumMults = 1\nMultSqlString = N/A\n"))
    assert contest.NumMults == 0
    assert contest.MultSqlString is None


def test_the_first_multiplier_key_name_is_the_un_suffixed_one():
    text = MINIMAL + "NumMults = 1\nMultSqlString = WPXPrefix\n"
    assert contest_from_udc(udc_for(text)).MultSqlString == "WPXPrefix"


def test_an_integer_points_value_is_applied():
    contest = contest_from_udc(udc_for(MINIMAL + "PointsPerContact = 5\n"))
    assert contest.PointsPerContact == 5
    assert "PointsPerContact" not in contest.UdcUnimplemented


def test_a_points_rule_is_flagged_and_falls_back():
    udc = udc_for(MINIMAL + "PointsPerContact = 40m, 1, 80m, 2\n")
    contest = contest_from_udc(udc)
    assert contest.PointsPerContact == 1  # UDC's default until the grammar lands
    assert "PointsPerContact" in contest.UdcUnimplemented
    assert "rule lists are not implemented" in messages(udc)


def test_a_qso_error_string_is_passed_through():
    contest = contest_from_udc(
        udc_for(MINIMAL + "QsoErrorString = RcvNrText_Any_not_Empty\n")
    )
    assert contest.QsoErrorString == "RcvNrText_Any_not_Empty"


def test_a_section_list_qso_error_string_falls_back_to_the_default_check():
    udc = udc_for(MINIMAL + "QsoErrorString = ARI\n")
    contest = contest_from_udc(udc)
    assert contest.QsoErrorString is None
    assert "QsoErrorString" in contest.UdcUnimplemented
    assert "will not be checked" in messages(udc)


BASE_LOG_COLUMNS = ["YYYY-MM-DD HH:MM:SS", "Call", "Freq (KHz)", "Mode"]


def test_log_info_names_are_translated_to_not1mm_columns():
    text = (
        MINIMAL + "LogInfo = SentReport, 500, NR, 500, SectionText, 500, Points, 500\n"
    )
    contest = contest_from_udc(udc_for(text))
    assert contest.LogInfo == [*BASE_LOG_COLUMNS, "Snt", "RcvNr", "Sect", "PTS"]


def test_the_log_window_always_shows_the_date_call_frequency_and_mode():
    # UDC's LogInfo table lists only exchange fields; the base columns are not
    # something a file can switch off.
    contest = contest_from_udc(udc_for(MINIMAL + "LogInfo = Exchange1, 500\n"))
    assert contest.LogInfo == [*BASE_LOG_COLUMNS, "Exchange1"]


def test_a_udc_that_names_a_base_column_does_not_duplicate_it():
    contest = contest_from_udc(
        udc_for(MINIMAL + "LogInfo = Call, 500, Mode, 500, Exchange1, 500\n")
    )
    assert contest.LogInfo.count("Call") == 1
    assert contest.LogInfo.count("Mode") == 1


def test_an_empty_log_info_uses_the_standard_columns():
    contest = contest_from_udc(udc_for(MINIMAL))
    assert contest.LogInfo == list(ContestBase.LogInfo)


def test_a_log_column_with_no_not1mm_equivalent_is_dropped():
    udc = udc_for(MINIMAL + "LogInfo = Exchange1, 500, GridSquare, 500\n")
    contest = contest_from_udc(udc)
    assert contest.LogInfo == [*BASE_LOG_COLUMNS, "Exchange1"]
    assert "LogInfo:GridSquare" in contest.UdcUnimplemented
    assert "no log-window column for GridSquare" in messages(udc)


def test_unimplemented_parameters_are_recorded_on_the_class():
    udc = udc_for(MINIMAL + "MultWindowType = ARI\nBonusPoints = DL, 25\n")
    contest = contest_from_udc(udc)
    assert "MultWindowType" in contest.UdcUnimplemented
    assert "BonusPoints" in contest.UdcUnimplemented
    assert "parsed, but not applied" in messages(udc)


def test_the_whole_contest_section_is_kept():
    contest = contest_from_udc(udc_for(MINIMAL))
    assert contest.UdcRaw["Name"] == "TEST"
    assert contest.UdcRaw["EntryWindowInfo"].startswith("SNTText")
    assert contest.UdcAuthor == {"AuthorName": "Test", "Callsign": "K6GTE"}
    assert contest.UdcFile["Revision"] == "1.0.0"


def test_the_factory_refuses_errors():
    with pytest.raises(UdcError):
        contest_from_udc(udc_for(MINIMAL.replace("Mode = CW", "Mode = FM")))


def test_load_udc_binds_the_parent(tmp_path):
    path = tmp_path / "load-me.udc"
    path.write_text(MINIMAL, encoding="utf-8")
    parent = object()
    contest = load_udc(path, parent)
    assert contest.parent is parent
    assert contest.ContestName == "load-me"


# -- identity --------------------------------------------------------------


def test_two_files_that_share_a_name_get_distinct_identities():
    # AGCW-YLCWP-om.udc and AGCW-YLCWP-yl.udc both declare Name = AGCW-YLCWP
    # and CabrilloName = AGCW-YL-CWP.
    om = udc_for(MINIMAL.replace("Name = TEST", "Name = AGCW-YLCWP"), "AGCW-YLCWP-om")
    yl = udc_for(MINIMAL.replace("Name = TEST", "Name = AGCW-YLCWP"), "AGCW-YLCWP-yl")
    om_contest = contest_from_udc(om)
    yl_contest = contest_from_udc(yl)
    assert om_contest.UdcName == yl_contest.UdcName == "AGCW-YLCWP"
    assert om_contest.CabrilloName == yl_contest.CabrilloName
    assert om_contest.ContestName != yl_contest.ContestName
    assert {om_contest.ContestName, yl_contest.ContestName} == {
        "AGCW-YLCWP-om",
        "AGCW-YLCWP-yl",
    }


# -- the reference list ----------------------------------------------------


def test_the_contest_key_list_is_the_documented_size():
    # UDC-FIELDS.md counts 88 [Contest] parameters.  A new one belongs in both.
    assert len(CONTEST_KEYS) == 88
    # [Contest] + [Author] + [File] (the four metadata keys, one of which,
    # Note, is not in N1MM's list); the two spelling aliases resolve to keys
    # that are already counted.
    assert len(KNOWN_KEYS) == 88 + 3 + 4
