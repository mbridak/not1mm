"""edit the macro buttons"""

from PyQt6 import QtWidgets, uic


class EditMacro(QtWidgets.QDialog):

    def __init__(self, function_key, app_data_path):
        self.function_key = function_key
        parent = None
        super().__init__(parent)
        uic.loadUi(app_data_path / "editmacro.ui", self)
        self.buttonBox.clicked.connect(self.store)
        self.macro_label.setText(function_key.text())
        self.the_macro.setText(function_key.toolTip())

    def store(self):
        """dialog magic"""
