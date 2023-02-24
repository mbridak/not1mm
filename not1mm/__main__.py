#!/usr/bin/env python3
"""
NOT1MM Logger
"""
# pylint: disable=unused-import, c-extension-no-member

import importlib
import logging
import os
import pkgutil
import re
import sqlite3
import sys
from datetime import datetime
from json import dumps, loads
from pathlib import Path
from shutil import copyfile
from xmlrpc.client import Error, ServerProxy

import psutil
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import (
    QDir,
    QPoint,
    QSize,
    QRect,
    Qt,
)  # pylint: disable=no-name-in-module
from PyQt5.QtGui import QFontDatabase  # pylint: disable=no-name-in-module

try:
    from not1mm.lib.cat_interface import CAT
    from not1mm.lib.cwinterface import CW
    from not1mm.lib.ham_utility import *
    from not1mm.lib.lookup import QRZlookup
    from not1mm.lib.version import __version__
except ModuleNotFoundError:
    from lib.cat_interface import CAT
    from lib.cwinterface import CW
    from lib.ham_utility import *
    from lib.lookup import QRZlookup
    from lib.version import __version__


loader = pkgutil.get_loader("not1mm")
WORKING_PATH = os.path.dirname(loader.get_filename())


if "XDG_DATA_HOME" in os.environ:
    DATA_PATH = os.environ.get("XDG_DATA_HOME")
else:
    DATA_PATH = str(Path.home() / ".local" / "share")
DATA_PATH += "/not1mm"
try:
    os.mkdir(DATA_PATH)
except FileExistsError:
    ...

if "XDG_CONFIG_HOME" in os.environ:
    CONFIG_PATH = os.environ.get("XDG_CONFIG_HOME")
else:
    CONFIG_PATH = str(Path.home() / ".config")
CONFIG_PATH += "/not1mm"
try:
    os.mkdir(CONFIG_PATH)
except FileExistsError:
    ...

CTYFILE = {}

with open(WORKING_PATH + "/data/cty.json", "rt", encoding="utf-8") as fd:
    CTYFILE = loads(fd.read())

DARK_STYLESHEET = ""

with open(WORKING_PATH + "/data/Combinear.qss") as stylefile:
    DARK_STYLESHEET = stylefile.read()


def cty_lookup(callsign: str):
    callsign = callsign.upper()
    for x in reversed(range(len(callsign))):
        searchitem = callsign[: x + 1]
        result = {key: val for key, val in CTYFILE.items() if key == searchitem}
        if not result:
            continue
        if result.get(searchitem).get("exact_match"):
            if searchitem == callsign:
                return result
            else:
                continue
        return result


class MainWindow(QtWidgets.QMainWindow):
    """
    The main window
    """

    pref_ref = {
        "useqrz": False,
        "lookupusername": "username",
        "lookuppassword": "password",
        "gridsquare": "",
        "run_state": True,
        "dark_mode": False,
        "command_buttons": True,
        "cw_macros": True,
        "bands_modes": True,
        "window_height": 200,
        "window_width": 600,
        "window_x": 120,
        "window_y": 120,
        "callsign": "",
        "name": "",
        "address1": "",
        "address2": "",
        "city": "",
        "state": "",
        "zip": "",
        "country": "",
        "cqzone": "",
        "ituzone": "",
        "license": "",
        "latitude": "",
        "longitude": "",
        "stationtxrx": "",
        "power": "",
        "antenna": "",
        "antheight": "",
        "asl": "",
        "section": "",
        "roverqth": "",
        "club": "",
        "email": "",
    }
    appstarted = False
    contest = None
    pref = None
    current_op = ""
    current_mode = ""
    current_band = ""
    look_up = None
    run_state = False
    fkeys = {}

    def __init__(self, *args, **kwargs):
        logger.info("MainWindow: __init__")
        super().__init__(*args, **kwargs)
        data_path = WORKING_PATH + "/data/main.ui"
        uic.loadUi(data_path, self)

        self.next_field = self.other
        self.field4.hide()
        self.actionCW_Macros.triggered.connect(self.cw_macros_stateChanged)
        self.actionCommand_Buttons.triggered.connect(self.command_buttons_stateChange)
        self.actionMode_and_Bands.triggered.connect(self.show_band_mode_stateChange)
        self.actionDark_Mode.triggered.connect(self.dark_mode_stateChange)
        self.actionPreferences.triggered.connect(self.preference_selected)
        self.radioButton_run.clicked.connect(self.run_sp_buttons_clicked)
        self.radioButton_sp.clicked.connect(self.run_sp_buttons_clicked)
        self.score.setText("0")
        self.callsign.textEdited.connect(self.callsign_changed)
        self.sent.setText("59")
        self.receive.setText("59")
        icon_path = WORKING_PATH + "/data/"
        self.greendot = QtGui.QPixmap(icon_path + "greendot.png")
        self.reddot = QtGui.QPixmap(icon_path + "reddot.png")
        self.leftdot.setPixmap(self.greendot)
        self.rightdot.setPixmap(self.reddot)

        self.F1.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.F1.customContextMenuRequested.connect(self.edit_F1)
        self.F1.clicked.connect(self.sendf1)
        self.F2.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.F2.customContextMenuRequested.connect(self.edit_F2)
        self.F2.clicked.connect(self.sendf2)
        self.F3.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.F3.customContextMenuRequested.connect(self.edit_F3)
        self.F3.clicked.connect(self.sendf3)
        self.F4.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.F4.customContextMenuRequested.connect(self.edit_F4)
        self.F4.clicked.connect(self.sendf4)
        self.F5.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.F5.customContextMenuRequested.connect(self.edit_F5)
        self.F5.clicked.connect(self.sendf5)
        self.F6.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.F6.customContextMenuRequested.connect(self.edit_F6)
        self.F6.clicked.connect(self.sendf6)
        self.F7.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.F7.customContextMenuRequested.connect(self.edit_F7)
        self.F7.clicked.connect(self.sendf7)
        self.F8.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.F8.customContextMenuRequested.connect(self.edit_F8)
        self.F8.clicked.connect(self.sendf8)
        self.F9.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.F9.customContextMenuRequested.connect(self.edit_F9)
        self.F9.clicked.connect(self.sendf9)
        self.F10.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.F10.customContextMenuRequested.connect(self.edit_F10)
        self.F10.clicked.connect(self.sendf10)
        self.F11.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.F11.customContextMenuRequested.connect(self.edit_F11)
        self.F11.clicked.connect(self.sendf11)
        self.F12.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.F12.customContextMenuRequested.connect(self.edit_F12)
        self.F12.clicked.connect(self.sendf12)
        self.select_contest()
        self.readpreferences()
        self.read_cw_macros()
        self.rig_control = CAT("rigctld", "localhost", 4532)

    def closeEvent(self, e):
        # Write window size and position to config file
        self.pref["window_width"] = self.size().width()
        self.pref["window_height"] = self.size().height()
        self.pref["window_x"] = self.pos().x()
        self.pref["window_y"] = self.pos().y()
        self.write_preference()

    def preference_selected(self):
        logger.debug("Preference selected")
        self.settings_dialog = EditSettings()
        self.settings_dialog.accepted.connect(self.save_settings)
        if self.pref.get("dark_mode"):
            self.settings_dialog.setStyleSheet(DARK_STYLESHEET)
        self.settings_dialog.Call.setText(self.pref.get("callsign", ""))
        self.settings_dialog.Name.setText(self.pref.get("name", ""))
        self.settings_dialog.Address1.setText(self.pref.get("address1", ""))
        self.settings_dialog.Address2.setText(self.pref.get("address2", ""))
        self.settings_dialog.City.setText(self.pref.get("city", ""))
        self.settings_dialog.State.setText(self.pref.get("state", ""))
        self.settings_dialog.Zip.setText(self.pref.get("zip", ""))
        self.settings_dialog.Country.setText(self.pref.get("country", ""))
        self.settings_dialog.GridSquare.setText(self.pref.get("gridsquare", ""))
        self.settings_dialog.CQZone.setText(self.pref.get("cqzone", ""))
        self.settings_dialog.ITUZone.setText(self.pref.get("ituzone", ""))
        self.settings_dialog.License.setText(self.pref.get("license", ""))
        self.settings_dialog.Latitude.setText(self.pref.get("latitude", ""))
        self.settings_dialog.Longitude.setText(self.pref.get("longitude", ""))
        self.settings_dialog.StationTXRX.setText(self.pref.get("stationtxrx", ""))
        self.settings_dialog.Power.setText(self.pref.get("power", ""))
        self.settings_dialog.Antenna.setText(self.pref.get("antenna", ""))
        self.settings_dialog.AntHeight.setText(self.pref.get("antheight", ""))
        self.settings_dialog.ASL.setText(self.pref.get("asl", ""))
        self.settings_dialog.ARRLSection.setText(self.pref.get("section", ""))
        self.settings_dialog.RoverQTH.setText(self.pref.get("roverqth", ""))
        self.settings_dialog.Club.setText(self.pref.get("club", ""))
        self.settings_dialog.Email.setText(self.pref.get("email", ""))
        self.settings_dialog.open()

    def save_settings(self):
        # self.settings_dialog.object.text():
        cs = self.settings_dialog.Call.text()
        self.pref["callsign"] = cs.upper()
        self.pref["name"] = self.settings_dialog.Name.text()
        self.pref["address1"] = self.settings_dialog.Address1.text()
        self.pref["address2"] = self.settings_dialog.Address2.text()
        self.pref["city"] = self.settings_dialog.City.text()
        self.pref["state"] = self.settings_dialog.State.text()
        self.pref["zip"] = self.settings_dialog.Zip.text()
        self.pref["country"] = self.settings_dialog.Country.text()
        self.pref["gridsquare"] = self.settings_dialog.GridSquare.text()
        self.pref["cqzone"] = self.settings_dialog.CQZone.text()
        self.pref["ituzone"] = self.settings_dialog.ITUZone.text()
        self.pref["license"] = self.settings_dialog.License.text()
        self.pref["latitude"] = self.settings_dialog.Latitude.text()
        self.pref["longitude"] = self.settings_dialog.Longitude.text()
        self.pref["stationtxrx"] = self.settings_dialog.StationTXRX.text()
        self.pref["power"] = self.settings_dialog.Power.text()
        self.pref["antenna"] = self.settings_dialog.Antenna.text()
        self.pref["antheight"] = self.settings_dialog.AntHeight.text()
        self.pref["asl"] = self.settings_dialog.ASL.text()
        self.pref["section"] = self.settings_dialog.ARRLSection.text()
        self.pref["roverqth"] = self.settings_dialog.RoverQTH.text()
        self.pref["club"] = self.settings_dialog.Club.text()
        self.pref["email"] = self.settings_dialog.Email.text()
        self.settings_dialog.close()
        self.write_preference()

    def select_contest(self):
        self.contest = doimp("arrl_field_day")
        logger.debug(f"Loaded Contest Name = {self.contest.name}")
        self.contest.interface(self)
        ...

    def edit_macro(self, function_key):
        self.edit_macro_dialog = EditMacro(function_key)
        self.edit_macro_dialog.accepted.connect(self.edited_macro)
        if self.pref.get("dark_mode"):
            self.edit_macro_dialog.setStyleSheet(DARK_STYLESHEET)
        self.edit_macro_dialog.open()

    def edited_macro(self):
        self.edit_macro_dialog.function_key.setText(
            self.edit_macro_dialog.macro_label.text()
        )
        self.edit_macro_dialog.function_key.setToolTip(
            self.edit_macro_dialog.the_macro.text()
        )
        self.edit_macro_dialog.close()
        # logger.debug(f"{self.current_op}")

    def edit_F1(self):
        logger.debug("F1 Right Clicked.")
        self.edit_macro(self.F1)

    def edit_F2(self):
        logger.debug("F2 Right Clicked.")
        self.edit_macro(self.F2)

    def edit_F3(self):
        logger.debug("F3 Right Clicked.")
        self.edit_macro(self.F3)

    def edit_F4(self):
        logger.debug("F4 Right Clicked.")
        self.edit_macro(self.F4)

    def edit_F5(self):
        logger.debug("F5 Right Clicked.")
        self.edit_macro(self.F5)

    def edit_F6(self):
        logger.debug("F6 Right Clicked.")
        self.edit_macro(self.F6)

    def edit_F7(self):
        logger.debug("F7 Right Clicked.")
        self.edit_macro(self.F7)

    def edit_F8(self):
        logger.debug("F8 Right Clicked.")
        self.edit_macro(self.F8)

    def edit_F9(self):
        logger.debug("F9 Right Clicked.")
        self.edit_macro(self.F9)

    def edit_F10(self):
        logger.debug("F10 Right Clicked.")
        self.edit_macro(self.F10)

    def edit_F11(self):
        logger.debug("F11 Right Clicked.")
        self.edit_macro(self.F11)

    def edit_F12(self):
        logger.debug("F12 Right Clicked.")
        self.edit_macro(self.F12)

    def sendf1(self):
        logger.debug("F1 Clicked")

    def sendf2(self):
        logger.debug("F2 Clicked")

    def sendf3(self):
        logger.debug("F3 Clicked")

    def sendf4(self):
        logger.debug("F4 Clicked")

    def sendf5(self):
        logger.debug("F5 Clicked")

    def sendf6(self):
        logger.debug("F6 Clicked")

    def sendf7(self):
        logger.debug("F7 Clicked")

    def sendf8(self):
        logger.debug("F8 Clicked")

    def sendf9(self):
        logger.debug("F9 Clicked")

    def sendf10(self):
        logger.debug("F10 Clicked")

    def sendf11(self):
        logger.debug("F11 Clicked")

    def sendf12(self):
        logger.debug("F12 Clicked")

    def run_sp_buttons_clicked(self):
        self.pref["run_state"] = self.radioButton_run.isChecked()
        self.write_preference()
        self.read_cw_macros()

    def write_preference(self):
        """
        Write preferences to json file.
        """
        try:
            with open(
                CONFIG_PATH + "/not1mm.json", "wt", encoding="utf-8"
            ) as file_descriptor:
                file_descriptor.write(dumps(self.pref, indent=4))
                logger.info("writing: %s", self.pref)
        except IOError as exception:
            ...
            logger.critical("writepreferences: %s", exception)

    def readpreferences(self):
        """
        Restore preferences if they exist, otherwise create some sane defaults.
        """
        try:
            if os.path.exists(CONFIG_PATH + "/not1mm.json"):
                with open(
                    CONFIG_PATH + "/not1mm.json", "rt", encoding="utf-8"
                ) as file_descriptor:
                    self.pref = loads(file_descriptor.read())
                    logger.info("%s", self.pref)
            else:
                logger.info("No preference file. Writing preference.")
                with open(
                    CONFIG_PATH + "/not1mm.json", "wt", encoding="utf-8"
                ) as file_descriptor:
                    self.pref = self.pref_ref.copy()
                    file_descriptor.write(dumps(self.pref, indent=4))
                    logger.info("%s", self.pref)
        except IOError as exception:
            ...
            logger.critical("Error: %s", exception)
        if self.pref.get("useqrz"):
            self.look_up = QRZlookup(
                self.pref.get("lookupusername"),
                self.pref.get("lookuppassword"),
            )
        if self.pref.get("run_state"):
            self.radioButton_run.setChecked(True)
        else:
            self.radioButton_sp.setChecked(True)

        if self.pref.get("dark_mode"):
            self.actionDark_Mode.setChecked(True)
        else:
            self.actionDark_Mode.setChecked(False)

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

        self.dark_mode()
        self.show_command_buttons()
        self.show_CW_macros()
        self.show_band_mode()

    def dark_mode_stateChange(self):
        self.pref["dark_mode"] = self.actionDark_Mode.isChecked()
        self.write_preference()
        self.dark_mode()

    def dark_mode(self):
        if self.pref.get("dark_mode"):
            self.setStyleSheet(DARK_STYLESHEET)
        else:
            self.setStyleSheet("")

    def cw_macros_stateChanged(self):
        self.pref["cw_macros"] = self.actionCW_Macros.isChecked()
        self.write_preference()
        self.show_CW_macros()

    def show_CW_macros(self):
        if self.pref.get("cw_macros"):
            self.Button_Row1.show()
            self.Button_Row2.show()
        else:
            self.Button_Row1.hide()
            self.Button_Row2.hide()

    def command_buttons_stateChange(self):
        self.pref["command_buttons"] = self.actionCommand_Buttons.isChecked()
        self.write_preference()
        self.show_command_buttons()

    def show_command_buttons(self):
        if self.pref.get("command_buttons"):
            self.Command_Buttons.show()
        else:
            self.Command_Buttons.hide()

    def show_band_mode_stateChange(self):
        self.pref["bands_modes"] = self.actionMode_and_Bands.isChecked()
        self.write_preference()
        self.show_band_mode()

    def show_band_mode(self):
        if self.actionMode_and_Bands.isChecked():
            self.Band_Mode_Frame.show()
        else:
            self.Band_Mode_Frame.hide()

    def callsign_changed(self):
        text = self.callsign.text()
        text = text.upper()
        stripped_text = text.strip()
        self.callsign.setText(stripped_text)

        if text[-1:] == " ":
            if stripped_text == "CW":
                self.setmode("CW")
                self.callsign.setText("")
                return
            if stripped_text == "SSB":
                self.setmode("SSB")
                self.callsign.setText("")
                return
            if stripped_text == "OPON":
                self.get_opon()
                self.callsign.setText("")
                return
            self.check_callsign(text)
            self.check_callsign2(text)
            self.next_field.setFocus()

    def check_callsign(self, callsign):
        result = cty_lookup(callsign)

        print(result)
        for a in result.items():
            entity = a[1].get("entity")
            cq = a[1].get("cq")
            itu = a[1].get("itu")
            continent = a[1].get("continent")
            lat = float(a[1].get("lat"))
            lon = float(a[1].get("long"))
            lon = lon * -1  # cty.dat file inverts longitudes
            primary_pfx = a[1].get("primary_pfx")
            heading = bearing_with_latlon(self.pref.get("gridsquare"), lat, lon)
            kilometers = distance_with_latlon(self.pref.get("gridsquare"), lat, lon)
            self.heading_distance.setText(
                f"heading {heading}° / distance {int(kilometers*0.621371)}mi {kilometers}km"
            )
            self.dx_entity.setText(
                f"{primary_pfx}: {continent}/{entity} cq:{cq} itu:{itu}"
            )

    def check_callsign2(self, callsign):  # fixme
        if hasattr(self.look_up, "session"):
            if self.look_up.session:
                response = self.look_up.lookup(callsign)
                logger.debug(f"The Response: {response}\n")
                if response:
                    theirgrid = response.get("grid")
                    theircountry = response.get("country")
                    if self.pref.get("gridsquare"):
                        heading = bearing(self.pref.get("gridsquare"), theirgrid)
                        kilometers = distance(self.pref.get("gridsquare"), theirgrid)
                        self.heading_distance.setText(
                            f"heading {heading}° / distance {int(kilometers*0.621371)}mi {kilometers}km {theirgrid}"
                        )
                    # self.dx_entity.setText(f"{theircountry}")
                # else:
                # self.heading_distance.setText("Lookup failed.")
            ...

    def setmode(self, mode: str) -> None:
        if mode == "CW":
            self.mode.setText("CW")
            self.sent.setText("599")
            self.receive.setText("599")
            return
        if mode == "SSB":
            self.mode.setText("SSB")
            self.sent.setText("59")
            self.receive.setText("59")

    def get_opon(self):
        self.opon_dialog = OpOn()
        self.opon_dialog.accepted.connect(self.new_op)
        self.opon_dialog.open()

    def new_op(self):
        if self.opon_dialog.NewOperator.text():
            self.current_op = self.opon_dialog.NewOperator.text()

        self.opon_dialog.close()
        logger.debug(f"New Op: {self.current_op}")

    def poll_radio(self):
        if self.rig_control.online:
            vfo = self.rig_control.get_vfo()
            mode = self.rig_control.get_mode()
            logger.debug(f"VFO: {vfo}  MODE: {mode}")

    def read_cw_macros(self) -> None:
        """
        Reads in the CW macros, firsts it checks to see if the file exists. If it does not,
        and this has been packaged with pyinstaller it will copy the default file from the
        temp directory this is running from... In theory.
        """

        if not Path(DATA_PATH + "/cwmacros.txt").exists():
            logger.debug("read_cw_macros: copying default macro file.")
            copyfile(WORKING_PATH + "/data/cwmacros.txt", DATA_PATH + "/cwmacros.txt")
        with open(
            DATA_PATH + "/cwmacros.txt", "r", encoding="utf-8"
        ) as file_descriptor:
            for line in file_descriptor:
                try:
                    mode, fkey, buttonname, cwtext = line.split("|")
                    if mode.strip().upper() == "R" and self.pref.get("run_state"):
                        self.fkeys[fkey.strip()] = (buttonname.strip(), cwtext.strip())
                    if mode.strip().upper() != "R" and not self.pref.get("run_state"):
                        self.fkeys[fkey.strip()] = (buttonname.strip(), cwtext.strip())
                except ValueError as err:
                    ...
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


class EditSettings(QtWidgets.QDialog):
    """Edit Settings"""

    def __init__(self):
        super().__init__(None)
        uic.loadUi(WORKING_PATH + "/data/settings.ui", self)
        self.buttonBox.clicked.connect(self.store)
        self.GridSquare.textEdited.connect(self.gridchanged)

    def store(self):
        """dialog magic"""
        ...
        # self.accept()

    def gridchanged(self):
        lat, lon = gridtolatlon(self.GridSquare.text())
        self.Latitude.setText(str(round(lat, 4)))
        self.Longitude.setText(str(round(lon, 4)))


class EditMacro(QtWidgets.QDialog):
    """Change the current operator"""

    def __init__(self, function_key):
        self.function_key = function_key
        parent = None
        super().__init__(parent)
        uic.loadUi(WORKING_PATH + "/data/editmacro.ui", self)
        self.buttonBox.clicked.connect(self.store)
        self.macro_label.setText(function_key.text())
        self.the_macro.setText(function_key.toolTip())

    def store(self):
        """dialog magic"""
        ...
        # self.accept()


class OpOn(QtWidgets.QDialog):
    """Change the current operator"""

    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(WORKING_PATH + "/data/opon.ui", self)
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""
        ...
        # self.accept()


def load_fonts_from_dir(directory: str) -> set:
    """
    Well it loads fonts from a directory...
    """
    font_families = set()
    for _fi in QDir(directory).entryInfoList(["*.ttf", "*.woff", "*.woff2"]):
        _id = QFontDatabase.addApplicationFont(_fi.absoluteFilePath())
        font_families |= set(QFontDatabase.applicationFontFamilies(_id))
    return font_families


def install_icons():
    os.system(
        "xdg-icon-resource install --size 32 --context apps --mode user "
        f"{WORKING_PATH}/data/k6gte.not1mm-32.png k6gte-not1mm"
    )
    os.system(
        "xdg-icon-resource install --size 64 --context apps --mode user "
        f"{WORKING_PATH}/data/k6gte.not1mm-64.png k6gte-not1mm"
    )
    os.system(
        "xdg-icon-resource install --size 128 --context apps --mode user "
        f"{WORKING_PATH}/data/k6gte.not1mm-128.png k6gte-not1mm"
    )
    os.system(f"xdg-desktop-menu install {WORKING_PATH}/data/k6gte-not1mm.desktop")


def doimp(modname):
    return importlib.import_module(f"not1mm.plugins.{modname}")


def run():
    """
    Main Entry
    """

    install_icons()
    timer.start(1000)

    sys.exit(app.exec())


logger = logging.getLogger("__name__")
handler = logging.StreamHandler()
formatter = logging.Formatter(
    datefmt="%H:%M:%S",
    fmt="[%(asctime)s] %(levelname)s %(module)s - %(funcName)s Line %(lineno)d:\n%(message)s",
)
handler.setFormatter(formatter)
logger.addHandler(handler)

if Path("./debug").exists():
    # if True:
    logger.setLevel(logging.DEBUG)
    logger.debug("debugging on")
else:
    logger.setLevel(logging.WARNING)
    logger.warning("debugging off")

app = QtWidgets.QApplication(sys.argv)
app.setStyle("Fusion")
font_path = WORKING_PATH + "/data"
families = load_fonts_from_dir(os.fspath(font_path))
logger.info(families)
window = MainWindow()
height = window.pref.get("window_height")
width = window.pref.get("window_width")
x = window.pref.get("window_x")
y = window.pref.get("window_y")
window.setGeometry(x, y, width, height)
window.setWindowTitle(f"Not1MM v{__version__}")
window.show()
timer = QtCore.QTimer()
timer.timeout.connect(window.poll_radio)


if __name__ == "__main__":
    run()
