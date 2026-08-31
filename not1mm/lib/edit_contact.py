"""Edit Contact Dialog"""

from PyQt6 import QtWidgets

from not1mm.lib.i18n import load_ui


class EditContact(QtWidgets.QDialog):
    """Edit Contact"""

    def __init__(self, app_data_path):
        super().__init__(None)
        load_ui(self, app_data_path / "editcontact.ui")
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""
