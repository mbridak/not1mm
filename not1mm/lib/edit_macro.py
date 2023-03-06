"""edit the macro buttons"""

from PyQt5 import QtWidgets, uic


class EditMacro(QtWidgets.QDialog):
    """Change the current operator"""

    def __init__(self, function_key, WORKING_PATH):
        self.function_key = function_key
        parent = None
        super().__init__(parent)
        uic.loadUi(WORKING_PATH + "/data/editmacro.ui", self)
        self.buttonBox.clicked.connect(self.store)
        self.macro_label.setText(function_key.text())
        self.the_macro.setText(function_key.toolTip())

    def store(self):
        """dialog magic"""
