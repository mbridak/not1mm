"""Edit key bindings dialog."""

from PyQt6 import QtCore, QtGui, QtWidgets, uic

import not1mm.actions
import not1mm.fsutils as fsutils
from not1mm.lib.preferences import Preferences

_KNOWN_CONTEXTS = [
    "*",
    "Callsign",
    "Report",
    "Exchange",
    "Other 1",
    "Other 2",
    "CW entry",
]


class EditKeys(QtWidgets.QDialog):
    """Dialog to view, add, edit, and remove key bindings."""

    _READONLY_FLAGS = (
        QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled
    )

    def __init__(self, key_bindings, parent=None):
        """Open Edit Keys dialog window and populate it"""

        super().__init__(parent)
        uic.loadUi(fsutils.APP_DATA_PATH / "edit_keys.ui", self)

        # load known actions by inspecting the not1mm.actions module
        self.actions = []
        self.action_docs = {}
        for action in vars(not1mm.actions):
            action_function = getattr(not1mm.actions, action)
            # skip everything starting with _ and check if this is a function
            if not action.startswith("_") and callable(action_function):
                self.actions.append(action)
                self.action_docs[action] = action_function.__doc__

        self._suppress_widget_signals = False
        self._context_combos = {}
        self._action_combos = {}
        self._key_edits = {}

        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)

        self.add_button.clicked.connect(self._on_add)
        self.remove_button.clicked.connect(self._on_remove)
        self.reset_all_button.clicked.connect(self._on_reset_all)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self._load(key_bindings)
        self._refresh()

    def _load(self, key_bindings):
        # populate dialog window with existing key bindings
        self._bindings = []
        for context_key, action in key_bindings.items():
            if ":" in context_key:
                context, _, key = context_key.partition(":")
            else:
                context, key = "*", context_key
            self._bindings.append(
                {
                    "context": context,
                    "key": key,
                    "action": action,
                }
            )

    def _refresh(self) -> None:
        self._suppress_widget_signals = True
        try:
            old_count = self.table.rowCount()
            self.table.setRowCount(len(self._bindings))

            new_context_combos = {}
            new_key_edits = {}
            new_action_combos = {}
            for row, entry in enumerate(self._bindings):
                existing = self.table.cellWidget(row, 0)
                if isinstance(existing, QtWidgets.QComboBox):
                    context_combo = existing
                    if context_combo.currentText() != entry["context"]:
                        context_combo.setCurrentText(entry["context"])
                else:
                    context_combo = QtWidgets.QComboBox()
                    context_combo.addItems(_KNOWN_CONTEXTS)
                    context_combo.setCurrentText(entry["context"])
                    context_combo.currentTextChanged.connect(
                        lambda text, r=row: self._on_context_changed(r, text)
                    )
                    self.table.setCellWidget(row, 0, context_combo)
                new_context_combos[row] = context_combo

                existing_edit = self.table.cellWidget(row, 1)
                if isinstance(existing_edit, QtWidgets.QKeySequenceEdit):
                    key_edit = existing_edit
                    if key_edit.keySequence().toString() != entry["key"]:
                        key_edit.setKeySequence(QtGui.QKeySequence(entry["key"]))
                else:
                    key_edit = QtWidgets.QKeySequenceEdit(
                        QtGui.QKeySequence(entry["key"])
                    )
                    key_edit.keySequenceChanged.connect(
                        lambda seq, r=row: self._on_key_sequence_changed(r, seq)
                    )
                    self.table.setCellWidget(row, 1, key_edit)
                new_key_edits[row] = key_edit

                existing_combo = self.table.cellWidget(row, 2)
                if isinstance(existing_combo, QtWidgets.QComboBox):
                    combo = existing_combo
                    if combo.currentText() != entry["action"]:
                        combo.setCurrentText(entry["action"])
                else:
                    combo = QtWidgets.QComboBox()
                    combo.setEditable(True)
                    combo.addItems(self.actions)
                    combo.setCurrentText(entry["action"])
                    combo.currentTextChanged.connect(
                        lambda text, r=row: self._on_action_changed(r, text)
                    )
                    self.table.setCellWidget(row, 2, combo)
                new_action_combos[row] = combo

                description_item = QtWidgets.QTableWidgetItem(
                    self.action_docs.get(entry["action"], "")
                )
                description_item.setFlags(self._READONLY_FLAGS)
                self.table.setItem(row, 3, description_item)

            for removed_row in range(len(self._bindings), old_count):
                for col in (0, 1, 2):
                    old = self.table.cellWidget(removed_row, col)
                    if old is not None:
                        old.deleteLater()

            self._context_combos = new_context_combos
            self._key_edits = new_key_edits
            self._action_combos = new_action_combos
            for col in range(3):
                self.table.resizeColumnToContents(col)
        finally:
            self._suppress_widget_signals = False

    def _selected_row(self) -> int:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return -1
        return rows[0].row()

    def _on_add(self) -> None:
        self._bindings.append({"context": "*", "key": "", "action": "NO_ACTION"})
        self._refresh()
        new_row = len(self._bindings) - 1
        self.table.selectRow(new_row)
        combo = self._action_combos.get(new_row)
        if combo is not None:
            self.table.setCurrentCell(new_row, 2)
            combo.setFocus()
            line_edit = combo.lineEdit()
            if line_edit is not None:
                line_edit.selectAll()

    def _on_remove(self) -> None:
        row = self._selected_row()
        if row < 0:
            return
        del self._bindings[row]
        self._refresh()
        if self._bindings:
            self.table.selectRow(min(row, len(self._bindings) - 1))

    def _on_reset_all(self) -> None:
        self._load(not1mm.actions.default_key_bindings)
        self._refresh()

    def _on_context_changed(self, row: int, context: str) -> None:
        if self._suppress_widget_signals:
            return
        if 0 <= row < len(self._bindings):
            self._bindings[row]["context"] = context

    def _on_action_changed(self, row: int, action: str) -> None:
        if self._suppress_widget_signals:
            return
        if not (0 <= row < len(self._bindings)):
            return
        self._bindings[row]["action"] = action
        desc_item = self.table.item(row, 3)
        desc_item.setText(self.action_docs.get(action, ""))

    def _on_key_sequence_changed(self, row: int, sequence: QtGui.QKeySequence) -> None:
        if self._suppress_widget_signals:
            return
        if 0 <= row < len(self._bindings):
            self._bindings[row]["key"] = sequence.toString()

    def save_keys(self) -> None:
        """
        Save keys configured in the dialog window to the preferences file.

        Format is dict mapping <context>:<key> (e.g. Callsign:Ctrl-Shift-A) to
        action names.
        """

        key_bindings = {}
        for entry in self._bindings:
            # skip incomplete entries
            if entry["key"] == "" or entry["action"] == "":
                continue
            # key_bindings key is "Ctrl+R" or "context:Ctrl+R"
            if entry["context"] == "*":
                context_key = entry["key"]
            else:
                context_key = entry["context"] + ":" + entry["key"]
            key_bindings[context_key] = entry["action"]
        pref = Preferences.data()
        pref["key_bindings"] = key_bindings
        Preferences.save()
