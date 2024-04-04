"""New Contest Dialog"""

import importlib
from PyQt6 import QtWidgets, uic


class NewContest(QtWidgets.QDialog):
    """New Contest"""

    def __init__(self, app_data_path):
        super().__init__(None)
        uic.loadUi(app_data_path / "new_contest.ui", self)
        self.buttonBox.clicked.connect(self.store)
        self.contest.currentTextChanged.connect(self.add_exchange_hint)

    def store(self):
        """dialog magic"""

    def add_exchange_hint(self):
        """add hint"""
        contest_name = self.contest.currentText().lower().replace(" ", "_")
        temp = importlib.import_module(f"not1mm.plugins.{contest_name}")
        if hasattr(temp, "EXCHANGE_HINT"):
            self.exchange.setPlaceholderText(temp.EXCHANGE_HINT)
        else:
            self.exchange.setPlaceholderText("")
