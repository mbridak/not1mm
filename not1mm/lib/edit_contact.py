"""Edit Contact Dialog"""

from PyQt6 import QtCore, QtGui, QtWidgets

from not1mm.lib import catppuccin
from not1mm.lib.i18n import load_ui

_RETHEME_EVENTS = frozenset(
    {
        QtCore.QEvent.Type.ApplicationPaletteChange,
        QtCore.QEvent.Type.PaletteChange,
    }
)


class EditContact(QtWidgets.QDialog):
    """Edit Contact"""

    def __init__(self, app_data_path):
        super().__init__(None)
        load_ui(self, app_data_path / "editcontact.ui")
        self.buttonBox.clicked.connect(self.store)
        self.apply_theme()

    def is_it_dark(self) -> bool:
        """Returns if the DE has a dark theme active."""
        hints = QtGui.QGuiApplication.styleHints()
        return hints.colorScheme() == QtCore.Qt.ColorScheme.Dark

    def apply_theme(self) -> None:
        """
        Dress the dialog in the active Catppuccin theme.

        The base sheet sets QPushButton color explicitly, and a stylesheet
        beats a widget palette, so the Delete button's destructive tint has
        to be a stylesheet rule as well. Its colour is catppuccin's accent
        for the active flavour, and the ID selector outranks the base
        sheet's bare QPushButton type selector, so only Delete is affected.
        """
        dark = self.is_it_dark()
        base = catppuccin.STYLESHEET if dark else catppuccin.LATTE_STYLESHEET
        accent = catppuccin.accent_for(dark)
        stylesheet = f"{base}\nQPushButton#delete_2 {{ color: {accent}; }}\n"
        if self.styleSheet() != stylesheet:
            self.setStyleSheet(stylesheet)

    def changeEvent(self, event) -> None:
        """
        Re-theme the dialog when the desktop colour scheme changes.

        Parameters
        ----------
        event : QEvent
            The event being delivered.

        Returns
        -------
        None
        """
        super().changeEvent(event)
        if event.type() in _RETHEME_EVENTS:
            self.apply_theme()

    def store(self):
        """dialog magic"""
