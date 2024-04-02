"""Select Contest Dialog"""

from PyQt6 import QtWidgets, uic


class SelectContest(QtWidgets.QDialog):
    """Select Contest"""

    def __init__(self, app_data_path):
        super().__init__(None)
        uic.loadUi(app_data_path / "pickcontest.ui", self)
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""
