"""Run every contest plugin against its test log and compare the export 1:1.

Fixtures live in ``not1mm/contest/<plugin>[/<case>]/``: ``contest.adif`` is the
input, ``contest.json`` the fixture (station, contest settings, prefs) and
``contest.log`` (or ``contest.edi`` for VHF contests) the expected export.

These tests pin the ADIF-import and export-formatting behaviour of each plugin.
Contest *scoring* is asserted separately, because ``imp_adif`` does not run the
plugin's ``points()`` for every contest.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

import not1mm
from not1mm.lib import plugin_common

from contest_harness import (
    CONTEST_DIR,
    ContestHarness,
    DummyProgress,
    discover_cases,
    export_record_count,
    pin_versions,
    validate_adif_lengths,
)

CASES = discover_cases()


@pytest.fixture
def headless(monkeypatch, tmp_path):
    """Neutralise plugin_common's Qt bits and redirect ``Path.home()``."""
    monkeypatch.setattr(plugin_common, "QProgressDialog", DummyProgress)
    monkeypatch.setattr(
        plugin_common.QCoreApplication, "processEvents", staticmethod(lambda: None)
    )
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    return tmp_path


def test_every_plugin_has_a_fixture_directory():
    """Each contest plugin gets a ``not1mm/contest/<plugin>/`` home."""
    plugins = {
        path.stem
        for path in (Path(not1mm.__file__).parent / "plugins").glob("*.py")
        if path.stem != "__init__"
    }
    directories = {path.name for path in CONTEST_DIR.iterdir() if path.is_dir()}
    missing = sorted(plugins - directories)
    assert not missing, f"missing not1mm/contest/ directories: {missing}"


@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_contest_log(case, headless, monkeypatch):
    module = importlib.import_module(f"not1mm.plugins.{case.contest}")
    pin_versions(monkeypatch)

    validate_adif_lengths(case.adif)

    if not case.exports:
        pytest.skip(f"{case.id}: the plugin writes no Cabrillo/EDI log")

    expected = case.golden("edi" if hasattr(module, "edi") else "log")
    assert expected.exists(), f"{case.id}: missing golden {expected.name}"

    harness = ContestHarness(module, case, headless)
    plugin_common.import_adif(harness)

    produced = harness.export(headless)
    assert produced is not None, f"{case.id}: plugin produced no export"
    assert produced.read_bytes() == expected.read_bytes(), (
        f"{case.id}: export differs from {expected.name}"
    )


@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_contest_score(case, headless, monkeypatch):
    """The scored log must match the hand-checked numbers in contest.json."""
    expected = json.loads(case.config.read_text(encoding="utf-8"))["expected"]
    module = importlib.import_module(f"not1mm.plugins.{case.contest}")
    pin_versions(monkeypatch)

    harness = ContestHarness(module, case, headless)
    plugin_common.import_adif(harness)
    harness.score_log()

    assert module.show_qso(harness) == expected["qsos"], f"{case.id}: qso count"
    if expected["mults"] is not None:
        assert module.show_mults(harness) == expected["mults"], f"{case.id}: mults"
    assert module.calc_score(harness) == expected["score"], f"{case.id}: score"


@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_log_points_match_the_scoring(case, headless, monkeypatch):
    """The points recorded in the log must be what the plugin scores.

    N1MM and not1mm write the Points column into a log as APP_N1MM_POINTS, so
    every fixture contact carries what it is worth.  Scoring the imported log
    has to reproduce that contact by contact - the total in ``expected`` can
    hide two contacts trading points.
    """
    module = importlib.import_module(f"not1mm.plugins.{case.contest}")
    pin_versions(monkeypatch)

    text = case.adif.read_text(encoding="ascii", errors="replace")
    assert text.count("APP_N1MM_POINTS") == text.count("<EOR>") > 0, (
        f"{case.id}: every contact must carry APP_N1MM_POINTS"
    )

    harness = ContestHarness(module, case, headless)
    plugin_common.import_adif(harness)
    recorded = {
        (contact.get("Call", ""), str(contact.get("TS", ""))): int(
            contact.get("Points") or 0
        )
        for contact in harness.database.fetch_all_contacts_asc()
    }

    harness.score_log()
    scored = {
        (contact.get("Call", ""), str(contact.get("TS", ""))): int(
            contact.get("Points") or 0
        )
        for contact in harness.database.fetch_all_contacts_asc()
    }
    assert scored == recorded, f"{case.id}: the plugin scores differently from the log"


@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_dupes_are_exported(case, headless, monkeypatch):
    """Every logged contact reaches the output, duplicate contacts included."""
    expected = json.loads(case.config.read_text(encoding="utf-8"))["expected"]
    module = importlib.import_module(f"not1mm.plugins.{case.contest}")
    pin_versions(monkeypatch)

    # dupe_type 4 contests never de-dupe, and the dupe_type 5 checks compare
    # against the wall clock (a 2/3 hour window), which a historical timestamp
    # cannot exercise deterministically. Everywhere else a dupe must be logged.
    if getattr(module, "dupe_type", 4) in (1, 2, 3):
        assert expected.get("dupes", 0) >= 1, f"{case.id}: the log must exercise a dupe"

    if not case.exports:
        pytest.skip(f"{case.id}: the plugin writes no Cabrillo/EDI log")

    harness = ContestHarness(module, case, headless)
    plugin_common.import_adif(harness)
    logged = len(harness.database.fetch_all_contacts_asc())

    golden = case.golden("edi" if hasattr(module, "edi") else "log")
    written = export_record_count(golden)
    assert written == logged, (
        f"{case.id}: {golden.name} holds {written} QSO records but the log has "
        f"{logged} contacts; duplicate contacts must not be dropped"
    )
