"""Edit OpOn"""

from PyQt6 import QtWidgets, uic


class OpOn(QtWidgets.QDialog):
    """Change the current operator"""

    def __init__(self, app_data_path, parent=None):
        super().__init__(parent)
        uic.loadUi(app_data_path / "opon.ui", self)
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""
