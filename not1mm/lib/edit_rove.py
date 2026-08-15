"""Edit Rover Location"""

from PyQt6 import QtWidgets

from not1mm.lib.i18n import load_ui


class Rove(QtWidgets.QDialog):
    """Change the current operator"""

    def __init__(self, app_data_path, parent=None):
        super().__init__(parent)
        load_ui(self, app_data_path / "rover.ui")
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""
