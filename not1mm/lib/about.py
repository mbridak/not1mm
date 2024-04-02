"""The About Dialog"""

# pylint: disable=c-extension-no-member

from PyQt6 import QtWidgets, uic


class About(QtWidgets.QDialog):
    """Waste of code space"""

    def __init__(self, app_data_path):
        parent = None
        super().__init__(parent)
        uic.loadUi(app_data_path / "about.ui", self)
        # self.buttonBox.clicked.connect(self.store)

    # def store(self):
    #     """dialog magic"""
