"""New Contest Dialog"""

from PyQt6 import QtWidgets

from not1mm.lib.contest import contest_metadata, contest_picker_entries
from not1mm.lib.i18n import load_ui


def fill_picker(combo) -> None:
    """Fill *combo* with the contests this installation can open.

    Kept a plain function so it can be exercised without a display: a combo
    only has to provide ``clear()`` and ``addItem()``.  The label is what the
    operator reads, the item data is the identifier the database stores.
    """
    combo.clear()
    for label, identifier in contest_picker_entries():
        combo.addItem(label, identifier)


class NewContest(QtWidgets.QDialog):
    """New Contest"""

    def __init__(self, app_data_path):
        super().__init__(None)
        load_ui(self, app_data_path / "new_contest.ui")
        # The .ui file no longer lists the contests: discovery fills them in,
        # so a new plugin shows up without anybody editing the dialog.
        fill_picker(self.contest)
        self.buttonBox.clicked.connect(self.store)
        self.contest.currentTextChanged.connect(self.add_exchange_hint)

    def store(self):
        """dialog magic"""

    def add_exchange_hint(self):
        """add hint"""
        self.soapbox.setPlaceholderText("")
        self.exchange.setPlaceholderText("")
        metadata = contest_metadata(self.contest.currentData())
        self.exchange.setPlaceholderText(getattr(metadata, "EXCHANGE_HINT", "") or "")
        self.soapbox.setPlaceholderText(getattr(metadata, "SOAPBOX_HINT", "") or "")
