"""Regression tests for DARC IARU Region 1 Field Day plugins."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from not1mm.lib.database import DataBase

REPO = Path(__file__).resolve().parents[1]
PLUGIN_PATHS = {
    "ssb": REPO / "not1mm/plugins/iaru_fieldday_r1_ssb.py",
    "cw": REPO / "not1mm/plugins/iaru_fieldday_r1_cw.py",
}


def load_plugin(kind: str):
    """Load a plugin without requiring the desktop GUI dependencies."""
    pyqt6 = types.ModuleType("PyQt6")
    pyqt6.QtWidgets = types.SimpleNamespace(
        QApplication=types.SimpleNamespace(translate=lambda _context, text: text)
    )
    plugin_common = types.ModuleType("not1mm.lib.plugin_common")
    plugin_common.gen_adif = lambda *args, **kwargs: None
    plugin_common.imp_adif = lambda *args, **kwargs: None
    plugin_common.get_points = lambda *args, **kwargs: 0
    plugin_common.online_score_xml = lambda *args, **kwargs: ""
    version = types.ModuleType("not1mm.lib.version")
    version.__version__ = "test"

    injected = {
        "PyQt6": pyqt6,
        "not1mm.lib.plugin_common": plugin_common,
        "not1mm.lib.version": version,
    }
    with patch.dict(sys.modules, injected):
        spec = importlib.util.spec_from_file_location(
            f"fieldday_{kind}_test", PLUGIN_PATHS[kind]
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


class Field:
    def __init__(self, value: str):
        self.value = value

    def text(self):
        return self.value


class FieldDayRegressionTests(unittest.TestCase):
    def test_database_dxcc_lookup_is_scoped_to_band(self):
        database = DataBase(":memory:", REPO / "not1mm/data", current_contest=5)
        try:
            database.exec_sql_commit(
                "INSERT INTO dxlog (ID, TS, Call, CountryPrefix, Band, ContestNR, Run1Run2, Continent) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("ID0", "2026-09-05 16:00:00", "DL1AAA", "DL", 7.0, 5, 0, "EU"),
            )
            self.assertEqual(
                database.fetch_dxcc_band_exists("DL", 14.0), {"dxcc_band_count": 0}
            )
            self.assertEqual(
                database.fetch_dxcc_band_exists("DL", 7.0), {"dxcc_band_count": 1}
            )
            self.assertEqual(
                database.fetch_dxcc_exists_before_me_on_band(
                    "DL", "2026-09-05 16:01:00", 7.0
                ),
                {"dxcc_band_count": 1},
            )
        finally:
            database.conn.close()

    def test_new_multiplier_is_scoped_to_band(self):
        for kind in PLUGIN_PATHS:
            with self.subTest(kind=kind):
                plugin = load_plugin(kind)
                
                database = DataBase(":memory:", REPO / "not1mm/data", current_contest=5)
                try:
                    app = types.SimpleNamespace(
                        contact={"CountryPrefix": "DL", "Band": 14.0},
                        sent=Field("59"),
                        receive=Field("59"),
                        other_1=Field("001"),
                        other_2=Field("001"),
                        database=database,
                    )
                    plugin.set_contact_vars(app)
                    self.assertEqual(app.contact["IsMultiplier1"], 1)

                    database.exec_sql_commit(
                        "INSERT INTO dxlog (ID, TS, Call, CountryPrefix, Band, ContestNR, Run1Run2, Continent) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("ID0", "2026-09-01 16:00:00", "DL1AAA", "DL", 7.0, 5, 0, "EU"),
                    )
                    plugin.set_contact_vars(app)
                    self.assertEqual(app.contact["IsMultiplier1"], 1)

                    database.exec_sql_commit(
                        "INSERT INTO dxlog (ID, TS, Call, CountryPrefix, Band, ContestNR, Run1Run2, Continent) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("ID1", "2026-09-02 16:00:00", "ON1AAB", "ON", 7.0, 5, 0, "EU"),
                    )
                    plugin.set_contact_vars(app)
                    self.assertEqual(app.contact["IsMultiplier1"], 1)

                    database.exec_sql_commit(
                        "INSERT INTO dxlog (ID, TS, Call, CountryPrefix, Band, ContestNR, Run1Run2, Continent) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("ID2", "2026-09-03 16:00:00", "ON1AAC", "ON", 14.0, 5, 0, "EU"),
                    )
                    plugin.set_contact_vars(app)
                    self.assertEqual(app.contact["IsMultiplier1"], 1)

                    database.exec_sql_commit(
                        "INSERT INTO dxlog (ID, TS, Call, CountryPrefix, Band, ContestNR, Run1Run2, Continent) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("ID3", "2026-09-04 16:00:00", "DL1AAD", "DL", 14.0, 5, 0, "EU"),
                    )
                    plugin.set_contact_vars(app)
                    self.assertEqual(app.contact["IsMultiplier1"], 0)
                finally:
                    database.conn.close()

    def test_recalculation_counts_same_entity_once_on_each_band(self):
        for kind in PLUGIN_PATHS:
            with self.subTest(kind=kind):
                plugin = load_plugin(kind)

                database = DataBase(":memory:", REPO / "not1mm/data", current_contest=5)
                try:
                    database.exec_sql_commit(
                        "INSERT INTO dxlog (ID, TS, Call, CountryPrefix, Band, ContestNR, Run1Run2, Continent) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("ID0", "2026-09-01 16:00:00", "DL1AAA", "DL", 7.0, 5, 0, "EU"),
                    )
                    database.exec_sql_commit(
                        "INSERT INTO dxlog (ID, TS, Call, CountryPrefix, Band, ContestNR, Run1Run2, Continent) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("ID2", "2026-09-02 16:00:00", "ON1AAB", "ON", 7.0, 5, 0, "EU"),
                    )
                    database.exec_sql_commit(
                        "INSERT INTO dxlog (ID, TS, Call, CountryPrefix, Band, ContestNR, Run1Run2, Continent) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("ID3", "2026-09-03 16:00:00", "DL1AAC", "DL", 7.0, 5, 0, "EU"),
                    )
                    database.exec_sql_commit(
                        "INSERT INTO dxlog (ID, TS, Call, CountryPrefix, Band, ContestNR, Run1Run2, Continent) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("ID4", "2026-09-04 16:00:00", "ON1AAD", "ON", 14.0, 5, 0, "EU"),
                    )
                    database.exec_sql_commit(
                        "INSERT INTO dxlog (ID, TS, Call, CountryPrefix, Band, ContestNR, Run1Run2, Continent) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("ID5", "2026-09-05 16:00:00", "ON1AAE", "ON", 14.0, 5, 0, "EU"),
                    )
                    database.exec_sql_commit(
                        "INSERT INTO dxlog (ID, TS, Call, CountryPrefix, Band, ContestNR, Run1Run2, Continent) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("ID6", "2026-09-06 16:00:00", "DL1AAF", "DL", 14.0, 5, 0, "EU"),
                    )


                    app = types.SimpleNamespace(
                        database=database,
                        station={"Call": "DM1ABC/P"},
                        contact_is_dupe=0,
                    )
                    plugin.recalculate_mults(app)
                    self.assertEqual(
                        [item["IsMultiplier1"] for item in database.fetch_all_contacts_asc()], [1, 1, 0, 1, 0, 1]
                    )
                finally:
                    database.conn.close()


if __name__ == "__main__":
    unittest.main()
