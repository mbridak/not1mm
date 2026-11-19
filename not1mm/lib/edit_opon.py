"""Edit OpOn"""

from PyQt6 import QtWidgets

from not1mm.lib.i18n import load_ui
from not1mm.lib.preferences import Preferences


class OpOn(QtWidgets.QDialog):
    """Change the current operator"""

    def __init__(self, app_data_path, parent):
        super().__init__(parent)
        load_ui(self, app_data_path / "opon.ui")
        self.parent = parent
        self.accepted.connect(self.new_op)

    def new_op(self) -> None:
        """
        Called when the user clicks the OK button on the OPON dialog.
        Create the new directory and copy the phonetic files.
        """
        if current_op := self.NewOperator.text().upper():
            self.parent.pref["current_op"] = current_op
            Preferences.save()
            self.parent.make_op_dir()
            self.parent.set_window_title()
        self.close()
