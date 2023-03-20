"""Edit Contact Dialog"""

from PyQt5 import QtWidgets, uic


class EditContact(QtWidgets.QDialog):
    """Edit Contact"""

    def __init__(self, WORKING_PATH):
        super().__init__(None)
        uic.loadUi(WORKING_PATH + "/data/editcontact.ui", self)
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""
