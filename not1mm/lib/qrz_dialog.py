"""Use QRZ dialog"""

from PyQt5 import QtWidgets, uic


class UseQRZ(QtWidgets.QDialog):
    """QRZ settings"""

    def __init__(self, WORKING_PATH):
        super().__init__(None)
        uic.loadUi(WORKING_PATH + "/data/use_qrz_dialog.ui", self)
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""
