"""Tests for the Cabrillo export of QSOs without an exchange."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from not1mm.plugins import rsgb_iota, ukeidx


@pytest.mark.parametrize(
    "plugin,empty_exchange",
    [(ukeidx, "000 --"), (rsgb_iota, "0000 ------")],
)
def test_cabrillo_empty_exchange_logs_zero(
    plugin, empty_exchange, tmp_path, monkeypatch
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    ctx = MagicMock()
    ctx.station = {"Call": "DL1ABC"}
    ctx.contest_settings = {}
    ctx.database.get_ops.return_value = []
    ctx.database.fetch_all_contacts_asc.return_value = [
        {
            "TS": "2026-01-24 12:00:00",
            "Mode": "CW",
            "Freq": 14025.0,
            "StationPrefix": "DL1ABC",
            "SNT": "599",
            "SentNr": "",
            "Call": "G4ABC",
            "RCV": "599",
            "NR": "",
        }
    ]
    plugin.cabrillo(ctx, "ascii")
    assert "Cabrillo saved" in ctx.show_message_box.call_args[0][0]
    [logfile] = tmp_path.glob("*.log")
    qso = [x for x in logfile.read_text().splitlines() if x.startswith("QSO:")]
    assert len(qso) == 1
    assert f"599 {empty_exchange} G4ABC" in qso[0]
    assert qso[0].endswith(f"599 {empty_exchange}")
