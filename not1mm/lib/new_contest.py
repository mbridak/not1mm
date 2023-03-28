"""New Contest Dialog"""

from PyQt5 import QtWidgets, uic


class NewContest(QtWidgets.QDialog):
    """New Contest"""

    def __init__(self, WORKING_PATH):
        super().__init__(None)
        uic.loadUi(WORKING_PATH + "/data/new_contest.ui", self)
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""
