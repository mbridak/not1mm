import sys

import pytest
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLineEdit, QWidget

from not1mm.lib.entry_rows import FULL, LOWER, UPPER, RadioIndicator, indicator_states

GREEN = "#a6e3a1"
GRAY = "#313244"


@pytest.mark.parametrize(
    "stereo, active_row, expected",
    [
        (False, 0, [(FULL, True), (None, False)]),
        (False, 1, [(None, False), (FULL, True)]),
        (True, 0, [(UPPER, True), (LOWER, False)]),
        (True, 1, [(UPPER, False), (LOWER, True)]),
    ],
)
def test_indicator_states(stereo, active_row, expected):
    assert indicator_states(stereo, active_row) == expected


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def indicator(qt_app):
    host = QWidget()
    layout = QHBoxLayout(host)
    edit = QLineEdit()
    edit.setFixedHeight(40)
    ind = RadioIndicator(edit)
    layout.addWidget(ind)
    layout.addWidget(edit)
    host.resize(300, 60)
    host.show()
    qt_app.processEvents()
    ind.set_colors(GREEN, GRAY, "#45475a")
    ind.host = host  # keep the parent alive
    return ind


def sample(ind, dy):
    """Colour at the circle's centre column, dy pixels from its centre
    (negative is up)."""
    image = ind.grab().toImage()
    rect = ind.circle_rect()
    return QColor(image.pixel(int(rect.center().x()), int(rect.center().y() + dy))).name()


def test_diameter_is_two_thirds_of_callsign_box(indicator):
    assert indicator.diameter == round(indicator.line_edit.sizeHint().height() * 2 / 3)


def test_full_circle_fills_both_halves(indicator):
    indicator.set_state(FULL, True)
    r = indicator.diameter / 4
    assert sample(indicator, -r) == GREEN
    assert sample(indicator, r) == GREEN


def test_upper_half_only(indicator):
    indicator.set_state(UPPER, False)
    r = indicator.diameter / 4
    assert sample(indicator, -r) == GRAY
    assert sample(indicator, r) != GRAY


def test_lower_half_only(indicator):
    indicator.set_state(LOWER, True)
    r = indicator.diameter / 4
    assert sample(indicator, r) == GREEN
    assert sample(indicator, -r) != GREEN


def test_no_shape_draws_nothing(indicator):
    indicator.set_state(None, False)
    r = indicator.diameter / 4
    assert sample(indicator, -r) not in (GREEN, GRAY)
    assert sample(indicator, r) not in (GREEN, GRAY)


def test_circle_centred_on_callsign_box(indicator):
    centre = indicator.mapTo(indicator.host, indicator.circle_rect().center().toPoint())
    edit_centre = indicator.line_edit.geometry().center()
    assert abs(centre.y() - edit_centre.y()) <= 1


def test_clicks_pass_through(indicator):
    from PyQt6.QtCore import Qt

    assert indicator.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
