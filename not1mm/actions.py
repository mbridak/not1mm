"""
Functions called from key events

Parameters: self (MainWindow)

All functions from this file (except when prefixed with _) appear in the Action
dropdown list, in the order they are defined in this file.

The function doc string is used as action description in the Edit Keys dialog.
"""

# pylint: disable=invalid-name

from not1mm.lib.edit_keys import EditKeys

default_key_bindings = {
    "Ctrl+R": "TOGGLE_RUN",
    "Ctrl+L": "LOG_NOW",
    "Ctrl+=": "LOG_NOW",
    "Ctrl+Shift+K": "TOGGLE_CW_INPUT",
    "Up": "PREV_SPOT",
    "Down": "NEXT_SPOT",
    "Ctrl+G": "FIND_DX",
    "Ctrl+M": "MARK_SPOT",
    "Ctrl+Q": "JUMP_TO_CQ",
    "Ctrl+S": "SPOT_DX",
    "Ctrl+,": "VFO_DOWN",
    "Ctrl+.": "VFO_UP",
    "PgDown": "CW_SPEED_DOWN",
    "PgUp": "CW_SPEED_UP",
    "Ctrl+W": "CLEAR_INPUTS",
    "Esc": "STOP_ALL",
    "Ctrl+T": "ADD_TEST_DATA",
}


def NO_ACTION(self) -> None:  # pylint: disable=unused-argument
    """Select key combination and action to bind"""


def TOGGLE_RUN(self) -> None:
    """Toggle between RUN and S&P"""
    self.set_running(not self.pref["run_state"])


def LOG_NOW(self) -> None:
    """Log the current contact"""
    self.save_contact()


def TOGGLE_CW_INPUT(self) -> None:
    """Toggle CW text entry field"""
    self.toggle_cw_entry()


def PREV_SPOT(self) -> None:
    """Jump to the previous spot in the bandmap"""
    cmd = {}
    cmd["cmd"] = "PREVSPOT"
    if self.bandmap_window:
        self.bandmap_window.msg_from_main(cmd)


def NEXT_SPOT(self) -> None:
    """Jump to the next spot in the bandmap"""
    cmd = {}
    cmd["cmd"] = "NEXTSPOT"
    if self.bandmap_window:
        self.bandmap_window.msg_from_main(cmd)


def FIND_DX(self) -> None:
    """Tune to a spot matching the partial callsign"""
    dx = self.callsign.text()
    if dx:
        cmd = {}
        cmd["cmd"] = "FINDDX"
        cmd["dx"] = dx
        if self.bandmap_window:
            self.bandmap_window.msg_from_main(cmd)


def SPOT_DX(self) -> None:
    """Spot the callsign to the cluster"""
    freq = self.radio_state.get("vfoa")
    dx = self.callsign.text()
    if freq and dx:
        cmd = {}
        cmd["cmd"] = "SPOTDX"
        cmd["dx"] = dx
        cmd["freq"] = float(int(freq) / 1000)
        if self.bandmap_window:
            self.bandmap_window.msg_from_main(cmd)


def MARK_SPOT(self) -> None:
    """Mark callsign to work later"""
    self.mark_spot(comment=f"{self.current_mode} MARKED")


def JUMP_TO_CQ(self) -> None:
    """Jump to the last CQ frequency"""
    if self.cq_freq:
        self.radio_state["vfoa"] = self.cq_freq
        if self.rig_control:
            self.rig_control.set_vfo(self.cq_freq)
        self.set_running(True)
        self.clearinputs()


def VFO_DOWN(self) -> None:
    """Step the VFO frequency down"""
    freq = self.radio_state.get("vfoa")
    selected_mode = self.radio_state.get("mode")
    if selected_mode == "CW":
        deltaf = 20
    elif selected_mode in ["LSB", "USB", "SSB"]:
        deltaf = 100
    else:
        deltaf = 0
    vfo = int(freq) - deltaf
    if self.rig_control:
        self.rig_control.set_vfo(vfo)


def VFO_UP(self) -> None:
    """Step the VFO frequency up"""
    freq = self.radio_state.get("vfoa")
    selected_mode = self.radio_state.get("mode")
    if selected_mode == "CW":
        deltaf = 20
    elif selected_mode in ["LSB", "USB", "SSB"]:
        deltaf = 100
    else:
        deltaf = 0
    vfo = int(freq) + deltaf
    if self.rig_control:
        self.rig_control.set_vfo(vfo)


def CW_SPEED_UP(self) -> None:
    """Increase CW sending speed"""
    if self.cw is not None:
        self.cw.speed += self.pref.get("cwstepping", 1)
        self.cw_speed.setValue(self.cw.speed)
        if self.cw.servertype == 1:
            self.cw.sendcw(f"\x1b2{self.cw.speed}")
        if self.cw.servertype == 2:
            self.cw.set_winkeyer_speed(self.cw_speed.value())


def CW_SPEED_DOWN(self) -> None:
    """Decrease CW sending speed"""
    if self.cw is not None:
        self.cw.speed -= self.pref.get("cwstepping", 1)
        self.cw_speed.setValue(self.cw.speed)
        if self.cw.servertype == 1:
            self.cw.sendcw(f"\x1b2{self.cw.speed}")
        if self.cw.servertype == 2:
            self.cw.set_winkeyer_speed(self.cw_speed.value())


def CLEAR_INPUTS(self) -> None:
    """Clear the input fields"""
    self.clearinputs()


def STOP_ALL(self) -> None:
    """Stop CW sending and antenna rotation"""
    self.stop_all()


def ADD_TEST_DATA(self) -> None:
    """Add test data to the log"""
    if hasattr(self.contest, "add_test_data"):
        self.contest.add_test_data(self)


def EDIT_KEYS(self) -> None:
    """Open the Edit Keys dialog"""

    def finished():
        self.edit_keys_dialog = None

    if self.edit_keys_dialog is None:
        key_bindings = self.pref.get("key_bindings", default_key_bindings)
        self.edit_keys_dialog = EditKeys(key_bindings=key_bindings, parent=self)
        if self.current_palette:
            self.edit_keys_dialog.setPalette(self.current_palette)
        self.edit_keys_dialog.accepted.connect(self.edit_keys_dialog.save_keys)
        self.edit_keys_dialog.finished.connect(finished)
        self.edit_keys_dialog.show()
