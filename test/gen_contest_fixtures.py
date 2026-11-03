"""Generate the contest log corpus in not1mm/contest/.

Run from anywhere:

    python3 test/gen_contest_fixtures.py

For every contest listed below it writes ``not1mm/contest/<plugin>/`` a file set
per log: ``<case>.adif`` (input QSOs), ``<case>.json`` (station, contest
settings and the expected qsos/mults/score/dupes) and ``<case>.log`` or
``<case>.edi`` (the golden export).  Everything goes through the real
``imp_adif`` and ``cabrillo``/``edi`` using
:class:`contest_harness.ContestHarness`, so a golden is always reproducible
from its input.

The generated files are committed; re-running the script rewrites them
identically unless a plugin's behaviour changed, which is exactly the point of
the corpus.  ``<case>`` is conventionally the station callsign.

Contests whose scoring depends on where *your* station is get extra logs from
another part of the world (see the ``variants``/``_B2_VARIANTS`` tables).
"""
import importlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "test"))

from not1mm.lib import plugin_common  # noqa: E402
from contest_harness import (  # noqa: E402
    CONTEST_DIR,
    Case,
    ContestHarness,
    DummyProgress,
    pin_versions,
    validate_adif_lengths,
)

plugin_common.QProgressDialog = DummyProgress
plugin_common.QCoreApplication.processEvents = staticmethod(lambda: None)

# scratch area for the exports the harness produces before they are copied
# into the repository as goldens
OUT = Path(tempfile.gettempdir()) / "not1mm-fixture-gen"
DATE = "20260801"


def qso(**kw):
    return "".join(f"<{k}:{len(str(v))}>{v}" for k, v in kw.items()) + "<EOR>\n"


def adif(qsos):
    return "contest log for not1mm tests\n<ADIF_VER:5>3.1.7\n<EOH>\n" + "".join(qsos)


_ADIF_FIELD = re.compile(r"<([A-Za-z0-9_]+):(\d+)(?::[A-Za-z])?>")


def adif_fields(record: str) -> dict:
    """The fields of one fixture ADIF record, keyed by tag."""
    fields = {}
    for match in _ADIF_FIELD.finditer(record):
        fields[match.group(1)] = record[match.end() : match.end() + int(match.group(2))]
    return fields


def record_key(record: str) -> tuple:
    """The database key, (Call, TS), of one fixture ADIF record."""
    fields = adif_fields(record)
    date = fields.get("QSO_DATE", "")
    time_on = fields.get("TIME_ON", "").zfill(6)
    stamp = (
        f"{date[:4]}-{date[4:6]}-{date[6:8]} "
        f"{time_on[:2]}:{time_on[2:4]}:{time_on[4:6]}"
    )
    return (fields.get("CALL", ""), stamp)


def split_records(qsos: list) -> list:
    """The fixture's contacts as one ADIF record string each.

    Fixtures are normally written one record per entry, but ``_relocate`` and a
    few builders store a whole log as a single blob, which would otherwise get
    the points of its first contact bolted onto every one of them.
    """
    records = []
    for entry in qsos:
        for part in entry.split("<EOR>"):
            part = part.strip("\r\n")
            if part:
                records.append(part + "<EOR>\n")
    return records


def with_n1mm_points(record: str, points: int) -> str:
    """The ADIF record with APP_N1MM_POINTS set to *points*.

    N1MM and not1mm write the Points column into a log as an APP_ field, so
    every fixture contact carries what it was worth and the corpus can check
    the plugin scores the same.
    """
    record = re.sub(r"<APP_N1MM_POINTS:\d+>[^<]*", "", record)
    value = f"<APP_N1MM_POINTS:{len(str(points))}>{points}"
    return record.replace("<EOR>", value + "<EOR>", 1)


class MP:
    def setattr(self, obj, name, value):
        setattr(obj, name, value)


CATS = {
    "OperatorCategory": "SINGLE-OP",
    "AssistedCategory": "NON-ASSISTED",
    "BandCategory": "ALL",
    "ModeCategory": "CW",
    "PowerCategory": "HIGH",
    "TransmitterCategory": "ONE",
    "OverlayCategory": "N/A",
    # several plugins read the start date when working out dupe windows or the
    # EDI header, so give every contest one
    "StartDate": "2026-01-03 12:00:00",
}
STATION = {
    "Call": "K6GTE",
    "Name": "Sample Operator",
    "Street1": "1 Example Lane",
    "City": "Anytown",
    "State": "CA",
    "Zip": "00000",
    "Country": "United States",
    "Email": "sample@example.com",
    "GridSquare": "DM13",
    "ARRLSection": "ORG",
    "Club": "Example Contest Club",
    "STXeq": "IC-7300",
    "SAnte": "Dipole",
    "SAntH1": "10m",
}


def cw(call, freq, t, sl, sr, **extra):
    """A CW QSO with the licence-year exchange used by euhfc."""
    return qso(CALL=call, QSO_DATE=DATE, TIME_ON=t, FREQ=freq, MODE="CW",
               SNT="599", RCV="599", STX_STRING=sl, SRX_STRING=sr, **extra)


FIXTURES = {}

# ---------------------------------------------------------------- euhfc
# Points: 1 per EU contact, 0 otherwise (injected).  Mult: distinct
# (licence-year, band).  Dupe: same call + band + mode.
FIXTURES["euhfc"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "82"},
        "qsos": [
            cw("OK2ABC", "14.025", "120000", "82", "17", STATION_CALLSIGN="K6GTE",
               COUNTRYPREFIX="OK", CONTINENT="EU", APP_N1MM_POINTS="1"),
            qso(CALL="DL1ABC", QSO_DATE=DATE, TIME_ON="120500", FREQ="14.050",
                MODE="SSB", SNT="59", RCV="59", STX_STRING="82", SRX_STRING="21",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="DL", CONTINENT="EU",
                APP_N1MM_POINTS="1"),
            qso(CALL="OK2ABC", QSO_DATE=DATE, TIME_ON="121000", FREQ="14.055",
                MODE="SSB", SNT="59", RCV="59", STX_STRING="82", SRX_STRING="17",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="OK", CONTINENT="EU",
                APP_N1MM_POINTS="1"),
            cw("OK2ABC", "14.025", "121500", "82", "17", STATION_CALLSIGN="K6GTE",
               COUNTRYPREFIX="OK", CONTINENT="EU", APP_N1MM_POINTS="0"),
            cw("DL1ABC", "7.030", "130000", "82", "21", STATION_CALLSIGN="K6GTE",
               COUNTRYPREFIX="DL", CONTINENT="EU", APP_N1MM_POINTS="1"),
            cw("N0AX", "14.030", "130500", "82", "17", STATION_CALLSIGN="K6GTE",
               COUNTRYPREFIX="K", CONTINENT="NA", APP_N1MM_POINTS="0"),
            cw("S51ZZ", "21.040", "131000", "82", "17", STATION_CALLSIGN="K6GTE",
               COUNTRYPREFIX="S5", CONTINENT="EU", APP_N1MM_POINTS="1"),
            cw("W1AW", "7.040", "131500", "82", "66", STATION_CALLSIGN="K6GTE",
               COUNTRYPREFIX="W", CONTINENT="NA", APP_N1MM_POINTS="0"),
            cw("I2ABC", "14.035", "132000", "82", "21", STATION_CALLSIGN="K6GTE",
               COUNTRYPREFIX="I", CONTINENT="EU", APP_N1MM_POINTS="1"),
            qso(CALL="F5ABC", QSO_DATE=DATE, TIME_ON="132500", FREQ="28.050",
                MODE="SSB", SNT="59", RCV="59", STX_STRING="82", SRX_STRING="17",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="F", CONTINENT="EU",
                APP_N1MM_POINTS="1"),
        ],
    },
    "DL1ABC": {
        "station": {
            **STATION,
            "Call": "DL1ABC", "Name": "Sample Operator", "Street1": "1 Beispielweg",
            "City": "Musterstadt", "State": "", "Zip": "00000", "Country": "Germany",
            "Email": "dl1abc@example.com", "GridSquare": "JO31",
            "ARRLSection": "DX", "Club": "Example Contest Club",
        },
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "17"},
        "qsos": [
            cw("S51ZZ", "14.020", "100000", "17", "82", STATION_CALLSIGN="DL1ABC",
               COUNTRYPREFIX="S5", CONTINENT="EU", APP_N1MM_POINTS="1"),
            cw("OK2ABC", "14.045", "100500", "17", "17", STATION_CALLSIGN="DL1ABC",
               COUNTRYPREFIX="OK", CONTINENT="EU", APP_N1MM_POINTS="1"),
            cw("S51ZZ", "3.530", "101000", "17", "82", STATION_CALLSIGN="DL1ABC",
               COUNTRYPREFIX="S5", CONTINENT="EU", APP_N1MM_POINTS="1"),
            qso(CALL="W1AW", QSO_DATE=DATE, TIME_ON="101500", FREQ="14.030",
                MODE="SSB", SNT="59", RCV="59", STX_STRING="17", SRX_STRING="66",
                STATION_CALLSIGN="DL1ABC", COUNTRYPREFIX="W", CONTINENT="NA",
                APP_N1MM_POINTS="0"),
            cw("S51ZZ", "14.020", "102000", "17", "82", STATION_CALLSIGN="DL1ABC",
               COUNTRYPREFIX="S5", CONTINENT="EU", APP_N1MM_POINTS="0"),
            qso(CALL="I2ABC", QSO_DATE=DATE, TIME_ON="102500", FREQ="21.030",
                MODE="SSB", SNT="59", RCV="59", STX_STRING="17", SRX_STRING="17",
                STATION_CALLSIGN="DL1ABC", COUNTRYPREFIX="I", CONTINENT="EU",
                APP_N1MM_POINTS="1"),
        ],
    },
}

# ------------------------------------------------------------ na_sprint_cw
FIXTURES["na_sprint_cw"] = {
    "K0RX": {
        "station": {**STATION, "Call": "K0RX", "Name": "Sample Operator",
                    "State": "MN", "ARRLSection": "MN", "GridSquare": "EN34",
                    "Club": "Example Contest Club"},
        "contest_settings": {**CATS, "SentExchange": "DAVE MN"},
        "qsos": [
            qso(CALL="N6TR", QSO_DATE="20260913", TIME_ON="000100", FREQ="14.040",
                MODE="CW", SNT="599", RCV="599", SENTNR="1", NR="154",
                NAME="RICK", SECT="NC", STATION_CALLSIGN="K0RX"),
            qso(CALL="K7GM", QSO_DATE="20260913", TIME_ON="000300", FREQ="14.060",
                MODE="CW", SNT="599", RCV="599", SENTNR="2", NR="13",
                NAME="TREE", SECT="OR", STATION_CALLSIGN="K0RX"),
            qso(CALL="N6TR", QSO_DATE="20260913", TIME_ON="000500", FREQ="14.040",
                MODE="CW", SNT="599", RCV="599", SENTNR="3", NR="155",
                NAME="RICK", SECT="NC", STATION_CALLSIGN="K0RX"),
            qso(CALL="N6TR", QSO_DATE="20260913", TIME_ON="000700", FREQ="7.040",
                MODE="CW", SNT="599", RCV="599", SENTNR="4", NR="156",
                NAME="RICK", SECT="NC", STATION_CALLSIGN="K0RX"),
            qso(CALL="W4AA", QSO_DATE="20260913", TIME_ON="000900", FREQ="7.060",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="22",
                NAME="BOB", SECT="VA", STATION_CALLSIGN="K0RX"),
            qso(CALL="KH6AA", QSO_DATE="20260913", TIME_ON="001100", FREQ="14.045",
                MODE="CW", SNT="599", RCV="599", SENTNR="6", NR="7",
                NAME="AKI", SECT="HI", STATION_CALLSIGN="K0RX"),
            qso(CALL="XE1AA", QSO_DATE="20260913", TIME_ON="001300", FREQ="21.040",
                MODE="CW", SNT="599", RCV="599", SENTNR="7", NR="9",
                NAME="JUAN", SECT="XE", STATION_CALLSIGN="K0RX"),
            qso(CALL="VE3AA", QSO_DATE="20260913", TIME_ON="001500", FREQ="7.045",
                MODE="CW", SNT="599", RCV="599", SENTNR="8", NR="31",
                NAME="ANN", SECT="ON", STATION_CALLSIGN="K0RX"),
            qso(CALL="N6TR", QSO_DATE="20260913", TIME_ON="001700", FREQ="21.040",
                MODE="CW", SNT="599", RCV="599", SENTNR="9", NR="157",
                NAME="RICK", SECT="NC", STATION_CALLSIGN="K0RX"),
            qso(CALL="DL1AA", QSO_DATE="20260913", TIME_ON="001900", FREQ="14.050",
                MODE="CW", SNT="599", RCV="599", SENTNR="10", NR="33",
                NAME="HANS", SECT="DX", STATION_CALLSIGN="K0RX"),
        ],
    },
}

# ------------------------------------------------------------ cq_wpx_rtty
FIXTURES["cq_wpx_rtty"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "RTTY", "SentExchange": "001"},
        "qsos": [
            qso(CALL="DL1ABC", QSO_DATE=DATE, TIME_ON="120000", FREQ="14.085",
                MODE="RTTY", SNT="599", RCV="599", SENTNR="001", NR="123",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="DL", WPXPREFIX="DL1",
                CONTINENT="EU"),
            qso(CALL="JA1ABC", QSO_DATE=DATE, TIME_ON="120300", FREQ="14.090",
                MODE="RTTY", SNT="599", RCV="599", SENTNR="002", NR="456",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="JA", WPXPREFIX="JA1",
                CONTINENT="AS"),
            qso(CALL="DL1ABC", QSO_DATE=DATE, TIME_ON="120600", FREQ="21.085",
                MODE="RTTY", SNT="599", RCV="599", SENTNR="003", NR="789",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="DL", WPXPREFIX="DL1",
                CONTINENT="EU"),
            qso(CALL="DL1ABC", QSO_DATE=DATE, TIME_ON="120900", FREQ="14.085",
                MODE="RTTY", SNT="599", RCV="599", SENTNR="004", NR="999",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="DL", WPXPREFIX="DL1",
                CONTINENT="EU"),
            qso(CALL="W1AW", QSO_DATE=DATE, TIME_ON="121200", FREQ="7.085",
                MODE="RTTY", SNT="599", RCV="599", SENTNR="005", NR="111",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="W", WPXPREFIX="W1",
                CONTINENT="NA"),
            qso(CALL="VK2ABC", QSO_DATE=DATE, TIME_ON="121500", FREQ="14.095",
                MODE="RTTY", SNT="599", RCV="599", SENTNR="006", NR="222",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="VK", WPXPREFIX="VK2",
                CONTINENT="OC"),
            qso(CALL="PY1ABC", QSO_DATE=DATE, TIME_ON="121800", FREQ="21.090",
                MODE="RTTY", SNT="599", RCV="599", SENTNR="007", NR="333",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="PY", WPXPREFIX="PY1",
                CONTINENT="SA"),
            qso(CALL="DL1ABC", QSO_DATE=DATE, TIME_ON="122100", FREQ="7.085",
                MODE="RTTY", SNT="599", RCV="599", SENTNR="008", NR="444",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="DL", WPXPREFIX="DL1",
                CONTINENT="EU"),
            qso(CALL="UA3ABC", QSO_DATE=DATE, TIME_ON="122400", FREQ="14.100",
                MODE="RTTY", SNT="599", RCV="599", SENTNR="009", NR="555",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="UA", WPXPREFIX="UA3",
                CONTINENT="EU"),
            qso(CALL="JA1ABC", QSO_DATE=DATE, TIME_ON="122700", FREQ="21.090",
                MODE="RTTY", SNT="599", RCV="599", SENTNR="010", NR="666",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="JA", WPXPREFIX="JA1",
                CONTINENT="AS"),
        ],
    },
}

# ------------------------------------------------------------ ca_qso_party
FIXTURES["ca_qso_party"] = {
    "K6GTE": {
        "station": {**STATION, "Call": "K6GTE", "ARRLSection": "ORG"},
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "ORG"},
        "qsos": [
            qso(CALL="W6ABC", QSO_DATE="20261003", TIME_ON="160000", FREQ="7.200",
                MODE="SSB", SENTNR="1", NR="5", EXCHANGE1="SCLA",
                STATION_CALLSIGN="K6GTE", SECT="SCLA"),
            qso(CALL="N6XYZ", QSO_DATE="20261003", TIME_ON="160300", FREQ="14.040",
                MODE="CW", SENTNR="2", NR="12", EXCHANGE1="SDIE",
                STATION_CALLSIGN="K6GTE", SECT="SDIE"),
            qso(CALL="W6ABC", QSO_DATE="20261003", TIME_ON="160600", FREQ="14.040",
                MODE="CW", SENTNR="3", NR="5", EXCHANGE1="SCLA",
                STATION_CALLSIGN="K6GTE", SECT="SCLA"),
            qso(CALL="W6ABC", QSO_DATE="20261003", TIME_ON="160900", FREQ="7.200",
                MODE="SSB", SENTNR="4", NR="5", EXCHANGE1="SCLA",
                STATION_CALLSIGN="K6GTE", SECT="SCLA"),
            qso(CALL="K7ABC", QSO_DATE="20261003", TIME_ON="161200", FREQ="7.210",
                MODE="SSB", SENTNR="5", NR="8", EXCHANGE1="WA",
                STATION_CALLSIGN="K6GTE", SECT="WA"),
            qso(CALL="KH6ABC", QSO_DATE="20261003", TIME_ON="161500", FREQ="14.045",
                MODE="CW", SENTNR="6", NR="3", EXCHANGE1="HI",
                STATION_CALLSIGN="K6GTE", SECT="HI"),
            qso(CALL="VE7ABC", QSO_DATE="20261003", TIME_ON="161800", FREQ="21.040",
                MODE="CW", SENTNR="7", NR="2", EXCHANGE1="BC",
                STATION_CALLSIGN="K6GTE", SECT="BC"),
            qso(CALL="JA1ABC", QSO_DATE="20261003", TIME_ON="162100", FREQ="14.050",
                MODE="CW", SENTNR="8", NR="1", EXCHANGE1="DX",
                STATION_CALLSIGN="K6GTE", SECT="DX"),
            qso(CALL="W6ABC", QSO_DATE="20261003", TIME_ON="162400", FREQ="21.040",
                MODE="CW", SENTNR="9", NR="5", EXCHANGE1="SCLA",
                STATION_CALLSIGN="K6GTE", SECT="SCLA"),
            qso(CALL="N0ABC", QSO_DATE="20261003", TIME_ON="162700", FREQ="7.220",
                MODE="SSB", SENTNR="10", NR="7", EXCHANGE1="CO",
                STATION_CALLSIGN="K6GTE", SECT="CO"),
        ],
    },
}

# ----------------------------------------------------------- arrl_vhf_jun
FIXTURES["arrl_vhf_jun"] = {
    "K6GTE": {
        "station": {**STATION, "BandCategory": "2M"},
        "contest_settings": {**CATS, "BandCategory": "2M", "ModeCategory": "SSB+CW"},
        "qsos": [
            qso(CALL="W1AW", QSO_DATE="20260613", TIME_ON="180000", FREQ="144.200",
                MODE="SSB", SENTNR="DM13", NR="FN31", GRIDSQUARE="FN31",
                STATION_CALLSIGN="K6GTE", APP_N1MM_POINTS="1500"),
            qso(CALL="K6ABA", QSO_DATE="20260613", TIME_ON="180300", FREQ="144.250",
                MODE="CW", SENTNR="DM13", NR="DM04", GRIDSQUARE="DM04",
                STATION_CALLSIGN="K6GTE", APP_N1MM_POINTS="300"),
            qso(CALL="W1AW", QSO_DATE="20260613", TIME_ON="180600", FREQ="50.200",
                MODE="SSB", SENTNR="DM13", NR="FN31", GRIDSQUARE="FN31",
                STATION_CALLSIGN="K6GTE", APP_N1MM_POINTS="2200"),
            qso(CALL="W1AW", QSO_DATE="20260613", TIME_ON="180900", FREQ="144.200",
                MODE="SSB", SENTNR="DM13", NR="FN31", GRIDSQUARE="FN31",
                STATION_CALLSIGN="K6GTE", APP_N1MM_POINTS="0"),
            qso(CALL="N6XYZ", QSO_DATE="20260613", TIME_ON="181200", FREQ="432.100",
                MODE="CW", SENTNR="DM13", NR="CM87", GRIDSQUARE="CM87",
                STATION_CALLSIGN="K6GTE", APP_N1MM_POINTS="500"),
            qso(CALL="K7ABC", QSO_DATE="20260613", TIME_ON="181500", FREQ="144.300",
                MODE="SSB", SENTNR="DM13", NR="CN85", GRIDSQUARE="CN85",
                STATION_CALLSIGN="K6GTE", APP_N1MM_POINTS="1200"),
        ],
    },
    # A station outside W/VE only gets credit for W/VE contacts (rule 1), so
    # the OK2ABC and JA1ABC QSOs earn neither points nor a multiplier here.
    "DL1ABC": {
        "station": {**STATION, "Call": "DL1ABC", "Country": "Germany",
                    "State": "", "GridSquare": "JN58", "ARRLSection": "DX",
                    "Email": "dl1abc@example.com"},
        "contest_settings": {**CATS, "BandCategory": "ALL",
                             "ModeCategory": "SSB+CW", "SentExchange": "JN58"},
        "qsos": [
            qso(CALL="W1AW", QSO_DATE="20260613", TIME_ON="180000", FREQ="144.200",
                MODE="SSB", SENTNR="JN58", NR="FN31", GRIDSQUARE="FN31",
                STATION_CALLSIGN="DL1ABC", APP_N1MM_POINTS="1500"),
            qso(CALL="OK2ABC", QSO_DATE="20260613", TIME_ON="180300", FREQ="144.250",
                MODE="CW", SENTNR="JN58", NR="JO70", GRIDSQUARE="JO70",
                STATION_CALLSIGN="DL1ABC", APP_N1MM_POINTS="300"),
            qso(CALL="N6XYZ", QSO_DATE="20260613", TIME_ON="180600", FREQ="50.200",
                MODE="SSB", SENTNR="JN58", NR="CM87", GRIDSQUARE="CM87",
                STATION_CALLSIGN="DL1ABC", APP_N1MM_POINTS="2200"),
            qso(CALL="JA1ABC", QSO_DATE="20260613", TIME_ON="180900", FREQ="432.100",
                MODE="CW", SENTNR="JN58", NR="PM95", GRIDSQUARE="PM95",
                STATION_CALLSIGN="DL1ABC", APP_N1MM_POINTS="500"),
            qso(CALL="W1AW", QSO_DATE="20260613", TIME_ON="181200", FREQ="144.200",
                MODE="SSB", SENTNR="JN58", NR="FN31", GRIDSQUARE="FN31",
                STATION_CALLSIGN="DL1ABC", APP_N1MM_POINTS="0"),
        ],
    },
}

# ----------------------------------------------------------- EA contests
# EA stations score 2 points with EA and 1 with DX; DX stations score 3 with
# EA and 1 with DX.  Each band counts the EADX-100 entities, the Spanish
# provinces and the contest's special station - EF0F (which sends SMR) for
# CW/SSB, EA4URE (which sends HQ) and the USA/VE/JA/VK call areas for RTTY.
_EA1ABC = {
    **STATION,
    "Call": "EA1ABC",
    "Country": "Spain",
    "State": "",
    "GridSquare": "IN80",
    "ARRLSection": "DX",
    "Email": "ea1abc@example.com",
}


def _mk_qso(mode, call, time_on, freq, sent, nr, station, prefix, continent):
    """One hand-written EA contact."""
    return qso(
        CALL=call,
        QSO_DATE="20260516",
        TIME_ON=time_on,
        FREQ=freq,
        MODE=mode,
        SNT="59" if mode == "SSB" else "599",
        RCV="59" if mode == "SSB" else "599",
        SENTNR=sent,
        NR=nr,
        COUNTRYPREFIX=prefix,
        CONTINENT=continent,
        STATION_CALLSIGN=station,
    )


def _ea_majestad_fixtures(mode):
    """The same log for the King of Spain CW and SSB contests."""
    return {
        "EA1ABC": {
            "station": _EA1ABC,
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "M"},
            "qsos": [
                _mk_qso(mode, "EA4XYZ", "120000", "14.020", "M", "M", "EA1ABC", "EA", "EU"),
                _mk_qso(mode, "EF0F", "120200", "14.025", "M", "SMR", "EA1ABC", "EA", "EU"),
                _mk_qso(mode, "DL1ABC", "120400", "14.030", "M", "101", "EA1ABC", "DL", "EU"),
                _mk_qso(mode, "EA4XYZ", "120600", "14.020", "M", "102", "EA1ABC", "EA", "EU"),
                _mk_qso(mode, "EA5XYZ", "121000", "7.020", "M", "A", "EA1ABC", "EA", "EU"),
                _mk_qso(mode, "K6GTE", "121200", "7.025", "M", "103", "EA1ABC", "K", "NA"),
            ],
        },
        "K6GTE": {
            "station": STATION,
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "001"},
            "qsos": [
                _mk_qso(mode, "EA4ABC", "120000", "14.020", "1", "M", "K6GTE", "EA", "EU"),
                _mk_qso(mode, "EF0F", "120200", "14.025", "2", "SMR", "K6GTE", "EA", "EU"),
                _mk_qso(mode, "DL1ABC", "120400", "14.030", "3", "001", "K6GTE", "DL", "EU"),
                _mk_qso(mode, "EA4ABC", "120600", "14.020", "4", "002", "K6GTE", "EA", "EU"),
                _mk_qso(mode, "VE3ABC", "121000", "7.020", "5", "003", "K6GTE", "VE", "NA"),
                _mk_qso(mode, "EA5XYZ", "121200", "7.025", "6", "A", "K6GTE", "EA", "EU"),
            ],
        },
    }


FIXTURES["ea_majestad_cw"] = _ea_majestad_fixtures("CW")
FIXTURES["ea_majestad_ssb"] = _ea_majestad_fixtures("SSB")

# The RTTY contest also counts the call areas of the USA, Canada, Japan and
# Australia, and EA4URE; KH6 and VK are in the logs so the US area cty.dat
# reports as its own entity is exercised.
FIXTURES["ea_rtty"] = {
    "EA1ABC": {
        "station": _EA1ABC,
        "contest_settings": {**CATS, "ModeCategory": "RTTY", "SentExchange": "M"},
        "qsos": [
            _mk_qso("RTTY", "EA4XYZ", "120000", "14.070", "M", "M", "EA1ABC", "EA", "EU"),
            _mk_qso("RTTY", "EA4URE", "120200", "14.075", "M", "HQ", "EA1ABC", "EA", "EU"),
            _mk_qso("RTTY", "DL1ABC", "120400", "14.080", "M", "101", "EA1ABC", "DL", "EU"),
            _mk_qso("RTTY", "EA4XYZ", "120600", "14.070", "M", "102", "EA1ABC", "EA", "EU"),
            _mk_qso("RTTY", "VE3ABC", "121000", "7.040", "M", "103", "EA1ABC", "VE", "NA"),
            _mk_qso("RTTY", "EA5XYZ", "121200", "7.045", "M", "A", "EA1ABC", "EA", "EU"),
        ],
    },
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "RTTY", "SentExchange": "001"},
        "qsos": [
            _mk_qso("RTTY", "EA4ABC", "120000", "14.070", "1", "M", "K6GTE", "EA", "EU"),
            _mk_qso("RTTY", "EA4URE", "120200", "14.075", "2", "HQ", "K6GTE", "EA", "EU"),
            _mk_qso("RTTY", "KH6ABC", "120400", "14.080", "3", "001", "K6GTE", "KH6", "OC"),
            _mk_qso("RTTY", "VK2ABC", "120600", "14.085", "4", "002", "K6GTE", "VK", "OC"),
            _mk_qso("RTTY", "EA4ABC", "120800", "14.070", "5", "003", "K6GTE", "EA", "EU"),
            _mk_qso("RTTY", "VE3ABC", "121000", "7.040", "6", "004", "K6GTE", "VE", "NA"),
            _mk_qso("RTTY", "EA5XYZ", "121200", "7.045", "7", "A", "K6GTE", "EA", "EU"),
        ],
    },
}

# ----------------------------------------------------- iaru_fieldday_r1_*
# Fixed station to fixed station is nothing; a fixed entrant scores 2 from a
# European portable and 6 from one outside Europe, and 2 or 3 from fixed
# stations in or outside Europe.  A portable entrant scores all four.
def _iaru_fd_fixtures(mode):
    """The same log for the IARU R1 Field Day CW and SSB contests."""

    def qsos_for(station):
        return [
            _mk_qso(mode, "DL2ABC", "120000", "14.040", "1", "2", station, "DL", "EU"),
            _mk_qso(mode, "DL3ABC/P", "120200", "14.045", "1", "3", station, "DL", "EU"),
            _mk_qso(mode, "K6GTE", "120400", "14.050", "1", "4", station, "K", "NA"),
            _mk_qso(mode, "W1AW/P", "120600", "14.055", "1", "5", station, "K", "NA"),
            _mk_qso(mode, "DL3ABC/P", "120800", "14.045", "1", "6", station, "DL", "EU"),
        ]

    return {
        # A fixed station: the two fixed-to-fixed contacts score nothing.
        "DL1ABC": {
            "station": {
                **STATION,
                "Call": "DL1ABC",
                "Country": "Germany",
                "State": "",
                "GridSquare": "JN58",
                "ARRLSection": "DX",
                "Email": "dl1abc@example.com",
            },
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "1"},
            "qsos": qsos_for("DL1ABC"),
        },
        # The same log from a portable station, where all four count.
        "DL2ABC": {
            "station": {
                **STATION,
                "Call": "DL2ABC/P",
                "Country": "Germany",
                "State": "",
                "GridSquare": "JN58",
                "ARRLSection": "DX",
                "Email": "dl2abc@example.com",
            },
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "1"},
            "qsos": qsos_for("DL2ABC/P"),
        },
    }


FIXTURES["iaru_fieldday_r1_cw"] = _iaru_fd_fixtures("CW")
FIXTURES["iaru_fieldday_r1_ssb"] = _iaru_fd_fixtures("SSB")

# --------------------------------------------------- john_moyle_field_day
# Phone is one point and CW two, and a contact scores when either end is in
# VK, ZL or P2: those stations score for everyone, while a station outside
# Oceania scores nothing for a contact outside it too.  A multiplier is each
# new VK/ZL/P2 prefix per band, per mode and per three-hour block (eight
# blocks from 0100 UTC), and a station may be worked once in each - so a
# repeat inside a block scores nothing and one in the next block scores
# again.  No prefix is written here: recalculate_mults() fills them from cty.
def _jm_contact(station, call, time_on, freq, mode, sentnr, nr):
    return qso(
        CALL=call,
        QSO_DATE="20260321",
        TIME_ON=time_on,
        FREQ=freq,
        MODE=mode,
        SNT="59" if mode == "SSB" else "599",
        RCV="59" if mode == "SSB" else "599",
        SENTNR=sentnr,
        NR=nr,
        STATION_CALLSIGN=station,
    )


FIXTURES["john_moyle_field_day"] = {
    "VK2ABC": {
        "station": {
            **STATION,
            "Call": "VK2ABC",
            "Country": "Australia",
            "State": "",
            "GridSquare": "QF56",
            "ARRLSection": "DX",
            "Email": "vk2abc@example.com",
        },
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "1"},
        "qsos": [
            # Block 0: VK3XYZ twice on the same band and mode, so the second
            # is a duplicate.
            _jm_contact("VK2ABC", "VK3XYZ", "020000", "7.030", "CW", "1", "2"),
            _jm_contact("VK2ABC", "VK3XYZ", "023000", "7.030", "CW", "1", "3"),
            # Block 1: the same station again, which is not.
            _jm_contact("VK2ABC", "VK3XYZ", "050000", "7.030", "CW", "1", "4"),
            _jm_contact("VK2ABC", "ZL1ABC", "053000", "14.030", "SSB", "2", "5"),
            # Block 2, then block 3.
            _jm_contact("VK2ABC", "P29ABC", "080000", "21.030", "CW", "3", "6"),
            _jm_contact("VK2ABC", "K6GTE", "110000", "28.030", "CW", "4", "7"),
        ],
    },
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "1"},
        "qsos": [
            _jm_contact("K6GTE", "VK2ABC", "020000", "7.030", "CW", "1", "2"),
            _jm_contact("K6GTE", "ZL1ABC", "050000", "14.030", "SSB", "2", "3"),
            # A station outside Oceania scores nothing for one outside it.
            _jm_contact("K6GTE", "DL1ABC", "080000", "21.030", "CW", "3", "4"),
            # Block 2 again: one that is not a duplicate, then one that is.
            _jm_contact("K6GTE", "VK2ABC", "083000", "7.030", "CW", "4", "5"),
            _jm_contact("K6GTE", "VK2ABC", "084500", "7.030", "CW", "5", "6"),
        ],
    },
}

# ------------------------------------------------------------ trans_tasman
# VK and ZL stations only, on 160, 80 and 40m, in three two-hour blocks from
# 0800 UTC.  A station may be worked once per band and mode in each block for
# one point, each different VK/ZL prefix counts once per band per block, and
# the score is the sum over the blocks of contacts x prefixes.  No prefix is
# written: recalculate_mults() fills them from cty.
def _tt_contact(station, call, time_on, freq, mode, sentnr, nr):
    return qso(
        CALL=call,
        QSO_DATE="20260718",
        TIME_ON=time_on,
        FREQ=freq,
        MODE=mode,
        SNT="59" if mode == "SSB" else "599",
        RCV="59" if mode == "SSB" else "599",
        SENTNR=sentnr,
        NR=nr,
        STATION_CALLSIGN=station,
    )


FIXTURES["trans_tasman"] = {
    "VK2ABC": {
        "station": {
            **STATION,
            "Call": "VK2ABC",
            "Country": "Australia",
            "State": "",
            "GridSquare": "QF56",
            "ARRLSection": "DX",
            "Email": "vk2abc@example.com",
        },
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "001"},
        "qsos": [
            # Block 0 (0800-1000): VK3XYZ on 80m CW twice, then on 40m.
            _tt_contact("VK2ABC", "VK3XYZ", "080000", "3.505", "CW", "001", "001"),
            _tt_contact("VK2ABC", "ZL1ABC", "081000", "3.515", "SSB", "002", "002"),
            _tt_contact("VK2ABC", "VK3XYZ", "082000", "3.505", "CW", "003", "003"),
            _tt_contact("VK2ABC", "VK5ABC", "083000", "7.030", "CW", "004", "004"),
            _tt_contact("VK2ABC", "VK3XYZ", "084000", "7.030", "CW", "005", "005"),
            # Block 1 (1000-1200): the same station and band as block 0, which
            # is a new contact, and two more prefixes.
            _tt_contact("VK2ABC", "VK3XYZ", "100500", "3.505", "CW", "006", "006"),
            _tt_contact("VK2ABC", "ZL2DEF", "101500", "3.515", "SSB", "007", "007"),
            _tt_contact("VK2ABC", "VK4ABC", "102500", "7.035", "SSB", "008", "008"),
            # Block 2 (1200-1400).
            _tt_contact("VK2ABC", "ZL1ABC", "120500", "3.505", "CW", "009", "009"),
            _tt_contact("VK2ABC", "VK6ABC", "121500", "7.040", "SSB", "010", "010"),
        ],
    },
    "ZL1ABC": {
        "station": {
            **STATION,
            "Call": "ZL1ABC",
            "Country": "New Zealand",
            "State": "",
            "GridSquare": "RF73",
            "ARRLSection": "DX",
            "Email": "zl1abc@example.com",
        },
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "001"},
        "qsos": [
            # Block 0: VK2ABC on 80m SSB twice, so the second is a duplicate.
            _tt_contact("ZL1ABC", "VK2ABC", "080000", "3.505", "SSB", "001", "001"),
            _tt_contact("ZL1ABC", "ZL2DEF", "081000", "3.515", "CW", "002", "002"),
            _tt_contact("ZL1ABC", "VK2ABC", "082000", "3.505", "SSB", "003", "003"),
            _tt_contact("ZL1ABC", "VK4ABC", "083000", "7.030", "CW", "004", "004"),
            # Block 1.
            _tt_contact("ZL1ABC", "VK2ABC", "100500", "3.505", "SSB", "005", "005"),
            _tt_contact("ZL1ABC", "ZL2DEF", "101500", "7.030", "CW", "006", "006"),
            # Block 2.
            _tt_contact("ZL1ABC", "VK3XYZ", "120500", "3.505", "CW", "007", "007"),
        ],
    },
}

# --------------------------------------------------------------- agcw_qrp
# AGCW QRP Contest, CW.  The QSO points depend on the two stations' power
# classes - QRO against QRO is nothing, QRO or MP against QRP or VLP is two,
# and only QRP against QRP or VLP is three - and a multiplier is each AGCW
# member once per band.  The old corpus was all QRP and VLP (three points),
# so it pinned the bug rather than catching it.
_AGCW_DL_STATION = {
    **STATION,
    "Call": "DL1ABC",
    "Country": "Germany",
    "State": "",
    "GridSquare": "JN58",
    "ARRLSection": "DX",
    "Email": "dl1abc@example.com",
}
_AGCW_SM_STATION = {
    **STATION,
    "Call": "SM5XYZ",
    "Country": "Sweden",
    "State": "",
    "GridSquare": "JO89",
    "ARRLSection": "DX",
    "Email": "sm5xyz@example.com",
}


def _agcw_contact(station, call, time_on, freq, sent, nr, date="20260314"):
    return qso(
        CALL=call,
        QSO_DATE=date,
        TIME_ON=time_on,
        FREQ=freq,
        MODE="CW",
        SNT="599",
        RCV="599",
        SENTNR=sent,
        NR=nr,
        STATION_CALLSIGN=station,
    )


FIXTURES["agcw_qrp"] = {
    # A QRO entrant: QRO against QRO scores nothing, and everything else it
    # works is two points.
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "CW", "PowerCategory": "HIGH",
                             "SentExchange": "001/QRO/1234"},
        "qsos": [
            # QRO against QRO: no points, but the member still multiplies
            _agcw_contact("K6GTE", "DL1ABC", "140000", "21.010",
                          "001/QRO/1234", "002/QRO/2345"),
            # QRO against QRP: two points, 3456 is a new member on 15m
            _agcw_contact("K6GTE", "DL2ABC", "140003", "21.015",
                          "002/QRO/1234", "003/QRP/3456"),
            # against MP: two points, and NM is no member
            _agcw_contact("K6GTE", "DL3ABC", "140006", "21.020",
                          "003/QRO/1234", "004/MP/NM"),
            # against VLP: two points, 4567 is a new member on 40m
            _agcw_contact("K6GTE", "DL4ABC", "140009", "7.010",
                          "004/QRO/1234", "005/VLP/4567"),
            # a duplicate on 15m
            _agcw_contact("K6GTE", "DL1ABC", "140012", "21.010",
                          "005/QRO/1234", "006/QRO/2345"),
            # 3456 already multiplied on 15m
            _agcw_contact("K6GTE", "DL5ABC", "140015", "21.025",
                          "006/QRO/1234", "007/QRP/3456"),
        ],
    },
    # A QRP entrant: three points against QRP and VLP, two against everything
    # else.
    "DL1ABC": {
        "station": _AGCW_DL_STATION,
        "contest_settings": {**CATS, "ModeCategory": "CW", "PowerCategory": "QRP",
                             "SentExchange": "001/QRP/1234"},
        "qsos": [
            _agcw_contact("DL1ABC", "OK2ABC", "140000", "3.505",
                          "001/QRP/1234", "002/QRP/2345"),
            _agcw_contact("DL1ABC", "OK3ABC", "140003", "3.510",
                          "002/QRP/1234", "003/VLP/3456"),
            _agcw_contact("DL1ABC", "OK4ABC", "140006", "3.515",
                          "003/QRP/1234", "004/MP/4567"),
            _agcw_contact("DL1ABC", "OK5ABC", "140009", "3.520",
                          "004/QRP/1234", "005/QRO/5678"),
            _agcw_contact("DL1ABC", "OK2ABC", "140012", "3.505",
                          "005/QRP/1234", "006/QRP/2345"),
            _agcw_contact("DL1ABC", "OK6ABC", "140015", "7.010",
                          "006/QRP/1234", "007/QRP/2345"),
        ],
    },
    # An MP entrant (the dialog calls it Low): two points against everything.
    "SM5XYZ": {
        "station": _AGCW_SM_STATION,
        "contest_settings": {**CATS, "ModeCategory": "CW", "PowerCategory": "LOW",
                             "SentExchange": "001/MP/1111"},
        "qsos": [
            _agcw_contact("SM5XYZ", "DL1ABC", "140000", "3.505",
                          "001/MP/1111", "002/QRP/2345"),
            _agcw_contact("SM5XYZ", "DL2ABC", "140003", "3.510",
                          "002/MP/1111", "003/VLP/3456"),
            _agcw_contact("SM5XYZ", "DL3ABC", "140006", "3.515",
                          "003/MP/1111", "004/MP/4567"),
            _agcw_contact("SM5XYZ", "DL4ABC", "140009", "3.520",
                          "004/MP/1111", "005/QRO/5678"),
            _agcw_contact("SM5XYZ", "DL1ABC", "140012", "3.505",
                          "005/MP/1111", "006/QRP/2345"),
            _agcw_contact("SM5XYZ", "DL5ABC", "140015", "7.010",
                          "006/MP/1111", "007/QRP/2345"),
        ],
    },
}

# ------------------------------------------------------- wia_remembrance
# WIA Remembrance Day Contest.  A contact is one point, two on 160m and two on
# 23cm and above, CW and RTTY double it, and a contact between 0100 and 0600
# local time triples it - "local" being the machine's, which the harness pins
# to UTC.  A station may be worked once per band within three hours, and rule
# 9.3a groups the modes: FM and SSB count as one mode, CW and RTTY as another.
# There are no multipliers.
def _rd_contact(call, time_on, freq, mode, nr):
    return qso(
        CALL=call,
        QSO_DATE="20260808",
        TIME_ON=time_on,
        FREQ=freq,
        MODE=mode,
        SNT="59" if mode in ("SSB", "FM") else "599",
        RCV="59" if mode in ("SSB", "FM") else "599",
        SENTNR="001",
        NR=nr,
        STATION_CALLSIGN="K6GTE",
    )


FIXTURES["wia_remembrance"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "001"},
        "qsos": [
            # 160m CW inside the window: (1+1) x 2 x 3
            _rd_contact("VK2ABC", "020000", "1.830", "CW", "001"),
            # 80m phone inside it: 1 x 3
            _rd_contact("VK3XYZ", "020500", "3.550", "SSB", "002"),
            # the same station, band and mode inside three hours
            _rd_contact("VK2ABC", "023000", "1.830", "CW", "003"),
            # 23cm CW inside the window: (1+1) x 2 x 3
            _rd_contact("VK4ABC", "030000", "1296.100", "CW", "004"),
            # FM is the same mode as SSB for the window (rule 9.3a), so this
            # is a duplicate of the 0205 phone contact
            _rd_contact("VK3XYZ", "031000", "3.550", "FM", "005"),
            # the same station, well past the three hours: it counts
            _rd_contact("VK3XYZ", "070000", "3.550", "SSB", "006"),
            # RTTY doubles, outside the window
            _rd_contact("VK5ABC", "080000", "7.030", "RTTY", "007"),
            # CW is the same mode as RTTY, so this is a duplicate too
            _rd_contact("VK5ABC", "081000", "7.030", "CW", "008"),
        ],
    },
}

# ------------------------------------------------------------------- raem
# Ernst Krenkel Memorial, CW on 80m to 10m.  50 points for the QSO, one more
# for every degree of latitude difference and again for longitude - the
# hemisphere letters set the sign and the longitude is the shorter way round -
# 100 more for a station inside the polar circles, and 300 more for working
# the RAEM memorial station itself.  An entrant inside the polar circles
# multiplies its score by 1.1.
def _raem_contact(station, call, time_on, freq, coords, sentnr, nr):
    return qso(
        CALL=call,
        QSO_DATE="20261227",
        TIME_ON=time_on,
        FREQ=freq,
        MODE="CW",
        SNT="599",
        RCV="599",
        SENTNR=sentnr,
        NR=nr,
        EXCHANGE1=coords,
        STATION_CALLSIGN=station,
    )


FIXTURES["raem"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "CW", "SentExchange": "33N117W"},
        "qsos": [
            # 50 + 22 latitude + 154 longitude
            _raem_contact("K6GTE", "UA3ABC", "000000", "3.505", "55N037O", "001", "001"),
            # the memorial station itself adds 300
            _raem_contact("K6GTE", "RAEM", "000200", "7.025", "55N037O", "002", "002"),
            # 69 north is inside the polar circle, and adds 100
            _raem_contact("K6GTE", "LA1ABC", "000400", "7.030", "69N018O", "003", "003"),
            # the southern hemisphere, and the shorter way round the globe
            _raem_contact("K6GTE", "ZL1ABC", "000600", "14.025", "36S174O", "004", "004"),
            # a duplicate, worked once per band
            _raem_contact("K6GTE", "UA3ABC", "000800", "3.505", "55N037O", "005", "005"),
        ],
    },
    "LA1ABC": {
        "station": {
            **STATION,
            "Call": "LA1ABC",
            "Country": "Norway",
            "State": "",
            "GridSquare": "JP99",
            "ARRLSection": "DX",
            "Email": "la1abc@example.com",
        },
        "contest_settings": {**CATS, "ModeCategory": "CW", "SentExchange": "69N018O"},
        "qsos": [
            # a polar entrant, so the whole score is multiplied by 1.1
            _raem_contact("LA1ABC", "UA3ABC", "000000", "3.505", "55N037O", "001", "001"),
            _raem_contact("LA1ABC", "K6GTE", "000200", "14.025", "33N117W", "002", "002"),
            # a duplicate on the band it was already worked
            _raem_contact("LA1ABC", "UA3ABC", "000400", "3.505", "55N037O", "003", "003"),
        ],
    },
}

# -------------------------------------------------------------- canada_day
# RAC Canada Day.  A RAC official station is 20 points, any other Canadian
# station 10 and a DX station 2, and the multiplier is each Canadian
# province/territory - which is what a VE station sends - once per band per
# mode.  A DX station sends a serial number instead, so it adds none.
def _cd_contact(station, call, time_on, freq, mode, nr, sentnr):
    return qso(
        CALL=call,
        QSO_DATE="20260701",
        TIME_ON=time_on,
        FREQ=freq,
        MODE=mode,
        SNT="59" if mode == "SSB" else "599",
        RCV="59" if mode == "SSB" else "599",
        SENTNR=sentnr,
        NR=nr,
        STATION_CALLSIGN=station,
    )


FIXTURES["canada_day"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "001"},
        "qsos": [
            # a province, a RAC official station, a serial, then the same
            # province on another band and mode, and the duplicate
            _cd_contact("K6GTE", "VE3ABC", "000000", "3.505", "CW", "ON", "001"),
            _cd_contact("K6GTE", "VE1RAC", "000200", "3.515", "CW", "NS", "002"),
            _cd_contact("K6GTE", "DL1ABC", "000400", "3.525", "CW", "001", "003"),
            _cd_contact("K6GTE", "VE3ABC", "000600", "7.025", "SSB", "ON", "004"),
            _cd_contact("K6GTE", "VE3ABC", "000800", "3.505", "CW", "ON", "005"),
            _cd_contact("K6GTE", "VE6ABC", "001000", "3.535", "SSB", "AB", "006"),
            _cd_contact("K6GTE", "W1AW", "001200", "7.035", "CW", "005", "007"),
        ],
    },
    "VE3ABC": {
        "station": {
            **STATION,
            "Call": "VE3ABC",
            "Country": "Canada",
            "State": "ON",
            "GridSquare": "FN03",
            "ARRLSection": "ON",
            "Email": "ve3abc@example.com",
        },
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "ON"},
        "qsos": [
            _cd_contact("VE3ABC", "VA2RAC", "000000", "3.505", "CW", "QC", "001"),
            _cd_contact("VE3ABC", "VE1ABC", "000200", "3.515", "CW", "NS", "002"),
            _cd_contact("VE3ABC", "DL1ABC", "000400", "7.025", "SSB", "001", "003"),
            _cd_contact("VE3ABC", "VE1ABC", "000600", "3.515", "CW", "NS", "004"),
            _cd_contact("VE3ABC", "VE5ABC", "000800", "7.035", "CW", "SK", "005"),
        ],
    },
}

# -------------------------------------------------------- ssa_mt_cw/_ssb
# Two points per valid QSO, and a multiplier is each contacted locator square -
# the first four characters - once per band.  The exchange is report, serial
# and locator, so the locator goes in EXCHANGE1 and the serial in NR, which is
# where the plugin reads them from.
def _ssa_mt_fixtures(mode):
    """The same log for the SSA Manadstest CW and SSB passes."""
    rpt = "59" if mode == "SSB" else "599"

    def contact(call, time_on, freq, sent, nr, locator, station, prefix):
        return qso(
            CALL=call,
            QSO_DATE="20260913",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT=rpt,
            RCV=rpt,
            SENTNR=sent,
            NR=nr,
            EXCHANGE1=locator,
            COUNTRYPREFIX=prefix,
            CONTINENT="EU" if prefix != "K" else "NA",
            STATION_CALLSIGN=station,
        )

    return {
        "SM5XYZ": {
            "station": {
                **STATION,
                "Call": "SM5XYZ",
                "Country": "Sweden",
                "State": "",
                "GridSquare": "JO89",
                "ARRLSection": "DX",
                "Email": "sm5xyz@example.com",
            },
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "JO89"},
            "qsos": [
                contact("SM3ABC", "140000", "3.525", "1", "02", "JP75", "SM5XYZ", "SM"),
                contact("SM6DEF", "140200", "3.530", "1", "03", "JO65", "SM5XYZ", "SM"),
                contact("SM3ABC", "140400", "3.525", "1", "04", "JP75", "SM5XYZ", "SM"),
                contact("SM7GHI", "151500", "7.010", "1", "05", "JO75", "SM5XYZ", "SM"),
                contact("DL1ABC", "151700", "7.015", "1", "06", "JO42", "SM5XYZ", "DL"),
            ],
        },
        "K6GTE": {
            "station": STATION,
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "DM13"},
            "qsos": [
                contact("SM3ABC", "140000", "3.525", "1", "01", "JP75", "K6GTE", "SM"),
                contact("SM6DEF", "151500", "7.010", "1", "02", "JO65", "K6GTE", "SM"),
                contact("SM3ABC", "140400", "3.525", "1", "03", "JP75", "K6GTE", "SM"),
            ],
        },
    }


FIXTURES["ssa_mt_cw"] = _ssa_mt_fixtures("CW")
FIXTURES["ssa_mt_ssb"] = _ssa_mt_fixtures("SSB")

# ------------------------------------------------------- oceania_dx_cw/_ssb
# A contact scores the band's points only when one end is in Oceania - 20 for
# 160m down to 1 for 20m - and a multiplier is each different prefix worked,
# once per band.  The prefixes go in the log because the multiplier reads them.
def _oceania_fixtures(mode):
    """The same log for the Oceania DX CW and SSB contests."""
    rpt = "59" if mode == "SSB" else "599"

    def contact(call, time_on, freq, wpx, prefix, continent, station):
        return qso(
            CALL=call,
            QSO_DATE="20261003",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT=rpt,
            RCV=rpt,
            SENTNR="1",
            NR="002",
            WPXPREFIX=wpx,
            COUNTRYPREFIX=prefix,
            CONTINENT=continent,
            STATION_CALLSIGN=station,
        )

    return {
        # An Oceania station scores every contact, wherever it is.
        "VK2ABC": {
            "station": {
                **STATION,
                "Call": "VK2ABC",
                "Country": "Australia",
                "State": "",
                "GridSquare": "QF56",
                "ARRLSection": "DX",
                "Email": "vk2abc@example.com",
            },
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "1"},
            "qsos": [
                contact("VK3XYZ", "100000", "14.025", "VK3", "VK", "OC", "VK2ABC"),
                contact("ZL1ABC", "100200", "7.025", "ZL1", "ZL", "OC", "VK2ABC"),
                contact("JA1ABC", "100400", "21.025", "JA1", "JA", "AS", "VK2ABC"),
                contact("VK3XYZ", "100600", "14.025", "VK3", "VK", "OC", "VK2ABC"),
                contact("K6GTE", "100800", "3.525", "K5", "K", "NA", "VK2ABC"),
            ],
        },
        # A station outside Oceania scores only for contacts with it.
        "K6GTE": {
            "station": STATION,
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "1"},
            "qsos": [
                contact("VK2ABC", "100000", "14.025", "VK2", "VK", "OC", "K6GTE"),
                contact("ZL1ABC", "100200", "7.025", "ZL1", "ZL", "OC", "K6GTE"),
                contact("DL1ABC", "100400", "21.025", "DL1", "DL", "EU", "K6GTE"),
                contact("VK2ABC", "100600", "14.025", "VK2", "VK", "OC", "K6GTE"),
            ],
        },
    }


FIXTURES["oceania_dx_cw"] = _oceania_fixtures("CW")
FIXTURES["oceania_dx_ssb"] = _oceania_fixtures("SSB")

# ------------------------------------------------------------- 10-10 parties
# Two points for a contact that carries a 10-10 number, one for a contact
# without one (record a zero in its place), and a station counts only once in
# the whole party - so a repeat, on any band, scores nothing.  There are no
# multipliers: the score is just the sum of the contact points.
#
# The four plugin modules differ only in mode and in the party they are set up
# for.  The exchange is name, 10-10 number and QTH, which is what the plugin
# stores in NR, so it is the field the points are read from and the field the
# Cabrillo QSO line prints.
def _ten_ten_fixtures(mode, date):
    """One log for a 10-10 QSO Party, driven at both point values."""
    rpt = "59" if mode == "SSB" else "599"

    def contact(call, time_on, freq, name, number, qth):
        return qso(
            CALL=call,
            QSO_DATE=date,
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT=rpt,
            RCV=rpt,
            STX_STRING="MIKE 1234 CA",
            SRX_STRING=f"{name} {number} {qth}",
            NAME=name,
            STATION_CALLSIGN="K6GTE",
        )

    return {
        "K6GTE": {
            "station": STATION,
            "contest_settings": {
                **CATS,
                "ModeCategory": mode,
                "SentExchange": "MIKE 1234 CA",
            },
            "qsos": [
                contact("W1ABC", "000100", "28.020", "RICK", "1010", "NC"),
                contact("DL1ABC", "000300", "28.040", "HANS", "0", "DL"),
                contact("W1ABC", "000500", "28.025", "RICK", "1010", "NC"),
                contact("K7ABC", "000700", "28.060", "BOB", "2020", "TX"),
                contact("DL1ABC", "000900", "28.045", "HANS", "0", "DL"),
            ],
        },
    }


FIXTURES["10_10_fall_cw"] = _ten_ten_fixtures("CW", "20261017")
FIXTURES["10_10_spring_cw"] = _ten_ten_fixtures("CW", "20260502")
FIXTURES["10_10_summer_phone"] = _ten_ten_fixtures("SSB", "20260801")
FIXTURES["10_10_winter_phone"] = _ten_ten_fixtures("SSB", "20260207")

# ------------------------------------------------------------- jidx_cw/jidx_ph
# Rule 5: only a contact between a JA station and a DX station scores, and the
# points come from the band - 4 on 160m, 2 on 80m, 1 on 40/20/15m and 2 on
# 10m.  JA-JA and DX-DX contacts are worth no points and no multiplier.
# Rule 6: a multiplier is each Japanese prefecture once per band, so the same
# prefecture worked on a second band counts again.
def _jidx_fixtures(mode):
    """Logs for the JIDX CW and Phone contests, logged from outside Japan."""
    rpt = "59" if mode == "SSB" else "599"

    def contact(station, call, time_on, freq, nr, prefix, continent):
        return qso(
            CALL=call,
            QSO_DATE="20260411",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT=rpt,
            RCV=rpt,
            SENTNR="3",
            NR=nr,
            COUNTRYPREFIX=prefix,
            CONTINENT=continent,
            STATION_CALLSIGN=station,
        )

    return {
        # An all-band entry: the per-band multiplier shows here, where a
        # prefecture worked on a second band counts again.
        "K6GTE": {
            "station": STATION,
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "3"},
            "qsos": [
                contact("K6GTE", "JA1ABC", "070000", "1.830", "01", "JA", "AS"),
                contact("K6GTE", "JA2DEF", "070200", "3.530", "13", "JA", "AS"),
                contact("K6GTE", "JA3GHI", "070400", "7.030", "25", "JA", "AS"),
                contact("K6GTE", "JA1ABC", "070600", "1.830", "01", "JA", "AS"),
                contact("K6GTE", "JA1ABC", "070800", "7.020", "01", "JA", "AS"),
                contact("K6GTE", "DL1ABC", "071000", "14.040", "14", "DL", "EU"),
                contact("K6GTE", "JA4JKL", "071200", "28.040", "40", "JA", "AS"),
            ],
        },
        # A 40m single-band low-power entry, which pins the Cabrillo category
        # against the band names the contest dialog actually offers.
        "K6GTE-40M": {
            "station": STATION,
            "contest_settings": {
                **CATS,
                "ModeCategory": mode,
                "BandCategory": "40M",
                "PowerCategory": "LOW",
                "SentExchange": "3",
            },
            "qsos": [
                contact("K6GTE", "JA1ABC", "070000", "7.030", "01", "JA", "AS"),
                contact("K6GTE", "JA2DEF", "070200", "7.040", "13", "JA", "AS"),
                contact("K6GTE", "JA1ABC", "070400", "7.030", "01", "JA", "AS"),
            ],
        },
    }


FIXTURES["jidx_cw"] = _jidx_fixtures("CW")
FIXTURES["jidx_ph"] = _jidx_fixtures("SSB")

# ------------------------------------------------------------- ari_40_80
# An Italian domestic contest on 80m and 40m.  CW is worth 3 points, digital
# (RTTY) 2 and phone 1; a multiplier is each Italian province once per mode
# per band.  The exchange is the two-letter province car code both ways.
def _italian_station():
    """A synthetic Italian station, for the Italy-centred contests."""
    return {
        **STATION,
        "Call": "I2ABC",
        "Country": "Italy",
        "State": "",
        "GridSquare": "JN45",
        "ARRLSection": "DX",
        "Email": "i2abc@example.com",
    }


def _ari_40_80_fixture():
    def contact(call, time_on, freq, mode, prov):
        return qso(
            CALL=call,
            QSO_DATE="20261212",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT="59" if mode == "SSB" else "599",
            RCV="59" if mode == "SSB" else "599",
            SENTNR="MI",
            EXCHANGE1=prov,
            STATION_CALLSIGN="I2ABC",
        )

    return {
        "I2ABC": {
            "station": _italian_station(),
            "contest_settings": {
                **CATS,
                "ModeCategory": "SSB+CW+DIGITAL",
                "SentExchange": "MI",
            },
            "qsos": [
                contact("IK1ABC", "130000", "3.550", "SSB", "TO"),
                contact("IW2DEF", "130200", "3.560", "CW", "BG"),
                contact("IZ3GHI", "130400", "7.030", "RTTY", "PD"),
                contact("IK1ABC", "130600", "3.550", "SSB", "TO"),
                contact("IK1ABC", "130800", "3.570", "CW", "TO"),
                contact("IW2DEF", "131000", "7.040", "SSB", "BG"),
                contact("IZ3GHI", "131200", "3.580", "RTTY", "PD"),
            ],
        },
    }


FIXTURES["ari_40_80"] = _ari_40_80_fixture()

# ------------------------------------------------------------------ ari_dx
# Scoring depends on where the entrant is.  Points: 0 with the entrant's own
# country, 1 with another country on the same continent, 3 across continents,
# and 10 with an I / IS (Sardinia) / IT9 (Sicily) station.  Multipliers are
# each Italian province and each entity outside I / IS / IT9, once per band.
def _ari_dx_fixtures():
    def contact(station, call, time_on, freq, mode, nr, prefix):
        return qso(
            CALL=call,
            QSO_DATE="20260502",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT="59" if mode == "SSB" else "599",
            RCV="59" if mode == "SSB" else "599",
            SENTNR="MI" if station == "I2ABC" else "001",
            NR=nr,
            COUNTRYPREFIX=prefix,
            STATION_CALLSIGN=station,
        )

    return {
        # A DX entrant: Italian contacts score 10, and provinces and countries
        # each count once per band.
        "K6GTE": {
            "station": STATION,
            "contest_settings": {
                **CATS,
                "ModeCategory": "SSB+CW+DIGITAL",
                "SentExchange": "001",
            },
            "qsos": [
                contact("K6GTE", "I2ABC", "120000", "3.505", "CW", "MI", "I"),
                contact("K6GTE", "DL1ABC", "120200", "3.515", "CW", "001", "DL"),
                contact("K6GTE", "IS0ABC", "120400", "3.525", "CW", "CA", "IS"),
                contact("K6GTE", "W1AW", "120600", "3.535", "CW", "005", "K"),
                contact("K6GTE", "IT9ABC", "120800", "7.025", "CW", "PA", "IT9"),
                contact("K6GTE", "DL1ABC", "121000", "7.035", "SSB", "002", "DL"),
                contact("K6GTE", "I2ABC", "121200", "3.505", "CW", "MI", "I"),
                contact("K6GTE", "OK2ABC", "121400", "3.545", "CW", "003", "OK"),
                contact("K6GTE", "VE3ABC", "121600", "3.555", "CW", "004", "VE"),
            ],
        },
        # An Italian entrant: its own country scores nothing, and Sardinia and
        # Sicily score 10 while counting no country multiplier.
        "I2ABC": {
            "station": _italian_station(),
            "contest_settings": {
                **CATS,
                "ModeCategory": "SSB+CW+DIGITAL",
                "SentExchange": "MI",
            },
            "qsos": [
                contact("I2ABC", "DL1ABC", "120000", "3.505", "CW", "001", "DL"),
                contact("I2ABC", "W1AW", "120200", "3.515", "CW", "005", "K"),
                contact("I2ABC", "OK2ABC", "120400", "3.525", "SSB", "003", "OK"),
                contact("I2ABC", "DL1ABC", "120600", "7.025", "CW", "002", "DL"),
                contact("I2ABC", "W1AW", "120800", "3.515", "CW", "005", "K"),
                contact("I2ABC", "VE3ABC", "121000", "7.035", "SSB", "004", "VE"),
            ],
        },
    }


FIXTURES["ari_dx"] = _ari_dx_fixtures()

# ------------------------------------------------------------ lz-dx/helvetia
# Two contests with the same point table: 10 points for the home country,
# 3 across continents and 1 within one - except that two LZ stations are only
# worth 1 point to each other.  They differ in their multipliers: LZ DX counts
# ITU zones for everyone plus LZ districts (foreign entrant) or DXCC countries
# (LZ entrant) per band, while Helvetia counts cantons and DXCC countries.
def _country_station(call, country, grid):
    """A synthetic station outside the United States."""
    return {
        **STATION,
        "Call": call,
        "Country": country,
        "State": "",
        "GridSquare": grid,
        "ARRLSection": "DX",
        "Email": f"{call.lower()}@example.com",
    }


def _lz_dx_fixtures():
    def contact(station, call, time_on, freq, mode, nr, zone, prefix):
        return qso(
            CALL=call,
            QSO_DATE="20261121",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT="59" if mode == "SSB" else "599",
            RCV="59" if mode == "SSB" else "599",
            SENTNR="SF" if station == "LZ1ABC" else "6",
            NR=nr,
            ZN=zone,
            COUNTRYPREFIX=prefix,
            STATION_CALLSIGN=station,
        )

    return {
        # A foreign entrant: LZ stations are 10 points, and the multipliers
        # are the ITU zones plus the LZ districts.
        "K6GTE": {
            "station": STATION,
            "contest_settings": {
                **CATS,
                "ModeCategory": "SSB+CW",
                "SentExchange": "6",
            },
            "qsos": [
                contact("K6GTE", "LZ1ABC", "120000", "3.505", "SSB", "SF", "28", "LZ"),
                contact("K6GTE", "DL1ABC", "120200", "3.515", "CW", "001", "28", "DL"),
                contact("K6GTE", "W1AW", "120400", "3.525", "CW", "005", "8", "K"),
                contact("K6GTE", "LZ2XYZ", "120600", "7.025", "SSB", "PD", "28", "LZ"),
                contact("K6GTE", "DL1ABC", "120800", "7.035", "CW", "002", "28", "DL"),
                contact("K6GTE", "JA1ABC", "121000", "7.045", "CW", "045", "45", "JA"),
                contact("K6GTE", "LZ1ABC", "121200", "3.505", "SSB", "SF", "28", "LZ"),
                contact("K6GTE", "LZ1ABC", "121400", "3.505", "CW", "SF", "28", "LZ"),
                contact("K6GTE", "VE3ABC", "121600", "14.045", "CW", "004", "9", "VE"),
            ],
        },
        # A Bulgarian entrant: an LZ contact is only 1 point, and the second
        # multiplier is the DXCC countries rather than the districts.
        "LZ1ABC": {
            "station": _country_station("LZ1ABC", "Bulgaria", "KN12"),
            "contest_settings": {
                **CATS,
                "ModeCategory": "SSB+CW",
                "SentExchange": "SF",
            },
            "qsos": [
                contact("LZ1ABC", "DL1ABC", "120000", "3.505", "CW", "001", "28", "DL"),
                contact("LZ1ABC", "W1AW", "120200", "3.515", "CW", "005", "8", "K"),
                contact("LZ1ABC", "JA1ABC", "120400", "7.025", "CW", "045", "45", "JA"),
                contact("LZ1ABC", "LZ2XYZ", "120600", "3.505", "SSB", "PD", "28", "LZ"),
                contact("LZ1ABC", "DL1ABC", "120800", "3.505", "CW", "002", "28", "DL"),
                contact("LZ1ABC", "PY1ABC", "121000", "7.035", "SSB", "015", "15", "PY"),
            ],
        },
    }


FIXTURES["lz-dx"] = _lz_dx_fixtures()


def _helvetia_fixtures():
    def contact(station, call, time_on, freq, mode, nr, prefix):
        return qso(
            CALL=call,
            QSO_DATE="20260425",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT="59" if mode == "SSB" else "599",
            RCV="59" if mode == "SSB" else "599",
            SENTNR="ZH" if station == "HB9ABC" else "001",
            NR=nr,
            COUNTRYPREFIX=prefix,
            STATION_CALLSIGN=station,
        )

    return {
        # A foreign entrant: HB stations are 10 points and bring the cantons.
        "K6GTE": {
            "station": STATION,
            "contest_settings": {
                **CATS,
                "ModeCategory": "SSB+CW",
                "SentExchange": "001",
            },
            "qsos": [
                contact("K6GTE", "HB9ABC", "130000", "3.505", "CW", "ZH", "HB"),
                contact("K6GTE", "DL1ABC", "130200", "3.515", "CW", "001", "DL"),
                contact("K6GTE", "W1AW", "130400", "3.525", "CW", "005", "K"),
                contact("K6GTE", "HB9XYZ", "130600", "7.025", "SSB", "BE", "HB"),
                contact("K6GTE", "DL1ABC", "130800", "7.035", "CW", "002", "DL"),
                contact("K6GTE", "HB9ABC", "131000", "3.505", "CW", "ZH", "HB"),
                contact("K6GTE", "HB9ABC", "131200", "3.505", "SSB", "ZH", "HB"),
                contact("K6GTE", "VE3ABC", "131400", "14.045", "CW", "004", "VE"),
            ],
        },
        # A Swiss entrant, where an HB contact is still 10 points.
        "HB9ABC": {
            "station": _country_station("HB9ABC", "Switzerland", "JN47"),
            "contest_settings": {
                **CATS,
                "ModeCategory": "SSB+CW",
                "SentExchange": "ZH",
            },
            "qsos": [
                contact("HB9ABC", "DL1ABC", "130000", "3.505", "CW", "001", "DL"),
                contact("HB9ABC", "HB9XYZ", "130200", "3.515", "SSB", "ZH", "HB"),
                contact("HB9ABC", "W1AW", "130400", "7.025", "CW", "005", "K"),
                contact("HB9ABC", "DL1ABC", "130600", "3.505", "CW", "002", "DL"),
                contact("HB9ABC", "VE3ABC", "130800", "7.035", "SSB", "004", "VE"),
            ],
        },
    }


FIXTURES["helvetia"] = _helvetia_fixtures()

# -------------------------------------------------------------- aadx_cw/ssb
# All Asian DX, where the entrant's side decides nearly everything.  An Asian
# station scores both Asian and non-Asian contacts (3/9 on 160m, 2/6 on 80m and
# 10m, 1/3 elsewhere); a non-Asian station scores only Asian contacts (3/2/2/1)
# and counts the Asian prefixes, while the Asian station counts DXCC entities.
# A contact within the entrant's own entity is worth nothing, and a station
# counts once per band.
def _aadx_fixtures(mode):
    rpt = "59" if mode == "SSB" else "599"

    def contact(station, call, time_on, freq, age):
        return qso(
            CALL=call,
            QSO_DATE="20260620",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT=rpt,
            RCV=rpt,
            SENTNR="25",
            NR=age,
            STATION_CALLSIGN=station,
        )

    return {
        # A non-Asian entrant: only the Asian contacts score, and the
        # multiplier is each Asian prefix once per band.
        "K6GTE": {
            "station": STATION,
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "25"},
            "qsos": [
                contact("K6GTE", "JA1ABC", "000000", "1.830", "30"),
                contact("K6GTE", "JA2DEF", "000200", "3.530", "40"),
                contact("K6GTE", "JA1ABC", "000400", "3.550", "30"),
                contact("K6GTE", "JA3GHI", "000600", "7.030", "50"),
                contact("K6GTE", "DL1ABC", "000800", "14.040", "60"),
                contact("K6GTE", "W1AW", "001000", "21.040", "70"),
                contact("K6GTE", "JA1ABC", "001200", "1.830", "30"),
                contact("K6GTE", "JA2DEF", "001400", "7.040", "40"),
                contact("K6GTE", "JA1ABC", "001600", "28.040", "30"),
            ],
        },
        # An Asian entrant: both sides score, the multiplier is each DXCC
        # entity once per band, and another Japanese station is worth nothing.
        "JA1ABC": {
            "station": _country_station("JA1ABC", "Japan", "PM95"),
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "25"},
            "qsos": [
                contact("JA1ABC", "BV1ABC", "000000", "1.830", "35"),
                contact("JA1ABC", "HL1ABC", "000200", "3.530", "45"),
                contact("JA1ABC", "JA2DEF", "000400", "3.550", "40"),
                contact("JA1ABC", "BV1ABC", "000600", "14.040", "35"),
                contact("JA1ABC", "DL1ABC", "000800", "1.830", "60"),
                contact("JA1ABC", "K6GTE", "001000", "3.550", "50"),
                contact("JA1ABC", "VU2ABC", "001200", "28.040", "55"),
                contact("JA1ABC", "DL1ABC", "001400", "7.040", "60"),
                contact("JA1ABC", "BV1ABC", "001600", "1.830", "35"),
                contact("JA1ABC", "HL1ABC", "001800", "1.830", "45"),
            ],
        },
    }


FIXTURES["aadx_cw"] = _aadx_fixtures("CW")
FIXTURES["aadx_ssb"] = _aadx_fixtures("SSB")

# ---------------------------------------------------------------- ref_cw/ssb
# The REF contest (Coupe du REF).  A French station scores 6/15 against another
# French station and 1/2 against a foreign one; a foreign entrant scores 1/3
# only for French stations.  The French multipliers - the departments of the
# mainland and Corsica plus the DOM/TOM prefixes - are simply the exchange a
# French station sends, so a new NR per band counts; the other multiplier is
# the non-French DXCC countries, which only a French entrant may claim.
def _ref_fixtures(mode):
    rpt = "59" if mode == "SSB" else "599"

    def contact(station, sent, call, time_on, freq, nr, prefix):
        return qso(
            CALL=call,
            QSO_DATE="20260124",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT=rpt,
            RCV=rpt,
            SENTNR=sent,
            NR=nr,
            COUNTRYPREFIX=prefix,
            STATION_CALLSIGN=station,
        )

    return {
        # A foreign entrant: only French stations score and only the French
        # multipliers count.
        "K6GTE": {
            "station": STATION,
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "001"},
            "qsos": [
                contact("K6GTE", "001", "F5ABC", "060000", "3.505", "75", "F"),
                contact("K6GTE", "001", "F6XYZ", "060200", "3.515", "2A", "F"),
                contact("K6GTE", "001", "FG5ABC", "060400", "7.025", "FG", "FG"),
                contact("K6GTE", "001", "F5ABC", "060600", "3.505", "75", "F"),
                contact("K6GTE", "001", "DL1ABC", "060800", "3.525", "001", "DL"),
                contact("K6GTE", "001", "F5ABC", "061000", "7.035", "75", "F"),
                contact("K6GTE", "001", "FM5ABC", "061200", "7.045", "FM", "FM"),
                contact("K6GTE", "001", "W1AW", "061400", "14.040", "005", "K"),
            ],
        },
        # A French entrant: 6/15 against French stations and 1/2 against
        # foreign ones, with the countries counting too.
        "F5ABC": {
            "station": _country_station("F5ABC", "France", "JN18"),
            "contest_settings": {**CATS, "ModeCategory": mode, "SentExchange": "75"},
            "qsos": [
                contact("F5ABC", "75", "F6XYZ", "060000", "3.505", "2A", "F"),
                contact("F5ABC", "75", "DL1ABC", "060200", "3.515", "001", "DL"),
                contact("F5ABC", "75", "K6GTE", "060400", "7.025", "005", "K"),
                contact("F5ABC", "75", "F6XYZ", "060600", "3.505", "2A", "F"),
                contact("F5ABC", "75", "F5DEF", "060800", "7.035", "75", "F"),
                contact("F5ABC", "75", "DL1ABC", "061000", "7.045", "002", "DL"),
                contact("F5ABC", "75", "K6GTE", "061200", "3.525", "006", "K"),
            ],
        },
    }


FIXTURES["ref_cw"] = _ref_fixtures("CW")
FIXTURES["ref_ssb"] = _ref_fixtures("SSB")

# -------------------------------------------------------------------- spdx
# SP DX Contest.  A Polish station scores 3 points for a station outside
# Europe, 1 for one inside it and nothing against another Polish station, and
# counts the DXCC countries it worked (Poland excepted).  A foreign station
# scores 3 for a Polish station and counts the 16 provinces, each once per
# band and regardless of mode.
def _spdx_fixtures():
    def contact(station, sent, call, time_on, freq, mode, nr, prefix):
        return qso(
            CALL=call,
            QSO_DATE="20260404",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT="59" if mode == "SSB" else "599",
            RCV="59" if mode == "SSB" else "599",
            SENTNR=sent,
            NR=nr,
            COUNTRYPREFIX=prefix,
            STATION_CALLSIGN=station,
        )

    return {
        # A foreign entrant: only the Polish stations score, and the
        # multiplier is the province once per band whatever the mode.
        "K6GTE": {
            "station": STATION,
            "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "001"},
            "qsos": [
                contact("K6GTE", "001", "SP1ABC", "150000", "3.505", "CW", "B", "SP"),
                contact("K6GTE", "001", "SP2DEF", "150200", "3.515", "CW", "C", "SP"),
                contact("K6GTE", "001", "SP1ABC", "150400", "7.025", "CW", "B", "SP"),
                contact("K6GTE", "001", "DL1ABC", "150600", "3.525", "CW", "001", "DL"),
                contact("K6GTE", "001", "SP1ABC", "150800", "3.505", "SSB", "B", "SP"),
                contact("K6GTE", "001", "SP3GHI", "151000", "28.040", "CW", "Z", "SP"),
                contact("K6GTE", "001", "SP1ABC", "151200", "3.505", "CW", "B", "SP"),
                contact("K6GTE", "001", "SP1ABC", "151400", "3.505", "SSB", "B", "SP"),
            ],
        },
        # A Polish entrant: 1 point inside Europe, 3 outside it, and the
        # multiplier is the DXCC country once per band, Poland excepted.
        "SP1ABC": {
            "station": _country_station("SP1ABC", "Poland", "KO02"),
            "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "B"},
            "qsos": [
                contact("SP1ABC", "B", "DL1ABC", "150000", "3.505", "CW", "001", "DL"),
                contact("SP1ABC", "B", "K6GTE", "150200", "3.515", "CW", "005", "K"),
                contact("SP1ABC", "B", "UA3ABC", "150400", "7.025", "CW", "010", "UA"),
                contact("SP1ABC", "B", "SP2DEF", "150600", "3.525", "CW", "C", "SP"),
                contact("SP1ABC", "B", "DL1ABC", "150800", "3.505", "SSB", "002", "DL"),
                contact("SP1ABC", "B", "K6GTE", "151000", "7.035", "CW", "006", "K"),
                contact("SP1ABC", "B", "DL1ABC", "151200", "3.505", "CW", "001", "DL"),
            ],
        },
    }


FIXTURES["spdx"] = _spdx_fixtures()

# -------------------------------------------------------------------- pacc
# Dutch PACC.  A Dutch station scores 1 point for every contact and counts the
# DXCC countries worked; a foreign station scores 1 point only for Dutch
# stations and counts the 12 provinces, each once per band per mode - so the
# same province on the same band in the other mode is a new multiplier.
def _pacc_fixtures():
    def contact(station, sent, call, time_on, freq, mode, nr, prefix):
        return qso(
            CALL=call,
            QSO_DATE="20260214",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT="59" if mode == "SSB" else "599",
            RCV="59" if mode == "SSB" else "599",
            SENTNR=sent,
            NR=nr,
            COUNTRYPREFIX=prefix,
            STATION_CALLSIGN=station,
        )

    return {
        # A foreign entrant: only the Dutch stations score, and the province
        # is a new multiplier once per band and mode.
        "K6GTE": {
            "station": STATION,
            "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "001"},
            "qsos": [
                contact("K6GTE", "001", "PA1ABC", "120000", "3.505", "CW", "NH", "PA"),
                contact("K6GTE", "001", "PA2DEF", "120200", "3.515", "CW", "ZH", "PA"),
                contact("K6GTE", "001", "PA1ABC", "120400", "3.505", "SSB", "NH", "PA"),
                contact("K6GTE", "001", "DL1ABC", "120600", "3.525", "CW", "001", "DL"),
                contact("K6GTE", "001", "PA1ABC", "120800", "7.025", "CW", "NH", "PA"),
                contact("K6GTE", "001", "PA1ABC", "121000", "3.505", "CW", "NH", "PA"),
                contact("K6GTE", "001", "PA2DEF", "121200", "3.515", "CW", "ZH", "PA"),
            ],
        },
        # A Dutch entrant: every contact is a point, and the country counts.
        # The log deliberately stays inside Europe: the W/JA/VE/UA/LU/PY call
        # areas are multipliers of their own and are not modelled yet.
        "PA1ABC": {
            "station": _country_station("PA1ABC", "Netherlands", "JO21"),
            "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "NH"},
            "qsos": [
                contact("PA1ABC", "NH", "DL1ABC", "120000", "3.505", "CW", "001", "DL"),
                contact("PA1ABC", "NH", "G4ABC", "120200", "3.515", "CW", "002", "G"),
                contact("PA1ABC", "NH", "DL1ABC", "120400", "3.505", "SSB", "003", "DL"),
                contact("PA1ABC", "NH", "ON4ABC", "120600", "7.025", "CW", "004", "ON"),
                contact("PA1ABC", "NH", "DL1ABC", "120800", "3.505", "CW", "001", "DL"),
                contact("PA1ABC", "NH", "F5ABC", "121000", "3.505", "SSB", "005", "F"),
            ],
        },
    }


FIXTURES["pacc"] = _pacc_fixtures()

# -------------------------------------------------------------------- hadx
# Hungarian DX Contest.  A Hungarian station is 10 points, a station on the
# entrant's own continent 2 and one on another continent 5.  The multiplier
# is each Hungarian county and each country (Hungary excepted) once per band,
# regardless of mode.  The counties arrive as the exchange; every other
# station sends a serial number, which is how the two are told apart.
def _hadx_fixtures():
    def contact(sent, call, time_on, freq, mode, nr, prefix):
        return qso(
            CALL=call,
            QSO_DATE="20260117",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT="59" if mode == "SSB" else "599",
            RCV="59" if mode == "SSB" else "599",
            SENTNR=sent,
            NR=nr,
            COUNTRYPREFIX=prefix,
            STATION_CALLSIGN="K6GTE",
        )

    return {
        "K6GTE": {
            "station": STATION,
            "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "001"},
            "qsos": [
                contact("001", "HA1ABC", "120000", "3.505", "CW", "BA", "HA"),
                contact("001", "DL1ABC", "120200", "3.515", "CW", "001", "DL"),
                contact("001", "W1AW", "120400", "3.525", "CW", "002", "K"),
                contact("001", "HA1ABC", "120600", "3.505", "CW", "BA", "HA"),
                contact("001", "HA2DEF", "120800", "7.025", "SSB", "BP", "HA"),
                contact("001", "DL1ABC", "121000", "3.515", "SSB", "003", "DL"),
                contact("001", "HA1ABC", "121200", "7.035", "CW", "BA", "HA"),
            ],
        },
    }


FIXTURES["hadx"] = _hadx_fixtures()

# -------------------------------------------------------------------- eudx
# European Union DX Contest.  An EU station identifies itself with a
# 4-character region code in place of an ITU zone, which is how each end is
# recognised.  Points are 2 for the entrant's own country, 10 for an EU
# country, 3 for a different country on the same continent and 5 across
# continents; each EU region and each DXCC country counts once per band.
def _eudx_fixtures():
    def contact(station, sent, call, time_on, freq, mode, nr, prefix):
        return qso(
            CALL=call,
            QSO_DATE="20260502",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT="59" if mode == "SSB" else "599",
            RCV="59" if mode == "SSB" else "599",
            SENTNR=sent,
            NR=nr,
            COUNTRYPREFIX=prefix,
            STATION_CALLSIGN=station,
        )

    return {
        # A non-EU entrant.
        "K6GTE": {
            "station": STATION,
            "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "8"},
            "qsos": [
                contact("K6GTE", "8", "DL1ABC", "120000", "3.505", "CW", "DE01", "DL"),
                contact("K6GTE", "8", "W1AW", "120200", "3.515", "CW", "008", "K"),
                contact("K6GTE", "8", "I2ABC", "120400", "3.525", "SSB", "IT01", "I"),
                contact("K6GTE", "8", "OK2ABC", "120600", "7.025", "CW", "28", "OK"),
                contact("K6GTE", "8", "DL1ABC", "120800", "3.505", "CW", "DE01", "DL"),
                contact("K6GTE", "8", "DL1ABC", "121000", "7.035", "CW", "DE02", "DL"),
                contact("K6GTE", "8", "VE3ABC", "121200", "3.525", "SSB", "009", "VE"),
            ],
        },
        # An EU entrant, whose own country is worth 2 and another EU country
        # 10, with a non-EU country on the continent between them.
        "DL1ABC": {
            "station": _country_station("DL1ABC", "Fed. Rep. of Germany", "JN58"),
            "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "DE01"},
            "qsos": [
                contact("DL1ABC", "DE01", "I2ABC", "120000", "3.505", "CW", "IT01", "I"),
                contact("DL1ABC", "DE01", "DL2XYZ", "120200", "3.515", "CW", "DE02", "DL"),
                contact("DL1ABC", "DE01", "OE1ABC", "120400", "3.525", "CW", "AT01", "OE"),
                contact("DL1ABC", "DE01", "K6GTE", "120600", "7.025", "CW", "008", "K"),
                contact("DL1ABC", "DE01", "HB9ABC", "120800", "7.035", "CW", "28", "HB"),
                contact("DL1ABC", "DE01", "I2ABC", "121000", "3.505", "CW", "IT01", "I"),
            ],
        },
    }


FIXTURES["eudx"] = _eudx_fixtures()

# ------------------------------------------------------------------- ok1wc
# OK1WC Memorial (MWC): one hour on Monday evening, CW only on 80m and 40m, a
# serial exchange, one point a QSO, and the multiplier is the last letter of
# the worked callsign once per band.  The old log put its contacts on 20m,
# 15m and 10m, which this contest does not use.
def _ok1wc_fixture():
    def contact(call, time_on, freq, nr):
        return qso(
            CALL=call,
            QSO_DATE="20260914",
            TIME_ON=time_on,
            FREQ=freq,
            MODE="CW",
            SNT="599",
            RCV="599",
            SENTNR="001",
            NR=nr,
            STATION_CALLSIGN="K6GTE",
        )

    return {
        "K6GTE": {
            "station": STATION,
            "contest_settings": {**CATS, "ModeCategory": "CW", "SentExchange": "001"},
            "qsos": [
                contact("OK2ABC", "163000", "3.530", "001"),
                contact("DL1ABD", "163100", "3.545", "002"),
                contact("OK2ABC", "163200", "7.030", "003"),
                contact("DL1ABD", "163300", "3.545", "004"),
                contact("SP1EFG", "163400", "7.040", "005"),
                contact("OK2ABC", "163500", "3.530", "006"),
                contact("DL1ABD", "163600", "7.045", "007"),
                contact("SP1EFG", "163700", "3.560", "008"),
            ],
        },
    }


FIXTURES["ok1wc"] = _ok1wc_fixture()

# ------------------------------------------------------------------ es_open
# ES Open HF Championship, an Estonian contest: four hours on 80m and 40m,
# CW worth 2 points and SSB 1, and a station worked once per mode in each full
# hour.  An Estonian station can work anyone, a foreign one only scores for
# Estonian stations, and the multiplier is the ES call area (ES0-ES9) once per
# band and mode.
def _es_open_fixtures():
    def contact(station, call, time_on, freq, mode, nr):
        # Neither COUNTRYPREFIX nor WPXPREFIX is written here:
        # recalculate_mults() fills both from cty, which is what an imported
        # log needs - the multiplier is read from WPXPrefix.
        return qso(
            CALL=call,
            QSO_DATE="20260418",
            TIME_ON=time_on,
            FREQ=freq,
            MODE=mode,
            SNT="59" if mode == "SSB" else "599",
            RCV="59" if mode == "SSB" else "599",
            SENTNR="001",
            NR=nr,
            STATION_CALLSIGN=station,
        )

    return {
        # A foreign entrant: only the Estonian stations score, and the
        # multiplier is their call area.  The last contact repeats one from
        # within the first hour (a duplicate) and one from the next hour
        # (which is not), so the hourly rule is what decides them.
        "K6GTE": {
            "station": STATION,
            "contest_settings": {
                **CATS,
                "ModeCategory": "SSB+CW",
                "SentExchange": "001",
                "StartDate": "2026-04-18 05:00:00",
            },
            "qsos": [
                contact("K6GTE", "ES1ABC", "050000", "3.505", "SSB", "001"),
                contact("K6GTE", "ES2DEF", "050100", "3.515", "CW", "002"),
                contact("K6GTE", "ES1ABC", "050200", "7.025", "CW", "003"),
                contact("K6GTE", "DL1ABC", "050300", "3.525", "CW", "004"),
                contact("K6GTE", "ES3GHI", "050400", "3.535", "SSB", "005"),
                contact("K6GTE", "ES1ABC", "050500", "3.505", "SSB", "006"),
                contact("K6GTE", "ES1ABC", "060000", "3.505", "SSB", "007"),
            ],
        },
        # An Estonian entrant: everyone scores, but the multiplier is still
        # only the ES call areas, and not its own.
        "ES1ABC": {
            "station": _country_station("ES1ABC", "Estonia", "KO29"),
            "contest_settings": {
                **CATS,
                "ModeCategory": "SSB+CW",
                "SentExchange": "001",
                "StartDate": "2026-04-18 05:00:00",
            },
            "qsos": [
                contact("ES1ABC", "DL1ABC", "050000", "3.505", "CW", "001"),
                contact("ES1ABC", "ES2DEF", "050100", "3.515", "CW", "002"),
                contact("ES1ABC", "ES2DEF", "050200", "7.025", "SSB", "003"),
                contact("ES1ABC", "OH2ABC", "050300", "3.525", "SSB", "004"),
                contact("ES1ABC", "ES2DEF", "050400", "3.515", "CW", "005"),
                contact("ES1ABC", "ES3GHI", "050500", "7.035", "CW", "006"),
                contact("ES1ABC", "ES1XYZ", "050600", "3.535", "SSB", "007"),
                contact("ES1ABC", "ES2DEF", "060000", "3.515", "CW", "008"),
            ],
        },
    }


FIXTURES["es_open"] = _es_open_fixtures()

# The other three ES plugins are ES Open's siblings, and their published rules
# could not be found, so the corpora pin what the plugins themselves describe:
# the same ES call-area / Estonian-region multipliers and the same
# period-based dupe rule.  Each log starts on the contest's own start time so
# the periods, and not the band/mode fallback, decide the duplicates.
def _es_contact(station, date, call, time_on, freq, mode, nr, prefix):
    return qso(
        CALL=call,
        QSO_DATE=date,
        TIME_ON=time_on,
        FREQ=freq,
        MODE=mode,
        SNT="59" if mode == "SSB" else "599",
        RCV="59" if mode == "SSB" else "599",
        SENTNR="001",
        NR=nr,
        COUNTRYPREFIX=prefix,
        STATION_CALLSIGN=station,
    )


def _es_field_day_fixture():
    """A portable station is 3 points, a QRP one 5, and the multiplier is the
    Estonian region in the received exchange, per band and mode."""
    return {
        "K6GTE": {
            "station": STATION,
            "contest_settings": {
                **CATS,
                "ModeCategory": "SSB+CW",
                "SentExchange": "001",
                "StartDate": "2026-06-06 00:00:00",
            },
            "qsos": [
                _es_contact("K6GTE", "20260606", "ES1ABC/P", "000000",
                            "3.505", "CW", "001HM", "ES"),
                _es_contact("K6GTE", "20260606", "DL1ABC/QRP", "000500",
                            "3.515", "CW", "001", "DL"),
                _es_contact("K6GTE", "20260606", "ES2DEF", "001000",
                            "7.025", "SSB", "003TA", "ES"),
                _es_contact("K6GTE", "20260606", "ES1ABC/P", "002000",
                            "3.505", "CW", "004HM", "ES"),
                _es_contact("K6GTE", "20260606", "ES1ABC/P", "010000",
                            "3.505", "CW", "005HM", "ES"),
            ],
        },
    }


FIXTURES["es_field_day"] = _es_field_day_fixture()


def _es_ll_kv_fixture():
    """SSB is a point and CW two, and this contest's score is its QSO points:
    the call areas show_mults() counts are not applied to it."""
    return {
        "K6GTE": {
            "station": STATION,
            "contest_settings": {
                **CATS,
                "ModeCategory": "SSB+CW",
                "SentExchange": "001",
                "StartDate": "2026-05-02 00:00:00",
            },
            "qsos": [
                _es_contact("K6GTE", "20260502", "ES1ABC", "000000",
                            "3.505", "CW", "001", "ES"),
                _es_contact("K6GTE", "20260502", "ES2DEF", "000500",
                            "3.515", "SSB", "002", "ES"),
                _es_contact("K6GTE", "20260502", "ES1ABC", "001000",
                            "3.505", "CW", "003", "ES"),
                _es_contact("K6GTE", "20260502", "ES1ABC", "001600",
                            "3.505", "CW", "004", "ES"),
                _es_contact("K6GTE", "20260502", "DL1ABC", "001900",
                            "7.025", "SSB", "005", "DL"),
            ],
        },
    }


FIXTURES["es_ll_kv"] = _es_ll_kv_fixture()


def _es_manual_key_fixture():
    """CW only.  A contact is worth 20 plus a seniority under 10, 10 plus one
    up to 20, or the seniority itself, and the operator's own seniority is
    added to the points before the call areas multiply them."""
    return {
        "K6GTE": {
            "station": STATION,
            "contest_settings": {
                **CATS,
                "ModeCategory": "CW",
                "SentExchange": "001",
                "StartDate": "2026-05-16 00:00:00",
            },
            "qsos": [
                _es_contact("K6GTE", "20260516", "ES1ABC", "000000",
                            "3.505", "CW", "05", "ES"),
                _es_contact("K6GTE", "20260516", "ES2DEF", "000500",
                            "3.515", "CW", "15", "ES"),
                _es_contact("K6GTE", "20260516", "ES3GHI", "001000",
                            "3.525", "CW", "25", "ES"),
                _es_contact("K6GTE", "20260516", "ES1ABC", "001200",
                            "3.505", "CW", "30", "ES"),
                _es_contact("K6GTE", "20260516", "ES1ABC", "001600",
                            "3.505", "CW", "35", "ES"),
            ],
        },
    }


FIXTURES["es_manual_key"] = _es_manual_key_fixture()

# -------------------------------------------------- rsgb_commonwealth_beru
# Rule 4: only Commonwealth Call Area stations may enter, and a contact inside
# the entrant's own call area does not count; the seven home nations do not
# count against each other either, but an HQ station may be worked by anyone.
# Rule 8: 5 points within a continent, 10 across it, and 20 bonus points for
# each of the first three contacts with a Commonwealth Call Area on each band.
FIXTURES["rsgb_commonwealth_beru"] = {
    "G3XYZ": {
        "station": {**STATION, "Call": "G3XYZ", "Country": "England", "State": "",
                    "GridSquare": "IO91", "ARRLSection": "DX",
                    "Email": "g3xyz@example.com"},
        "contest_settings": {**CATS, "SentExchange": "001"},
        "qsos": [
            # rule 4(b): our own call area does not count
            qso(CALL="G4ABC", QSO_DATE="20260314", TIME_ON="100000", FREQ="3.520",
                MODE="CW", SNT="599", RCV="599", SENTNR="1", NR="11",
                COUNTRYPREFIX="G", CONTINENT="EU", STATION_CALLSIGN="G3XYZ"),
            # rule 4(d): the home nations do not count against each other
            qso(CALL="GM0ABC", QSO_DATE="20260314", TIME_ON="100200", FREQ="3.525",
                MODE="CW", SNT="599", RCV="599", SENTNR="2", NR="22",
                COUNTRYPREFIX="GM", CONTINENT="EU", STATION_CALLSIGN="G3XYZ"),
            # everyone else does: 10 points across a continent, and 20 bonus
            # for each of the first three on a band
            qso(CALL="VE3ABC", QSO_DATE="20260314", TIME_ON="100400", FREQ="3.530",
                MODE="CW", SNT="599", RCV="599", SENTNR="3", NR="33",
                COUNTRYPREFIX="VE", CONTINENT="NA", STATION_CALLSIGN="G3XYZ"),
            qso(CALL="VK2ABC", QSO_DATE="20260314", TIME_ON="100600", FREQ="3.535",
                MODE="CW", SNT="599", RCV="599", SENTNR="4", NR="44",
                COUNTRYPREFIX="VK", CONTINENT="OC", STATION_CALLSIGN="G3XYZ"),
            qso(CALL="ZL1ABC", QSO_DATE="20260314", TIME_ON="100800", FREQ="3.540",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="55",
                COUNTRYPREFIX="ZL", CONTINENT="OC", STATION_CALLSIGN="G3XYZ"),
            # the fourth on this band, so no bonus
            qso(CALL="5B4ABC", QSO_DATE="20260314", TIME_ON="101000", FREQ="3.545",
                MODE="CW", SNT="599", RCV="599", SENTNR="6", NR="66",
                COUNTRYPREFIX="5B", CONTINENT="AS", STATION_CALLSIGN="G3XYZ"),
            # outside the Commonwealth: no points
            qso(CALL="DL1ABC", QSO_DATE="20260314", TIME_ON="101200", FREQ="3.550",
                MODE="CW", SNT="599", RCV="599", SENTNR="7", NR="77",
                COUNTRYPREFIX="DL", CONTINENT="EU", STATION_CALLSIGN="G3XYZ"),
            # a new band earns its own bonus
            qso(CALL="VE3ABC", QSO_DATE="20260314", TIME_ON="101400", FREQ="7.020",
                MODE="CW", SNT="599", RCV="599", SENTNR="8", NR="88",
                COUNTRYPREFIX="VE", CONTINENT="NA", STATION_CALLSIGN="G3XYZ"),
            # rules 4(c) and 4(e): an HQ station identifies by sending 'HQ'
            # after its serial, and is contactable even in our own call area
            qso(CALL="G4HQ", QSO_DATE="20260314", TIME_ON="101600", FREQ="14.020",
                MODE="CW", SNT="599", RCV="599", SENTNR="9", NR="003 HQ",
                COUNTRYPREFIX="G", CONTINENT="EU", STATION_CALLSIGN="G3XYZ"),
            # a duplicate, which still has to be logged
            qso(CALL="VE3ABC", QSO_DATE="20260314", TIME_ON="101800", FREQ="3.520",
                MODE="CW", SNT="599", RCV="599", SENTNR="10", NR="010",
                COUNTRYPREFIX="VE", CONTINENT="NA", STATION_CALLSIGN="G3XYZ"),
        ],
    },
    # A Canadian entrant: VE1 and VE3 are different Commonwealth Call Areas,
    # so the first counts and the second does not; Canada is in North America,
    # so a contact with England is across a continent.
    "VE3ABC": {
        "station": {**STATION, "Call": "VE3ABC", "Country": "Canada", "State": "",
                    "GridSquare": "FN03", "ARRLSection": "ONS",
                    "Email": "ve3abc@example.com"},
        "contest_settings": {**CATS, "SentExchange": "001"},
        "qsos": [
            qso(CALL="VE1ABC", QSO_DATE="20260314", TIME_ON="100000", FREQ="3.520",
                MODE="CW", SNT="599", RCV="599", SENTNR="1", NR="11",
                COUNTRYPREFIX="VE", CONTINENT="NA", STATION_CALLSIGN="VE3ABC"),
            # rule 4(b): our own call area does not count
            qso(CALL="VE3XYZ", QSO_DATE="20260314", TIME_ON="100200", FREQ="3.525",
                MODE="CW", SNT="599", RCV="599", SENTNR="2", NR="22",
                COUNTRYPREFIX="VE", CONTINENT="NA", STATION_CALLSIGN="VE3ABC"),
            qso(CALL="G4ABC", QSO_DATE="20260314", TIME_ON="100400", FREQ="3.530",
                MODE="CW", SNT="599", RCV="599", SENTNR="3", NR="33",
                COUNTRYPREFIX="G", CONTINENT="EU", STATION_CALLSIGN="VE3ABC"),
            # outside the Commonwealth: no points
            qso(CALL="K6GTE", QSO_DATE="20260314", TIME_ON="100600", FREQ="3.535",
                MODE="CW", SNT="599", RCV="599", SENTNR="4", NR="44",
                COUNTRYPREFIX="K", CONTINENT="NA", STATION_CALLSIGN="VE3ABC"),
            qso(CALL="VE1ABC", QSO_DATE="20260314", TIME_ON="100800", FREQ="7.020",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="55",
                COUNTRYPREFIX="VE", CONTINENT="NA", STATION_CALLSIGN="VE3ABC"),
            qso(CALL="ZS1ABC", QSO_DATE="20260314", TIME_ON="101000", FREQ="7.025",
                MODE="CW", SNT="599", RCV="599", SENTNR="6", NR="66",
                COUNTRYPREFIX="ZS", CONTINENT="AF", STATION_CALLSIGN="VE3ABC"),
            # a duplicate, which still has to be logged
            qso(CALL="VE1ABC", QSO_DATE="20260314", TIME_ON="101200", FREQ="3.520",
                MODE="CW", SNT="599", RCV="599", SENTNR="7", NR="77",
                COUNTRYPREFIX="VE", CONTINENT="NA", STATION_CALLSIGN="VE3ABC"),
        ],
    },
}

# ---------------------------------------------------------- rsgb_80m_cc
# One 90-minute session per mode.  Rule 6: a UK&CD station must be at one or
# both ends of a contact for it to score, and a QSO with the Society's station
# (G6XX or a regional variant) is worth five points.  The pattern the other
# contests share works OK2ABC/DL1ABC/... , none of them UK&CD, so these cases
# are written out.
FIXTURES["rsgb_80m_cc"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "SentExchange": "001"},
        "qsos": [
            qso(CALL="G4ABC", QSO_DATE="20260212", TIME_ON="200000", FREQ="3.520",
                MODE="CW", SNT="599", RCV="599", SENTNR="1", NR="11",
                COUNTRYPREFIX="G", CONTINENT="EU", STATION_CALLSIGN="K6GTE"),
            qso(CALL="GM0ABC", QSO_DATE="20260212", TIME_ON="200200", FREQ="3.525",
                MODE="CW", SNT="599", RCV="599", SENTNR="2", NR="22",
                COUNTRYPREFIX="GM", CONTINENT="EU", STATION_CALLSIGN="K6GTE"),
            # the Society's station: five points
            qso(CALL="G6XX", QSO_DATE="20260212", TIME_ON="200400", FREQ="3.530",
                MODE="CW", SNT="599", RCV="599", SENTNR="3", NR="33",
                COUNTRYPREFIX="G", CONTINENT="EU", STATION_CALLSIGN="K6GTE"),
            # no UK&CD station at either end: no points
            qso(CALL="DL1ABC", QSO_DATE="20260212", TIME_ON="200600", FREQ="3.540",
                MODE="CW", SNT="599", RCV="599", SENTNR="4", NR="44",
                COUNTRYPREFIX="DL", CONTINENT="EU", STATION_CALLSIGN="K6GTE"),
            qso(CALL="OK2ABC", QSO_DATE="20260212", TIME_ON="200800", FREQ="3.545",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="55",
                COUNTRYPREFIX="OK", CONTINENT="EU", STATION_CALLSIGN="K6GTE"),
            # a duplicate, which still has to be logged
            qso(CALL="G4ABC", QSO_DATE="20260212", TIME_ON="201000", FREQ="3.520",
                MODE="CW", SNT="599", RCV="599", SENTNR="6", NR="66",
                COUNTRYPREFIX="G", CONTINENT="EU", STATION_CALLSIGN="K6GTE"),
        ],
    },
    # A datamodes session.  Rule 6 lets a station be worked once on PSK63 and
    # once on RTTY, so both count and the mode codes go out as PS and RY; the
    # third contact is the RTTY duplicate.
    "M0ABC": {
        "station": {**STATION, "Call": "M0ABC", "Country": "England", "State": "",
                    "GridSquare": "IO91", "ARRLSection": "DX",
                    "Email": "m0abc@example.com"},
        "contest_settings": {**CATS, "ModeCategory": "RTTY", "SentExchange": "001"},
        "qsos": [
            qso(CALL="G4ABC", QSO_DATE="20260212", TIME_ON="200000", FREQ="3.595",
                MODE="RTTY", SNT="599", RCV="599", SENTNR="1", NR="11",
                COUNTRYPREFIX="G", CONTINENT="EU", STATION_CALLSIGN="M0ABC"),
            qso(CALL="G4ABC", QSO_DATE="20260212", TIME_ON="200300", FREQ="3.585",
                MODE="PSK31", SNT="599", RCV="599", SENTNR="2", NR="22",
                COUNTRYPREFIX="G", CONTINENT="EU", STATION_CALLSIGN="M0ABC"),
            qso(CALL="G4ABC", QSO_DATE="20260212", TIME_ON="200600", FREQ="3.595",
                MODE="RTTY", SNT="599", RCV="599", SENTNR="3", NR="33",
                COUNTRYPREFIX="G", CONTINENT="EU", STATION_CALLSIGN="M0ABC"),
        ],
    },
}

# -------------------------------------------------------------- cq_ww_cw
FIXTURES["cq_ww_cw"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "SentExchange": "5"},
        "qsos": [
            qso(CALL="DL1ABC", QSO_DATE="20261128", TIME_ON="000500", FREQ="3.520",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="14", ZN="14",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="DL", CONTINENT="EU",
                APP_N1MM_POINTS="3"),
            qso(CALL="JA1ABC", QSO_DATE="20261128", TIME_ON="000800", FREQ="14.020",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="25", ZN="25",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="JA", CONTINENT="AS",
                APP_N1MM_POINTS="3"),
            qso(CALL="DL1ABC", QSO_DATE="20261128", TIME_ON="001100", FREQ="14.025",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="14", ZN="14",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="DL", CONTINENT="EU",
                APP_N1MM_POINTS="3"),
            qso(CALL="DL1ABC", QSO_DATE="20261128", TIME_ON="001400", FREQ="3.520",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="14", ZN="14",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="DL", CONTINENT="EU",
                APP_N1MM_POINTS="0"),
            qso(CALL="K1ABC", QSO_DATE="20261128", TIME_ON="001700", FREQ="14.030",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="5", ZN="5",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="K", CONTINENT="NA",
                APP_N1MM_POINTS="2"),
            qso(CALL="UA3ABC", QSO_DATE="20261128", TIME_ON="002000", FREQ="7.020",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="16", ZN="16",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="UA", CONTINENT="EU",
                APP_N1MM_POINTS="3"),
            qso(CALL="PY1ABC", QSO_DATE="20261128", TIME_ON="002300", FREQ="10.120",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="11", ZN="11",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="PY", CONTINENT="SA",
                APP_N1MM_POINTS="2"),
            qso(CALL="JA1ABC", QSO_DATE="20261128", TIME_ON="002600", FREQ="7.025",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="25", ZN="25",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="JA", CONTINENT="AS",
                APP_N1MM_POINTS="3"),
            qso(CALL="ZS1ABC", QSO_DATE="20261128", TIME_ON="002900", FREQ="21.020",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="38", ZN="38",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="ZS", CONTINENT="AF",
                APP_N1MM_POINTS="3"),
            qso(CALL="VE3ABC", QSO_DATE="20261128", TIME_ON="003200", FREQ="14.035",
                MODE="CW", SNT="599", RCV="599", SENTNR="5", NR="4", ZN="4",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="VE", CONTINENT="NA",
                APP_N1MM_POINTS="2"),
        ],
    },
}

# ------------------------------------------------------------ arrl_ss_cw
FIXTURES["arrl_ss_cw"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "SentExchange": "A 78 ORG"},
        "qsos": [
            qso(CALL="W1AW", QSO_DATE="20261107", TIME_ON="210000", FREQ="14.040",
                MODE="CW", SENTNR="1", NR="12", PREC="A", CK="78", SECT="CT",
                STATION_CALLSIGN="K6GTE"),
            qso(CALL="N0AX", QSO_DATE="20261107", TIME_ON="210300", FREQ="14.045",
                MODE="CW", SENTNR="2", NR="33", PREC="B", CK="95", SECT="MO",
                STATION_CALLSIGN="K6GTE"),
            qso(CALL="W1AW", QSO_DATE="20261107", TIME_ON="210600", FREQ="7.040",
                MODE="CW", SENTNR="3", NR="44", PREC="A", CK="78", SECT="CT",
                STATION_CALLSIGN="K6GTE"),
            qso(CALL="W1AW", QSO_DATE="20261107", TIME_ON="210900", FREQ="14.040",
                MODE="CW", SENTNR="4", NR="55", PREC="A", CK="78", SECT="CT",
                STATION_CALLSIGN="K6GTE"),
            qso(CALL="K5ABC", QSO_DATE="20261107", TIME_ON="211200", FREQ="21.040",
                MODE="CW", SENTNR="5", NR="66", PREC="Q", CK="99", SECT="NTX",
                STATION_CALLSIGN="K6GTE"),
            qso(CALL="VE3ABC", QSO_DATE="20261107", TIME_ON="211500", FREQ="14.050",
                MODE="CW", SENTNR="6", NR="77", PREC="A", CK="88", SECT="ONS",
                STATION_CALLSIGN="K6GTE"),
            qso(CALL="KH6ABC", QSO_DATE="20261107", TIME_ON="211800", FREQ="7.045",
                MODE="CW", SENTNR="7", NR="88", PREC="U", CK="77", SECT="PAC",
                STATION_CALLSIGN="K6GTE"),
            qso(CALL="KP4ABC", QSO_DATE="20261107", TIME_ON="212100", FREQ="21.045",
                MODE="CW", SENTNR="8", NR="99", PREC="B", CK="66", SECT="PR",
                STATION_CALLSIGN="K6GTE"),
            qso(CALL="N0AX", QSO_DATE="20261107", TIME_ON="212400", FREQ="7.050",
                MODE="CW", SENTNR="9", NR="11", PREC="B", CK="95", SECT="MO",
                STATION_CALLSIGN="K6GTE"),
            qso(CALL="W1AW", QSO_DATE="20261107", TIME_ON="212700", FREQ="21.050",
                MODE="CW", SENTNR="10", NR="22", PREC="A", CK="78", SECT="CT",
                STATION_CALLSIGN="K6GTE"),
            # a station outside W/VE sends "DX": no points, no multiplier
            qso(CALL="DL1ABC", QSO_DATE="20261107", TIME_ON="213000", FREQ="14.060",
                MODE="CW", SENTNR="11", NR="11", PREC="B", CK="95", SECT="DX",
                STATION_CALLSIGN="K6GTE"),
        ],
    },
}

# -------------------------------------------------------------- cwt
FIXTURES["cwt"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "SentExchange": "MIKE 1234"},
        "qsos": [
            qso(CALL="W1AW", QSO_DATE="20260107", TIME_ON="190000", FREQ="7.030",
                MODE="CW", SNT="599", RCV="599", SENTNR="1234", NR="5678",
                NAME="BOB", STATION_CALLSIGN="K6GTE"),
            qso(CALL="DL1ABC", QSO_DATE="20260107", TIME_ON="190300", FREQ="14.030",
                MODE="CW", SNT="599", RCV="599", SENTNR="1234", NR="CWA",
                NAME="HANS", STATION_CALLSIGN="K6GTE"),
            qso(CALL="W1AW", QSO_DATE="20260107", TIME_ON="190600", FREQ="14.030",
                MODE="CW", SNT="599", RCV="599", SENTNR="1234", NR="1111",
                NAME="BOB", STATION_CALLSIGN="K6GTE"),
            qso(CALL="W1AW", QSO_DATE="20260107", TIME_ON="190900", FREQ="7.030",
                MODE="CW", SNT="599", RCV="599", SENTNR="1234", NR="2222",
                NAME="BOB", STATION_CALLSIGN="K6GTE"),
            qso(CALL="K1ABC", QSO_DATE="20260107", TIME_ON="191200", FREQ="14.035",
                MODE="CW", SNT="599", RCV="599", SENTNR="1234", NR="3333",
                NAME="ANN", STATION_CALLSIGN="K6GTE"),
            qso(CALL="JA1ABC", QSO_DATE="20260107", TIME_ON="191500", FREQ="21.030",
                MODE="CW", SNT="599", RCV="599", SENTNR="1234", NR="4444",
                NAME="KEN", STATION_CALLSIGN="K6GTE"),
            qso(CALL="UA3ABC", QSO_DATE="20260107", TIME_ON="191800", FREQ="7.035",
                MODE="CW", SNT="599", RCV="599", SENTNR="1234", NR="5555",
                NAME="IVAN", STATION_CALLSIGN="K6GTE"),
            qso(CALL="DL1ABC", QSO_DATE="20260107", TIME_ON="192100", FREQ="7.035",
                MODE="CW", SNT="599", RCV="599", SENTNR="1234", NR="6666",
                NAME="HANS", STATION_CALLSIGN="K6GTE"),
            qso(CALL="VE3ABC", QSO_DATE="20260107", TIME_ON="192400", FREQ="14.040",
                MODE="CW", SNT="599", RCV="599", SENTNR="1234", NR="7777",
                NAME="BOB", STATION_CALLSIGN="K6GTE"),
            qso(CALL="W1AW", QSO_DATE="20260107", TIME_ON="192700", FREQ="21.035",
                MODE="CW", SNT="599", RCV="599", SENTNR="1234", NR="8888",
                NAME="BOB", STATION_CALLSIGN="K6GTE"),
        ],
    },
}

# -------------------------------------------------------------- rdxc
FIXTURES["rdxc"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "TX"},
        "qsos": [
            qso(CALL="RA3AAA", QSO_DATE="20260321", TIME_ON="080000", FREQ="14.025",
                MODE="CW", SNT="599", RCV="599", SENTNR="TX", NR="MO",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="UA", CONTINENT="EU"),
            qso(CALL="UA9ABC", QSO_DATE="20260321", TIME_ON="080300", FREQ="21.025",
                MODE="SSB", SNT="59", RCV="59", SENTNR="TX", NR="SV",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="UA9", CONTINENT="AS"),
            qso(CALL="RA3AAA", QSO_DATE="20260321", TIME_ON="080600", FREQ="7.025",
                MODE="CW", SNT="599", RCV="599", SENTNR="TX", NR="MO",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="UA", CONTINENT="EU"),
            qso(CALL="RA3AAA", QSO_DATE="20260321", TIME_ON="080900", FREQ="14.025",
                MODE="CW", SNT="599", RCV="599", SENTNR="TX", NR="MO",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="UA", CONTINENT="EU"),
            qso(CALL="DL1ABC", QSO_DATE="20260321", TIME_ON="081200", FREQ="14.030",
                MODE="CW", SNT="599", RCV="599", SENTNR="TX", NR="DL",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="DL", CONTINENT="EU"),
            qso(CALL="JA1ABC", QSO_DATE="20260321", TIME_ON="081500", FREQ="21.030",
                MODE="SSB", SNT="59", RCV="59", SENTNR="TX", NR="JA",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="JA", CONTINENT="AS"),
            qso(CALL="UA3ABC", QSO_DATE="20260321", TIME_ON="081800", FREQ="14.035",
                MODE="CW", SNT="599", RCV="599", SENTNR="TX", NR="MA",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="UA", CONTINENT="EU"),
            qso(CALL="UA9ABC", QSO_DATE="20260321", TIME_ON="082100", FREQ="14.040",
                MODE="CW", SNT="599", RCV="599", SENTNR="TX", NR="SV",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="UA9", CONTINENT="AS"),
            qso(CALL="W1AW", QSO_DATE="20260321", TIME_ON="082400", FREQ="7.030",
                MODE="CW", SNT="599", RCV="599", SENTNR="TX", NR="CT",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="K", CONTINENT="NA"),
            qso(CALL="PY1ABC", QSO_DATE="20260321", TIME_ON="082700", FREQ="10.120",
                MODE="CW", SNT="599", RCV="599", SENTNR="TX", NR="PY",
                STATION_CALLSIGN="K6GTE", COUNTRYPREFIX="PY", CONTINENT="SA"),
        ],
    },
}

# ------------------------------------------------------- VHF contests (EDI)
VHF_STATION = {
    **STATION,
    "Name": "Sample Operator",
    "Street1": "1 Beispielweg",
    "City": "Musterstadt",
    "State": "",
    "Zip": "00000",
    "Country": "Germany",
    "Email": "dl1abc@example.com",
    "GridSquare": "JN58",
    "ARRLSection": "DX",
    "Club": "Example Contest Club",
}
FIXTURES["nac_vhf"] = {
    "DL1ABC": {
        "station": {**VHF_STATION, "Call": "DL1ABC"},
        "contest_settings": {**CATS, "BandCategory": "2M", "ModeCategory": "SSB+CW",
                             "StartDate": "2026-06-06 12:00:00",
                             "SentExchange": "JN58"},
        "qsos": [
            qso(CALL="OK1ABC", QSO_DATE="20260606", TIME_ON="140000", FREQ="144.300",
                MODE="SSB", SNT="59", RCV="59", SENTNR="JN58", NR="JO70",
                EXCHANGE1="JO70", GRIDSQUARE="JO70", STATION_CALLSIGN="DL1ABC"),
            qso(CALL="DL2XYZ", QSO_DATE="20260606", TIME_ON="140300", FREQ="144.320",
                MODE="CW", SNT="599", RCV="599", SENTNR="JN58", NR="JN49",
                EXCHANGE1="JN49", GRIDSQUARE="JN49", STATION_CALLSIGN="DL1ABC"),
            qso(CALL="OK1ABC", QSO_DATE="20260606", TIME_ON="140600", FREQ="144.300",
                MODE="SSB", SNT="59", RCV="59", SENTNR="JN58", NR="JO70",
                EXCHANGE1="JO70", GRIDSQUARE="JO70", STATION_CALLSIGN="DL1ABC"),
            qso(CALL="OK1ABC", QSO_DATE="20260606", TIME_ON="140900", FREQ="432.200",
                MODE="CW", SNT="599", RCV="599", SENTNR="JN58", NR="JO70",
                EXCHANGE1="JO70", GRIDSQUARE="JO70", STATION_CALLSIGN="DL1ABC"),
            qso(CALL="OE1ABC", QSO_DATE="20260606", TIME_ON="141200", FREQ="144.340",
                MODE="SSB", SNT="59", RCV="59", SENTNR="JN58", NR="JN78",
                EXCHANGE1="JN78", GRIDSQUARE="JN78", STATION_CALLSIGN="DL1ABC"),
            qso(CALL="SP1ABC", QSO_DATE="20260606", TIME_ON="141500", FREQ="50.200",
                MODE="SSB", SNT="59", RCV="59", SENTNR="JN58", NR="JO91",
                EXCHANGE1="JO91", GRIDSQUARE="JO91", STATION_CALLSIGN="DL1ABC"),
        ],
    },
}
# ------------------------------------------------------------- vhf_sprint
# VHF & Up Sprints.  On 50, 144, 222 and 432 MHz a contact is one point, on
# the Microwave Sprint (902 MHz and up) it is the distance in kilometres, and
# the multiplier is each grid square worked per band - a grid counts once per
# band whatever mode it was worked on.
_VHF_SPRINT_DL_STATION = {
    **VHF_STATION,
    "Call": "DL1ABC",
    "GridSquare": "JN58",
    "Name": "Sample Operator",
    "Street1": "1 Beispielweg",
    "City": "Musterstadt",
    "Zip": "00000",
    "Country": "Germany",
    "Email": "dl1abc@example.com",
    "Club": "Example Contest Club",
}


def _sprint_contact(station, call, time_on, freq, mode, grid):
    return qso(
        CALL=call,
        QSO_DATE="20260810",
        TIME_ON=time_on,
        FREQ=freq,
        MODE=mode,
        SNT="599" if mode == "CW" else "59",
        RCV="599" if mode == "CW" else "59",
        NR=grid,
        EXCHANGE1=grid,
        GRIDSQUARE=grid,
        STATION_CALLSIGN=station,
    )


FIXTURES["vhf_sprint"] = {
    "K6GTE": {
        "station": STATION,  # DM13
        "contest_settings": {**CATS, "BandCategory": "ALL", "ModeCategory": "SSB+CW",
                             "SentExchange": "DM13"},
        "qsos": [
            # 50, 144 and 432 MHz are a point each
            _sprint_contact("K6GTE", "W1AW", "180000", "50.200", "SSB", "FN31"),
            _sprint_contact("K6GTE", "W1AW", "180300", "144.200", "SSB", "FN31"),
            _sprint_contact("K6GTE", "W1AW", "180600", "432.100", "SSB", "FN31"),
            # the Microwave Sprint is the distance: DM13 to FN31 is 3965 km
            _sprint_contact("K6GTE", "W1AW", "180900", "1296.100", "SSB", "FN31"),
            # a duplicate on the band and mode
            _sprint_contact("K6GTE", "W1AW", "181200", "144.200", "SSB", "FN31"),
            # the same grid on another band is another multiplier
            _sprint_contact("K6GTE", "N0AX", "181500", "144.220", "CW", "EN34"),
        ],
    },
    "DL1ABC": {
        "station": _VHF_SPRINT_DL_STATION,
        "contest_settings": {**CATS, "BandCategory": "ALL", "ModeCategory": "SSB+CW",
                             "SentExchange": "JN58"},
        "qsos": [
            # microwave only: 367 and 441 km
            _sprint_contact("DL1ABC", "OK1ABC", "180000", "1296.100", "CW", "JO70"),
            _sprint_contact("DL1ABC", "OK2ABC", "180300", "2304.100", "CW", "JO31"),
            _sprint_contact("DL1ABC", "OK1ABC", "180600", "1296.100", "CW", "JO70"),
        ],
    },
}

# ---------------------------------------------------------------- darc_vhf
FIXTURES["darc_vhf"] = {
    "DL1ABC": {
        "station": {**VHF_STATION, "Call": "DL1ABC"},
        "contest_settings": {**CATS, "BandCategory": "2M", "ModeCategory": "SSB+CW",
                             "StartDate": "2026-09-05 14:00:00",
                             "SentExchange": "JN58"},
        "qsos": [
            qso(CALL="DK0ABC", QSO_DATE="20260905", TIME_ON="140000", FREQ="144.310",
                MODE="SSB", SNT="59", RCV="59", SENTNR="JN58", NR="JO31",
                EXCHANGE1="JO31", GRIDSQUARE="JO31", STATION_CALLSIGN="DL1ABC"),
            qso(CALL="DL2XYZ", QSO_DATE="20260905", TIME_ON="140300", FREQ="144.330",
                MODE="CW", SNT="599", RCV="599", SENTNR="JN58", NR="JN49",
                EXCHANGE1="JN49", GRIDSQUARE="JN49", STATION_CALLSIGN="DL1ABC"),
            qso(CALL="DK0ABC", QSO_DATE="20260905", TIME_ON="140600", FREQ="432.210",
                MODE="CW", SNT="599", RCV="599", SENTNR="JN58", NR="JO31",
                EXCHANGE1="JO31", GRIDSQUARE="JO31", STATION_CALLSIGN="DL1ABC"),
            qso(CALL="OK1ABC", QSO_DATE="20260905", TIME_ON="140900", FREQ="144.350",
                MODE="SSB", SNT="59", RCV="59", SENTNR="JN58", NR="JO70",
                EXCHANGE1="JO70", GRIDSQUARE="JO70", STATION_CALLSIGN="DL1ABC"),
            qso(CALL="DK0ABC", QSO_DATE="20260905", TIME_ON="141200", FREQ="144.310",
                MODE="SSB", SNT="59", RCV="59", SENTNR="JN58", NR="JO31",
                EXCHANGE1="JO31", GRIDSQUARE="JO31", STATION_CALLSIGN="DL1ABC"),
        ],
    },
}
# ------------------------------------------------------ stew_perry_topband
# Stew Perry Topband Distance Challenge, 160m CW.  A contact is one point plus
# one for every 500 km between the two grids, and the entrant's own power
# multiplies the final score: x1.5 for low power and x3 for QRP.  There are no
# multipliers.
_STEW_DL_STATION = {
    **STATION,
    "Call": "DL1ABC",
    "Country": "Fed. Rep. of Germany",
    "State": "",
    "GridSquare": "JN58",
    "ARRLSection": "DX",
    "Email": "dl1abc@example.com",
}
_STEW_SM_STATION = {
    **STATION,
    "Call": "SM5XYZ",
    "Country": "Sweden",
    "State": "",
    "GridSquare": "JO89",
    "ARRLSection": "DX",
    "Email": "sm5xyz@example.com",
}


def _stew_contact(station, call, time_on, grid):
    return qso(
        CALL=call,
        QSO_DATE="20261226",
        TIME_ON=time_on,
        FREQ="1.830",
        MODE="CW",
        SNT="599",
        RCV="599",
        EXCHANGE1=grid,
        STATION_CALLSIGN=station,
    )


FIXTURES["stew_perry_topband"] = {
    # High power: the score is just the QSO points.
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "CW", "PowerCategory": "HIGH",
                             "SentExchange": "DM13"},
        "qsos": [
            # DM13 to FN31 is 3965 km: 1 + 7
            _stew_contact("K6GTE", "W1AW", "150000", "FN31"),
            # to JN58 is 9633 km: 1 + 19
            _stew_contact("K6GTE", "DL1ABC", "150200", "JN58"),
            # to EN34 is 2408 km: 1 + 4
            _stew_contact("K6GTE", "N0AX", "150400", "EN34"),
            # worked once per contest
            _stew_contact("K6GTE", "W1AW", "150600", "FN31"),
        ],
    },
    # Low power: 33 points is not it - 20 + 1 + 3 = 24, times 1.5.
    "DL1ABC": {
        "station": _STEW_DL_STATION,
        "contest_settings": {**CATS, "ModeCategory": "CW", "PowerCategory": "LOW",
                             "SentExchange": "JN58"},
        "qsos": [
            _stew_contact("DL1ABC", "K6GTE", "150000", "DM13"),
            _stew_contact("DL1ABC", "OK2ABC", "150200", "JO70"),
            _stew_contact("DL1ABC", "SM5XYZ", "150400", "JO89"),
            _stew_contact("DL1ABC", "K6GTE", "150600", "DM13"),
        ],
    },
    # QRP: 18 + 3 + 3 = 24, times three.
    "SM5XYZ": {
        "station": _STEW_SM_STATION,
        "contest_settings": {**CATS, "ModeCategory": "CW", "PowerCategory": "QRP",
                             "SentExchange": "JO89"},
        "qsos": [
            _stew_contact("SM5XYZ", "K6GTE", "150000", "DM13"),
            _stew_contact("SM5XYZ", "DL1ABC", "150200", "JN58"),
            _stew_contact("SM5XYZ", "OK2ABC", "150400", "JO70"),
            _stew_contact("SM5XYZ", "K6GTE", "150600", "DM13"),
        ],
    },
}

# --------------------------------------------------------------- iaru_hf
# IARU HF World Championship.  One point for a contact in your own ITU zone or
# with an IARU HQ station or official (which send a society abbreviation
# rather than a zone), 3 for another zone on your continent and 5 for another
# continent.  The multipliers are the ITU zones and the HQ stations worked on
# each band - once per band, not per mode.
_IARU_US_STATION = {**STATION, "IARUZone": 8}
_IARU_DL_STATION = {
    **STATION,
    "Call": "DL1ABC",
    "Country": "Fed. Rep. of Germany",
    "State": "",
    "GridSquare": "JN58",
    "ARRLSection": "DX",
    "IARUZone": 28,
    "Email": "dl1abc@example.com",
}


def _iaru_contact(station, call, time_on, freq, mode, sent, zn, continent=None):
    field = {
        "CALL": call,
        "QSO_DATE": "20260711",
        "TIME_ON": time_on,
        "FREQ": freq,
        "MODE": mode,
        "SNT": "599" if mode == "CW" else "59",
        "RCV": "599" if mode == "CW" else "59",
        "SENTNR": sent,
        "ZN": zn,
        "NR": zn,
        "STATION_CALLSIGN": station,
    }
    if continent is not None:
        field["CONTINENT"] = continent
    return qso(**field)


FIXTURES["iaru_hf"] = {
    "K6GTE": {
        "station": _IARU_US_STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW",
                             "StartDate": "2026-07-11 12:00:00",
                             "SentExchange": "8"},
        "qsos": [
            # our own zone: one point
            _iaru_contact("K6GTE", "N0AX", "120000", "14.025", "CW", "8", "8", "NA"),
            # another continent: five points
            _iaru_contact("K6GTE", "DL1ABC", "120300", "14.025", "SSB", "8", "28", "EU"),
            # an HQ station sends ARRL, not a zone: one point, a multiplier
            _iaru_contact("K6GTE", "W1AW", "120600", "14.025", "CW", "8", "ARRL", "NA"),
            # another zone on our continent: three points
            _iaru_contact("K6GTE", "KL7ABC", "120900", "7.030", "CW", "8", "1", "NA"),
            # a duplicate on the band and mode
            _iaru_contact("K6GTE", "N0AX", "121200", "14.025", "CW", "8", "8", "NA"),
            # the same zone again, on the band but not the mode: it scores but
            # is not a second multiplier
            _iaru_contact("K6GTE", "DL1ABC", "121500", "14.025", "CW", "8", "28"),
        ],
    },
    "DL1ABC": {
        "station": _IARU_DL_STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW",
                             "StartDate": "2026-07-11 12:00:00",
                             "SentExchange": "28"},
        "qsos": [
            _iaru_contact("DL1ABC", "DL2ABC", "120000", "7.030", "CW", "28", "28", "EU"),
            _iaru_contact("DL1ABC", "K6GTE", "120300", "14.025", "SSB", "28", "8", "NA"),
            _iaru_contact("DL1ABC", "SM5XYZ", "120600", "14.025", "CW", "28", "18", "EU"),
            _iaru_contact("DL1ABC", "W1AW", "120900", "14.025", "CW", "28", "ARRL", "NA"),
            _iaru_contact("DL1ABC", "K6GTE", "121200", "14.025", "SSB", "28", "8", "NA"),
            _iaru_contact("DL1ABC", "SM5XYZ", "121500", "14.025", "SSB", "28", "18", "EU"),
        ],
    },
}

# ------------------------------------------------------ phone_weekly_test
# Phone Weekly Test (Phone Fray).  A North American station scores a point for
# every contact and anyone else scores one only against North America, and the
# multipliers are each US state, VE province and North American country other
# than W/VE, once per band.  A station outside North America sends only a name,
# so it has no section and gives no multiplier.
_PWT_DL_STATION = {
    **STATION,
    "Call": "DL1ABC",
    "Country": "Fed. Rep. of Germany",
    "State": "",
    "GridSquare": "JN58",
    "ARRLSection": "DX",
    "Email": "dl1abc@example.com",
}


def _pwt_contact(station, call, time_on, freq, sent, name, sect):
    return qso(
        CALL=call,
        QSO_DATE="20260113",
        TIME_ON=time_on,
        FREQ=freq,
        MODE="SSB",
        SNT="59",
        RCV="59",
        SENTNR=sent,
        NAME=name,
        SECT=sect,
        STATION_CALLSIGN=station,
    )


FIXTURES["phone_weekly_test"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB", "SentExchange": "SAM CA"},
        "qsos": [
            _pwt_contact("K6GTE", "N0AX", "010000", "3.580", "SAM CA", "RICK", "NC"),
            _pwt_contact("K6GTE", "VE3ABC", "010100", "3.585", "SAM CA", "BOB", "ON"),
            # a European station keeps its name only, and is no multiplier
            _pwt_contact("K6GTE", "DL1ABC", "010200", "7.080", "SAM CA", "HANS", ""),
            _pwt_contact("K6GTE", "N0AX", "010300", "3.580", "SAM CA", "RICK", "NC"),
            _pwt_contact("K6GTE", "W1AW", "010400", "14.080", "SAM CA", "ANN", "CT"),
            _pwt_contact("K6GTE", "DL1ABC", "010500", "7.080", "SAM CA", "HANS", ""),
        ],
    },
    # Outside North America: only the North American contacts score.
    "DL1ABC": {
        "station": _PWT_DL_STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB", "SentExchange": "HANS DX"},
        "qsos": [
            _pwt_contact("DL1ABC", "N0AX", "010000", "3.580", "HANS DX", "RICK", "NC"),
            _pwt_contact("DL1ABC", "K6GTE", "010100", "3.585", "HANS DX", "SAM", "CA"),
            _pwt_contact("DL1ABC", "DL2ABC", "010200", "7.080", "HANS DX", "JOCHEN", ""),
            _pwt_contact("DL1ABC", "N0AX", "010300", "3.580", "HANS DX", "RICK", "NC"),
            _pwt_contact("DL1ABC", "W1AW", "010400", "14.080", "HANS DX", "ANN", "CT"),
            _pwt_contact("DL1ABC", "DL2ABC", "010500", "7.080", "HANS DX", "JOCHEN", ""),
        ],
    },
}

# ---------------------------------------------------------- labre_rs_digi
# LABRE-RS Digi Contest, FT8/FT4.  A contact is one point, two for a station in
# Rio Grande do Sul (the 3rd call area), and the multiplier is each two-
# character grid field once per band.  A station may be worked once per band.
_LABRE_PY1_STATION = {
    **STATION,
    "Call": "PY1ABC",
    "Country": "Brazil",
    "State": "",
    "GridSquare": "GG87",
    "ARRLSection": "DX",
    "Email": "py1abc@example.com",
}


def _labre_contact(station, call, time_on, freq, sent, grid, pfx):
    return qso(
        CALL=call,
        QSO_DATE="20260201",
        TIME_ON=time_on,
        FREQ=freq,
        MODE="FT8",
        SNT="599",
        RCV="599",
        SENTNR=sent,
        NR=grid,
        COUNTRYPREFIX=pfx,
        STATION_CALLSIGN=station,
    )


FIXTURES["labre_rs_digi"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "RTTY", "SentExchange": "DM13"},
        "qsos": [
            # Rio Grande do Sul is the 3rd call area: two points
            _labre_contact("K6GTE", "PY3ABC", "000000", "3.580", "DM13", "GG87", "PY"),
            _labre_contact("K6GTE", "DL1ABC", "000100", "3.585", "DM13", "JO70", "DL"),
            # a duplicate on the band
            _labre_contact("K6GTE", "PY3ABC", "000200", "3.580", "DM13", "GG87", "PY"),
            # PY1 is Brazil but not the 3rd area, so only one point
            _labre_contact("K6GTE", "PY1ABC", "000300", "7.080", "DM13", "GG87", "PY"),
            _labre_contact("K6GTE", "LU1ABC", "000400", "7.085", "DM13", "GF05", "LU"),
        ],
    },
    "PY1ABC": {
        "station": _LABRE_PY1_STATION,
        "contest_settings": {**CATS, "ModeCategory": "RTTY", "SentExchange": "GG87"},
        "qsos": [
            _labre_contact("PY1ABC", "PY3ABC", "000000", "3.580", "GG87", "GG87", "PY"),
            _labre_contact("PY1ABC", "DL1ABC", "000100", "3.585", "GG87", "JO70", "DL"),
            _labre_contact("PY1ABC", "PY3ABC", "000200", "3.580", "GG87", "GG87", "PY"),
            _labre_contact("PY1ABC", "LU1ABC", "000300", "7.080", "GG87", "GF05", "LU"),
        ],
    },
}

# ---------------------------------------------------------- qso_party_rst
# The generic State QSO Party, its RST exchange flavour.  Phone is one point,
# CW and digital two, and the multiplier is each county, state or country
# once across all bands and modes.  A county is four letters, or a two-letter
# state or province, or DX.
def _party_rst_contact(station, call, time_on, freq, mode, exch):
    rst = "59" if mode in ("SSB", "LSB", "USB", "FM", "AM") else "599"
    return qso(
        CALL=call,
        QSO_DATE="20260606",
        TIME_ON=time_on,
        FREQ=freq,
        MODE=mode,
        SNT=rst,
        RCV=rst,
        SENTNR=exch,
        EXCHANGE1=exch,
        STATION_CALLSIGN=station,
    )


FIXTURES["qso_party_rst"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "ORG"},
        "qsos": [
            # phone is one point
            _party_rst_contact("K6GTE", "W6ABC", "180000", "7.200", "SSB", "SCLA"),
            # CW and digital are two
            _party_rst_contact("K6GTE", "N6XYZ", "180300", "14.040", "CW", "SDIE"),
            _party_rst_contact("K6GTE", "K7ABC", "180600", "7.210", "SSB", "WA"),
            _party_rst_contact("K6GTE", "JA1ABC", "180900", "21.040", "FT8", "DX"),
            _party_rst_contact("K6GTE", "VE7ABC", "181200", "21.045", "CW", "BC"),
            _party_rst_contact("K6GTE", "KH6ABC", "181500", "14.045", "RTTY", "HI"),
            # the same county again, on another band
            _party_rst_contact("K6GTE", "W6ABC", "181800", "14.200", "SSB", "SCLA"),
        ],
    },
}

# ----------------------------------------------------------- qso_party_sn
# The same, with a serial number in place of the RST.
def _party_sn_contact(station, call, time_on, freq, mode, nr, exch):
    return qso(
        CALL=call,
        QSO_DATE="20260606",
        TIME_ON=time_on,
        FREQ=freq,
        MODE=mode,
        SENTNR=nr,
        NR=nr,
        EXCHANGE1=exch,
        STATION_CALLSIGN=station,
    )


FIXTURES["qso_party_sn"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW", "SentExchange": "ORG"},
        "qsos": [
            _party_sn_contact("K6GTE", "W6ABC", "180000", "7.200", "SSB", "5", "SCLA"),
            _party_sn_contact("K6GTE", "N6XYZ", "180300", "14.040", "CW", "12", "SDIE"),
            _party_sn_contact("K6GTE", "K7ABC", "180600", "7.210", "SSB", "7", "WA"),
            _party_sn_contact("K6GTE", "JA1ABC", "180900", "21.040", "FT8", "9", "DX"),
            _party_sn_contact("K6GTE", "VE7ABC", "181200", "21.045", "CW", "2", "BC"),
            _party_sn_contact("K6GTE", "KH6ABC", "181500", "14.045", "RTTY", "3", "HI"),
            _party_sn_contact("K6GTE", "W6ABC", "181800", "14.200", "SSB", "5", "SCLA"),
        ],
    },
}

# ------------------------------------------------------------- randomgram
# RandomGram, CW.  RST plus one random five-character group, two points a
# contact, and a station may be worked again on the same band - the contest's
# N1MM UDC has DupeType = 4 and NumMults = 0.  It has no Cabrillo or EDI
# output (the event wants a list of the groups received), so the fixture is
# marked export = false and only its scoring is checked.
def _rg_contact(station, call, time_on, freq, sent, received):
    return qso(
        CALL=call,
        QSO_DATE="20261114",
        TIME_ON=time_on,
        FREQ=freq,
        MODE="CW",
        SNT="599",
        RCV="599",
        SENTNR=sent,
        NR=received,
        COMMENT=received,
        STATION_CALLSIGN=station,
    )


FIXTURES["randomgram"] = {
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "CW", "SentExchange": "A7N67"},
        "qsos": [
            _rg_contact("K6GTE", "ZL3TK", "120000", "7.030", "A7N67", "9RIB6"),
            _rg_contact("K6GTE", "N1FG", "120300", "7.035", "9RIB6", "SJM1D"),
            _rg_contact("K6GTE", "VK2DVA", "120600", "14.030", "SJM1D", "6O113"),
            # the same station again on the same band: no dupe restrictions
            _rg_contact("K6GTE", "ZL3TK", "120900", "7.030", "6O113", "UPTNK"),
            _rg_contact("K6GTE", "N1FG", "121200", "14.035", "UPTNK", "KJ4VJ"),
        ],
    },
}

# ------------------------------------------------------------- rda_contest
# RDA Contest, CW and SSB.  A non-Russian station gets 10 points for each
# Russian one it works and counts RDA districts.  A Russian station gets 1
# point for another Russian on its continent and 2 for one on another, 3 for a
# different country on its own continent and 5 for one on another, and counts
# both DXCC countries (once per band) and RDA districts (irrespective of
# band).  Kaliningrad scores as European Russia but is its own DXCC country
# and district, and Asiatic Russia is its own DXCC country too.
_RDA_UA3_STATION = {
    **STATION,
    "Call": "UA3ABC",
    "Country": "European Russia",
    "State": "",
    "GridSquare": "KO85",
    "ARRLSection": "DX",
    "Email": "ua3abc@example.com",
}


def _rda_contact(station, call, time_on, freq, mode, sent, nr, pfx):
    rst = "599" if mode == "CW" else "59"
    return qso(
        CALL=call,
        QSO_DATE="20260815",
        TIME_ON=time_on,
        FREQ=freq,
        MODE=mode,
        SNT=rst,
        RCV=rst,
        SENTNR=sent,
        NR=nr,
        COUNTRYPREFIX=pfx,
        STATION_CALLSIGN=station,
    )


FIXTURES["rda_contest"] = {
    # Outside Russia: 10 points a Russian contact, and RDA districts only.
    "K6GTE": {
        "station": STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW",
                             "StartDate": "2026-08-15 08:00:00",
                             "SentExchange": "001"},
        "qsos": [
            _rda_contact("K6GTE", "UA3ABC", "000000", "14.025", "CW", "001", "MO-01", "UA"),
            _rda_contact("K6GTE", "UA9ABC", "000300", "7.030", "CW", "002", "SV-01", "UA9"),
            # a duplicate on the band, same exchange
            _rda_contact("K6GTE", "UA3ABC", "000600", "14.025", "CW", "003", "MO-01", "UA"),
            # a non-Russian station is worth no points to a non-Russian one
            _rda_contact("K6GTE", "DL1ABC", "000900", "14.050", "SSB", "004", "001", "DL"),
            # MO-01 is already counted, whatever the band
            _rda_contact("K6GTE", "RA3ABC", "001200", "7.030", "CW", "005", "MO-01", "UA"),
            # Kaliningrad is its own award district
            _rda_contact("K6GTE", "UA2ABC", "001500", "14.025", "CW", "006", "KA-01", "UA2"),
        ],
    },
    # Inside European Russia: the whole points table and both multiplier kinds.
    "UA3ABC": {
        "station": _RDA_UA3_STATION,
        "contest_settings": {**CATS, "ModeCategory": "SSB+CW",
                             "StartDate": "2026-08-15 08:00:00",
                             "SentExchange": "MO-01"},
        "qsos": [
            # Asiatic Russia is Russian on another continent: 2 points
            _rda_contact("UA3ABC", "UA9ABC", "000000", "14.025", "CW", "MO-01", "SV-01", "UA9"),
            # another European Russian: 1 point
            _rda_contact("UA3ABC", "R3ABC", "000300", "14.030", "CW", "MO-01", "MO-05", "UA"),
            # a different country on the same continent: 3 points
            _rda_contact("UA3ABC", "DL1ABC", "000600", "7.030", "SSB", "MO-01", "001", "DL"),
            # a different continent: 5 points
            _rda_contact("UA3ABC", "N0AX", "000900", "7.035", "CW", "MO-01", "002", "K"),
            _rda_contact("UA3ABC", "UA9ABC", "001200", "14.025", "CW", "MO-01", "SV-01", "UA9"),
            # Kaliningrad scores as European Russia: 1 point, but it is a
            # separate country multiplier and district
            _rda_contact("UA3ABC", "UA2ABC", "001500", "7.040", "CW", "MO-01", "KA-01", "UA2"),
        ],
    },
}

# ------------------------------------------------------- ta_vhf_uhf_contest
# TA VHF/UHF Contest.  A contact is the distance in kilometres times a band
# factor (6m x1, 2m x2, 70cm x3) times a mode factor (FM x1, SSB x2, CW x3),
# and the score is the sum - there are no separate multipliers.  The band
# column is a float, so it has to be compared as one.
FIXTURES["ta_vhf_uhf_contest"] = {
    "TA1ABC": {
        "station": {**VHF_STATION, "Call": "TA1ABC", "GridSquare": "KN41",
                    "Name": "Sample Operator", "Street1": "1 Ornek Sokak",
                    "City": "Orneksehir", "Zip": "00000", "Country": "Turkey",
                    "Email": "ta1abc@example.com", "Club": "Example Contest Club"},
        "contest_settings": {**CATS, "BandCategory": "ALL", "ModeCategory": "SSB+CW",
                             "StartDate": "2026-07-04 12:00:00",
                             "SentExchange": "KN41"},
        "qsos": [
            # 2m CW: 202 km x 2 x 3
            qso(CALL="TA2XYZ", QSO_DATE="20260704", TIME_ON="120000", FREQ="144.300",
                MODE="CW", SNT="599", RCV="599", SENTNR="KN41", NR="KN50",
                EXCHANGE1="KN50", GRIDSQUARE="KN50", STATION_CALLSIGN="TA1ABC"),
            # 2m SSB: 280 km x 2 x 2
            qso(CALL="TA3ABC", QSO_DATE="20260704", TIME_ON="120300", FREQ="144.320",
                MODE="SSB", SNT="59", RCV="59", SENTNR="KN41", NR="KM59",
                EXCHANGE1="KM59", GRIDSQUARE="KM59", STATION_CALLSIGN="TA1ABC"),
            # 6m FM: 356 km x 1 x 1
            qso(CALL="TA4ABC", QSO_DATE="20260704", TIME_ON="120450", FREQ="50.200",
                MODE="FM", SNT="59", RCV="59", SENTNR="KN41", NR="KN60",
                EXCHANGE1="KN60", GRIDSQUARE="KN60", STATION_CALLSIGN="TA1ABC"),
            # 70cm CW: 202 km x 3 x 3
            qso(CALL="TA2XYZ", QSO_DATE="20260704", TIME_ON="120600", FREQ="432.200",
                MODE="CW", SNT="599", RCV="599", SENTNR="KN41", NR="KN50",
                EXCHANGE1="KN50", GRIDSQUARE="KN50", STATION_CALLSIGN="TA1ABC"),
            # a duplicate on 2m
            qso(CALL="TA2XYZ", QSO_DATE="20260704", TIME_ON="120900", FREQ="144.300",
                MODE="CW", SNT="599", RCV="599", SENTNR="KN41", NR="KN50",
                EXCHANGE1="KN50", GRIDSQUARE="KN50", STATION_CALLSIGN="TA1ABC"),
        ],
    },
}


# ---------------------------------------------------------------- batch 2
# A shared 10-QSO pattern, so every log exercises: a new multiplier, a second
# one, a repeat call on the same band, a dupe, the same call on a new band, a
# new call that is not a multiplier, another band, another multiplier, a dupe
# again, and a fourth band.
B2_PATTERN = [
    ("OK2ABC", 0, "CW", 0),
    ("DL1ABC", 0, "SSB", 1),
    ("OK2ABC", 0, "SSB", 0),
    ("OK2ABC", 1, "CW", 0),
    ("DL1ABC", 1, "CW", 1),
    ("N0AX", 0, "CW", 0),
    ("JA1ABC", 2, "CW", 2),
    ("W1AW", 1, "CW", 0),
    ("OK2ABC", 0, "CW", 0),
    ("PY1ABC", 3, "SSB", 3),
]
B2_OTHER = {
    "OK2ABC": ("OK", "EU"),
    "DL1ABC": ("DL", "EU"),
    "N0AX": ("K", "NA"),
    "JA1ABC": ("JA", "AS"),
    "W1AW": ("W", "NA"),
    "PY1ABC": ("PY", "SA"),
}
B2_BANDS = {
    "default": ["14.025", "7.030", "21.040", "28.050"],
    "160": ["1.825", "1.830", "1.835", "1.840"],
    "10": ["28.025", "28.050", "28.100", "28.150"],
    "vhf": ["50.200", "144.200", "432.100", "1296.100"],
}


def station_for(call, country="United States", state="CA", section="ORG", grid="DM13"):
    """A synthetic station at the given call/location."""
    return {
        **STATION,
        "Call": call,
        "Country": country,
        "State": state,
        "ARRLSection": section,
        "GridSquare": grid,
        "Email": f"{call.lower()}@example.com",
    }


def variant(call, country="Germany", state="", section="DX", grid="JN58"):
    """An extra location for a contest whose scoring depends on where *you* are."""
    return {
        "my_call": call,
        "station": station_for(call, country, state, section, grid),
    }


def dln(sent=None, call="DL1ABC"):
    """A German variant, optionally sending a different exchange."""
    extra = variant(call)
    if sent is not None:
        extra["sent"] = sent
    return extra


DL = variant("DL1ABC")
UA = variant("UA3ABC", country="European Russia", grid="KO85")
JA = variant("JA1ABC", country="Japan", grid="PM95")
SM = variant("SM5XYZ", country="Sweden", grid="JO89")


def b2_qsos(spec):
    bands = B2_BANDS[spec.get("bands", "default")]
    my_call = spec.get("my_call", STATION["Call"])
    out = []
    for i, (call, band_idx, pattern_mode, xi) in enumerate(B2_PATTERN):
        prefix, continent = B2_OTHER[call]
        mode = spec.get("mode") or pattern_mode
        fields = {
            "CALL": call,
            "QSO_DATE": DATE,
            "TIME_ON": f"{1200 + i * 5:06d}",
            "FREQ": bands[band_idx],
            "MODE": mode,
            "STATION_CALLSIGN": my_call,
            "SNT": "59" if mode == "SSB" else "599",
            "RCV": "59" if mode == "SSB" else "599",
            "COUNTRYPREFIX": prefix,
            "CONTINENT": continent,
        }
        fields.update(spec["sent"])
        fields.update(spec["x"][xi])
        if spec.get("wpx"):
            fields["WPXPREFIX"] = prefix + "1"
        out.append(qso(**fields))
    return out


def ser(*numbers):
    return [{"NR": n} for n in numbers]


BATCH2 = {
    "cq_wpx_cw": dict(sent={"SENTNR": "001"}, x=ser("123", "456", "789", "321"),
                      mode="CW", wpx=True),
    "cq_wpx_ssb": dict(sent={"SENTNR": "001"}, x=ser("123", "456", "789", "321"),
                       mode="SSB", wpx=True),
    "cq_ww_ssb": dict(
        sent={"SENTNR": "5"},
        x=[{"ZN": "14", "NR": "14"}, {"ZN": "25", "NR": "25"},
           {"ZN": "38", "NR": "38"}, {"ZN": "11", "NR": "11"}],
        mode="SSB"),
    "cq_ww_rtty": dict(
        sent={"SENTNR": "5"},
        x=[{"ZN": "14", "EXCHANGE1": "DL"}, {"ZN": "25", "EXCHANGE1": "JA"},
           {"ZN": "5", "EXCHANGE1": "TX"}, {"ZN": "16", "EXCHANGE1": "UA"}],
        mode="RTTY"),
    "cq_160_cw": dict(
        sent={"SENTNR": "TX"},
        x=[{"EXCHANGE1": "DL"}, {"EXCHANGE1": "JA"}, {"EXCHANGE1": "TX"},
           {"EXCHANGE1": "UA"}],
        mode="CW", bands="160"),
    "cq_160_ssb": dict(
        sent={"SENTNR": "TX"},
        x=[{"EXCHANGE1": "DL"}, {"EXCHANGE1": "JA"}, {"EXCHANGE1": "TX"},
           {"EXCHANGE1": "UA"}],
        mode="SSB", bands="160"),
    "arrl_dx_cw": dict(sent={"SENTNR": "TX"}, x=ser("100", "500", "1000", "050"),
                       mode="CW"),
    "arrl_dx_ssb": dict(sent={"SENTNR": "TX"}, x=ser("100", "500", "1000", "050"),
                        mode="SSB"),
    "arrl_10m": dict(sent={"SENTNR": "TX"}, x=ser("001", "002", "003", "004"),
                     bands="10"),
    "arrl_160m": dict(
        sent={"SENTNR": "TX"},
        x=[{"EXCHANGE1": "DL"}, {"EXCHANGE1": "JA"}, {"EXCHANGE1": "TX"},
           {"EXCHANGE1": "UA"}],
        mode="CW", bands="160"),
    "arrl_ss_phone": dict(
        sent={"SENTNR": "1"},
        x=[{"NR": "12", "PREC": "A", "CK": "78", "SECT": "CT"},
           {"NR": "33", "PREC": "B", "CK": "95", "SECT": "MO"},
           {"NR": "66", "PREC": "Q", "CK": "99", "SECT": "NTX"},
           # a station outside W/VE sends "DX": no points, no multiplier
           {"NR": "99", "PREC": "B", "CK": "66", "SECT": "DX"}],
        mode="SSB"),
    "naqp_cw": dict(
        sent={"SENTNR": "MIKE CA"},
        x=[{"NAME": "RICK", "SECT": "NC"}, {"NAME": "BOB", "SECT": "TX"},
           {"NAME": "ANN", "SECT": "OR"}, {"NAME": "KEN", "SECT": "HI"}],
        mode="CW"),
    "naqp_ssb": dict(
        sent={"SENTNR": "MIKE CA"},
        x=[{"NAME": "RICK", "SECT": "NC"}, {"NAME": "BOB", "SECT": "TX"},
           {"NAME": "ANN", "SECT": "OR"}, {"NAME": "KEN", "SECT": "HI"}],
        mode="SSB"),
    "naqp_rtty": dict(
        sent={"SENTNR": "MIKE CA"},
        x=[{"NAME": "RICK", "SECT": "NC"}, {"NAME": "BOB", "SECT": "TX"},
           {"NAME": "ANN", "SECT": "OR"}, {"NAME": "KEN", "SECT": "HI"}],
        mode="RTTY"),
    "na_sprint_rtty": dict(
        sent={"SENTNR": "1"},
        x=[{"NR": "154", "NAME": "RICK", "SECT": "NC"},
           {"NR": "13", "NAME": "TREE", "SECT": "OR"},
           {"NR": "7", "NAME": "AKI", "SECT": "HI"},
           {"NR": "9", "NAME": "JUAN", "SECT": "XE"}],
        mode="RTTY"),
    "cq_ww_vhf": dict(
        sent={"SENTNR": "DM13", "SNT": "", "RCV": ""},
        x=[{"NR": "FN31", "GRIDSQUARE": "FN31"}, {"NR": "JO70", "GRIDSQUARE": "JO70"},
           {"NR": "CM87", "GRIDSQUARE": "CM87"}, {"NR": "KN50", "GRIDSQUARE": "KN50"}],
        bands="vhf"),
    "arrl_vhf_jan": dict(
        sent={"SENTNR": "DM13"},
        x=[{"NR": "FN31", "GRIDSQUARE": "FN31"}, {"NR": "JO70", "GRIDSQUARE": "JO70"},
           {"NR": "CM87", "GRIDSQUARE": "CM87"}, {"NR": "KN50", "GRIDSQUARE": "KN50"}],
        bands="vhf"),
    "arrl_vhf_sep": dict(
        sent={"SENTNR": "DM13"},
        x=[{"NR": "FN31", "GRIDSQUARE": "FN31"}, {"NR": "JO70", "GRIDSQUARE": "JO70"},
           {"NR": "CM87", "GRIDSQUARE": "CM87"}, {"NR": "KN50", "GRIDSQUARE": "KN50"}],
        bands="vhf"),
    "cwo": dict(
        sent={"SENTNR": "1"},
        x=[{"NR": "1234", "NAME": "BOB"}, {"NR": "5678", "NAME": "HANS"},
           {"NR": "1111", "NAME": "ANN"}, {"NR": "2222", "NAME": "KEN"}],
        mode="CW"),
    "icwc_mst": dict(
        sent={"SENTNR": "1"},
        x=[{"NAME": "BOB", "NR": "1234"}, {"NAME": "HANS", "NR": "5678"},
           {"NAME": "ANN", "NR": "1111"}, {"NAME": "KEN", "NR": "2222"}],
        mode="CW"),
    "k1usn_sst": dict(
        sent={"SENTNR": "MIKE CA"},
        x=[{"NAME": "BOB", "SECT": "CA"}, {"NAME": "HANS", "SECT": "ON"},
           {"NAME": "ANN", "SECT": "OR"}, {"NAME": "KEN", "SECT": "HI"}],
        mode="CW"),
}

BATCH3 = {}

_NAQP = [{"NAME": "RICK", "SECT": "NC"}, {"NAME": "BOB", "SECT": "TX"},
         {"NAME": "ANN", "SECT": "OR"}, {"NAME": "KEN", "SECT": "HI"}]
_GRID = [{"NR": "FN31"}, {"NR": "JO70"}, {"NR": "CM87"}, {"NR": "KN50"}]
_DOK = [{"NR": "P01"}, {"NR": "B02"}, {"NR": "NM"}, {"NR": "C03"}]
_IOTA = [{"NR": "002 EU-005"}, {"NR": "003 NA-001"},
         {"NR": "004 AS-007"}, {"NR": "005 OC-001"}]

BATCH4 = {
    "arrl_field_day": dict(
        sent={"EXCHANGE1": "1D ORG"},
        x=[{"EXCHANGE1": "1D ORG", "SECT": "ORG"},
           {"EXCHANGE1": "2A CT", "SECT": "CT"},
           {"EXCHANGE1": "1D DL", "SECT": "DX"},
           {"EXCHANGE1": "3A MO", "SECT": "MO"}]),
    "arrl_rtty_ru": dict(sent={"SENTNR": "TX"},
                         x=[{"NR": "TX"}, {"NR": "DL"}, {"NR": "JA"}, {"NR": "UA"}],
                         mode="RTTY"),
    "cqws": dict(sent={"SENTNR": "1"},
                 x=[{"EXCHANGE1": "SP"}, {"EXCHANGE1": "RE"},
                    {"EXCHANGE1": "DX"}, {"EXCHANGE1": "GE"}]),
    # dxpedition, general_logging and randomgram have no cabrillo()/edi()
    # output at all -- their export functions are empty -- so they cannot have
    # a golden log and stay placeholder directories.
    "darc_schwaben": dict(sent={"SENTNR": "A01"}, x=_DOK, wpx=True),
    "darc_xmas": dict(sent={"SENTNR": "A01"}, x=_DOK, wpx=True),
    "rsgb_iota": dict(sent={"SENTNR": "001"}, x=_IOTA),
    "sac_cw": dict(sent={"SENTNR": "001"}, x=ser("002", "003", "004", "005"),
                   mode="CW"),
    "sac_ssb": dict(sent={"SENTNR": "001"}, x=ser("002", "003", "004", "005"),
                    mode="SSB"),
    "ukeidx": dict(sent={"SENTNR": "001"},
                   x=[{"NR": "002 G"}, {"NR": "003 DL"}, {"NR": "004 G"},
                      {"NR": "005 JA"}]),
    "weekly_rtty": dict(sent={"SENTNR": "MIKE MA"}, x=_NAQP, mode="RTTY"),
    "wag": dict(sent={"SENTNR": "1"},
                x=[{"NR": "A01"}, {"NR": "P02"}, {"NR": "1"}, {"NR": "2"}]),
    "winter_field_day": dict(
        sent={"EXCHANGE1": "1O ORG"},
        x=[{"EXCHANGE1": "1O CT"}, {"EXCHANGE1": "2A DL"},
           {"EXCHANGE1": "1O MO"}, {"EXCHANGE1": "3A WA"}]),
}

_B2_CATEGORY = {"CW": "CW", "SSB": "SSB", "RTTY": "RTTY", None: "SSB+CW"}
# Contests whose scoring depends on where *your* station is get a second log
# from a station in a different part of the world.
_B2_VARIANTS = {
    "cq_wpx_cw": [DL],
    "cq_wpx_ssb": [DL],
    "cq_ww_ssb": [dln({"SENTNR": "14"})],
    "cq_ww_rtty": [dln({"SENTNR": "14"})],
    "cq_160_cw": [dln({"SENTNR": "14"})],
    "cq_160_ssb": [dln({"SENTNR": "14"})],
    "arrl_dx_cw": [dln({"SENTNR": "100"})],
    "arrl_dx_ssb": [dln({"SENTNR": "100"})],
    "arrl_160m": [dln({"SENTNR": "14"})],
    # a station outside W/VE only gets credit for W/VE contacts (rule 1)
    "arrl_vhf_jan": [dln({"SENTNR": "JN58"})],
    "arrl_vhf_sep": [dln({"SENTNR": "JN58"})],
    "naqp_cw": [dln({"SENTNR": "MIKE DX"})],
    "naqp_ssb": [dln({"SENTNR": "MIKE DX"})],
    "naqp_rtty": [dln({"SENTNR": "MIKE DX"})],
    "darc_schwaben": [DL],
    "darc_xmas": [DL],
    "rsgb_iota": [variant("G3XYZ", country="England", grid="IO91")],
    "sac_cw": [SM],
    "sac_ssb": [SM],
    "ukeidx": [variant("G3XYZ", country="England", grid="IO91")],
    # WAG scores differently inside and outside DL
    "wag": [dln({"SENTNR": "A01"})],
}

for _name, _spec in {**BATCH2, **BATCH3, **BATCH4}.items():
    _cases = {}
    for _loc in [{"my_call": STATION["Call"], "station": STATION}] + _B2_VARIANTS.get(
        _name, []
    ):
        _merged = {**_spec, **_loc}
        _cases[_merged["my_call"]] = {
            "station": _merged["station"],
            "contest_settings": {
                **CATS,
                "ModeCategory": _B2_CATEGORY[_spec.get("mode")],
                "SentExchange": _spec["sent"].get("SENTNR", ""),
            },
            "qsos": b2_qsos(_merged),
        }
    FIXTURES[_name] = _cases


def _relocate(contest, base_case, call, station, sent=None):
    """Re-log a hand-written case as a station somewhere else.

    Its QSOs already carry STATION_CALLSIGN, so rewrite that (and the sent
    exchange); everything else stays. The point is to drive the
    location-dependent scoring branches.
    """
    base = FIXTURES[contest][base_case]
    text = "".join(base["qsos"])
    text = re.sub(
        r"<STATION_CALLSIGN:\d+>[^<]*",
        f"<STATION_CALLSIGN:{len(call)}>{call}",
        text,
    )
    settings = dict(base["contest_settings"])
    if sent is not None:
        settings["SentExchange"] = sent
    FIXTURES[contest][call] = {
        "station": station,
        "contest_settings": settings,
        "qsos": [text],
    }


_relocate("cq_ww_cw", "K6GTE", "DL1ABC",
          station_for("DL1ABC", "Germany", grid="JN58"), sent="14")
_relocate("cq_wpx_rtty", "K6GTE", "DL1ABC",
          station_for("DL1ABC", "Germany", grid="JN58"))
_relocate("rdxc", "K6GTE", "UA3ABC",
          station_for("UA3ABC", "European Russia", grid="KO85"), sent="MO")
_relocate("ca_qso_party", "K6GTE", "W1AW",
          station_for("W1AW", "United States", state="CT", section="CT", grid="FN31"),
          sent="CT")
_relocate("na_sprint_cw", "K0RX", "DL1ZZ",
          station_for("DL1ZZ", "Germany", grid="JN58"), sent="DAVE DX")
# A UK entrant: every contact in the log now has a UK&CD station at one end,
# so the DL and OK contacts score here where they did not for K6GTE.
_relocate("rsgb_80m_cc", "K6GTE", "G3XYZ",
          station_for("G3XYZ", "England", section="DX", grid="IO91"))


def main():
    for plugin, cases in FIXTURES.items():
        module = importlib.import_module(f"not1mm.plugins.{plugin}")
        # pin after the import so this module's copy is included
        pin_versions(MP())
        plugin_dir = CONTEST_DIR / plugin
        plugin_dir.mkdir(parents=True, exist_ok=True)
        for case_name, fixture in cases.items():
            fixture["qsos"] = split_records(fixture["qsos"])
            (plugin_dir / f"{case_name}.adif").write_text(
                adif(fixture["qsos"]), encoding="ascii"
            )
            (plugin_dir / f"{case_name}.json").write_text(
                json.dumps(
                    {
                        "station": fixture["station"],
                        "contest_settings": fixture["contest_settings"],
                        "pref": {"contest": 1},
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            placeholder = plugin_dir / ".gitkeep"
            if placeholder.exists():
                placeholder.unlink()

            case = Case(plugin, case_name, plugin_dir)
            validate_adif_lengths(case.adif)

            home = OUT / case.id
            shutil.rmtree(home, ignore_errors=True)
            home.mkdir(parents=True, exist_ok=True)
            Path.home = staticmethod(lambda h=home: h)
            harness = ContestHarness(module, case, home)
            plugin_common.import_adif(harness)
            produced = harness.export(home)

            # Score once to learn what each contact is worth, write that into
            # the log the way a real export does, then score again from the
            # log that now says it - so the fixture and the plugin agree.
            points_by_key = {
                (c.get("Call", ""), str(c.get("TS", ""))): int(c.get("Points") or 0)
                for c in harness.database.fetch_all_contacts_asc()
            }
            fixture["qsos"] = [
                with_n1mm_points(record, points_by_key[record_key(record)])
                for record in fixture["qsos"]
            ]
            (plugin_dir / f"{case_name}.adif").write_text(
                adif(fixture["qsos"]), encoding="ascii"
            )
            validate_adif_lengths(case.adif)

            shutil.rmtree(home, ignore_errors=True)
            home.mkdir(parents=True, exist_ok=True)
            harness = ContestHarness(module, case, home)
            plugin_common.import_adif(harness)
            produced = harness.export(home)

            qsos = module.show_qso(harness)
            mults = module.show_mults(harness)
            score = module.calc_score(harness)
            config = json.loads(case.config.read_text(encoding="utf-8"))
            config["expected"] = {
                "qsos": qsos,
                "mults": mults,
                "score": score,
                "dupes": harness.dupes,
            }
            # A plugin with no Cabrillo/EDI output - RandomGram submits a list
            # of received groups, not a log - keeps its score in the corpus but
            # is marked export = false so the runner skips the export
            # comparison.  It is the only key written, so a plugin that does
            # export leaves the fixture exactly as it was.
            if produced is None:
                config["export"] = False
                for suffix in ("log", "edi"):
                    case.golden(suffix).unlink(missing_ok=True)
                where = "(no export)"
            else:
                config.pop("export", None)
                golden = case.golden("edi" if produced.suffix == ".edi" else "log")
                golden.write_bytes(produced.read_bytes())
                where = golden.name
            case.config.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

            rows = harness.database.fetch_all_contacts_asc()
            points = [r.get("Points") for r in rows]
            print(
                f"== {case.id:26s} -> {where:13s} "
                f"logged={len(rows):2d} qsos={qsos} mults={mults} score={score}"
            )
            print(f"     points={points}")
            for m in harness.messages:
                if "duplicate" in m.lower() or "Error" in m:
                    print(f"     msg: {m}")

        # A case renamed or dropped by the fixtures leaves its files behind;
        # remove anything this run did not write.
        keep = set(cases)
        for leftover in plugin_dir.iterdir():
            if (
                leftover.suffix in (".adif", ".json", ".log", ".edi")
                and leftover.stem not in keep
            ):
                print(f"-- {plugin}/{leftover.stem}: stale, removed {leftover.name}")
                leftover.unlink()


if __name__ == "__main__":
    main()
