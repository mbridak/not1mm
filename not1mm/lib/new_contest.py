"""New Contest Dialog"""

from PyQt6 import QtWidgets

from not1mm.lib.contest import contest_metadata
from not1mm.lib.i18n import load_ui


class NewContest(QtWidgets.QDialog):
    """New Contest"""

    def __init__(self, app_data_path):
        super().__init__(None)
        load_ui(self, app_data_path / "new_contest.ui")
        self.buttonBox.clicked.connect(self.store)
        self.contest.currentTextChanged.connect(self.add_exchange_hint)

    def store(self):
        """dialog magic"""

    def add_exchange_hint(self):
        """add hint"""
        self.soapbox.setPlaceholderText("")
        self.exchange.setPlaceholderText("")
        contest_name = self.contest.currentText().lower().replace(" ", "_")
        metadata = contest_metadata(contest_name)
        self.exchange.setPlaceholderText(getattr(metadata, "EXCHANGE_HINT", "") or "")
        self.soapbox.setPlaceholderText(getattr(metadata, "SOAPBOX_HINT", "") or "")
