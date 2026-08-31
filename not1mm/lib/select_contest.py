"""Select Contest Dialog"""

from PyQt6 import QtWidgets

from not1mm.lib.i18n import load_ui


class SelectContest(QtWidgets.QDialog):
    """Select Contest"""

    def __init__(self, app_data_path):
        super().__init__(None)
        load_ui(self, app_data_path / "pickcontest.ui")
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""
