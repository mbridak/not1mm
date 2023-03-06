"""Edit OpOn"""

from PyQt5 import QtWidgets, uic


class OpOn(QtWidgets.QDialog):
    """Change the current operator"""

    def __init__(self, WORKING_PATH, parent=None):
        super().__init__(parent)
        uic.loadUi(WORKING_PATH + "/data/opon.ui", self)
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""
