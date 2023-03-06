"""Edit Settings Dialog"""

from PyQt5 import QtWidgets, uic

from not1mm.lib.ham_utility import gridtolatlon


class EditSettings(QtWidgets.QDialog):
    """Edit Settings"""

    def __init__(self, WORKING_PATH):
        super().__init__(None)
        uic.loadUi(WORKING_PATH + "/data/settings.ui", self)
        self.buttonBox.clicked.connect(self.store)
        self.GridSquare.textEdited.connect(self.gridchanged)

    def store(self):
        """dialog magic"""

    def gridchanged(self):
        """Populated the Lat and Lon fields when the gridsquare changes"""
        lat, lon = gridtolatlon(self.GridSquare.text())
        self.Latitude.setText(str(round(lat, 4)))
        self.Longitude.setText(str(round(lon, 4)))
