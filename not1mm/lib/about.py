"""The About Dialog"""

from PyQt5 import QtWidgets, uic


class About(QtWidgets.QDialog):
    """Waste of code space"""

    def __init__(self, WORKING_PATH):
        parent = None
        super().__init__(parent)
        uic.loadUi(WORKING_PATH + "/data/about.ui", self)
        # self.buttonBox.clicked.connect(self.store)

    # def store(self):
    #     """dialog magic"""
