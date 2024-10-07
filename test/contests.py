import pytest
import os

from PyQt6 import QtCore, QtWidgets

import not1mm.__main__ as not1mm
import not1mm.fsutils as fsutils

WAIT_TIME = 10

# Entry options:
#   callsign
#   sent (field1)
#   receive (field2)
#   other_1 (field3)
#   other_2 (field4)

CONTEST_DATA = {
    "General Logging": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "dan",
            "other_2": "cool dude",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "dan",
            "other_2": "cool dude",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_1": "mike",
            "other_2": "cool dude",
        },
    ],
    "10 10 FALL CW": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_2": "dan 1234 ia",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_2": "dan 1234 ia",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_2": "mike 1234 ca",
        },
    ],
    "10 10 SPRING CW": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_2": "dan 1234 ia",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_2": "dan 1234 ia",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_2": "mike 1234 ca",
        },
    ],
    "10 10 SUMMER PHONE": [
        {"callsign": "KF0NRV", "sent": "59", "receive": "59", "other_2": "dan 1234 ia"},
        {"callsign": "KF0NRV", "sent": "59", "receive": "59", "other_2": "dan 1234 ia"},
        {"callsign": "K6GTE", "sent": "59", "receive": "59", "other_2": "mike 1234 ca"},
    ],
    "10 10 WINTER PHONE": [
        {"callsign": "KF0NRV", "sent": "59", "receive": "59", "other_2": "dan 1234 ia"},
        {"callsign": "KF0NRV", "sent": "59", "receive": "59", "other_2": "dan 1234 ia"},
        {"callsign": "K6GTE", "sent": "59", "receive": "59", "other_2": "mike 1234 ca"},
    ],
    "ARRL 10M": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1234",
            "other_2": "ia",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1234",
            "other_2": "ia",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_1": "2345",
            "other_2": "ca",
        },
    ],
    "ARRL DX CW": [
        {"callsign": "KF0NRV", "sent": "599", "receive": "599", "other_2": "100W"},
        {"callsign": "KF0NRV", "sent": "599", "receive": "599", "other_2": "100W"},
        {"callsign": "K6GTE", "sent": "599", "receive": "599", "other_2": "100W"},
    ],
    "ARRL DX SSB": [
        {"callsign": "KF0NRV", "sent": "59", "receive": "59", "other_2": "100W"},
        {"callsign": "KF0NRV", "sent": "59", "receive": "59", "other_2": "100W"},
        {"callsign": "K6GTE", "sent": "59", "receive": "59", "other_2": "100W"},
    ],
    "ARRL FIELD DAY": [
        {"callsign": "KF0NRV", "other_1": "1", "other_2": "a"},
        {"callsign": "KF0NRV", "other_1": "1", "other_2": "a"},
        {"callsign": "K6GTE", "other_1": "1", "other_2": "a"},
    ],
    "ARRL SS CW": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1",
            "other_2": "27",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "2",
            "other_2": "42",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_1": "3",
            "other_2": "100",
        },
    ],
    "ARRL SS PHONE": [
        {
            "callsign": "KF0NRV",
            "sent": "59",
            "receive": "59",
            "other_1": "1",
            "other_2": "27",
        },
        {
            "callsign": "KF0NRV",
            "sent": "59",
            "receive": "59",
            "other_1": "2",
            "other_2": "42",
        },
        {
            "callsign": "K6GTE",
            "sent": "59",
            "receive": "59",
            "other_1": "3",
            "other_2": "100",
        },
    ],
    "ARRL VHF JAN": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1234",
            "other_2": "BB22AA",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1234",
            "other_2": "BB22AA",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_1": "2345",
            "other_2": "AA11bb",
        },
    ],
    "ARRL VHF JUN": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1234",
            "other_2": "BB22AA",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1234",
            "other_2": "BB22AA",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_1": "2345",
            "other_2": "AA11bb",
        },
    ],
    "ARRL VHF SEP": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1234",
            "other_2": "BB22AA",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1234",
            "other_2": "BB22AA",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_1": "2345",
            "other_2": "AA11bb",
        },
    ],
    "CANADA DAY": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1",
            "other_2": "ia",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "2",
            "other_2": "ia",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_1": "3",
            "other_2": "ca",
        },
    ],
    "CQ 160 CW": [
        {"callsign": "KF0NRV", "sent": "599", "receive": "599", "other_2": "ia"},
        {"callsign": "KF0NRV", "sent": "599", "receive": "599", "other_2": "ia"},
        {"callsign": "K6GTE", "sent": "599", "receive": "599", "other_2": "ca"},
    ],
    "CQ 160 SSB": [
        {"callsign": "KF0NRV", "sent": "59", "receive": "59", "other_2": "ia"},
        {"callsign": "KF0NRV", "sent": "59", "receive": "59", "other_2": "ia"},
        {"callsign": "K6GTE", "sent": "59", "receive": "59", "other_2": "ca"},
    ],
    "CQ WPX CW": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1",
            "other_2": "3",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "2",
            "other_2": "2",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_1": "3",
            "other_2": "1",
        },
    ],
    "CQ WPX SSB": [
        {
            "callsign": "KF0NRV",
            "sent": "59",
            "receive": "59",
            "other_1": "1",
            "other_2": "3",
        },
        {
            "callsign": "KF0NRV",
            "sent": "59",
            "receive": "59",
            "other_1": "2",
            "other_2": "2",
        },
        {
            "callsign": "K6GTE",
            "sent": "59",
            "receive": "59",
            "other_1": "3",
            "other_2": "1",
        },
    ],
    "CQ WW CW": [
        {"callsign": "KF0NRV", "sent": "599", "receive": "599", "other_2": "4"},
        {"callsign": "KF0NRV", "sent": "599", "receive": "599", "other_2": "4"},
        {"callsign": "K6GTE", "sent": "599", "receive": "599", "other_2": "3"},
    ],
    "CQ WW RTTY": [
        {"callsign": "KF0NRV", "sent": "599", "receive": "599", "other_2": "4"},
        {"callsign": "KF0NRV", "sent": "599", "receive": "599", "other_2": "4"},
        {"callsign": "K6GTE", "sent": "599", "receive": "599", "other_2": "3"},
    ],
    "CQ WW SSB": [
        {"callsign": "KF0NRV", "sent": "59", "receive": "59", "other_2": "4"},
        {"callsign": "KF0NRV", "sent": "59", "receive": "59", "other_2": "4"},
        {"callsign": "K6GTE", "sent": "59", "receive": "59", "other_2": "3"},
    ],
    "CWT": [
        {"callsign": "KF0NRV", "other_1": "dan", "other_2": "ia"},
        {"callsign": "KF0NRV", "other_1": "dan", "other_2": "ia"},
        {"callsign": "K6GTE", "other_1": "mike", "other_2": "ca"},
    ],
    "HELVETIA": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1",
            "other_2": "3",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "2",
            "other_2": "2",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_1": "3",
            "other_2": "1",
        },
    ],
    "ICWC MST": [
        {"callsign": "KF0NRV", "sent": "1", "other_1": "dan", "other_2": "1"},
        {"callsign": "KF0NRV", "sent": "2", "other_1": "dan", "other_2": "2"},
        {"callsign": "K6GTE", "sent": "3", "other_1": "mike", "other_2": "3"},
    ],
    "IARU FIELDDAY R1 CW": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1",
            "other_2": "1",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "2",
            "other_2": "2",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_1": "3",
            "other_2": "3",
        },
    ],
    "IARU FIELDDAY R1 SSB": [
        {
            "callsign": "KF0NRV",
            "sent": "59",
            "receive": "59",
            "other_1": "1",
            "other_2": "1",
        },
        {
            "callsign": "KF0NRV",
            "sent": "59",
            "receive": "59",
            "other_1": "2",
            "other_2": "2",
        },
        {
            "callsign": "K6GTE",
            "sent": "59",
            "receive": "59",
            "other_1": "3",
            "other_2": "3",
        },
    ],
    "IARU HF": [
        {"callsign": "KF0NRV", "sent": "599", "receive": "599", "other_2": "7"},
        {"callsign": "KF0NRV", "sent": "599", "receive": "599", "other_2": "7"},
        {"callsign": "K6GTE", "sent": "599", "receive": "599", "other_2": "6"},
    ],
    "JIDX CW": [
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "1",
            "other_2": "1",
        },
        {
            "callsign": "KF0NRV",
            "sent": "599",
            "receive": "599",
            "other_1": "2",
            "other_2": "2",
        },
        {
            "callsign": "K6GTE",
            "sent": "599",
            "receive": "599",
            "other_1": "3",
            "other_2": "3",
        },
    ],
    "JIDX PH": [
        {
            "callsign": "KF0NRV",
            "sent": "59",
            "receive": "59",
            "other_1": "1",
            "other_2": "1",
        },
        {
            "callsign": "KF0NRV",
            "sent": "59",
            "receive": "59",
            "other_1": "2",
            "other_2": "2",
        },
        {
            "callsign": "K6GTE",
            "sent": "59",
            "receive": "59",
            "other_1": "3",
            "other_2": "3",
        },
    ],
    "K1USN SST": [
        {"callsign": "KF0NRV", "other_1": "dan", "other_2": "ia"},
        {"callsign": "KF0NRV", "other_1": "dan", "other_2": "ia"},
        {"callsign": "K6GTE", "other_1": "mike", "other_2": "ca"},
    ],
    "NAQP CW": [
        {"callsign": "KF0NRV", "other_1": "dan", "other_2": "ia"},
        {"callsign": "KF0NRV", "other_1": "dan", "other_2": "ia"},
        {"callsign": "K6GTE", "other_1": "mike", "other_2": "ca"},
    ],
    "NAQP SSB": [
        {"callsign": "KF0NRV", "other_1": "dan", "other_2": "ia"},
        {"callsign": "KF0NRV", "other_1": "dan", "other_2": "ia"},
        {"callsign": "K6GTE", "other_1": "mike", "other_2": "ca"},
    ],
    "PHONE WEEKLY TEST": [
        {"callsign": "KF0NRV", "other_1": "dan", "other_2": "ia"},
        {"callsign": "KF0NRV", "other_1": "dan", "other_2": "ia"},
        {"callsign": "K6GTE", "other_1": "mike", "other_2": "ca"},
    ],
    "STEW PERRY TOPBAND": [
        {"callsign": "KF0NRV", "sent": "599", "receive": "599", "other_1": "BB22AA"},
        {"callsign": "KF0NRV", "sent": "599", "receive": "599", "other_1": "BB22AA"},
        {"callsign": "K6GTE", "sent": "599", "receive": "599", "other_1": "AA11bb"},
    ],
    "WEEKLY RTTY": [
        {"callsign": "KF0NRV", "other_1": "dan", "other_2": "ia"},
        {"callsign": "KF0NRV", "other_1": "dan", "other_2": "ia"},
        {"callsign": "K6GTE", "other_1": "mike", "other_2": "ca"},
    ],
    "WINTER FIELD DAY": [
        {"callsign": "KF0NRV", "other_1": "1", "other_2": "a"},
        {"callsign": "KF0NRV", "other_1": "1", "other_2": "a"},
        {"callsign": "K6GTE", "other_1": "1", "other_2": "a"},
    ],
}


@pytest.fixture
def app(qtbot):
    # Qbot setup
    not1mm_app = not1mm.MainWindow(not1mm.splash)
    not1mm_app.show()
    qtbot.addWidget(not1mm_app)

    # Stub out filepicker and create a new database
    if os.path.exists(fsutils.USER_DATA_PATH / "contest_testing.db"):
        os.remove(fsutils.USER_DATA_PATH / "contest_testing.db")
    not1mm_app.filepicker = lambda x: "contest_testing.db"
    not1mm_app.actionNew_Database.trigger()

    # Enter initial setings as default
    settings_dialog = not1mm_app.settings_dialog
    settings_dialog.Call.setText("K5TUX")
    settings_dialog.ITUZone.setText("7")
    settings_dialog.CQZone.setText("4")
    settings_dialog.Country.setText("United States")
    settings_dialog.GridSquare.setText("EM37bb")
    settings_dialog.Latitude.setText("37.0625")
    settings_dialog.Longitude.setText("-93.875")

    qtbot.keyClick(
        settings_dialog,
        QtCore.Qt.Key.Key_Tab,
        modifier=QtCore.Qt.KeyboardModifier.ShiftModifier,
        delay=WAIT_TIME,
    )
    qtbot.keyClick(settings_dialog, QtCore.Qt.Key.Key_Return)

    # Enter initial contest as default
    contest_dialog = not1mm_app.contest_dialog
    qtbot.keyClick(
        contest_dialog,
        QtCore.Qt.Key.Key_Tab,
        modifier=QtCore.Qt.KeyboardModifier.ShiftModifier,
        delay=WAIT_TIME,
    )
    qtbot.keyClick(contest_dialog, QtCore.Qt.Key.Key_Return)
    yield not1mm_app
    # Cleanup
    if os.path.exists(fsutils.USER_DATA_PATH / "contest_testing.db"):
        os.remove(fsutils.USER_DATA_PATH / "contest_testing.db")


def test_contests(app, qtbot):
    # Each contest has an initial log, a duplicate log, and a unique log

    for contest in CONTEST_DATA:
        app.actionNew_Contest.trigger()

        contest_dialog = app.contest_dialog
        contest_dialog.contest.setCurrentText(contest)
        qtbot.keyClick(
            contest_dialog,
            QtCore.Qt.Key.Key_Tab,
            modifier=QtCore.Qt.KeyboardModifier.ShiftModifier,
            delay=WAIT_TIME,
        )
        qtbot.keyClick(contest_dialog, QtCore.Qt.Key.Key_Return)

        # Enter each field and tab keystroke to exercise plugin hooks
        for entry in CONTEST_DATA[contest]:
            if "callsign" in entry:
                app.callsign.setText(entry["callsign"])
                qtbot.keyClick(app, QtCore.Qt.Key.Key_Tab, delay=WAIT_TIME)

            if "sent" in entry:
                app.sent.setText(entry["sent"])
                qtbot.keyClick(app, QtCore.Qt.Key.Key_Tab, delay=WAIT_TIME)

            if "receive" in entry:
                app.receive.setText(entry["receive"])
                qtbot.keyClick(app, QtCore.Qt.Key.Key_Tab, delay=WAIT_TIME)

            if "other_1" in entry:
                app.other_1.setText(entry["other_1"])
                qtbot.keyClick(app, QtCore.Qt.Key.Key_Tab, delay=WAIT_TIME)

            if "other_2" in entry:
                app.other_2.setText(entry["other_2"])

            qtbot.wait(WAIT_TIME)
            qtbot.keyClick(app.callsign, QtCore.Qt.Key.Key_Return)
