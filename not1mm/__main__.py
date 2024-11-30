#!/usr/bin/env python3
"""
not1mm Contest logger
Email: michael.bridak@gmail.com
GPL V3
Purpose: Provides main logging window and a crap ton more.
"""
# pylint: disable=unused-import, c-extension-no-member, no-member, invalid-name, too-many-lines, no-name-in-module
# pylint: disable=logging-fstring-interpolation, logging-not-lazy, line-too-long, bare-except

# alt cluster hamqth.com 7300

import datetime
import importlib
import locale
import logging
from logging.handlers import RotatingFileHandler
import os
import socket
import sys
import uuid

from json import dumps, loads
from json.decoder import JSONDecodeError
from pathlib import Path
from shutil import copyfile

import notctyparser

try:
    import sounddevice as sd
except OSError as exception:
    print(exception)
    print("portaudio is not installed")
    sd = None
from PyQt6 import QtCore, QtGui, QtWidgets, uic
from PyQt6.QtCore import QDir, Qt, QThread, QSettings, QCoreApplication
from PyQt6.QtGui import QFontDatabase, QColorConstants, QPalette, QColor, QPixmap
from PyQt6.QtWidgets import QFileDialog, QSplashScreen, QApplication
from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR

from not1mm.lib.about import About
from not1mm.lib.cwinterface import CW
from not1mm.lib.database import DataBase
from not1mm.lib.edit_macro import EditMacro
from not1mm.lib.edit_opon import OpOn
from not1mm.lib.edit_station import EditStation
from not1mm.lib.ham_utility import (
    bearing,
    bearing_with_latlon,
    calculate_wpx_prefix,
    distance,
    distance_with_latlon,
    get_logged_band,
    getband,
    reciprocol,
    fakefreq,
)

# from not1mm.lib.multicast import Multicast
from not1mm.lib.n1mm import N1MM
from not1mm.lib.new_contest import NewContest
from not1mm.lib.super_check_partial import SCP
from not1mm.lib.select_contest import SelectContest
from not1mm.lib.settings import Settings
from not1mm.lib.version import __version__
from not1mm.lib.versiontest import VersionTest
from not1mm.lib.ft8_watcher import FT8Watcher
from not1mm.lib.fldigi_watcher import FlDigiWatcher
from not1mm.lib.fldigi_sendstring import FlDigi_Comm

import not1mm.fsutils as fsutils
from not1mm.logwindow import LogWindow
from not1mm.checkwindow import CheckWindow
from not1mm.bandmap import BandMapWindow
from not1mm.vfo import VfoWindow
from not1mm.radio import Radio
from not1mm.voice_keying import Voice
from not1mm.lookupservice import LookupService

poll_time = datetime.datetime.now()


class MainWindow(QtWidgets.QMainWindow):
    """
    The main window
    """

    ctyfile = {}
    pref_ref = {
        "sounddevice": "default",
        "useqrz": False,
        "lookupusername": "username",
        "lookuppassword": "password",
        "run_state": True,
        "command_buttons": False,
        "cw_macros": True,
        "bands_modes": True,
        "bands": ["160", "80", "40", "20", "15", "10"],
        "current_database": "ham.db",
        "contest": "",
        "multicast_group": "239.1.1.1",
        "multicast_port": 2239,
        "interface_ip": "0.0.0.0",
        "send_n1mm_packets": False,
        "n1mm_station_name": "20M CW Tent",
        "n1mm_operator": "Bernie",
        "n1mm_radioport": "127.0.0.1:12060",
        "n1mm_contactport": "127.0.0.1:12060",
        "n1mm_lookupport": "127.0.0.1:12060",
        "n1mm_scoreport": "127.0.0.1:12060",
        "usehamdb": False,
        "usehamqth": False,
        "cloudlog": False,
        "cloudlogapi": "",
        "cloudlogurl": "",
        "CAT_ip": "127.0.0.1",
        "userigctld": False,
        "useflrig": False,
        "cwip": "127.0.0.1",
        "cwport": 6789,
        "cwtype": 0,
        "useserver": False,
        "CAT_port": 4532,
        "cluster_server": "dxc.nc7j.com",
        "cluster_port": 7373,
        "cluster_filter": "Set DX Filter SpotterCont=NA",
        "cluster_mode": "OPEN",
        "cluster_expire": 1,
        "logwindow": False,
        "bandmapwindow": False,
        "checkwindow": False,
        "vfowindow": False,
        "darkmode": True,
    }
    appstarted = False
    contact = {}
    contest = None
    contest_settings = {}
    pref = None
    station = {}
    current_op = ""
    current_mode = ""
    current_band = ""
    default_rst = "59"
    cw = None
    look_up = None
    run_state = False
    fkeys = {}
    about_dialog = None
    qrz_dialog = None
    settings_dialog = None
    edit_macro_dialog = None
    contest_dialog = None
    configuration_dialog = None
    opon_dialog = None
    dbname = fsutils.USER_DATA_PATH, "/ham.db"
    radio_state = {}
    rig_control = None
    worked_list = {}
    cw_entry_visible = False
    last_focus = None
    oldtext = ""
    text_color = QColorConstants.Black
    current_palette = None
    use_esm = False
    use_call_history = False
    esm_dict = {}

    radio_thread = QThread()
    voice_thread = QThread()
    fldigi_thread = QThread()

    fldigi_watcher = None
    rig_control = None
    log_window = None
    check_window = None
    bandmap_window = None
    vfo_window = None
    lookup_service = None
    fldigi_util = None

    current_widget = None

    def __init__(self, splash):
        super().__init__()
        logger.info("MainWindow: __init__")
        self.splash = splash
        self.dock_loc = {
            "Top": Qt.DockWidgetArea.TopDockWidgetArea,
            "Right": Qt.DockWidgetArea.RightDockWidgetArea,
            "Left": Qt.DockWidgetArea.LeftDockWidgetArea,
            "Bottom": Qt.DockWidgetArea.BottomDockWidgetArea,
        }

        self.setCorner(Qt.Corner.TopRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self.setCorner(
            Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.setCorner(Qt.Corner.TopLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        uic.loadUi(fsutils.APP_DATA_PATH / "main.ui", self)
        self.history_info.hide()
        QApplication.instance().focusObjectChanged.connect(self.on_focus_changed)
        self.inputs_dict = {
            self.callsign: "callsign",
            self.sent: "sent",
            self.receive: "receive",
            self.other_1: "other_1",
            self.other_2: "other_2",
        }
        self.cw_entry.hide()
        self.leftdot.hide()
        self.rightdot.hide()
        self.n1mm = N1MM()
        self.ft8 = FT8Watcher()
        self.ft8.set_callback(None)
        self.mscp = SCP(fsutils.APP_DATA_PATH)
        self.next_field = self.other_2
        self.dupe_indicator.hide()

        self.cw_speed.valueChanged.connect(self.cwspeed_spinbox_changed)

        self.cw_entry.textChanged.connect(self.handle_text_change)
        self.cw_entry.returnPressed.connect(self.toggle_cw_entry)

        self.actionCW_Macros.triggered.connect(self.cw_macros_state_changed)
        self.actionDark_Mode_2.triggered.connect(self.dark_mode_state_changed)
        self.actionCommand_Buttons_2.triggered.connect(
            self.command_buttons_state_change
        )
        self.actionLog_Window.triggered.connect(self.launch_log_window)
        self.actionBandmap.triggered.connect(self.launch_bandmap_window)
        self.actionCheck_Window.triggered.connect(self.launch_check_window)
        self.actionVFO.triggered.connect(self.launch_vfo)
        self.actionRecalculate_Mults.triggered.connect(self.recalculate_mults)
        self.actionLoad_Call_History_File.triggered.connect(self.load_call_history)

        self.actionGenerate_Cabrillo_ASCII.triggered.connect(
            lambda x: self.generate_cabrillo("ascii")
        )
        self.actionGenerate_Cabrillo_UTF8.triggered.connect(
            lambda x: self.generate_cabrillo("utf-8")
        )
        self.actionGenerate_ADIF.triggered.connect(self.generate_adif)

        self.actionConfiguration_Settings.triggered.connect(
            self.edit_configuration_settings
        )
        self.actionStationSettings.triggered.connect(self.edit_station_settings)

        self.actionNew_Contest.triggered.connect(self.new_contest_dialog)
        self.actionOpen_Contest.triggered.connect(self.open_contest)
        self.actionEdit_Current_Contest.triggered.connect(self.edit_contest)

        self.actionNew_Database.triggered.connect(self.new_database)
        self.actionOpen_Database.triggered.connect(self.open_database)

        self.actionEdit_Macros.triggered.connect(self.edit_macros)

        self.actionAbout.triggered.connect(self.show_about_dialog)
        self.actionHotKeys.triggered.connect(self.show_key_help)
        self.actionHelp.triggered.connect(self.show_help_dialog)
        self.actionUpdate_CTY.triggered.connect(self.check_for_new_cty)
        self.actionUpdate_MASTER_SCP.triggered.connect(self.update_masterscp)
        self.actionQuit.triggered.connect(self.quit_app)

        self.radioButton_run.clicked.connect(self.run_sp_buttons_clicked)
        self.radioButton_sp.clicked.connect(self.run_sp_buttons_clicked)
        self.score.setText("0")
        self.callsign.textEdited.connect(self.callsign_changed)
        self.callsign.returnPressed.connect(self.check_esm_with_enter)
        self.callsign.cursorPositionChanged.connect(self.check_esm)
        self.sent.returnPressed.connect(self.check_esm_with_enter)
        self.sent.cursorPositionChanged.connect(self.check_esm)
        self.receive.returnPressed.connect(self.check_esm_with_enter)
        self.receive.cursorPositionChanged.connect(self.check_esm)
        self.other_1.returnPressed.connect(self.check_esm_with_enter)
        self.other_1.textEdited.connect(self.other_1_changed)
        self.other_1.cursorPositionChanged.connect(self.check_esm)
        self.other_2.returnPressed.connect(self.check_esm_with_enter)
        self.other_2.textEdited.connect(self.other_2_changed)
        self.other_2.cursorPositionChanged.connect(self.check_esm)

        self.sent.setText("59")
        self.receive.setText("59")
        icon_path = fsutils.APP_DATA_PATH
        self.greendot = QtGui.QPixmap(str(icon_path / "greendot.png"))
        self.reddot = QtGui.QPixmap(str(icon_path / "reddot.png"))
        self.leftdot.setPixmap(self.greendot)
        self.rightdot.setPixmap(self.reddot)

        self.radio_grey = QtGui.QPixmap(str(icon_path / "radio_grey.png"))
        self.radio_red = QtGui.QPixmap(str(icon_path / "radio_red.png"))
        self.radio_green = QtGui.QPixmap(str(icon_path / "radio_green.png"))
        self.radio_icon.setPixmap(self.radio_grey)

        self.log_it.clicked.connect(self.save_contact)
        self.wipe.clicked.connect(self.clearinputs)
        self.esc_stop.clicked.connect(self.stop_cw)
        self.mark.clicked.connect(self.mark_spot)
        self.spot_it.clicked.connect(self.spot_dx)

        self.F1.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.F1.customContextMenuRequested.connect(lambda x: self.edit_macro(self.F1))
        self.F1.clicked.connect(lambda x: self.process_function_key(self.F1))
        self.F2.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.F2.customContextMenuRequested.connect(lambda x: self.edit_macro(self.F2))
        self.F2.clicked.connect(lambda x: self.process_function_key(self.F2))
        self.F3.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.F3.customContextMenuRequested.connect(lambda x: self.edit_macro(self.F3))
        self.F3.clicked.connect(lambda x: self.process_function_key(self.F3))
        self.F4.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.F4.customContextMenuRequested.connect(lambda x: self.edit_macro(self.F4))
        self.F4.clicked.connect(lambda x: self.process_function_key(self.F4))
        self.F5.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.F5.customContextMenuRequested.connect(lambda x: self.edit_macro(self.F5))
        self.F5.clicked.connect(lambda x: self.process_function_key(self.F5))
        self.F6.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.F6.customContextMenuRequested.connect(lambda x: self.edit_macro(self.F6))
        self.F6.clicked.connect(lambda x: self.process_function_key(self.F6))
        self.F7.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.F7.customContextMenuRequested.connect(lambda x: self.edit_macro(self.F7))
        self.F7.clicked.connect(lambda x: self.process_function_key(self.F7))
        self.F8.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.F8.customContextMenuRequested.connect(lambda x: self.edit_macro(self.F8))
        self.F8.clicked.connect(lambda x: self.process_function_key(self.F8))
        self.F9.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.F9.customContextMenuRequested.connect(lambda x: self.edit_macro(self.F9))
        self.F9.clicked.connect(lambda x: self.process_function_key(self.F9))
        self.F10.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.F10.customContextMenuRequested.connect(lambda x: self.edit_macro(self.F10))
        self.F10.clicked.connect(lambda x: self.process_function_key(self.F10))
        self.F11.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.F11.customContextMenuRequested.connect(lambda x: self.edit_macro(self.F11))
        self.F11.clicked.connect(lambda x: self.process_function_key(self.F11))
        self.F12.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.F12.customContextMenuRequested.connect(lambda x: self.edit_macro(self.F12))
        self.F12.clicked.connect(lambda x: self.process_function_key(self.F12))

        self.cw_band_160.mousePressEvent = lambda x: self.change_to_band_and_mode(
            160, "CW"
        )
        self.cw_band_80.mousePressEvent = lambda x: self.change_to_band_and_mode(
            80, "CW"
        )
        self.cw_band_60.mousePressEvent = lambda x: self.change_to_band_and_mode(
            60, "CW"
        )
        self.cw_band_40.mousePressEvent = lambda x: self.change_to_band_and_mode(
            40, "CW"
        )
        self.cw_band_30.mousePressEvent = lambda x: self.change_to_band_and_mode(
            30, "CW"
        )
        self.cw_band_20.mousePressEvent = lambda x: self.change_to_band_and_mode(
            20, "CW"
        )
        self.cw_band_17.mousePressEvent = lambda x: self.change_to_band_and_mode(
            17, "CW"
        )
        self.cw_band_15.mousePressEvent = lambda x: self.change_to_band_and_mode(
            15, "CW"
        )
        self.cw_band_12.mousePressEvent = lambda x: self.change_to_band_and_mode(
            12, "CW"
        )
        self.cw_band_10.mousePressEvent = lambda x: self.change_to_band_and_mode(
            10, "CW"
        )
        self.cw_band_6.mousePressEvent = lambda x: self.change_to_band_and_mode(6, "CW")
        self.cw_band_4.mousePressEvent = lambda x: self.change_to_band_and_mode(4, "CW")
        self.cw_band_2.mousePressEvent = lambda x: self.change_to_band_and_mode(2, "CW")
        self.cw_band_125.mousePressEvent = lambda x: self.change_to_band_and_mode(
            222, "CW"
        )
        self.cw_band_70cm.mousePressEvent = lambda x: self.change_to_band_and_mode(
            432, "CW"
        )
        self.cw_band_33cm.mousePressEvent = lambda x: self.change_to_band_and_mode(
            902, "CW"
        )
        self.cw_band_23cm.mousePressEvent = lambda x: self.change_to_band_and_mode(
            1240, "CW"
        )

        self.ssb_band_160.mousePressEvent = lambda x: self.change_to_band_and_mode(
            160, "SSB"
        )
        self.ssb_band_80.mousePressEvent = lambda x: self.change_to_band_and_mode(
            80, "SSB"
        )
        self.ssb_band_60.mousePressEvent = lambda x: self.change_to_band_and_mode(
            60, "SSB"
        )
        self.ssb_band_40.mousePressEvent = lambda x: self.change_to_band_and_mode(
            40, "SSB"
        )
        self.ssb_band_20.mousePressEvent = lambda x: self.change_to_band_and_mode(
            20, "SSB"
        )
        self.ssb_band_17.mousePressEvent = lambda x: self.change_to_band_and_mode(
            17, "SSB"
        )
        self.ssb_band_15.mousePressEvent = lambda x: self.change_to_band_and_mode(
            15, "SSB"
        )
        self.ssb_band_12.mousePressEvent = lambda x: self.change_to_band_and_mode(
            12, "SSB"
        )
        self.ssb_band_10.mousePressEvent = lambda x: self.change_to_band_and_mode(
            10, "SSB"
        )
        self.ssb_band_6.mousePressEvent = lambda x: self.change_to_band_and_mode(
            6, "SSB"
        )
        self.ssb_band_4.mousePressEvent = lambda x: self.change_to_band_and_mode(
            4, "SSB"
        )
        self.ssb_band_2.mousePressEvent = lambda x: self.change_to_band_and_mode(
            2, "SSB"
        )
        self.ssb_band_125.mousePressEvent = lambda x: self.change_to_band_and_mode(
            222, "SSB"
        )
        self.ssb_band_70cm.mousePressEvent = lambda x: self.change_to_band_and_mode(
            432, "SSB"
        )
        self.ssb_band_33cm.mousePressEvent = lambda x: self.change_to_band_and_mode(
            902, "SSB"
        )
        self.ssb_band_23cm.mousePressEvent = lambda x: self.change_to_band_and_mode(
            1240, "SSB"
        )

        self.rtty_band_160.mousePressEvent = lambda x: self.change_to_band_and_mode(
            160, "RTTY"
        )
        self.rtty_band_80.mousePressEvent = lambda x: self.change_to_band_and_mode(
            80, "RTTY"
        )
        self.rtty_band_60.mousePressEvent = lambda x: self.change_to_band_and_mode(
            60, "RTTY"
        )
        self.rtty_band_40.mousePressEvent = lambda x: self.change_to_band_and_mode(
            40, "RTTY"
        )
        self.rtty_band_30.mousePressEvent = lambda x: self.change_to_band_and_mode(
            30, "RTTY"
        )
        self.rtty_band_20.mousePressEvent = lambda x: self.change_to_band_and_mode(
            20, "RTTY"
        )
        self.rtty_band_17.mousePressEvent = lambda x: self.change_to_band_and_mode(
            17, "RTTY"
        )
        self.rtty_band_15.mousePressEvent = lambda x: self.change_to_band_and_mode(
            15, "RTTY"
        )
        self.rtty_band_12.mousePressEvent = lambda x: self.change_to_band_and_mode(
            12, "RTTY"
        )
        self.rtty_band_10.mousePressEvent = lambda x: self.change_to_band_and_mode(
            10, "RTTY"
        )
        self.rtty_band_6.mousePressEvent = lambda x: self.change_to_band_and_mode(
            6, "RTTY"
        )
        self.rtty_band_4.mousePressEvent = lambda x: self.change_to_band_and_mode(
            4, "RTTY"
        )
        self.rtty_band_2.mousePressEvent = lambda x: self.change_to_band_and_mode(
            2, "RTTY"
        )
        self.rtty_band_125.mousePressEvent = lambda x: self.change_to_band_and_mode(
            222, "RTTY"
        )
        self.rtty_band_70cm.mousePressEvent = lambda x: self.change_to_band_and_mode(
            432, "RTTY"
        )
        self.rtty_band_33cm.mousePressEvent = lambda x: self.change_to_band_and_mode(
            902, "RTTY"
        )
        self.rtty_band_23cm.mousePressEvent = lambda x: self.change_to_band_and_mode(
            1240, "RTTY"
        )

        self.band_indicators_cw = {
            "160": self.cw_band_160,
            "80": self.cw_band_80,
            "60": self.cw_band_60,
            "40": self.cw_band_40,
            "30": self.cw_band_30,
            "20": self.cw_band_20,
            "17": self.cw_band_17,
            "15": self.cw_band_15,
            "12": self.cw_band_12,
            "10": self.cw_band_10,
            "6": self.cw_band_6,
            "4": self.cw_band_4,
            "2": self.cw_band_2,
            "1.25": self.cw_band_125,
            "70cm": self.cw_band_70cm,
            "33cm": self.cw_band_33cm,
            "23cm": self.cw_band_23cm,
        }

        self.band_indicators_ssb = {
            "160": self.ssb_band_160,
            "80": self.ssb_band_80,
            "60": self.ssb_band_60,
            "40": self.ssb_band_40,
            "20": self.ssb_band_20,
            "17": self.ssb_band_17,
            "15": self.ssb_band_15,
            "12": self.ssb_band_12,
            "10": self.ssb_band_10,
            "6": self.ssb_band_6,
            "4": self.ssb_band_4,
            "2": self.ssb_band_2,
            "1.25": self.ssb_band_125,
            "70cm": self.ssb_band_70cm,
            "33cm": self.ssb_band_33cm,
            "23cm": self.ssb_band_23cm,
        }

        self.band_indicators_rtty = {
            "160": self.rtty_band_160,
            "80": self.rtty_band_80,
            "60": self.rtty_band_60,
            "40": self.rtty_band_40,
            "30": self.rtty_band_30,
            "20": self.rtty_band_20,
            "17": self.rtty_band_17,
            "15": self.rtty_band_15,
            "12": self.rtty_band_12,
            "10": self.rtty_band_10,
            "6": self.rtty_band_6,
            "4": self.rtty_band_4,
            "2": self.rtty_band_2,
            "1.25": self.rtty_band_125,
            "70cm": self.rtty_band_70cm,
            "33cm": self.rtty_band_33cm,
            "23cm": self.rtty_band_23cm,
        }

        self.all_mode_indicators = {
            "CW": self.band_indicators_cw,
            "SSB": self.band_indicators_ssb,
            "RTTY": self.band_indicators_rtty,
        }

        self.setWindowIcon(
            QtGui.QIcon(str(fsutils.APP_DATA_PATH / "k6gte.not1mm-32.png"))
        )

        self.show_splash_msg("Loading CTY file.")

        try:
            with open(
                fsutils.APP_DATA_PATH / "cty.json", "rt", encoding="utf-8"
            ) as c_file:
                self.ctyfile = loads(c_file.read())
        except (IOError, JSONDecodeError, TypeError):
            logging.CRITICAL("There was an error parsing the BigCity file.")

        self.show_splash_msg("Starting LookUp Service.")

        self.lookup_service = LookupService()
        self.lookup_service.message.connect(self.dockwidget_message)
        self.lookup_service.hide()

        self.show_splash_msg("Reading preferences.")
        self.readpreferences()

        self.show_splash_msg("Starting voice thread.")
        self.voice_process = Voice()
        self.voice_process.moveToThread(self.voice_thread)
        self.voice_thread.started.connect(self.voice_process.run)
        self.voice_thread.finished.connect(self.voice_process.deleteLater)
        self.voice_process.ptt_on.connect(self.ptt_on)
        self.voice_process.ptt_off.connect(self.ptt_off)
        self.voice_process.current_op = self.current_op
        self.voice_process.data_path = fsutils.USER_DATA_PATH
        self.voice_process.sounddevice = self.pref.get("sounddevice", "default")
        self.voice_thread.start()

        self.dbname = fsutils.USER_DATA_PATH / self.pref.get(
            "current_database", "ham.db"
        )
        self.database = DataBase(self.dbname, fsutils.APP_DATA_PATH)
        self.station = self.database.fetch_station()
        if self.station is None:
            self.station = {}
            self.edit_station_settings()
            self.station = self.database.fetch_station()
            if self.station is None:
                self.station = {}
        self.contact = self.database.empty_contact.copy()
        self.current_op = self.station.get("Call", "")
        self.voice_process.current_op = self.current_op
        self.make_op_dir()

        logger.debug(f"{QT_VERSION_STR=} {PYQT_VERSION_STR=}")
        x = PYQT_VERSION_STR.split(".")
        old_Qt = True
        # test if pyqt version is at least 6.7.1
        if len(x) == 1:
            if int(x[0]) > 6:
                old_Qt = False
        elif len(x) >= 2:
            if int(x[0]) >= 6 and int(x[1]) >= 8:
                old_Qt = False

        # Featureset for wayland if pyqt is older that 6.7.1
        dockfeatures = (
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
        )

        self.show_splash_msg("Setting up BandMapWindow.")
        self.bandmap_window = BandMapWindow()
        self.bandmap_window.setObjectName("bandmap-window")
        if os.environ.get("WAYLAND_DISPLAY") and old_Qt is True:
            self.bandmap_window.setFeatures(dockfeatures)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.bandmap_window)
        self.bandmap_window.hide()
        self.bandmap_window.cluster_expire.connect(self.cluster_expire_updated)
        self.bandmap_window.message.connect(self.dockwidget_message)
        self.bandmap_window.callsignField.setText(self.current_op)

        self.show_splash_msg("Setting up CheckWindow.")
        self.check_window = CheckWindow()
        self.check_window.setObjectName("check-window")
        if os.environ.get("WAYLAND_DISPLAY") and old_Qt is True:
            self.check_window.setFeatures(dockfeatures)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.check_window)
        self.check_window.hide()
        self.check_window.message.connect(self.dockwidget_message)

        self.show_splash_msg("Setting up VFOWindow.")
        self.vfo_window = VfoWindow()
        self.vfo_window.setObjectName("vfo-window")
        if os.environ.get("WAYLAND_DISPLAY") and old_Qt is True:
            self.vfo_window.setFeatures(dockfeatures)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.vfo_window)
        self.vfo_window.hide()

        self.show_splash_msg("Setting up LogWindow.")
        self.log_window = LogWindow()
        self.log_window.setObjectName("log-window")
        if os.environ.get("WAYLAND_DISPLAY") and old_Qt is True:
            self.log_window.setFeatures(dockfeatures)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.log_window)
        self.log_window.hide()
        self.log_window.message.connect(self.dockwidget_message)

        self.clearinputs()
        self.show_splash_msg("Loading contest.")
        self.load_contest()
        self.show_splash_msg("Reading macros.")
        self.read_macros()

        self.show_splash_msg("Starting FlDigi watcher.")
        self.fldigi_watcher = FlDigiWatcher()
        self.fldigi_watcher.moveToThread(self.fldigi_thread)
        self.fldigi_thread.started.connect(self.fldigi_watcher.run)
        self.fldigi_thread.finished.connect(self.fldigi_watcher.deleteLater)
        self.fldigi_watcher.poll_callback.connect(self.fldigi_qso)
        self.fldigi_thread.start()

        self.show_splash_msg("Restoring window states.")
        self.settings = QSettings("K6GTE", "not1mm")
        if self.settings.value("windowState") is not None:
            self.restoreState(self.settings.value("windowState"))
        if self.settings.value("geometry") is not None:
            self.restoreGeometry(self.settings.value("geometry"))

        self.actionLog_Window.setChecked(self.pref.get("logwindow", False))
        if self.actionLog_Window.isChecked():
            self.log_window.show()
        else:
            self.log_window.hide()

        self.actionBandmap.setChecked(self.pref.get("bandmapwindow", False))
        if self.actionBandmap.isChecked():
            self.bandmap_window.show()
        else:
            self.bandmap_window.hide()

        self.actionCheck_Window.setChecked(self.pref.get("checkwindow", False))
        if self.actionCheck_Window.isChecked():
            self.check_window.show()
            self.check_window.setActive(True)
        else:
            self.check_window.hide()
            self.check_window.setActive(False)

        self.actionVFO.setChecked(self.pref.get("vfowindow", False))
        if self.actionVFO.isChecked():
            self.vfo_window.show()
        else:
            self.vfo_window.hide()

        self.cwspeed_spinbox_changed()

        if not DEBUG_ENABLED:
            if VersionTest(__version__).test():
                self.show_message_box(
                    "There is a newer version of not1mm available.\n"
                    "You can udate to the current version by using:\npip install -U not1mm"
                )

    def load_call_history(self) -> None:
        """"""
        filename = self.filepicker("other")
        if filename:
            self.database.create_callhistory_table()
            self.database.delete_callhistory()

            try:
                with open(filename, "rt", encoding="utf-8") as file_descriptor:
                    lines = file_descriptor.readlines()
                    if "!!Order!!" in lines[0]:
                        item_names = lines[0].strip().split(",")
                        # ['!!Order!!', 'Call', 'Sect', 'State', 'CK', 'UserText', '']
                        item_names = item_names[1:-1]
                        # ['Call', 'Sect', 'State', 'CK', 'UserText']
                        lines = lines[1:]
                        group_list = []
                        for line in lines:
                            if line.startswith("#"):
                                continue
                            group = {}
                            fields = line.strip().split(",")
                            # ['4U1WB','MDC','DC','89','']
                            number_of_fields = len(fields)
                            count = 0
                            try:
                                for item in item_names:
                                    if item == "":
                                        continue
                                    if count < number_of_fields:
                                        group[item] = fields[count]
                                    else:
                                        group[item] = ""
                                    count += 1
                                group_list.append(group)
                                # database.add_callhistory_item(group)
                                # print(f"{group=}")
                            except IndexError:
                                ...
                        self.database.add_callhistory_items(group_list)
            except FileNotFoundError as err:
                self.show_message_box(f"{err}")

    def on_focus_changed(self, new):
        """"""
        if self.use_esm:
            if hasattr(self.contest, "process_esm"):
                self.contest.process_esm(self, new_focused_widget=new)

    def make_button_green(self, the_button: QtWidgets.QPushButton) -> None:
        """Turn the_button green."""
        if the_button is not None:
            pal = QPalette()
            pal.isCopyOf(self.current_palette)
            greenColor = QColor(0, 128, 0)
            pal.setBrush(QPalette.ColorRole.Button, greenColor)
            the_button.setPalette(pal)

    def restore_button_color(self, the_button: QtWidgets.QPushButton) -> None:
        """Restores the color of the button"""
        the_button.setPalette(self.current_palette)

    def check_esm_with_enter(self):
        """Check for ESM, otherwise save contact."""
        if self.use_esm:
            if hasattr(self.contest, "process_esm"):
                self.contest.process_esm(self, with_enter=True)
            else:
                self.save_contact()
        else:
            self.save_contact()

    def check_esm(self):
        """Check for ESM, otherwise save contact."""
        if self.use_esm:
            if hasattr(self.contest, "process_esm"):
                self.contest.process_esm(self)
            else:
                ...
                # self.save_contact()
        else:
            ...
            # self.save_contact()

    def show_splash_msg(self, msg: str) -> None:
        """Show text message in the splash window."""
        self.splash.showMessage(
            msg,
            alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            color=QColor(255, 255, 0),
        )
        QCoreApplication.processEvents()

    def dockwidget_message(self, msg):
        """signal from bandmap"""
        if msg:
            if msg.get("cmd", "") == "GETCOLUMNS":
                if hasattr(self.contest, "columns"):
                    cmd = {}
                    cmd["cmd"] = "SHOWCOLUMNS"
                    cmd["COLUMNS"] = self.contest.columns
                    if self.log_window:
                        self.log_window.msg_from_main(cmd)
                return
            if msg.get("cmd", "") == "TUNE":
                # b'{"cmd": "TUNE", "freq": 7.0235, "spot": "MM0DGI"}'
                self.clearinputs()
                if self.vfo_window:
                    self.vfo_window.msg_from_main(msg)
                vfo = msg.get("freq")
                vfo = float(vfo) * 1000000
                self.radio_state["vfoa"] = int(vfo)
                if self.rig_control:
                    self.rig_control.set_vfo(int(vfo))
                spot = msg.get("spot", "")
                self.callsign.setText(spot)
                self.callsign_changed()
                self.callsign.setFocus()
                self.callsign.activateWindow()
                return

            if msg.get("cmd", "") == "GETWORKEDLIST":
                result = self.database.get_calls_and_bands()
                cmd = {}
                cmd["cmd"] = "WORKED"
                cmd["worked"] = result
                if self.bandmap_window:
                    self.bandmap_window.msg_from_main(cmd)
                return

            if msg.get("cmd", "") == "GETCONTESTSTATUS":
                cmd = {
                    "cmd": "CONTESTSTATUS",
                    "contest": self.contest_settings,
                    "operator": self.current_op,
                }
                if self.bandmap_window:
                    self.bandmap_window.msg_from_main(cmd)
                    self.bandmap_window.callsignField.setText(self.current_op)
                return

            if msg.get("cmd", "") == "CHANGECALL":
                self.callsign.setText(msg.get("call", ""))
                self.callsign.setFocus()

            if msg.get("cmd", "") == "CHECKSPOTS":
                if self.check_window:
                    self.check_window.msg_from_main(msg)

            # '{"cmd": "LOOKUP_RESPONSE", "station": "fredo", "result": {"call": "K6GTE", "aliases": "KM6HQI", "dxcc": "291", "nickname": "Mike", "fname": "Michael C", "name": "Bridak", "addr1": "2854 W Bridgeport Ave", "addr2": "Anaheim", "state": "CA", "zip": "92804", "country": "United States", "lat": "33.825460", "lon": "-117.987510", "grid": "DM13at", "county": "Orange", "ccode": "271", "fips": "06059", "land": "United States", "efdate": "2021-01-13", "expdate": "2027-11-07", "class": "G", "codes": "HVIE", "email": "michael.bridak@gmail.com", "u_views": "3049", "bio": "7232", "biodate": "2023-04-10 17:56:55", "image": "https://cdn-xml.qrz.com/e/k6gte/qsl.png", "imageinfo": "285:545:99376", "moddate": "2021-04-08 21:41:07", "MSA": "5945", "AreaCode": "714", "TimeZone": "Pacific", "GMTOffset": "-8", "DST": "Y", "eqsl": "0", "mqsl": "1", "cqzone": "3", "ituzone": "6", "born": "1967", "lotw": "1", "user": "K6GTE", "geoloc": "geocode", "name_fmt": "Michael C \\"Mike\\" Bridak"}}'

            if msg.get("cmd", "") == "LOOKUP_RESPONSE":
                if msg.get("result", None) is not None:
                    fname = msg.get("result", {}).get("fname", "")
                    name = msg.get("result", {}).get("name", "")
                    grid = msg.get("result", {}).get("grid", "")
                    nickname = msg.get("result", {}).get("nickname", "")

                    if self.contest:
                        if "General Logging" in self.contest.name:
                            if nickname:
                                self.other_1.setText(nickname)
                            elif fname:
                                self.other_1.setText(fname)
                            elif name:
                                self.other_1.setText(name)

                    if grid:
                        self.contact["GridSquare"] = grid
                    # _theircountry = response.get("country", "")
                    if self.station.get("GridSquare", ""):
                        heading = bearing(self.station.get("GridSquare", ""), grid)
                        kilometers = distance(self.station.get("GridSquare", ""), grid)
                        self.heading_distance.setText(
                            f"{grid} Hdg {heading}° LP {reciprocol(heading)}° / "
                            f"distance {int(kilometers*0.621371)}mi {kilometers}km"
                        )

    def cluster_expire_updated(self, number):
        """signal from bandmap"""
        self.pref["cluster_expire"] = int(number)
        self.write_preference()

    def fldigi_qso(self, result: str):
        """
        gets called when there is a new fldigi qso logged.

        {
            'FREQ': '7.029500',
            'CALL': 'DL2DSL',
            'MODE': 'RTTY',
            'NAME': 'BOB',
            'QSO_DATE': '20240904',
            'QSO_DATE_OFF': '20240904',
            'TIME_OFF': '212825',
            'TIME_ON': '212800',
            'RST_RCVD': '599',
            'RST_SENT': '599',
            'BAND': '40M',
            'COUNTRY': 'FED. REP. OF GERMANY',
            'CQZ': '14',
            'STX': '000',
            'STX_STRING': '1D ORG',
            'CLASS': '1D',
            'ARRL_SECT': 'DX',
            'TX_PWR': '0',
            'OPERATOR': 'K6GTE',
            'STATION_CALLSIGN': 'K6GTE',
            'MY_GRIDSQUARE': 'DM13AT',
            'MY_CITY': 'ANAHEIM, CA',
            'MY_STATE': 'CA'
        }

        """

        if result and result != "NONE":
            datadict = {}
            splitdata = result.upper().strip().split("<")
            for data in splitdata:
                if data:
                    tag = data.split(":")
                    if tag == ["EOR>"]:
                        break
                    datadict[tag[0]] = tag[1].split(">")[1].strip()
            logger.debug(f"{datadict=}")
            if hasattr(self.contest, "ft8_handler"):
                self.contest.set_self(self)
                self.contest.ft8_handler(datadict)

    def setDarkMode(self, setdarkmode=False) -> None:
        """Forces a darkmode palette."""

        logger.debug(f"Dark mode set to: {setdarkmode}")

        cmd = {}
        cmd["cmd"] = "DARKMODE"
        cmd["state"] = setdarkmode
        if self.log_window:
            self.log_window.msg_from_main(cmd)
        if self.bandmap_window:
            self.bandmap_window.msg_from_main(cmd)
        if self.check_window:
            self.check_window.msg_from_main(cmd)
        if self.vfo_window:
            self.vfo_window.msg_from_main(cmd)

        if setdarkmode:
            darkPalette = QPalette()
            darkColor = QColor(56, 56, 56)
            disabledColor = QColor(127, 127, 127)
            darkPalette.setColor(QPalette.ColorRole.Window, darkColor)
            darkPalette.setColor(QPalette.ColorRole.WindowText, QColorConstants.White)
            darkPalette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
            darkPalette.setColor(QPalette.ColorRole.AlternateBase, darkColor)
            darkPalette.setColor(QPalette.ColorRole.Text, QColorConstants.White)
            darkPalette.setColor(QPalette.ColorRole.Button, darkColor)
            darkPalette.setColor(QPalette.ColorRole.ButtonText, QColorConstants.White)
            darkPalette.setColor(QPalette.ColorRole.BrightText, QColorConstants.Red)
            darkPalette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
            darkPalette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
            darkPalette.setColor(
                QPalette.ColorRole.HighlightedText, QColorConstants.Black
            )
            darkPalette.setColor(
                QPalette.ColorGroup.Disabled,
                QPalette.ColorRole.ButtonText,
                disabledColor,
            )
            darkPalette.setColor(
                QPalette.ColorGroup.Disabled,
                QPalette.ColorRole.HighlightedText,
                disabledColor,
            )
            darkPalette.setColor(
                QPalette.ColorGroup.Disabled,
                QPalette.ColorRole.Text,
                disabledColor,
            )

            self.current_palette = darkPalette
            self.setPalette(darkPalette)
            self.text_color = QColorConstants.White
            self.menuFile.setPalette(darkPalette)
            self.menuHelp.setPalette(darkPalette)
            self.menuOther.setPalette(darkPalette)
            self.menuView.setPalette(darkPalette)
            self.menuWindow.setPalette(darkPalette)
            self.callsign.setPalette(darkPalette)
            self.sent.setPalette(darkPalette)
            self.receive.setPalette(darkPalette)
            self.other_1.setPalette(darkPalette)
            self.other_2.setPalette(darkPalette)
            self.cw_entry.setPalette(darkPalette)
        else:
            palette = self.style().standardPalette()
            self.current_palette = palette
            self.setPalette(palette)
            self.menuFile.setPalette(palette)
            self.menuHelp.setPalette(palette)
            self.menuOther.setPalette(palette)
            self.menuView.setPalette(palette)
            self.menuWindow.setPalette(palette)
            self.callsign.setPalette(palette)
            self.sent.setPalette(palette)
            self.receive.setPalette(palette)
            self.other_1.setPalette(palette)
            self.other_2.setPalette(palette)
            self.cw_entry.setPalette(palette)
            self.text_color = QColorConstants.Black

    def set_radio_icon(self, state: int) -> None:
        """
        Change CAT icon state

        Parameters
        ----------
        state : int
        The state of the CAT icon. 0 = grey, 1 = red, 2 = green

        Returns
        -------
        None
        """

        displaystate = [self.radio_grey, self.radio_red, self.radio_green]
        try:
            self.radio_icon.setPixmap(displaystate[state])
        except (IndexError, TypeError) as err:
            logger.debug(err)

    def toggle_cw_entry(self) -> None:
        """
        Toggle the CW entry field on and off.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.cw_entry_visible = not self.cw_entry_visible
        if self.cw_entry_visible:
            self.last_focus = app.focusWidget()
            self.cw_entry.clear()
            self.cw_entry.show()
            self.cw_entry.setFocus()
            return
        self.cw_entry.hide()
        self.cw_entry.clearFocus()
        if self.last_focus:
            self.last_focus.setFocus()

    def handle_text_change(self) -> None:
        """
        ....

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        newtext = self.cw_entry.text()
        if len(newtext) < len(self.oldtext):
            # self.send_backspace()
            self.oldtext = newtext
            return
        if self.pref.get("cwtype") == 3 and self.rig_control is not None:
            self.rig_control.sendcw(newtext[len(self.oldtext) :])
        elif self.cw is not None:
            self.cw.sendcw(newtext[len(self.oldtext) :])
        self.oldtext = newtext

    def change_to_band_and_mode(self, band: int, mode: str) -> None:
        """
        Gets a sane frequency for the chosen band and mode.
        Then changes to that,

        Parameters
        ----------
        band : int
        mode : str

        Returns
        -------
        Nothing
        """

        if mode in ["CW", "SSB", "RTTY"]:
            freq = fakefreq(str(band), mode)
            self.change_freq(freq)
            vfo = float(freq)
            vfo = int(vfo * 1000)
            if mode == "CW":
                mode = self.rig_control.last_cw_mode
            if mode == "RTTY":
                mode = self.rig_control.last_data_mode
            self.change_mode(mode, intended_freq=vfo)

    def quit_app(self) -> None:
        """
        Send multicast quit message, then quit the program.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        cmd = {}
        cmd["cmd"] = "HALT"
        if self.lookup_service:
            self.lookup_service.msg_from_main(cmd)
        app.quit()

    def show_message_box(self, message: str) -> None:
        """
        Displays a dialog box with a message.

        Paramters
        ---------
        message : str

        Returns
        -------
        None
        """

        message_box = QtWidgets.QMessageBox()
        if self.current_palette:
            message_box.setPalette(self.current_palette)
        message_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        message_box.setText(message)
        message_box.setWindowTitle("Information")
        message_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        _ = message_box.exec()

    def show_about_dialog(self) -> None:
        """
        Show the About dialog when the menu item is clicked.

        Parameters
        ----------
        Takes no parameters.

        Returns
        -------
        None
        """

        self.about_dialog = About(fsutils.APP_DATA_PATH)
        if self.current_palette:
            self.about_dialog.setPalette(self.current_palette)

        self.about_dialog.donors.setSource(
            QtCore.QUrl.fromLocalFile(f"{fsutils.APP_DATA_PATH / 'donors.html'}")
        )
        self.about_dialog.open()

    def show_help_dialog(self):
        """
        Show the Help dialog when the menu item is clicked.

        Parameters
        ----------
        Takes no parameters.

        Returns
        -------
        None
        """

        self.about_dialog = About(fsutils.APP_DATA_PATH)
        if self.current_palette:
            self.about_dialog.setPalette(self.current_palette)

        self.about_dialog.setWindowTitle("Help")
        self.about_dialog.setGeometry(0, 0, 800, 600)
        self.about_dialog.donors.setSource(
            QtCore.QUrl.fromLocalFile(str(fsutils.APP_DATA_PATH / "not1mm.html"))
        )
        self.about_dialog.open()

    def update_masterscp(self) -> None:
        """
        Tries to update the MASTER.SCP file when the menu item is clicked.

        Displays a dialog advising if it was updated.

        Parameters
        ----------
        Takes no parameters.

        Returns
        -------
        None
        """

        if self.mscp.update_masterscp():
            self.show_message_box("MASTER.SCP file updated.")
            return
        self.show_message_box("MASTER.SCP could not be updated.")

    def edit_configuration_settings(self) -> None:
        """
        Configuration Settings was clicked

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.configuration_dialog = Settings(fsutils.APP_DATA_PATH, self.pref)
        if self.current_palette:
            self.configuration_dialog.setPalette(self.current_palette)
        self.configuration_dialog.usehamdb_radioButton.hide()
        self.configuration_dialog.show()
        self.configuration_dialog.accepted.connect(self.edit_configuration_return)

    def edit_configuration_return(self) -> None:
        """
        Returns here when configuration dialog closed with okay.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.configuration_dialog.save_changes()
        self.write_preference()
        # logger.debug("%s", f"{self.pref}")
        self.readpreferences()

    def new_database(self) -> None:
        """
        Create new database file.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        filename = self.filepicker("new")
        if filename:
            if filename[-3:] != ".db":
                filename += ".db"
            self.pref["current_database"] = os.path.basename(filename)
            self.write_preference()
            self.dbname = fsutils.USER_DATA_PATH / self.pref.get(
                "current_database", "ham.db"
            )
            self.database = DataBase(self.dbname, fsutils.APP_DATA_PATH)
            self.contact = self.database.empty_contact.copy()
            self.station = self.database.fetch_station()
            if self.station is None:
                self.station = {}
            self.current_op = self.station.get("Call", "")
            self.voice_process.current_op = self.current_op
            self.make_op_dir()
            cmd = {}
            cmd["cmd"] = "NEWDB"
            if self.log_window:
                self.log_window.msg_from_main(cmd)
            self.clearinputs()
            self.edit_station_settings()

    def open_database(self) -> None:
        """
        Open existing database file.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        filename = self.filepicker("open")
        if filename:
            self.pref["current_database"] = os.path.basename(filename)
            self.write_preference()
            self.dbname = fsutils.USER_DATA_PATH / self.pref.get(
                "current_database", "ham.db"
            )
            self.database = DataBase(self.dbname, fsutils.MODULE_PATH)
            self.contact = self.database.empty_contact.copy()
            self.station = self.database.fetch_station()
            if self.station is None:
                self.station = {}
            if self.station.get("Call", "") == "":
                self.edit_station_settings()
            self.current_op = self.station.get("Call", "")
            self.voice_process.current_op = self.current_op
            self.make_op_dir()
            cmd = {}
            cmd["cmd"] = "NEWDB"
            if self.log_window:
                self.log_window.msg_from_main(cmd)
            self.clearinputs()
            self.open_contest()

    def new_contest(self) -> None:
        """Create new contest in existing database."""

    def open_contest(self) -> None:
        """
        Switch to a different existing contest in existing database.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        logger.debug("Open Contest selected")
        contests = self.database.fetch_all_contests()
        logger.debug("%s", f"{contests}")

        if contests:
            self.contest_dialog = SelectContest(fsutils.APP_DATA_PATH)
            if self.current_palette:
                self.contest_dialog.setPalette(self.current_palette)

            self.contest_dialog.contest_list.setRowCount(0)
            self.contest_dialog.contest_list.setColumnCount(4)
            self.contest_dialog.contest_list.verticalHeader().setVisible(False)
            self.contest_dialog.contest_list.setColumnWidth(1, 200)
            self.contest_dialog.contest_list.setColumnWidth(2, 200)
            self.contest_dialog.contest_list.setHorizontalHeaderItem(
                0, QtWidgets.QTableWidgetItem("Contest Nr")
            )
            self.contest_dialog.contest_list.setHorizontalHeaderItem(
                1, QtWidgets.QTableWidgetItem("Contest Name")
            )
            self.contest_dialog.contest_list.setHorizontalHeaderItem(
                2, QtWidgets.QTableWidgetItem("Contest Start")
            )
            self.contest_dialog.contest_list.setHorizontalHeaderItem(
                3, QtWidgets.QTableWidgetItem("Not UIsed")
            )
            self.contest_dialog.contest_list.setColumnHidden(0, True)
            self.contest_dialog.contest_list.setColumnHidden(3, True)
            self.contest_dialog.accepted.connect(self.open_contest_return)
            for contest in contests:
                number_of_rows = self.contest_dialog.contest_list.rowCount()
                self.contest_dialog.contest_list.insertRow(number_of_rows)
                contest_id = str(contest.get("ContestID", 1))
                contest_name = contest.get("ContestName", 1)
                start_date = contest.get("StartDate", 1)
                self.contest_dialog.contest_list.setItem(
                    number_of_rows, 0, QtWidgets.QTableWidgetItem(contest_id)
                )
                self.contest_dialog.contest_list.setItem(
                    number_of_rows, 1, QtWidgets.QTableWidgetItem(contest_name)
                )
                self.contest_dialog.contest_list.setItem(
                    number_of_rows, 2, QtWidgets.QTableWidgetItem(start_date)
                )
        self.contest_dialog.show()

    def open_contest_return(self) -> None:
        """
        Called by open_contest when contest selected.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        selected_row = self.contest_dialog.contest_list.currentRow()
        contest = self.contest_dialog.contest_list.item(selected_row, 0).text()
        self.pref["contest"] = contest
        self.write_preference()
        logger.debug("Selected contest: %s", f"{contest}")
        self.load_contest()
        self.worked_list = self.database.get_calls_and_bands()
        self.send_worked_list()

    def refill_dropdown(self, target, source) -> None:
        """
        Refill QCombobox widget with value.

        Parameters
        ----------
        target : QComboBox
        The target widget to be refilled
        source : str
        The value to be used to fill the target widget

        Returns
        -------
        None
        """

        index = target.findText(source)
        target.setCurrentIndex(index)

    def edit_contest(self) -> None:
        """
        Edit the current contest settings.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        logger.debug("Edit contest Dialog")
        if self.contest is None:
            self.show_message_box("You have no contest defined.")
            return
        if self.contest_settings is None:
            return

        self.contest_dialog = NewContest(fsutils.APP_DATA_PATH)
        if self.current_palette:
            self.contest_dialog.setPalette(self.current_palette)
            self.contest_dialog.exchange.setPalette(self.current_palette)
            self.contest_dialog.operators.setPalette(self.current_palette)
            self.contest_dialog.contest.setPalette(self.current_palette)

        self.contest_dialog.setWindowTitle("Edit Contest")
        self.contest_dialog.title.setText("")
        self.contest_dialog.accepted.connect(self.save_edited_contest)
        value = self.contest_settings.get("ContestName").upper().replace("_", " ")
        if value == "GENERAL LOGGING":
            value = "General Logging"
        self.refill_dropdown(self.contest_dialog.contest, value)
        value = self.contest_settings.get("OperatorCategory")
        self.refill_dropdown(self.contest_dialog.operator_class, value)
        value = self.contest_settings.get("BandCategory")
        self.refill_dropdown(self.contest_dialog.band, value)
        value = self.contest_settings.get("PowerCategory")
        self.refill_dropdown(self.contest_dialog.power, value)
        value = self.contest_settings.get("ModeCategory")
        self.refill_dropdown(self.contest_dialog.mode, value)
        value = self.contest_settings.get("OverlayCategory")
        self.refill_dropdown(self.contest_dialog.overlay, value)
        self.contest_dialog.operators.setText(self.contest_settings.get("Operators"))
        self.contest_dialog.soapbox.setPlainText(self.contest_settings.get("Soapbox"))
        self.contest_dialog.exchange.setText(self.contest_settings.get("SentExchange"))
        value = self.contest_settings.get("StationCategory")
        self.refill_dropdown(self.contest_dialog.station, value)
        value = self.contest_settings.get("AssistedCategory")
        self.refill_dropdown(self.contest_dialog.assisted, value)
        value = self.contest_settings.get("TransmitterCategory")
        self.refill_dropdown(self.contest_dialog.transmitter, value)
        value = self.contest_settings.get("StartDate")
        the_date, the_time = value.split()
        self.contest_dialog.dateTimeEdit.setDate(
            QtCore.QDate.fromString(the_date, "yyyy-MM-dd")
        )
        self.contest_dialog.dateTimeEdit.setCalendarPopup(True)
        self.contest_dialog.dateTimeEdit.setTime(
            QtCore.QTime.fromString(the_time, "hh:mm:ss")
        )
        self.contest_dialog.open()

    def save_edited_contest(self) -> None:
        """
        Save the edited contest.
        Called by edit_contest().

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        contest = {}
        contest["ContestName"] = (
            self.contest_dialog.contest.currentText().lower().replace(" ", "_")
        )
        contest["StartDate"] = self.contest_dialog.dateTimeEdit.dateTime().toString(
            "yyyy-MM-dd hh:mm:ss"
        )
        contest["OperatorCategory"] = self.contest_dialog.operator_class.currentText()
        contest["BandCategory"] = self.contest_dialog.band.currentText()
        contest["PowerCategory"] = self.contest_dialog.power.currentText()
        contest["ModeCategory"] = self.contest_dialog.mode.currentText()
        contest["OverlayCategory"] = self.contest_dialog.overlay.currentText()
        contest["Operators"] = self.contest_dialog.operators.text()
        contest["Soapbox"] = self.contest_dialog.soapbox.toPlainText()
        contest["SentExchange"] = self.contest_dialog.exchange.text()
        contest["ContestNR"] = self.pref.get("contest", 1)
        contest["StationCategory"] = self.contest_dialog.station.currentText()
        contest["AssistedCategory"] = self.contest_dialog.assisted.currentText()
        contest["TransmitterCategory"] = self.contest_dialog.transmitter.currentText()

        logger.debug("%s", f"{contest}")
        self.database.update_contest(contest)
        self.write_preference()
        self.load_contest()

    def load_contest(self) -> None:
        """
        Loads the contest stored in the preference file.
        If no contest is defined, a new contest is created.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if self.pref.get("contest"):
            self.contest_settings = self.database.fetch_contest_by_id(
                self.pref.get("contest")
            )
            if self.contest_settings:
                try:
                    self.database.current_contest = self.pref.get("contest")
                    if self.contest_settings.get("ContestName"):
                        self.contest = doimp(self.contest_settings.get("ContestName"))
                        logger.debug("Loaded Contest Name = %s", self.contest.name)
                        self.set_window_title()
                        self.contest.init_contest(self)
                        self.hide_band_mode(
                            self.contest_settings.get("ModeCategory", "")
                        )
                        logger.debug("%s", f"{self.contest_settings}")
                        if self.contest_settings.get("ModeCategory", "") == "CW":
                            self.setmode("CW")
                            self.radio_state["mode"] = "CW"
                            if self.rig_control:
                                if self.rig_control.online:
                                    self.rig_control.set_mode("CW")
                            band = getband(str(self.radio_state.get("vfoa", "0.0")))
                            self.set_band_indicator(band)
                            self.set_window_title()
                        if self.contest_settings.get("ModeCategory", "") == "RTTY":
                            self.setmode("RTTY")
                            self.radio_state["mode"] = "RTTY"
                            if self.rig_control:
                                if self.rig_control.online:
                                    self.rig_control.set_mode("RTTY")
                            band = getband(str(self.radio_state.get("vfoa", "0.0")))
                            self.set_band_indicator(band)
                            self.set_window_title()
                        if self.contest_settings.get("ModeCategory", "") == "SSB":
                            self.setmode("SSB")
                            if int(self.radio_state.get("vfoa", 0)) > 10000000:
                                self.radio_state["mode"] = "USB"
                            else:
                                self.radio_state["mode"] = "LSB"
                            band = getband(str(self.radio_state.get("vfoa", "0.0")))
                            self.set_band_indicator(band)
                            self.set_window_title()
                            if self.rig_control:
                                self.rig_control.set_mode(self.radio_state.get("mode"))
                except ModuleNotFoundError:
                    self.pref["contest"] = 1
                    self.show_message_box("Contest plugin not found")

                if hasattr(self.contest, "mode"):
                    logger.debug("%s", f"  ****  {self.contest}")
                    if self.contest.mode in ["CW", "BOTH"]:
                        self.cw_speed.show()
                    else:
                        self.cw_speed.hide()

                if hasattr(self.contest, "ft8_handler"):
                    self.contest.set_self(self)
                    self.ft8.set_callback(self.contest.ft8_handler)
                else:
                    self.ft8.set_callback(None)

                self.clearinputs()
                cmd = {}
                cmd["cmd"] = "NEWDB"
                if self.log_window:
                    self.log_window.msg_from_main(cmd)
                if hasattr(self.contest, "columns"):
                    cmd = {}
                    cmd["cmd"] = "SHOWCOLUMNS"
                    cmd["COLUMNS"] = self.contest.columns
                    if self.log_window:
                        self.log_window.msg_from_main(cmd)
            self.read_macros()

    def check_for_new_cty(self) -> None:
        """
        Checks for a new cty.dat file.
        The following steps are performed:
        - Check if the file exists
        - Check if the file is newer than the one in the data folder
        - If the file is newer, load it and show a message box

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        try:
            cty = notctyparser.BigCty(fsutils.APP_DATA_PATH / "cty.json")
            update_available = cty.check_update()
        except (AttributeError, ValueError, locale.Error) as the_error:
            logger.debug("cty parser returned an error: %s", the_error)
            return
        logger.debug("Newer cty file available %s", str(update_available))

        if update_available:
            try:
                updated = cty.update()
            except ResourceWarning as the_error:
                logger.debug("cty parser returned an error: %s", the_error)
                return
            if updated:
                cty.dump(fsutils.APP_DATA_PATH / "cty.json")
                self.show_message_box("cty file updated.")
                try:
                    with open(
                        fsutils.APP_DATA_PATH / "cty.json", "rt", encoding="utf-8"
                    ) as ctyfile:
                        self.ctyfile = loads(ctyfile.read())
                except (IOError, JSONDecodeError, TypeError) as err:
                    logging.CRITICAL(
                        f"There was an error {err} parsing the BigCity file."
                    )
            else:
                self.show_message_box("An Error occured updating file.")
        else:
            self.show_message_box("CTY file is up to date.")

    def hide_band_mode(self, the_mode: str) -> None:
        """
        Hide the unused band and mode frames.
        Show the used band and mode frames.

        Parameters
        ----------
        the_mode : str
        The mode to show.

        Returns
        -------
        None
        """

        logger.debug("%s", f"{the_mode}")
        self.Band_Mode_Frame_CW.hide()
        self.Band_Mode_Frame_SSB.hide()
        self.Band_Mode_Frame_RTTY.hide()
        modes = {
            "CW": (self.Band_Mode_Frame_CW,),
            "SSB": (self.Band_Mode_Frame_SSB,),
            "RTTY": (self.Band_Mode_Frame_RTTY,),
            "PSK": (self.Band_Mode_Frame_RTTY,),
            "SSB+CW": (self.Band_Mode_Frame_CW, self.Band_Mode_Frame_SSB),
            "BOTH": (self.Band_Mode_Frame_CW, self.Band_Mode_Frame_SSB),
            "DIGITAL": (self.Band_Mode_Frame_RTTY,),
            "SSB+CW+DIGITAL": (
                self.Band_Mode_Frame_RTTY,
                self.Band_Mode_Frame_CW,
                self.Band_Mode_Frame_SSB,
            ),
            "FM": (self.Band_Mode_Frame_SSB,),
        }
        frames = modes.get(the_mode)
        if frames:
            for frame in frames:
                frame.show()

    def show_key_help(self) -> None:
        """
        Show help box for hotkeys.
        Provides a list of hotkeys and what they do.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.show_message_box(
            "[CTRL-Esc]\tStops cwdaemon from sending Morse.\n"
            "[PgUp]\tIncreases the cw sending speed.\n"
            "[PgDown]\tDecreases the cw sending speed.\n"
            "[Arrow-Up] Jump to the next spot above the current VFO cursor\n"
            "\tin the bandmap window (CAT Required).\n"
            "[Arrow-Down] Jump to the next spot below the current\n"
            "\tVFO cursor in the bandmap window (CAT Required).\n"
            "[TAB]\tMove cursor to the right one field.\n"
            "[Shift-Tab]\tMove cursor left One field.\n"
            "[SPACE]\tWhen in the callsign field, will move the input to the\n"
            "\tfirst field needed for the exchange.\n"
            "[Enter]\tSubmits the fields to the log. Unless ESM is enabled.\n"
            "[F1-F12]\tSend (CW or Voice) macros.\n"
            "[CTRL-G]\tTune to a spot matching partial text in the callsign\n"
            "\tentry field (CAT Required).\n"
            "[CTRL-M]\tMark Callsign to the bandmap window to work later."
            "[CTRL-S]\tSpot Callsign to the cluster.\n"
            "[CTRL-SHIFT-K] Open CW text input field.\n"
            "[CTRL-=]\tLog the contact without sending the ESM macros.\n"
            "[CTRL-W]\tClears the input fields of any text.\n"
        )

    def filepicker(self, action: str) -> str:
        """
        Get a filename

        Parameters:
        ----------
        action: 'new' or 'open'

        Returns:
        -------
        str: filename
        """

        options = (
            QFileDialog.Option.DontUseNativeDialog
            | QFileDialog.Option.DontConfirmOverwrite
        )
        if action == "new":
            file, _ = QFileDialog.getSaveFileName(
                self,
                "Choose a Database",
                str(fsutils.USER_DATA_PATH),
                "Database (*.db)",
                options=options,
            )
        if action == "open":
            file, _ = QFileDialog.getOpenFileName(
                self,
                "Choose a Database",
                str(fsutils.USER_DATA_PATH),
                "Database (*.db)",
                options=options,
            )
        if action == "other":
            file, _ = QFileDialog.getOpenFileName(
                self,
                "Choose a File",
                "~/",
                "Any (*.*)",
                options=options,
            )
        return file

    def recalculate_mults(self) -> None:
        """Recalculate Multipliers"""
        self.contest.recalculate_mults(self)
        self.clearinputs()

    def launch_log_window(self) -> None:
        """Launch the log window"""
        self.pref["logwindow"] = self.actionLog_Window.isChecked()
        self.write_preference()
        if self.actionLog_Window.isChecked():
            self.log_window.show()
        else:
            self.log_window.hide()

    def launch_bandmap_window(self) -> None:
        """Launch the bandmap window"""
        self.pref["bandmapwindow"] = self.actionBandmap.isChecked()
        self.write_preference()
        if self.actionBandmap.isChecked():
            self.bandmap_window.show()
        else:
            self.bandmap_window.hide()

    def launch_check_window(self) -> None:
        """Launch the check window"""
        self.pref["checkwindow"] = self.actionCheck_Window.isChecked()
        self.write_preference()
        if self.actionCheck_Window.isChecked():
            self.check_window.show()
            self.check_window.setActive(True)
        else:
            self.check_window.hide()
            self.check_window.setActive(False)

    def launch_vfo(self) -> None:
        """Launch the VFO window"""
        self.pref["vfowindow"] = self.actionVFO.isChecked()
        self.write_preference()
        if self.actionVFO.isChecked():
            self.vfo_window.show()
        else:
            self.vfo_window.hide()

    def clear_band_indicators(self) -> None:
        """
        Clear the indicators.

        Parameters:
        ----------
        None

        Returns:
        -------
        None
        """
        for _, indicators in self.all_mode_indicators.items():
            for _, indicator in indicators.items():
                indicator.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
                if self.text_color == QColorConstants.Black:
                    indicator.setStyleSheet(
                        "font-family: JetBrains Mono ExtraLight; color: black;"
                    )
                else:
                    indicator.setStyleSheet(
                        "font-family: JetBrains Mono ExtraLight; color: white"
                    )

    def set_band_indicator(self, band: str) -> None:
        """
        Set the band indicator

        Parameters:
        ----------
        band: str
        band to set indicator for

        Returns:
        -------
        None
        """

        if band and self.current_mode:
            self.clear_band_indicators()
            indicator = self.all_mode_indicators[self.current_mode].get(band, None)
            if indicator:
                indicator.setFrameShape(QtWidgets.QFrame.Shape.Box)
                indicator.setStyleSheet(
                    "font-family: JetBrains Mono ExtraLight; color: green;"
                )

    def closeEvent(self, _event) -> None:
        """
        Write window size and position to config file.

        Parameters:
        ----------
        _event: QCloseEvent

        Returns:
        -------
        None
        """

        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.sync()

        try:  # Shutdown the radio thread.
            if self.radio_thread.isRunning():
                self.rig_control.time_to_quit = True
                self.radio_thread.quit()
                self.radio_thread.wait(1000)

        except (RuntimeError, AttributeError):
            ...

        cmd = {}
        cmd["cmd"] = "HALT"
        if self.bandmap_window:
            self.bandmap_window.msg_from_main(cmd)
        if self.log_window:
            self.log_window.msg_from_main(cmd)
        if self.lookup_service:
            self.lookup_service.msg_from_main(cmd)
        self.write_preference()

    def cty_lookup(self, callsign: str) -> list:
        """Lookup callsign in cty.dat file.

        Parameters
        ----------
        callsign : str
        callsign to lookup

        Returns
        -------
        return : list
        list of dicts containing the callsign and the station.
        """
        callsign = callsign.upper()
        for count in reversed(range(len(callsign))):
            searchitem = callsign[: count + 1]
            result = {
                key: val for key, val in self.ctyfile.items() if key == searchitem
            }
            if not result:
                continue
            if result.get(searchitem).get("exact_match"):
                if searchitem == callsign:
                    return result
                continue
            return result

    def cwspeed_spinbox_changed(self) -> None:
        """
        Triggered when value of CW speed in the spinbox changes.

        Parameters:
        ----------
        None

        Returns:
        -------
        None
        """
        if self.cw is None:
            return
        if self.cw.servertype == 1:
            self.cw.speed = self.cw_speed.value()
            self.cw.sendcw(f"\x1b2{self.cw.speed}")
        if self.cw.servertype == 2:
            self.cw.set_winkeyer_speed(self.cw_speed.value())
        if self.rig_control:
            if self.pref.get("cwtype") == 3 and self.rig_control is not None:
                if self.rig_control.interface == "flrig":
                    self.rig_control.cat.set_flrig_cw_speed(self.cw_speed.value())
                elif self.rig_control.interface == "rigctld":
                    self.rig_control.cat.set_rigctl_cw_speed(self.cw_speed.value())

    def stop_cw(self):
        """"""
        if self.cw is not None:
            if self.cw.servertype == 1:
                self.cw.sendcw("\x1b4")
                return
        if self.rig_control:
            if self.rig_control.online:
                if self.pref.get("cwtype") == 3 and self.rig_control is not None:
                    if self.rig_control.interface == "flrig":
                        self.rig_control.cat.set_flrig_cw_send(False)
                        self.rig_control.cat.set_flrig_cw_send(True)

    def mark_spot(self):
        """"""
        freq = self.radio_state.get("vfoa")
        dx = self.callsign.text()
        if freq and dx:
            cmd = {}
            cmd["cmd"] = "MARKDX"
            cmd["dx"] = dx
            cmd["freq"] = float(int(freq) / 1000)
            if self.bandmap_window:
                self.bandmap_window.msg_from_main(cmd)

    def spot_dx(self):
        """"""
        freq = self.radio_state.get("vfoa")
        dx = self.callsign.text()
        if freq and dx:
            cmd = {}
            cmd["cmd"] = "SPOTDX"
            cmd["dx"] = dx
            cmd["freq"] = float(int(freq) / 1000)
            if self.bandmap_window:
                self.bandmap_window.msg_from_main(cmd)

    def keyPressEvent(self, event) -> None:  # pylint: disable=invalid-name
        """
        This overrides Qt key event.

        Parameters:
        ----------
        event: QKeyEvent
        Qt key event

        Returns:
        -------
        None

        Control
        QWRTYIOPSFGHJLBNM,./;'[]//-


        shift control
        ABCDEFGHIJKLMNOPQRSTUVWXY
        """
        modifier = event.modifiers()
        # the_key = event.key()

        # print(f"Modifier is {modifier=} Key is {the_key=}")

        if (
            event.key() == Qt.Key.Key_Equal
            and modifier == Qt.KeyboardModifier.ControlModifier
        ):
            self.save_contact()
            return
        if event.key() == Qt.Key.Key_K:
            self.toggle_cw_entry()
            return
        if (
            event.key() == Qt.Key.Key_S
            and modifier == Qt.KeyboardModifier.ControlModifier
        ):
            freq = self.radio_state.get("vfoa")
            dx = self.callsign.text()
            if freq and dx:
                cmd = {}
                cmd["cmd"] = "SPOTDX"
                cmd["dx"] = dx
                cmd["freq"] = float(int(freq) / 1000)
                if self.bandmap_window:
                    self.bandmap_window.msg_from_main(cmd)
            return
        if (
            event.key() == Qt.Key.Key_M
            and modifier == Qt.KeyboardModifier.ControlModifier
        ):
            freq = self.radio_state.get("vfoa")
            dx = self.callsign.text()
            if freq and dx:
                cmd = {}
                cmd["cmd"] = "MARKDX"
                cmd["dx"] = dx
                cmd["freq"] = float(int(freq) / 1000)
                if self.bandmap_window:
                    self.bandmap_window.msg_from_main(cmd)
            return
        if (
            event.key() == Qt.Key.Key_G
            and modifier == Qt.KeyboardModifier.ControlModifier
        ):
            dx = self.callsign.text()
            if dx:
                cmd = {}
                cmd["cmd"] = "FINDDX"
                cmd["dx"] = dx
                if self.bandmap_window:
                    self.bandmap_window.msg_from_main(cmd)
            return
        if (
            event.key() == Qt.Key.Key_W
            and modifier == Qt.KeyboardModifier.ControlModifier
        ):  # pylint: disable=no-member
            self.clearinputs()
            return
        if (
            event.key() == Qt.Key.Key_Escape
            and modifier != Qt.KeyboardModifier.ControlModifier
        ):
            if self.cw is not None:
                if self.cw.servertype == 1:
                    self.cw.sendcw("\x1b4")
                    return
            if self.rig_control:
                if self.rig_control.online:
                    if self.pref.get("cwtype") == 3 and self.rig_control is not None:
                        if self.rig_control.interface == "flrig":
                            self.rig_control.cat.set_flrig_cw_send(False)
                            self.rig_control.cat.set_flrig_cw_send(True)
        if event.key() == Qt.Key.Key_Up:
            cmd = {}
            cmd["cmd"] = "PREVSPOT"
            if self.bandmap_window:
                self.bandmap_window.msg_from_main(cmd)
            return
        if event.key() == Qt.Key.Key_Down:
            cmd = {}
            cmd["cmd"] = "NEXTSPOT"
            if self.bandmap_window:
                self.bandmap_window.msg_from_main(cmd)
            return
        if (
            event.key() == Qt.Key.Key_PageUp
            and modifier != Qt.KeyboardModifier.ControlModifier
        ):
            if self.cw is not None:
                self.cw.speed += 1
                self.cw_speed.setValue(self.cw.speed)
                if self.cw.servertype == 1:
                    self.cw.sendcw(f"\x1b2{self.cw.speed}")
                if self.cw.servertype == 2:
                    self.cw.set_winkeyer_speed(self.cw_speed.value())
            return
        if (
            event.key() == Qt.Key.Key_PageDown
            and modifier != Qt.KeyboardModifier.ControlModifier
        ):
            if self.cw is not None:
                self.cw.speed -= 1
                self.cw_speed.setValue(self.cw.speed)
                if self.cw.servertype == 1:
                    self.cw.sendcw(f"\x1b2{self.cw.speed}")
                if self.cw.servertype == 2:
                    self.cw.set_winkeyer_speed(self.cw_speed.value())
            return
        if event.key() == Qt.Key.Key_Tab or event.key() == Qt.Key.Key_Backtab:
            if self.sent.hasFocus():
                logger.debug("From sent")
                if modifier == Qt.KeyboardModifier.ShiftModifier:
                    prev_tab = self.tab_prev.get(self.sent)
                    prev_tab.setFocus()
                    prev_tab.deselect()
                    prev_tab.end(False)
                else:
                    next_tab = self.tab_next.get(self.sent)
                    next_tab.setFocus()
                    next_tab.deselect()
                    next_tab.end(False)
                return
            if self.receive.hasFocus():
                logger.debug("From receive")
                if modifier == Qt.KeyboardModifier.ShiftModifier:
                    prev_tab = self.tab_prev.get(self.receive)
                    prev_tab.setFocus()
                    prev_tab.deselect()
                    prev_tab.end(False)
                else:
                    next_tab = self.tab_next.get(self.receive)
                    next_tab.setFocus()
                    next_tab.deselect()
                    next_tab.end(False)
                return
            if self.other_1.hasFocus():
                logger.debug("From other_1")
                if modifier == Qt.KeyboardModifier.ShiftModifier:
                    prev_tab = self.tab_prev.get(self.other_1)
                    prev_tab.setFocus()
                    prev_tab.deselect()
                    prev_tab.end(False)
                else:
                    next_tab = self.tab_next.get(self.other_1)
                    next_tab.setFocus()
                    next_tab.deselect()
                    next_tab.end(False)
                return
            if self.other_2.hasFocus():
                logger.debug("From other_2")
                if modifier == Qt.KeyboardModifier.ShiftModifier:
                    prev_tab = self.tab_prev.get(self.other_2)
                    prev_tab.setFocus()
                    prev_tab.deselect()
                    prev_tab.end(False)
                else:
                    next_tab = self.tab_next.get(self.other_2)
                    next_tab.setFocus()
                    next_tab.deselect()
                    next_tab.end(False)
                return
            if self.callsign.hasFocus():
                logger.debug("From callsign")
                self.check_callsign(self.callsign.text())
                if self.check_dupe(self.callsign.text()):
                    self.dupe_indicator.show()
                else:
                    self.dupe_indicator.hide()
                if modifier == Qt.KeyboardModifier.ShiftModifier:
                    prev_tab = self.tab_prev.get(self.callsign)
                    prev_tab.setFocus()
                    prev_tab.deselect()
                    prev_tab.end(False)
                else:
                    text = self.callsign.text()
                    text = text.upper()
                    cmd = {}
                    cmd["cmd"] = "LOOKUP_CALL"
                    cmd["call"] = text
                    if self.lookup_service:
                        self.lookup_service.msg_from_main(cmd)
                    next_tab = self.tab_next.get(self.callsign)
                    next_tab.setFocus()
                    next_tab.deselect()
                    next_tab.end(False)
                return
        if event.key() == Qt.Key.Key_F1:
            self.process_function_key(self.F1)
        if event.key() == Qt.Key.Key_F2:
            self.process_function_key(self.F2)
        if event.key() == Qt.Key.Key_F3:
            self.process_function_key(self.F3)
        if event.key() == Qt.Key.Key_F4:
            self.process_function_key(self.F4)
        if event.key() == Qt.Key.Key_F5:
            self.process_function_key(self.F5)
        if event.key() == Qt.Key.Key_F6:
            self.process_function_key(self.F6)
        if event.key() == Qt.Key.Key_F7:
            self.process_function_key(self.F7)
        if event.key() == Qt.Key.Key_F8:
            self.process_function_key(self.F8)
        if event.key() == Qt.Key.Key_F9:
            self.process_function_key(self.F9)
        if event.key() == Qt.Key.Key_F10:
            self.process_function_key(self.F10)
        if event.key() == Qt.Key.Key_F11:
            self.process_function_key(self.F11)
        if event.key() == Qt.Key.Key_F12:
            self.process_function_key(self.F12)

    def set_window_title(self) -> None:
        """
        Set window title based on current state.
        """

        vfoa = self.radio_state.get("vfoa", "")
        if vfoa:
            try:
                vfoa = int(vfoa) / 1000
            except ValueError:
                vfoa = 0.0
        else:
            vfoa = 0.0
        contest_name = ""
        if self.contest:
            contest_name = self.contest.name
        line = (
            f"vfoa:{round(vfoa,2)} "
            f"mode:{self.radio_state.get('mode', '')} "
            f"OP:{self.current_op} {contest_name} "
            f"- Not1MM v{__version__}"
        )
        self.setWindowTitle(line)

    def send_worked_list(self) -> None:
        """
        Send message containing worked contacts and bands

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        cmd = {}
        cmd["cmd"] = "WORKED"
        cmd["worked"] = self.worked_list
        logger.debug("%s", f"{cmd}")
        if self.bandmap_window:
            self.bandmap_window.msg_from_main(cmd)

    def clearinputs(self) -> None:
        """
        Clears the text input fields and sets focus to callsign field.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.dupe_indicator.hide()
        self.contact = self.database.empty_contact.copy()
        self.heading_distance.setText("")
        self.history_info.setText("")
        self.dx_entity.setText("")

        if self.contest:
            mults = self.contest.show_mults(self)
            qsos = self.contest.show_qso(self)
            multstring = f"{qsos}/{mults}"
            self.mults.setText(multstring)
            score = self.contest.calc_score(self)
            self.score.setText(str(score))
            self.contest.reset_label(self)
            if (
                self.contest.name != "ICWC Medium Speed Test"
                and self.contest.name != "RAEM"
            ):
                if self.current_mode in ("CW", "RTTY"):
                    self.sent.setText("599")
                    self.receive.setText("599")
                else:
                    self.sent.setText("59")
                    self.receive.setText("59")
            else:
                self.sent.setText("")
        self.callsign.clear()
        self.other_1.clear()
        self.other_2.clear()
        self.callsign.setFocus()
        cmd = {}
        cmd["cmd"] = "CALLCHANGED"
        cmd["call"] = ""
        if self.log_window:
            self.log_window.msg_from_main(cmd)
        if self.bandmap_window:
            self.bandmap_window.msg_from_main(cmd)
        if self.check_window:
            self.check_window.msg_from_main(cmd)

    def save_contact(self) -> None:
        """
        Save contact to database.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        logger.debug("saving contact")
        if self.contest is None:
            self.show_message_box("You have no contest defined...")
            return
        if len(self.callsign.text()) < 3:
            return
        if not any(char.isdigit() for char in self.callsign.text()):
            return
        if not any(char.isalpha() for char in self.callsign.text()):
            return
        self.contact["TS"] = datetime.datetime.now(datetime.timezone.utc).isoformat(
            " "
        )[:19]
        self.contact["Call"] = self.callsign.text()
        if self.contact.get("Mode") not in (
            "FT8",
            "FT4",
            "RTTY",
            "PSK31",
            "FSK441",
            "MSK144",
            "JT65",
            "JT9",
            "Q65",
        ):
            self.contact["Freq"] = round(
                float(self.radio_state.get("vfoa", 0.0)) / 1000, 2
            )
            self.contact["QSXFreq"] = round(
                float(self.radio_state.get("vfoa", 0.0)) / 1000, 2
            )
            self.contact["Mode"] = self.radio_state.get("mode", "")
        self.contact["Freq"] = round(float(self.radio_state.get("vfoa", 0.0)) / 1000, 2)
        self.contact["QSXFreq"] = round(
            float(self.radio_state.get("vfoa", 0.0)) / 1000, 2
        )
        self.contact["ContestName"] = self.contest.cabrillo_name
        self.contact["ContestNR"] = self.pref.get("contest", "0")
        self.contact["StationPrefix"] = self.station.get("Call", "")
        self.contact["WPXPrefix"] = calculate_wpx_prefix(self.callsign.text())
        self.contact["IsRunQSO"] = self.radioButton_run.isChecked()
        self.contact["Operator"] = self.current_op
        self.contact["NetBiosName"] = socket.gethostname()
        self.contact["IsOriginal"] = 1
        self.contact["ID"] = uuid.uuid4().hex
        self.contest.set_contact_vars(self)
        self.contact["Points"] = self.contest.points(self)
        debug_output = f"{self.contact}"
        logger.debug(debug_output)

        if self.n1mm:
            logger.debug("packets %s", f"{self.n1mm.send_contact_packets}")
            if self.n1mm.send_contact_packets:
                self.n1mm.contact_info["timestamp"] = self.contact["TS"]
                self.n1mm.contact_info["oldcall"] = self.n1mm.contact_info["call"] = (
                    self.contact["Call"]
                )
                self.n1mm.contact_info["txfreq"] = self.n1mm.contact_info["rxfreq"] = (
                    self.n1mm.radio_info["Freq"]
                )
                self.n1mm.contact_info["mode"] = self.contact["Mode"]
                self.n1mm.contact_info["contestname"] = self.contact[
                    "ContestName"
                ].replace("-", "")
                self.n1mm.contact_info["contestnr"] = self.contact["ContestNR"]
                self.n1mm.contact_info["stationprefix"] = self.contact["StationPrefix"]
                self.n1mm.contact_info["wpxprefix"] = self.contact["WPXPrefix"]
                self.n1mm.contact_info["IsRunQSO"] = self.contact["IsRunQSO"]
                self.n1mm.contact_info["operator"] = self.contact["Operator"]
                self.n1mm.contact_info["mycall"] = self.contact["Operator"]
                self.n1mm.contact_info["StationName"] = self.n1mm.contact_info[
                    "NetBiosName"
                ] = self.contact["NetBiosName"]
                self.n1mm.contact_info["IsOriginal"] = self.contact["IsOriginal"]
                self.n1mm.contact_info["ID"] = self.contact["ID"]
                self.n1mm.contact_info["points"] = self.contact["Points"]
                self.n1mm.contact_info["snt"] = self.contact["SNT"]
                self.n1mm.contact_info["rcv"] = self.contact["RCV"]
                self.n1mm.contact_info["sntnr"] = self.contact["SentNr"]
                self.n1mm.contact_info["rcvnr"] = self.contact["NR"]
                self.n1mm.contact_info["ismultiplier1"] = self.contact.get(
                    "IsMultiplier1", 0
                )
                self.n1mm.contact_info["ismultiplier2"] = self.contact.get(
                    "IsMultiplier2", 0
                )
                self.n1mm.contact_info["ismultiplier3"] = self.contact.get(
                    "IsMultiplier3", 0
                )
                self.n1mm.contact_info["section"] = self.contact["Sect"]
                self.n1mm.contact_info["prec"] = self.contact["Prec"]
                self.n1mm.contact_info["ck"] = self.contact["CK"]
                self.n1mm.contact_info["zn"] = self.contact["ZN"]
                self.n1mm.contact_info["power"] = self.contact["Power"]
                self.n1mm.contact_info["band"] = self.contact["Band"]
                logger.debug("%s", f"{self.n1mm.contact_info}")
                self.n1mm.send_contact_info()

        self.database.log_contact(self.contact)
        self.worked_list = self.database.get_calls_and_bands()
        self.send_worked_list()
        self.clearinputs()

        cmd = {}
        cmd["cmd"] = "UPDATELOG"
        if self.log_window:
            self.log_window.msg_from_main(cmd)
        if self.check_window:
            self.check_window.msg_from_main(cmd)

    def new_contest_dialog(self) -> None:
        """
        Show new contest dialog.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        logger.debug("New contest Dialog")

        self.contest_dialog = NewContest(fsutils.APP_DATA_PATH)
        if self.current_palette:
            self.contest_dialog.setPalette(self.current_palette)
            self.contest_dialog.exchange.setPalette(self.current_palette)
            self.contest_dialog.operators.setPalette(self.current_palette)

        self.contest_dialog.accepted.connect(self.save_contest)
        self.contest_dialog.dateTimeEdit.setDate(QtCore.QDate.currentDate())
        self.contest_dialog.dateTimeEdit.setCalendarPopup(True)
        self.contest_dialog.dateTimeEdit.setTime(QtCore.QTime(0, 0))
        self.contest_dialog.power.setCurrentText("LOW")
        self.contest_dialog.station.setCurrentText("FIXED")
        self.contest_dialog.open()

    def save_contest(self) -> None:
        """
        Save Contest to database.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        next_number = self.database.get_next_contest_nr()
        contest = {}
        contest["ContestName"] = (
            self.contest_dialog.contest.currentText().lower().replace(" ", "_")
        )
        contest["StartDate"] = self.contest_dialog.dateTimeEdit.dateTime().toString(
            "yyyy-MM-dd hh:mm:ss"
        )
        contest["OperatorCategory"] = self.contest_dialog.operator_class.currentText()
        contest["BandCategory"] = self.contest_dialog.band.currentText()
        contest["PowerCategory"] = self.contest_dialog.power.currentText()
        contest["ModeCategory"] = self.contest_dialog.mode.currentText()
        contest["OverlayCategory"] = self.contest_dialog.overlay.currentText()
        # contest['ClaimedScore'] = self.contest_dialog.
        contest["Operators"] = self.contest_dialog.operators.text()
        contest["Soapbox"] = self.contest_dialog.soapbox.toPlainText()
        contest["SentExchange"] = self.contest_dialog.exchange.text()
        contest["ContestNR"] = next_number.get("count", 1)
        self.pref["contest"] = next_number.get("count", 1)
        # contest['SubType'] = self.contest_dialog.
        contest["StationCategory"] = self.contest_dialog.station.currentText()
        contest["AssistedCategory"] = self.contest_dialog.assisted.currentText()
        contest["TransmitterCategory"] = self.contest_dialog.transmitter.currentText()
        # contest['TimeCategory'] = self.contest_dialog.
        logger.debug("%s", f"{contest}")
        self.database.add_contest(contest)
        self.write_preference()
        self.load_contest()

    def edit_station_settings(self) -> None:
        """
        Show settings dialog for station.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        logger.debug("Station Settings selected")

        self.settings_dialog = EditStation(fsutils.APP_DATA_PATH)
        if self.current_palette:
            self.settings_dialog.setPalette(self.current_palette)

        self.settings_dialog.accepted.connect(self.save_settings)
        self.settings_dialog.Call.setText(self.station.get("Call", ""))
        self.settings_dialog.Name.setText(self.station.get("Name", ""))
        self.settings_dialog.Address1.setText(self.station.get("Street1", ""))
        self.settings_dialog.Address2.setText(self.station.get("Street2", ""))
        self.settings_dialog.City.setText(self.station.get("City", ""))
        self.settings_dialog.State.setText(self.station.get("State", ""))
        self.settings_dialog.Zip.setText(self.station.get("Zip", ""))
        self.settings_dialog.Country.setText(self.station.get("Country", ""))
        self.settings_dialog.GridSquare.setText(self.station.get("GridSquare", ""))
        self.settings_dialog.CQZone.setText(str(self.station.get("CQZone", "")))
        self.settings_dialog.ITUZone.setText(str(self.station.get("IARUZone", "")))
        self.settings_dialog.License.setText(self.station.get("LicenseClass", ""))
        self.settings_dialog.Latitude.setText(str(self.station.get("Latitude", "")))
        self.settings_dialog.Longitude.setText(str(self.station.get("Longitude", "")))
        self.settings_dialog.StationTXRX.setText(self.station.get("stationtxrx", ""))
        self.settings_dialog.Power.setText(self.station.get("SPowe", ""))
        self.settings_dialog.Antenna.setText(self.station.get("SAnte", ""))
        self.settings_dialog.AntHeight.setText(self.station.get("SAntH1", ""))
        self.settings_dialog.ASL.setText(self.station.get("SAntH2", ""))
        self.settings_dialog.ARRLSection.setText(self.station.get("ARRLSection", ""))
        self.settings_dialog.RoverQTH.setText(self.station.get("RoverQTH", ""))
        self.settings_dialog.Club.setText(self.station.get("Club", ""))
        self.settings_dialog.Email.setText(self.station.get("Email", ""))
        self.settings_dialog.open()

    def save_settings(self) -> None:
        """
        Save Station settings to database.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        cs = self.settings_dialog.Call.text()
        self.station = {}
        self.station["Call"] = cs.upper()
        self.station["Name"] = self.settings_dialog.Name.text().title()
        self.station["Street1"] = self.settings_dialog.Address1.text().title()
        self.station["Street2"] = self.settings_dialog.Address2.text().title()
        self.station["City"] = self.settings_dialog.City.text().title()
        self.station["State"] = self.settings_dialog.State.text().upper()
        self.station["Zip"] = self.settings_dialog.Zip.text()
        self.station["Country"] = self.settings_dialog.Country.text().title()
        self.station["GridSquare"] = self.settings_dialog.GridSquare.text()
        self.station["CQZone"] = self.settings_dialog.CQZone.text()
        self.station["IARUZone"] = self.settings_dialog.ITUZone.text()
        self.station["LicenseClass"] = self.settings_dialog.License.text().title()
        self.station["Latitude"] = self.settings_dialog.Latitude.text()
        self.station["Longitude"] = self.settings_dialog.Longitude.text()
        self.station["STXeq"] = self.settings_dialog.StationTXRX.text()
        self.station["SPowe"] = self.settings_dialog.Power.text()
        self.station["SAnte"] = self.settings_dialog.Antenna.text()
        self.station["SAntH1"] = self.settings_dialog.AntHeight.text()
        self.station["SAntH2"] = self.settings_dialog.ASL.text()
        self.station["ARRLSection"] = self.settings_dialog.ARRLSection.text().upper()
        self.station["RoverQTH"] = self.settings_dialog.RoverQTH.text()
        self.station["Club"] = self.settings_dialog.Club.text().title()
        self.station["Email"] = self.settings_dialog.Email.text()
        self.database.add_station(self.station)
        self.settings_dialog.close()
        if self.current_op == "":
            self.current_op = self.station.get("Call", "")
            self.voice_process.current_op = self.current_op
            self.make_op_dir()
        contest_count = self.database.fetch_all_contests()
        if len(contest_count) == 0:
            self.new_contest_dialog()

    def edit_macro(self, function_key) -> None:
        """
        Show edit macro dialog for function key.

        Parameters
        ----------
        function_key : str
        Function key to edit.

        Returns
        -------
        None
        """

        self.edit_macro_dialog = EditMacro(function_key, fsutils.APP_DATA_PATH)

        if self.current_palette:
            self.edit_macro_dialog.setPalette(self.current_palette)

        self.edit_macro_dialog.accepted.connect(self.edited_macro)
        self.edit_macro_dialog.open()

    def edited_macro(self) -> None:
        """
        Save edited macro to database.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.edit_macro_dialog.function_key.setText(
            self.edit_macro_dialog.macro_label.text()
        )
        self.edit_macro_dialog.function_key.setToolTip(
            self.edit_macro_dialog.the_macro.text()
        )
        self.edit_macro_dialog.close()

    def process_macro(self, macro: str) -> str:
        """
        Process CW macro substitutions for contest.

        Parameters
        ----------
        macro : str
        Macro to process.

        Returns
        -------
        str
        Processed macro.
        """

        result = self.database.get_serial()
        next_serial = str(result.get("serial_nr", "1"))
        if next_serial == "None":
            next_serial = "1"
        macro = macro.upper()
        if self.radio_state.get("mode") == "CW":
            macro = macro.replace("#", next_serial.rjust(3, "T"))
        else:
            macro = macro.replace("#", next_serial)
        macro = macro.replace("{MYCALL}", self.station.get("Call", ""))
        macro = macro.replace("{HISCALL}", self.callsign.text())
        if self.radio_state.get("mode") == "CW":
            macro = macro.replace("{SNT}", self.sent.text().replace("9", "n"))
        else:
            macro = macro.replace("{SNT}", self.sent.text())
        if self.radio_state.get("mode") == "CW":
            macro = macro.replace(
                "{SENTNR}", self.other_1.text().lstrip("0").rjust(3, "T")
            )
        else:
            macro = macro.replace("{SENTNR}", self.other_1.text())
        macro = macro.replace(
            "{EXCH}", self.contest_settings.get("SentExchange", "xxx")
        )
        return macro

    def ptt_on(self) -> None:
        """
        Turn on ptt for rig.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        logger.debug("PTT On")
        if self.rig_control:
            self.leftdot.setPixmap(self.greendot)
            app.processEvents()
            self.rig_control.ptt_on()

    def ptt_off(self) -> None:
        """
        Turn off ptt for rig.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        logger.debug("PTT Off")
        if self.rig_control:
            self.leftdot.setPixmap(self.reddot)
            app.processEvents()
            self.rig_control.ptt_off()

    def process_function_key(self, function_key, rttysendrx=True) -> None:
        """
        Called when a function key is clicked.

        Parameters
        ----------
        function_key : QPushButton
        Function key to process.

        Returns
        -------
        None
        """

        logger.debug("Function Key: %s", function_key.text())
        if self.n1mm:
            self.n1mm.radio_info["FunctionKeyCaption"] = function_key.text()
        if self.radio_state.get("mode") in ["LSB", "USB", "SSB"]:
            self.voice_process.voice_string(self.process_macro(function_key.toolTip()))
            # self.voice_string(self.process_macro(function_key.toolTip()))
            return
        if self.radio_state.get("mode") in [
            "RTTY",
            "USB-D",
            "LSB-D",
            "PKTLSB",
            "PKTUSB",
            "DIGI-U",
            "DIGI-L",
        ]:
            self.fldigi_util.send_string(
                self.process_macro(function_key.toolTip()), rxafter=rttysendrx
            )
            return
        if self.cw:
            if self.pref.get("cwtype") == 3 and self.rig_control is not None:
                self.rig_control.sendcw(self.process_macro(function_key.toolTip()))
                return
            self.cw.sendcw(self.process_macro(function_key.toolTip()))

    def run_sp_buttons_clicked(self) -> None:
        """
        Handle Run/S&P mode changes.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        self.pref["run_state"] = self.radioButton_run.isChecked()
        self.write_preference()
        self.read_macros()
        self.check_esm()

    def write_preference(self) -> None:
        """
        Write preferences to file.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        logger.debug("writepreferences")
        try:
            with open(fsutils.CONFIG_FILE, "wt", encoding="utf-8") as file_descriptor:
                file_descriptor.write(dumps(self.pref, indent=4))
                # logger.info("writing: %s", self.pref)
        except (IOError, TypeError, ValueError) as exception:
            logger.critical("writepreferences: %s", exception)

    def readpreferences(self) -> None:
        """
        Restore preferences if they exist, otherwise create some sane defaults.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        logger.debug("readpreferences")
        try:
            if os.path.exists(fsutils.CONFIG_FILE):
                with open(
                    fsutils.CONFIG_FILE, "rt", encoding="utf-8"
                ) as file_descriptor:
                    try:
                        self.pref = loads(file_descriptor.read())
                    except (JSONDecodeError, TypeError):
                        logging.CRITICAL(
                            "There was an error parsing the preference file."
                        )
                    logger.info("%s", self.pref)
            else:
                logger.info("No preference file. Writing preference.")
                with open(
                    fsutils.CONFIG_FILE, "wt", encoding="utf-8"
                ) as file_descriptor:
                    self.pref = self.pref_ref.copy()
                    file_descriptor.write(dumps(self.pref, indent=4))
                    logger.info("%s", self.pref)
        except (IOError, TypeError, ValueError) as exception:
            logger.critical("Error: %s", exception)

        if self.pref.get("run_state"):
            self.radioButton_run.setChecked(True)
        else:
            self.radioButton_sp.setChecked(True)

        if self.pref.get("command_buttons"):
            self.actionCommand_Buttons.setChecked(True)
        else:
            self.actionCommand_Buttons.setChecked(False)

        if self.pref.get("cw_macros"):
            self.actionCW_Macros.setChecked(True)
        else:
            self.actionCW_Macros.setChecked(False)

        if self.pref.get("bands_modes"):
            self.actionMode_and_Bands.setChecked(True)
        else:
            self.actionMode_and_Bands.setChecked(False)

        cmd = {}
        cmd["cmd"] = "REFRESH_LOOKUP"
        if self.lookup_service:
            self.lookup_service.msg_from_main(cmd)

        if self.pref.get("darkmode"):
            self.actionDark_Mode_2.setChecked(True)
            self.setDarkMode(True)
        else:
            self.setDarkMode(False)
            self.actionDark_Mode_2.setChecked(False)

        try:
            if self.radio_thread.isRunning():
                self.rig_control.time_to_quit = True
                self.radio_thread.quit()
                self.radio_thread.wait(1000)

        except (RuntimeError, AttributeError):
            ...

        self.rig_control = None
        self.fldigi_util = FlDigi_Comm()

        if self.pref.get("useflrig", False):
            logger.debug(
                "Using flrig: %s",
                f"{self.pref.get('CAT_ip')} {self.pref.get('CAT_port')}",
            )
            self.rig_control = Radio(
                "flrig",
                self.pref.get("CAT_ip", "127.0.0.1"),
                int(self.pref.get("CAT_port", 12345)),
            )
            self.rig_control.delta = int(self.pref.get("CAT_polldelta", 555))
            self.rig_control.moveToThread(self.radio_thread)
            self.radio_thread.started.connect(self.rig_control.run)
            self.radio_thread.finished.connect(self.rig_control.deleteLater)
            self.rig_control.poll_callback.connect(self.poll_radio)
            self.radio_thread.start()

        elif self.pref.get("userigctld", False):
            logger.debug(
                "Using rigctld: %s",
                f"{self.pref.get('CAT_ip')} {self.pref.get('CAT_port')}",
            )
            self.rig_control = Radio(
                "rigctld",
                self.pref.get("CAT_ip", "127.0.0.1"),
                int(self.pref.get("CAT_port", 4532)),
            )
            self.rig_control.delta = int(self.pref.get("CAT_polldelta", 555))
            self.rig_control.moveToThread(self.radio_thread)
            self.radio_thread.started.connect(self.rig_control.run)
            self.radio_thread.finished.connect(self.rig_control.deleteLater)
            self.rig_control.poll_callback.connect(self.poll_radio)
            self.radio_thread.start()
        else:
            self.rig_control = Radio(
                "fake",
                self.pref.get("CAT_ip", "127.0.0.1"),
                int(self.pref.get("CAT_port", 0000)),
            )
            self.rig_control.delta = int(self.pref.get("CAT_polldelta", 555))
            self.rig_control.moveToThread(self.radio_thread)
            self.radio_thread.started.connect(self.rig_control.run)
            self.radio_thread.finished.connect(self.rig_control.deleteLater)
            self.rig_control.poll_callback.connect(self.poll_radio)
            self.radio_thread.start()

        self.cw = None
        if (
            self.pref.get("cwport")
            and self.pref.get("cwip")
            and self.pref.get("cwtype")
        ):
            self.cw = CW(
                int(self.pref.get("cwtype")),
                self.pref.get("cwip"),
                int(self.pref.get("cwport")),
            )
            self.cw.speed = 20
            if self.cw.servertype == 2:
                self.cw.set_winkeyer_speed(20)

        self.n1mm = None
        if self.pref.get("send_n1mm_packets", False):
            try:
                self.n1mm = N1MM(
                    self.pref.get("n1mm_radioport", "127.0.0.1:12060"),
                    self.pref.get("n1mm_contactport", "127.0.0.1:12061"),
                    self.pref.get("n1mm_lookupport", "127.0.0.1:12060"),
                    self.pref.get("n1mm_scoreport", "127.0.0.1:12060"),
                )
            except ValueError:
                logger.warning("%s", f"{ValueError}")
            self.n1mm.send_radio_packets = self.pref.get("send_n1mm_radio", False)
            self.n1mm.send_contact_packets = self.pref.get("send_n1mm_contact", False)
            self.n1mm.send_lookup_packets = self.pref.get("send_n1mm_lookup", False)
            self.n1mm.send_score_packets = self.pref.get("send_n1mm_score", False)
            self.n1mm.radio_info["StationName"] = self.pref.get("n1mm_station_name", "")

        self.show_command_buttons()
        self.show_CW_macros()

        # If bands list is empty fill it with HF.
        if self.pref.get("bands", []) == []:
            self.pref["bands"] = [
                "160",
                "80",
                "40",
                "20",
                "15",
                "10",
            ]

        # Hide all the bands and then show only the wanted bands.
        for _indicator in [
            self.band_indicators_cw,
            self.band_indicators_ssb,
            self.band_indicators_rtty,
        ]:
            for _bandind in _indicator.values():
                _bandind.hide()
            for band_to_show in self.pref.get("bands", []):
                if band_to_show in _indicator:
                    _indicator[band_to_show].show()

        fkey_dict = {
            "F1": self.F1,
            "F2": self.F2,
            "F3": self.F3,
            "F4": self.F4,
            "F5": self.F5,
            "F6": self.F6,
            "F7": self.F7,
            "F8": self.F8,
            "F9": self.F9,
            "F10": self.F10,
            "F11": self.F11,
            "F12": self.F12,
            "DISABLED": None,
        }

        self.use_call_history = self.pref.get("use_call_history", False)
        if self.use_call_history:
            self.history_info.show()
        else:
            self.history_info.hide()
        self.use_esm = self.pref.get("use_esm", False)
        self.esm_dict["CQ"] = fkey_dict.get(self.pref.get("esm_cq", "DISABLED"))
        self.esm_dict["EXCH"] = fkey_dict.get(self.pref.get("esm_exch", "DISABLED"))
        self.esm_dict["QRZ"] = fkey_dict.get(self.pref.get("esm_qrz", "DISABLED"))
        self.esm_dict["AGN"] = fkey_dict.get(self.pref.get("esm_agn", "DISABLED"))
        self.esm_dict["HISCALL"] = fkey_dict.get(
            self.pref.get("esm_hiscall", "DISABLED")
        )
        self.esm_dict["MYCALL"] = fkey_dict.get(self.pref.get("esm_mycall", "DISABLED"))
        self.esm_dict["QSOB4"] = fkey_dict.get(self.pref.get("esm_qsob4", "DISABLED"))

    def dark_mode_state_changed(self) -> None:
        """Called when the Dark Mode menu state is changed."""
        self.pref["darkmode"] = self.actionDark_Mode_2.isChecked()
        self.write_preference()
        self.setDarkMode(self.actionDark_Mode_2.isChecked())

    def cw_macros_state_changed(self) -> None:
        """
        Menu item to show/hide macro buttons.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.pref["cw_macros"] = self.actionCW_Macros.isChecked()
        self.write_preference()
        self.show_CW_macros()

    def show_CW_macros(self) -> None:
        """
        Show/Hide the macro buttons.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if self.pref.get("cw_macros"):
            self.Button_Row1.show()
            self.Button_Row2.show()
        else:
            self.Button_Row1.hide()
            self.Button_Row2.hide()

    def command_buttons_state_change(self) -> None:
        """
        Menu item to show/hide command buttons

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.pref["command_buttons"] = self.actionCommand_Buttons_2.isChecked()
        self.write_preference()
        self.show_command_buttons()

    def show_command_buttons(self) -> None:
        """
        Show/Hide the command buttons depending on the preference.

        Parameters
        ----------
        None

        Returns
        -------

        """

        if self.pref.get("command_buttons"):
            self.Command_Buttons.show()
        else:
            self.Command_Buttons.hide()

    def is_floatable(self, item: str) -> bool:
        """
        Check to see if string can be a float.

        Parameters
        ----------
        item : str
        The string to test.

        Returns
        -------
        bool
        True if string can be a float, False otherwise.
        """

        if item.isnumeric():
            return True
        try:
            _test = float(item)
        except ValueError:
            return False
        return True

    def other_1_changed(self) -> None:
        """
        The text in the other_1 field has changed.
        Strip out any spaces and set the text.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if self.contest:
            if hasattr(self.contest, "advance_on_space"):
                if self.contest.advance_on_space[3]:
                    text = self.other_1.text()
                    text = text.upper()
                    # position = self.other_1.cursorPosition()
                    stripped_text = text.strip().replace(" ", "")
                    self.other_1.setText(stripped_text)
                    # self.other_1.setCursorPosition(position)
                    if " " in text:
                        next_tab = self.tab_next.get(self.other_1)
                        next_tab.setFocus()
                        next_tab.deselect()
                        next_tab.end(False)

    def other_2_changed(self) -> None:
        """
        Text in other_2 has changed.
        Strip out any spaces and set the text.
        Parse the exchange if the contest is ARRL Sweepstakes.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if self.contest:
            if "ARRL Sweepstakes" in self.contest.name:
                self.contest.parse_exchange(self)
                return
            if hasattr(self.contest, "advance_on_space"):
                if self.contest.advance_on_space[4]:
                    text = self.other_2.text()
                    text = text.upper()
                    # position = self.other_2.cursorPosition()
                    stripped_text = text.strip().replace(" ", "")
                    self.other_2.setText(stripped_text)
                    # self.other_2.setCursorPosition(position)
                    if " " in text:
                        next_tab = self.tab_next.get(self.other_2)
                        next_tab.setFocus()
                        next_tab.deselect()
                        next_tab.end(False)

    def callsign_changed(self) -> None:
        """
        Called when text in the callsign field has changed.
        Strip out any spaces and set the text.
        Check if the field contains a command.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        text = self.callsign.text()
        text = text.upper()
        position = self.callsign.cursorPosition()
        stripped_text = text.strip().replace(" ", "")
        self.callsign.setText(stripped_text)
        self.callsign.setCursorPosition(position)

        if " " in text:
            if stripped_text == "CW":
                self.change_mode(stripped_text)
                return
            if stripped_text == "RTTY":
                self.change_mode(stripped_text)
                return
            if stripped_text == "SSB":
                self.change_mode(stripped_text)
                return
            if stripped_text == "OPON":
                self.get_opon()
                self.clearinputs()
                return
            if stripped_text == "HELP":
                self.show_help_dialog()
                self.clearinputs()
                return
            if self.is_floatable(stripped_text):
                self.change_freq(stripped_text)
                self.clearinputs()
                return
            cmd = {}
            cmd["cmd"] = "LOOKUP_CALL"
            cmd["call"] = stripped_text
            if self.lookup_service:
                self.lookup_service.msg_from_main(cmd)
            self.next_field.setFocus()
            if self.contest:
                if self.use_call_history and hasattr(
                    self.contest, "check_call_history"
                ):
                    self.contest.check_call_history(self)
                if "CQ WW" in self.contest.name or "IARU HF" in self.contest.name:
                    self.contest.prefill(self)
            return
        cmd = {}
        cmd["cmd"] = "CALLCHANGED"
        cmd["call"] = stripped_text
        if self.bandmap_window:
            self.bandmap_window.msg_from_main(cmd)
        if self.log_window:
            self.log_window.msg_from_main(cmd)
        if self.check_window:
            self.check_window.msg_from_main(cmd)
        self.check_callsign(stripped_text)
        if self.check_dupe(stripped_text):
            self.dupe_indicator.show()
        else:
            self.dupe_indicator.hide()
        if self.contest:
            if self.use_call_history and hasattr(
                self.contest, "populate_history_info_line"
            ):
                self.contest.populate_history_info_line(self)

    def change_freq(self, stripped_text: str) -> None:
        """
        Change Radios VFO to given frequency in Khz.

        Parameters
        ----------
        stripped_text: str

        Stripped of any spaces.

        Returns
        -------
        None
        """

        vfo = float(stripped_text)
        vfo = int(vfo * 1000)

        if self.rig_control:
            self.rig_control.set_vfo(vfo)
            return

        band = getband(str(vfo))
        self.set_band_indicator(band)
        self.radio_state["vfoa"] = vfo
        self.radio_state["band"] = band
        self.contact["Band"] = get_logged_band(str(vfo))
        self.set_window_title()
        self.clearinputs()

        cmd = {}
        cmd["cmd"] = "RADIO_STATE"
        cmd["band"] = band
        cmd["vfoa"] = vfo
        if self.bandmap_window:
            self.bandmap_window.msg_from_main(cmd)

    def change_mode(self, mode: str, intended_freq=None) -> None:
        """
        Change mode to given mode.
        Send the new mode to the rig control.
        Set the band indicator.
        Set the window title.
        Clear the inputs.
        Read the CW macros.

        Parameters
        ----------
        mode : str
        Mode to change to.

        Returns
        -------
        None
        """
        if mode in ("CW", "CW-U", "CW-L", "CWR"):
            if self.rig_control and self.rig_control.online:
                self.rig_control.set_mode(self.rig_control.last_cw_mode)
                if self.pref.get("cwtype") == 3 and self.rig_control is not None:
                    if self.rig_control.interface == "flrig":
                        self.cwspeed_spinbox_changed()
                        self.rig_control.cat.set_flrig_cw_send(True)
            else:
                self.setmode("CW")
                self.radio_state["mode"] = "CW"
                band = getband(str(self.radio_state.get("vfoa", "0.0")))
                self.set_band_indicator(band)
            self.set_window_title()
            self.clearinputs()
            self.read_macros()
            return
        if mode in (
            "DIGI-U",
            "DIGI-L",
            "RTTY",
            "RTTY-R",
            "LSB-D",
            "USB-D",
            "AM-D",
            "FM-D",
        ):
            if self.rig_control and self.rig_control.online:
                self.rig_control.set_mode(self.rig_control.last_data_mode)
            else:
                self.radio_state["mode"] = "RTTY"
            self.setmode("RTTY")
            band = getband(str(self.radio_state.get("vfoa", "0.0")))
            self.set_band_indicator(band)
            self.set_window_title()
            self.clearinputs()
            self.read_macros()
            return
        if mode == "SSB":
            if intended_freq:
                freq = intended_freq
            else:
                freq = int(self.radio_state.get("vfoa", 0))

            if freq > 10000000:
                self.radio_state["mode"] = "USB"
            else:
                self.radio_state["mode"] = "LSB"

            if self.rig_control and self.rig_control.online:
                self.rig_control.set_mode(self.radio_state.get("mode"))
            else:
                self.setmode("SSB")
                band = getband(str(self.radio_state.get("vfoa", "0.0")))
                self.set_band_indicator(band)
            self.set_window_title()
            self.clearinputs()
            self.read_macros()

    def check_callsign(self, callsign) -> None:
        """
        Check callsign as it's being entered in the big_cty index.
        Get DX entity, CQ, ITU and continent.
        Geographic information. Distance and Heading.

        Parameters
        ----------
        callsign : str
        Callsign to check.

        Returns
        -------
        None
        """

        result = self.cty_lookup(callsign)
        debug_result = f"{result}"
        logger.debug("%s", debug_result)
        if result:
            for a in result.items():
                entity = a[1].get("entity", "")
                cq = a[1].get("cq", "")
                itu = a[1].get("itu", "")
                continent = a[1].get("continent")
                lat = float(a[1].get("lat", "0.0"))
                lon = float(a[1].get("long", "0.0"))
                lon = lon * -1  # cty.dat file inverts longitudes
                primary_pfx = a[1].get("primary_pfx", "")
                heading = bearing_with_latlon(self.station.get("GridSquare"), lat, lon)
                kilometers = distance_with_latlon(
                    self.station.get("GridSquare"), lat, lon
                )
                self.heading_distance.setText(
                    f"Regional Hdg {heading}° LP {reciprocol(heading)}° / "
                    f"distance {int(kilometers*0.621371)}mi {kilometers}km"
                )
                self.contact["CountryPrefix"] = primary_pfx
                self.contact["ZN"] = int(cq)
                if self.contest:
                    if self.contest.name in ("IARU HF", "LZ DX"):
                        self.contact["ZN"] = int(itu)
                self.contact["Continent"] = continent
                self.dx_entity.setText(
                    f"{primary_pfx}: {continent}/{entity} cq:{cq} itu:{itu}"
                )
                if len(callsign) > 2:
                    if self.contest:
                        if (
                            "CQ WW" not in self.contest.name
                            and "IARU HF" not in self.contest.name
                        ):
                            self.contest.prefill(self)

    def check_dupe(self, call: str) -> bool:
        """Checks if a callsign is a dupe on current band/mode."""
        if self.contest is None:
            self.show_message_box("You have no contest loaded.")
            return False
        self.contest.predupe(self)
        band = float(get_logged_band(str(self.radio_state.get("vfoa", 0.0))))
        mode = self.radio_state.get("mode", "")
        debugline = (
            f"Call: {call} Band: {band} Mode: {mode} Dupetype: {self.contest.dupe_type}"
        )
        logger.debug("%s", debugline)
        if self.contest.dupe_type == 1:
            result = self.database.check_dupe(call)
        if self.contest.dupe_type == 2:
            result = self.database.check_dupe_on_band(call, band)
        if self.contest.dupe_type == 3:
            result = self.database.check_dupe_on_band_mode(call, band, mode)
        if self.contest.dupe_type == 4:
            result = {"isdupe": False}
        debugline = f"{result}"
        logger.debug("%s", debugline)
        return result.get("isdupe", False)

    def setmode(self, mode: str) -> None:
        """Call when the mode changes."""
        if mode in ("CW", "CW-U", "CW-L", "CWR"):
            if self.current_mode != "CW":
                self.current_mode = "CW"
                self.sent.setText("599")
                self.receive.setText("599")
                self.read_macros()
                if self.contest:
                    if self.contest.name == "ICWC Medium Speed Test":
                        self.contest.prefill(self)
            return
        if mode == "SSB":
            if self.current_mode != "SSB":
                self.current_mode = "SSB"
                self.sent.setText("59")
                self.receive.setText("59")
                self.read_macros()
            return
        if mode in ("RTTY", "DIGI-U", "DIGI-L"):
            if self.current_mode != "RTTY":
                self.current_mode = "RTTY"
                self.sent.setText("599")
                self.receive.setText("599")
                self.read_macros()

    def get_opon(self) -> None:
        """
        Ctrl+O Open the OPON dialog.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.opon_dialog = OpOn(fsutils.APP_DATA_PATH)

        if self.current_palette:
            self.opon_dialog.setPalette(self.current_palette)

        self.opon_dialog.accepted.connect(self.new_op)
        self.opon_dialog.open()

    def new_op(self) -> None:
        """
        Called when the user clicks the OK button on the OPON dialog.
        Create the new directory and copy the phonetic files.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if self.opon_dialog.NewOperator.text():
            self.current_op = self.opon_dialog.NewOperator.text().upper()
            self.voice_process.current_op = self.current_op
            if self.bandmap_window:
                self.bandmap_window.callsignField.setText(self.current_op)
        self.opon_dialog.close()
        logger.debug("New Op: %s", self.current_op)
        self.make_op_dir()
        self.set_window_title()

    def make_op_dir(self) -> None:
        """
        Create OP directory if it does not exist.
        Copy the phonetic files to the new directory.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if self.current_op:
            op_path = fsutils.USER_DATA_PATH / self.current_op
            logger.debug("op_path: %s", str(op_path))
            if op_path.is_dir() is False:
                logger.debug("Creating Op Directory: %s", str(op_path))
                os.mkdir(str(op_path))
            if op_path.is_dir():
                source_path = fsutils.APP_DATA_PATH / "phonetics"
                logger.debug("source_path: %s", str(source_path))
                for child in source_path.iterdir():
                    destination_file = op_path / child.name
                    if destination_file.is_file() is False:
                        logger.debug("Destination: %s", str(destination_file))
                        destination_file.write_bytes(child.read_bytes())

    def poll_radio(self, the_dict):
        """
        Gets called by thread worker radio.py
        Passing in a dictionary object with the
        vfo freq, mode, bandwidth, and online state of the radio.
        """
        logger.debug(f"{the_dict=}")
        self.set_radio_icon(0)
        info_dirty = False
        vfo = the_dict.get("vfoa", "")
        mode = the_dict.get("mode", "")
        bw = the_dict.get("bw", "")
        online = the_dict.get("online", False)

        if online is False:
            self.set_radio_icon(1)
        else:
            self.set_radio_icon(2)

        if vfo == "":
            return
        if self.radio_state.get("vfoa") != vfo:
            info_dirty = True
            self.radio_state["vfoa"] = vfo
        band = getband(str(vfo))
        self.radio_state["band"] = band
        self.contact["Band"] = get_logged_band(str(vfo))
        self.set_band_indicator(band)

        if self.rig_control and self.rig_control.online:
            self.rig_control.get_modes()

        if self.radio_state.get("mode") != mode:
            info_dirty = True
            self.radio_state["mode"] = mode

        if self.radio_state.get("bw") != bw:
            info_dirty = True
            self.radio_state["bw"] = bw

        if mode in ("CW", "CW-U", "CW-L", "CWR"):
            self.setmode(mode)
        if mode == "LSB" or mode == "USB":
            self.setmode("SSB")
        if mode in (
            "RTTY",
            "RTTY-R",
            "LSB-D",
            "USB-D",
            "AM-D",
            "FM-D",
            "DIGI-U",
            "DIGI-L",
            "RTTYR",
            "PKTLSB",
            "PKTUSB",
        ):
            self.setmode("RTTY")

        cmd = {}
        cmd["cmd"] = "RADIO_STATE"
        cmd["band"] = band
        cmd["vfoa"] = vfo
        cmd["mode"] = mode
        cmd["bw"] = bw
        if self.bandmap_window:
            self.bandmap_window.msg_from_main(cmd)
        if info_dirty:
            try:
                logger.debug("VFO: %s  MODE: %s BW: %s", vfo, mode, bw)
                self.set_window_title()
                cmd = {}
                cmd["cmd"] = "RADIO_STATE"
                cmd["band"] = band
                cmd["vfoa"] = vfo
                cmd["mode"] = mode
                cmd["bw"] = bw
                if self.bandmap_window:
                    self.bandmap_window.msg_from_main(cmd)
                if self.n1mm:
                    self.n1mm.radio_info["Freq"] = vfo[:-1]
                    self.n1mm.radio_info["TXFreq"] = vfo[:-1]
                    self.n1mm.radio_info["Mode"] = mode
                    self.n1mm.radio_info["OpCall"] = self.current_op
                    self.n1mm.radio_info["IsRunning"] = str(
                        self.pref.get("run_state", False)
                    )
                    if self.n1mm.send_radio_packets:
                        self.n1mm.send_radio()
            except TypeError as err:
                logger.debug(f"{err=} {vfo=} {the_dict=}")

    def get_macro_filename(self):
        """"""
        # Have not1mm check in USER_DATA_PATH for the existence of a folder with the contests name.
        # If it exists, check to see if a cw/ssb/rtty macro files exists within it and load them before
        # falling back to the default ones.
        # If user selects menu option to edit the current macro file, make the previous checks, if the
        # specific one does not exist, copy the default to the contest directory and edit that copy.
        if self.radio_state.get("mode") in ("CW", "CW-L", "CW-R", "CWR"):
            macro_file = "cwmacros.txt"
        elif self.radio_state.get("mode") in (
            "RTTY",
            "RTTY-R",
            "LSB-D",
            "USB-D",
            "AM-D",
            "FM-D",
            "DIGI-U",
            "DIGI-L",
            "RTTYR",
            "PKTLSB",
            "PKTUSB",
            "FSK",
        ):
            macro_file = "rttymacros.txt"
        else:
            macro_file = "ssbmacros.txt"

        try:
            if not (fsutils.USER_DATA_PATH / self.contest.name).exists():
                os.mkdir(fsutils.USER_DATA_PATH / self.contest.name)
        except AttributeError:
            return ""

        if not (fsutils.USER_DATA_PATH / macro_file).exists():
            try:
                copyfile(
                    fsutils.APP_DATA_PATH / macro_file,
                    fsutils.USER_DATA_PATH / macro_file,
                )
            except IOError as err:
                logger.critical(f"Error {err} copying macro file.")

        if not (fsutils.USER_DATA_PATH / self.contest.name / macro_file).exists():
            try:
                copyfile(
                    fsutils.APP_DATA_PATH / macro_file,
                    fsutils.USER_DATA_PATH / self.contest.name / macro_file,
                )
            except IOError as err:
                logger.critical(f"Error {err} copying macro file.")

        return fsutils.USER_DATA_PATH / self.contest.name / macro_file

    def edit_macros(self) -> None:
        """
        Calls the default text editor to edit the CW macro file.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        macro_file = self.get_macro_filename()

        try:
            fsutils.openFileWithOS(macro_file)
        except FileNotFoundError | PermissionError | OSError as err:
            logger.critical(f"Could not open file {macro_file} {err}")
        self.read_macros()

    def read_macros(self) -> None:
        """
        Reads in the CW macros, firsts it checks to see if the file exists. If it does not,
        and this has been packaged with pyinstaller it will copy the default file from the
        temp directory this is running from... In theory.
        """

        macro_file = self.get_macro_filename()

        try:
            with open(macro_file, "r", encoding="utf-8") as file_descriptor:
                for line in file_descriptor:
                    mode, fkey, buttonname, cwtext = line.split("|")
                    if mode.strip().upper() == "R" and self.pref.get("run_state"):
                        self.fkeys[fkey.strip()] = (buttonname.strip(), cwtext.strip())
                    if mode.strip().upper() != "R" and not self.pref.get("run_state"):
                        self.fkeys[fkey.strip()] = (buttonname.strip(), cwtext.strip())
        except (IOError, ValueError) as err:
            logger.info("read_cw_macros: %s", err)
        keys = self.fkeys.keys()
        if "F1" in keys:
            self.F1.setText(f"F1: {self.fkeys['F1'][0]}")
            self.F1.setToolTip(self.fkeys["F1"][1])
        if "F2" in keys:
            self.F2.setText(f"F2: {self.fkeys['F2'][0]}")
            self.F2.setToolTip(self.fkeys["F2"][1])
        if "F3" in keys:
            self.F3.setText(f"F3: {self.fkeys['F3'][0]}")
            self.F3.setToolTip(self.fkeys["F3"][1])
        if "F4" in keys:
            self.F4.setText(f"F4: {self.fkeys['F4'][0]}")
            self.F4.setToolTip(self.fkeys["F4"][1])
        if "F5" in keys:
            self.F5.setText(f"F5: {self.fkeys['F5'][0]}")
            self.F5.setToolTip(self.fkeys["F5"][1])
        if "F6" in keys:
            self.F6.setText(f"F6: {self.fkeys['F6'][0]}")
            self.F6.setToolTip(self.fkeys["F6"][1])
        if "F7" in keys:
            self.F7.setText(f"F7: {self.fkeys['F7'][0]}")
            self.F7.setToolTip(self.fkeys["F7"][1])
        if "F8" in keys:
            self.F8.setText(f"F8: {self.fkeys['F8'][0]}")
            self.F8.setToolTip(self.fkeys["F8"][1])
        if "F9" in keys:
            self.F9.setText(f"F9: {self.fkeys['F9'][0]}")
            self.F9.setToolTip(self.fkeys["F9"][1])
        if "F10" in keys:
            self.F10.setText(f"F10: {self.fkeys['F10'][0]}")
            self.F10.setToolTip(self.fkeys["F10"][1])
        if "F11" in keys:
            self.F11.setText(f"F11: {self.fkeys['F11'][0]}")
            self.F11.setToolTip(self.fkeys["F11"][1])
        if "F12" in keys:
            self.F12.setText(f"F12: {self.fkeys['F12'][0]}")
            self.F12.setToolTip(self.fkeys["F12"][1])

    def generate_adif(self) -> None:
        """
        Calls the contest ADIF file generator.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        # https://www.adif.org/315/ADIF_315.htm
        logger.debug("******ADIF*****")
        self.contest.adif(self)

    def generate_cabrillo(self, file_encoding: str) -> None:
        """
        Calls the contest Cabrillo file generator. Maybe.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        logger.debug("******Cabrillo*****")
        self.contest.cabrillo(self, file_encoding)


def load_fonts_from_dir(directory: str) -> set:
    """
    Well it loads fonts from a directory...

    Parameters
    ----------
    directory : str
    The directory to load fonts from.

    Returns
    -------
    set
    A set of font families installed in the directory.
    """
    font_families = set()
    for _fi in QDir(directory).entryInfoList(["*.ttf", "*.woff", "*.woff2"]):
        _id = QFontDatabase.addApplicationFont(_fi.absoluteFilePath())
        font_families |= set(QFontDatabase.applicationFontFamilies(_id))
    return font_families


def install_icons() -> None:
    """Install icons"""

    if sys.platform == "linux":
        os.system(
            "xdg-icon-resource install --size 32 --context apps --mode user "
            f"{fsutils.APP_DATA_PATH}/k6gte.not1mm-32.png k6gte-not1mm"
        )
        os.system(
            "xdg-icon-resource install --size 64 --context apps --mode user "
            f"{fsutils.APP_DATA_PATH}/k6gte.not1mm-64.png k6gte-not1mm"
        )
        os.system(
            "xdg-icon-resource install --size 128 --context apps --mode user "
            f"{fsutils.APP_DATA_PATH}/k6gte.not1mm-128.png k6gte-not1mm"
        )
        os.system(
            f"xdg-desktop-menu install {fsutils.APP_DATA_PATH}/k6gte-not1mm.desktop"
        )


def doimp(modname) -> object:
    """
    Imports a module.

    Parameters
    ----------
    modname : str
    The name of the module to import.

    Returns
    -------
    object
    The module object.
    """

    logger.debug("doimp: %s", modname)
    return importlib.import_module(f"not1mm.plugins.{modname}")


def run() -> None:
    """
    Main Entry
    """
    splash.show()
    # app.processEvents()
    splash.showMessage(
        "Starting Up",
        alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        color=QColor(255, 255, 0),
    )
    QCoreApplication.processEvents()

    families = load_fonts_from_dir(os.fspath(fsutils.APP_DATA_PATH))
    logger.info(f"font families {families}")
    window = MainWindow(splash)
    window.callsign.setFocus()
    splash.finish(window)
    window.show()
    logger.debug(
        f"Resolved OS file system paths: MODULE_PATH {fsutils.MODULE_PATH}, USER_DATA_PATH {fsutils.USER_DATA_PATH}, CONFIG_PATH {fsutils.CONFIG_PATH}"
    )
    install_icons()
    sys.exit(app.exec())


DEBUG_ENABLED = False
if Path("./debug").exists():
    DEBUG_ENABLED = True

logger = logging.getLogger("__main__")

logging.basicConfig(
    level=logging.DEBUG if DEBUG_ENABLED else logging.CRITICAL,
    format="[%(asctime)s] %(levelname)s %(name)s - %(funcName)s Line %(lineno)d: %(message)s",
    handlers=[
        RotatingFileHandler(fsutils.LOG_FILE, maxBytes=10490000, backupCount=20),
        logging.StreamHandler(),
    ],
)
logging.getLogger("PyQt6.uic.uiparser").setLevel("INFO")
logging.getLogger("PyQt6.uic.properties").setLevel("INFO")

app = QtWidgets.QApplication(sys.argv)

pixmap = QPixmap(f"{os.fspath(fsutils.APP_DATA_PATH)}/splash.png")
splash = QSplashScreen(pixmap)

if __name__ == "__main__":
    run()
