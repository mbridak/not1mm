"""Edit Contact Dialog"""

from PyQt6 import QtWidgets, uic


class EditContact(QtWidgets.QDialog):
    """Edit Contact"""

    def __init__(self, app_data_path):
        super().__init__(None)
        uic.loadUi(app_data_path / "editcontact.ui", self)
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""
