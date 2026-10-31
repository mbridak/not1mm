"""
Second entry row for SO2V: the run radio's QSO on top, the S&P radio's below.
GPL V3

Contest plugins reach the entry widgets by name at call time --
self.callsign.text(), self.other_1.setText(), self.field3.show() -- across
~3,700 call sites in 96 plugins. Rather than touch them, MainWindow rebinds the
five line-edit names to whichever row is active, and replaces the label and
field-frame names with FanOut proxies so a plugin hiding a field or renaming a
label does it on both rows at once.

The S&P row is cloned from main.ui's own entry-row layout, so it matches the
run row exactly: same widgets, sizes, stretch, labels.
"""

import copy
import io
import xml.etree.ElementTree as ET
from pathlib import Path

from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QPoint, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

# The five entry line edits, rebound to the active row.
ENTRY_ROLES = ("callsign", "sent", "receive", "other_1", "other_2")
# Field frames and their labels, fanned out to both rows.
FRAME_NAMES = ("callsignfield", "field1", "field2", "field3", "field4")
LABEL_NAMES = ("callsign_label", "snt_label", "rcv_label", "other_label", "exch_label")

ENTRY_ROW_LAYOUT = "horizontalLayout"

FULL, UPPER, LOWER = "full", "upper", "lower"


def indicator_states(stereo: bool, active_row: int) -> list:
    """(shape, active) for the run row's and the S&P row's indicator.

    Mono: the radio you are on is in both ears -- a full circle on its row,
    nothing on the muted one. Stereo: run left, S&P right -- the run row
    shows the upper half, the S&P row the lower half. Green marks the radio
    you are on, gray the other.
    """
    if stereo:
        return [(UPPER, active_row == 0), (LOWER, active_row == 1)]
    return [(FULL, True) if row == active_row else (None, False) for row in (0, 1)]


class RadioIndicator(QtWidgets.QWidget):
    """Circle left of a row's callsign box: which radio is active (green vs
    gray) and what you are hearing from it (full, half, or nothing)."""

    def __init__(self, line_edit: QtWidgets.QLineEdit) -> None:
        super().__init__()
        self.line_edit = line_edit
        self.shape = None
        self.active = False
        self.active_color = QColor("#a6e3a1")
        self.inactive_color = QColor("#313244")
        self.inactive_edge = QColor("#45475a")
        self.diameter = round(line_edit.sizeHint().height() * 2 / 3)
        self.setFixedWidth(self.diameter + 12)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_colors(self, active: str, inactive: str, inactive_edge: str) -> None:
        self.active_color = QColor(active)
        self.inactive_color = QColor(inactive)
        self.inactive_edge = QColor(inactive_edge)
        self.update()

    def set_state(self, shape, active: bool) -> None:
        self.shape = shape
        self.active = bool(active)
        self.setAccessibleName(
            f"radio {'active' if active else 'inactive'}, audio "
            f"{ {FULL: 'both ears', UPPER: 'left', LOWER: 'right'}.get(shape, 'muted') }"
        )
        self.update()

    def circle_rect(self) -> QRectF:
        """Centred on the callsign box, not on the label above it."""
        d = self.diameter
        centre = self.mapFromGlobal(
            self.line_edit.mapToGlobal(QPoint(0, self.line_edit.height() // 2))
        )
        return QRectF((self.width() - d) / 2, centre.y() - d / 2, d, d)

    def paintEvent(self, _event) -> None:
        if not self.shape:
            return
        rect = self.circle_rect()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.active:
            painter.setBrush(self.active_color)
            painter.setPen(Qt.PenStyle.NoPen)
        else:
            painter.setBrush(self.inactive_color)
            painter.setPen(QPen(self.inactive_edge, 1))
        if self.shape == FULL:
            painter.drawEllipse(rect)
        elif self.shape == UPPER:
            painter.drawPie(rect, 0, 180 * 16)
        else:
            painter.drawPie(rect, 180 * 16, 180 * 16)
        painter.end()


class FanOut:
    """Stands in for one widget that exists once per row.

    Mutating calls go to every row; queries answer from the first (the run
    row), which is what a single-row window would have answered.
    """

    BROADCAST = frozenset(
        {
            "show",
            "hide",
            "setVisible",
            "setHidden",
            "setEnabled",
            "setText",
            "setToolTip",
            "setAccessibleName",
            "setAccessibleDescription",
            "setStyleSheet",
            "setFont",
            "setPalette",
            "setAlignment",
            "setWordWrap",
            "clear",
        }
    )

    def __init__(self, *widgets) -> None:
        object.__setattr__(self, "_widgets", widgets)

    @property
    def widgets(self):
        return self._widgets

    def __getattr__(self, name):
        first = getattr(self._widgets[0], name)
        if name == "findChild":

            def find(*args, **kwargs):
                found = [w.findChild(*args, **kwargs) for w in self._widgets]
                if any(child is None for child in found):
                    return found[0]
                return FanOut(*found)

            return find
        if name in self.BROADCAST and callable(first):

            def fan(*args, **kwargs):
                result = first(*args, **kwargs)
                for widget in self._widgets[1:]:
                    getattr(widget, name)(*args, **kwargs)
                return result

            return fan
        return first

    def __setattr__(self, name, value):
        for widget in self._widgets:
            setattr(widget, name, value)


def entry_row_ui_xml(ui_file: Path) -> str:
    """A standalone .ui document holding a copy of main.ui's entry row."""
    root = ET.parse(ui_file).getroot()
    layout = root.find(f".//layout[@name='{ENTRY_ROW_LAYOUT}']")
    if layout is None:
        raise ValueError(f"{ui_file} has no layout named {ENTRY_ROW_LAYOUT}")
    ui = ET.Element("ui", version="4.0")
    ET.SubElement(ui, "class").text = "SpEntryRow"
    widget = ET.SubElement(ui, "widget", {"class": "QWidget", "name": "SpEntryRow"})
    widget.append(copy.deepcopy(layout))
    return ET.tostring(ui, encoding="unicode")


def build_entry_row(ui_file: Path, like_layout=None) -> QtWidgets.QWidget:
    """Build the S&P entry row. Every named widget from the run row exists on
    the returned QWidget under the same attribute name."""
    row = QtWidgets.QWidget()
    uic.loadUi(io.StringIO(entry_row_ui_xml(ui_file)), row)
    # As a widget's top-level layout it would pick up default margins the
    # nested original does not have, and the columns would stop lining up.
    row.layout().setContentsMargins(0, 0, 0, 0)
    if like_layout is not None:
        row.layout().setSpacing(like_layout.spacing())
    return row
