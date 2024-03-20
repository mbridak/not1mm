"""New Contest Dialog"""

from PyQt5 import QtWidgets, uic


class NewContest(QtWidgets.QDialog):
    """New Contest"""

    def __init__(self, app_data_path):
        super().__init__(None)
        uic.loadUi(app_data_path / "new_contest.ui", self)
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""
