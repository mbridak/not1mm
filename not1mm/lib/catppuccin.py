"""
Catppuccin themes for not1mm.

Provides QPalettes and Qt stylesheets for both Catppuccin Mocha (dark)
and Catppuccin Latte (light).
See https://github.com/catppuccin/catppuccin for colour definitions.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette


def _qcolor(hex_str: str) -> QColor:
    """Convert a '#rrggbb' string to QColor."""
    return QColor(hex_str)


# ═══════════════════════════════════════════════════════════════════════════
#  Catppuccin Mocha  (dark)
# ═══════════════════════════════════════════════════════════════════════════

ROSEWATER = "#f5e0dc"
FLAMINGO  = "#f2cdcd"
PINK      = "#f5c2e7"
MAUVE     = "#cba6f7"
RED       = "#f38ba8"
MARoon    = "#eba0ac"
PEACH     = "#fab387"
YELLOW    = "#f9e2af"
GREEN     = "#a6e3a1"
TEAL      = "#94e2d5"
SKY       = "#89dceb"
SAPPHIRE  = "#74c7ec"
BLUE      = "#89b4fa"
LAVENDER  = "#b4befe"

TEXT      = "#cdd6f4"
SUBTEXT1  = "#bac2de"
SUBTEXT0  = "#a6adc8"
OVERLAY2  = "#9399b2"
OVERLAY1  = "#7f849c"
OVERLAY0  = "#6c7086"
SURFACE2  = "#585b70"
SURFACE1  = "#45475a"
SURFACE0  = "#313244"
BASE      = "#1e1e2e"
MANTLE    = "#181825"
CRUST     = "#11111b"


def build_palette() -> QPalette:
    """Return a QPalette dressed in Catppuccin Mocha."""
    p = QPalette()

    p.setColor(QPalette.ColorRole.Window,          _qcolor(BASE))
    p.setColor(QPalette.ColorRole.WindowText,       _qcolor(TEXT))
    p.setColor(QPalette.ColorRole.Base,             _qcolor(MANTLE))
    p.setColor(QPalette.ColorRole.AlternateBase,    _qcolor(SURFACE0))
    p.setColor(QPalette.ColorRole.Text,             _qcolor(TEXT))
    p.setColor(QPalette.ColorRole.Button,           _qcolor(SURFACE0))
    p.setColor(QPalette.ColorRole.ButtonText,       _qcolor(TEXT))
    p.setColor(QPalette.ColorRole.BrightText,       _qcolor(FLAMINGO))
    p.setColor(QPalette.ColorRole.Link,             _qcolor(BLUE))
    p.setColor(QPalette.ColorRole.Highlight,        _qcolor(MAUVE))
    p.setColor(QPalette.ColorRole.HighlightedText,  _qcolor(BASE))
    p.setColor(QPalette.ColorRole.PlaceholderText,  _qcolor(OVERLAY0))

    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText,      _qcolor(OVERLAY1))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, _qcolor(OVERLAY1))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,            _qcolor(OVERLAY1))

    return p


# ═══════════════════════════════════════════════════════════════════════════
#  Catppuccin Latte  (light)
# ═══════════════════════════════════════════════════════════════════════════

L_ROSEWATER = "#dc8a78"
L_FLAMINGO  = "#dd7878"
L_PINK      = "#ea76cb"
L_MAUVE     = "#8839ef"
L_RED       = "#d20f39"
L_MAROON    = "#e64553"
L_PEACH     = "#fe640b"
L_YELLOW    = "#df8e1d"
L_GREEN     = "#40a02b"
L_TEAL      = "#179299"
L_SKY       = "#04a5e5"
L_SAPPHIRE  = "#209fb5"
L_BLUE      = "#1e66f5"
L_LAVENDER  = "#7287fd"

L_TEXT      = "#4c4f69"
L_SUBTEXT1  = "#5c5f77"
L_SUBTEXT0  = "#6c6f85"
L_OVERLAY2  = "#7c7f93"
L_OVERLAY1  = "#8c8fa1"
L_OVERLAY0  = "#9ca0b0"
L_SURFACE2  = "#acb0be"
L_SURFACE1  = "#bcc0cc"
L_SURFACE0  = "#ccd0da"
L_BASE      = "#eff1f5"
L_MANTLE    = "#e6e9ef"
L_CRUST     = "#dce0e8"


def build_latte_palette() -> QPalette:
    """Return a QPalette dressed in Catppuccin Latte."""
    p = QPalette()

    p.setColor(QPalette.ColorRole.Window,          _qcolor(L_BASE))
    p.setColor(QPalette.ColorRole.WindowText,       _qcolor(L_TEXT))
    p.setColor(QPalette.ColorRole.Base,             _qcolor(L_MANTLE))
    p.setColor(QPalette.ColorRole.AlternateBase,    _qcolor(L_SURFACE0))
    p.setColor(QPalette.ColorRole.Text,             _qcolor(L_TEXT))
    p.setColor(QPalette.ColorRole.Button,           _qcolor(L_SURFACE0))
    p.setColor(QPalette.ColorRole.ButtonText,       _qcolor(L_TEXT))
    p.setColor(QPalette.ColorRole.BrightText,       _qcolor(L_RED))
    p.setColor(QPalette.ColorRole.Link,             _qcolor(L_BLUE))
    p.setColor(QPalette.ColorRole.Highlight,        _qcolor(L_MAUVE))
    p.setColor(QPalette.ColorRole.HighlightedText,  _qcolor(L_BASE))
    p.setColor(QPalette.ColorRole.PlaceholderText,  _qcolor(L_OVERLAY0))

    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText,      _qcolor(L_OVERLAY1))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, _qcolor(L_OVERLAY1))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,            _qcolor(L_OVERLAY1))

    return p


# ═══════════════════════════════════════════════════════════════════════════
#  Mocha stylesheet (dark)
# ═══════════════════════════════════════════════════════════════════════════

STYLESHEET = f"""
QMainWindow, QDialog {{
    background-color: {BASE};
    color: {TEXT};
}}

QWidget {{
    background-color: {BASE};
    color: {TEXT};
}}

QDockWidget {{
    border: 2px solid {SURFACE1};
    titlebar-close-icon: none;
}}

QDockWidget::title {{
    background-color: {SURFACE0};
    padding: 4px;
}}

QMenuBar {{
    background-color: {MANTLE};
    color: {TEXT};
}}

QMenuBar::item:selected {{
    background-color: {SURFACE0};
}}

QMenu {{
    background-color: {SURFACE0};
    color: {TEXT};
    border: 1px solid {SURFACE1};
}}

QMenu::item:selected {{
    background-color: {MAUVE};
    color: {BASE};
}}

QToolBar {{
    background-color: {MANTLE};
    border: none;
}}

QPushButton {{
    background-color: {SURFACE0};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    padding: 4px 12px;
}}

QPushButton:hover {{
    background-color: {SURFACE1};
}}

QPushButton:pressed {{
    background-color: {SURFACE2};
}}

QPushButton:disabled {{
    background-color: {CRUST};
    color: {OVERLAY1};
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {CRUST};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    selection-background-color: {MAUVE};
    selection-color: {BASE};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {BLUE};
}}

QComboBox {{
    background-color: {SURFACE0};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    padding: 4px 8px;
}}

QComboBox:hover {{
    background-color: {SURFACE1};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {SURFACE0};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    selection-background-color: {MAUVE};
    selection-color: {BASE};
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {CRUST};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    padding: 2px 4px;
}}

QLabel {{
    color: {TEXT};
    background-color: transparent;
}}

QTabWidget::pane {{
    border: 1px solid {SURFACE1};
    background-color: {BASE};
}}

QTabBar::tab {{
    background-color: {SURFACE0};
    color: {SUBTEXT0};
    padding: 6px 14px;
    border: 1px solid {SURFACE1};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}

QTabBar::tab:selected {{
    background-color: {BASE};
    color: {TEXT};
}}

QTabBar::tab:hover {{
    background-color: {SURFACE1};
}}

QScrollBar:vertical {{
    background-color: {MANTLE};
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {SURFACE2};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {OVERLAY1};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {MANTLE};
    height: 10px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {SURFACE2};
    min-width: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {OVERLAY1};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QTableView, QTableWidget {{
    background-color: {CRUST};
    alternate-background-color: {MANTLE};
    color: {TEXT};
    gridline-color: {SURFACE1};
    border: 1px solid {SURFACE1};
    selection-background-color: {MAUVE};
    selection-color: {BASE};
}}

QHeaderView::section {{
    background-color: {SURFACE0};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    padding: 4px;
}}

QGroupBox {{
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
    color: {TEXT};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}

QCheckBox {{
    color: {TEXT};
    spacing: 6px;
}}

QRadioButton {{
    color: {TEXT};
    spacing: 6px;
}}

QProgressBar {{
    background-color: {CRUST};
    border: 1px solid {SURFACE1};
    border-radius: 4px;
    text-align: center;
    color: {TEXT};
}}

QProgressBar::chunk {{
    background-color: {MAUVE};
    border-radius: 3px;
}}

QSlider::groove:horizontal {{
    background-color: {SURFACE1};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background-color: {BLUE};
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {LAVENDER};
}}

QToolTip {{
    background-color: {SURFACE0};
    color: {TEXT};
    border: 1px solid {SURFACE1};
    padding: 4px;
}}
"""


# ═══════════════════════════════════════════════════════════════════════════
#  Latte stylesheet (light)
# ═══════════════════════════════════════════════════════════════════════════

LATTE_STYLESHEET = f"""
QMainWindow, QDialog {{
    background-color: {L_BASE};
    color: {L_TEXT};
}}

QWidget {{
    background-color: {L_BASE};
    color: {L_TEXT};
}}

QDockWidget {{
    border: 2px solid {L_SURFACE1};
    titlebar-close-icon: none;
}}

QDockWidget::title {{
    background-color: {L_SURFACE0};
    padding: 4px;
}}

QMenuBar {{
    background-color: {L_MANTLE};
    color: {L_TEXT};
}}

QMenuBar::item:selected {{
    background-color: {L_SURFACE0};
}}

QMenu {{
    background-color: {L_SURFACE0};
    color: {L_TEXT};
    border: 1px solid {L_SURFACE1};
}}

QMenu::item:selected {{
    background-color: {L_MAUVE};
    color: {L_BASE};
}}

QToolBar {{
    background-color: {L_MANTLE};
    border: none;
}}

QPushButton {{
    background-color: {L_SURFACE0};
    color: {L_TEXT};
    border: 1px solid {L_SURFACE1};
    border-radius: 4px;
    padding: 4px 12px;
}}

QPushButton:hover {{
    background-color: {L_SURFACE1};
}}

QPushButton:pressed {{
    background-color: {L_SURFACE2};
}}

QPushButton:disabled {{
    background-color: {L_CRUST};
    color: {L_OVERLAY1};
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {L_CRUST};
    color: {L_TEXT};
    border: 1px solid {L_SURFACE1};
    border-radius: 4px;
    selection-background-color: {L_MAUVE};
    selection-color: {L_BASE};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {L_BLUE};
}}

QComboBox {{
    background-color: {L_SURFACE0};
    color: {L_TEXT};
    border: 1px solid {L_SURFACE1};
    border-radius: 4px;
    padding: 4px 8px;
}}

QComboBox:hover {{
    background-color: {L_SURFACE1};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {L_SURFACE0};
    color: {L_TEXT};
    border: 1px solid {L_SURFACE1};
    selection-background-color: {L_MAUVE};
    selection-color: {L_BASE};
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {L_CRUST};
    color: {L_TEXT};
    border: 1px solid {L_SURFACE1};
    border-radius: 4px;
    padding: 2px 4px;
}}

QLabel {{
    color: {L_TEXT};
    background-color: transparent;
}}

QTabWidget::pane {{
    border: 1px solid {L_SURFACE1};
    background-color: {L_BASE};
}}

QTabBar::tab {{
    background-color: {L_SURFACE0};
    color: {L_SUBTEXT0};
    padding: 6px 14px;
    border: 1px solid {L_SURFACE1};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}

QTabBar::tab:selected {{
    background-color: {L_BASE};
    color: {L_TEXT};
}}

QTabBar::tab:hover {{
    background-color: {L_SURFACE1};
}}

QScrollBar:vertical {{
    background-color: {L_MANTLE};
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {L_SURFACE2};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {L_OVERLAY1};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {L_MANTLE};
    height: 10px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {L_SURFACE2};
    min-width: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {L_OVERLAY1};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QTableView, QTableWidget {{
    background-color: {L_CRUST};
    alternate-background-color: {L_MANTLE};
    color: {L_TEXT};
    gridline-color: {L_SURFACE1};
    border: 1px solid {L_SURFACE1};
    selection-background-color: {L_MAUVE};
    selection-color: {L_BASE};
}}

QHeaderView::section {{
    background-color: {L_SURFACE0};
    color: {L_TEXT};
    border: 1px solid {L_SURFACE1};
    padding: 4px;
}}

QGroupBox {{
    border: 1px solid {L_SURFACE1};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
    color: {L_TEXT};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}

QCheckBox {{
    color: {L_TEXT};
    spacing: 6px;
}}

QRadioButton {{
    color: {L_TEXT};
    spacing: 6px;
}}

QProgressBar {{
    background-color: {L_CRUST};
    border: 1px solid {L_SURFACE1};
    border-radius: 4px;
    text-align: center;
    color: {L_TEXT};
}}

QProgressBar::chunk {{
    background-color: {L_MAUVE};
    border-radius: 3px;
}}

QSlider::groove:horizontal {{
    background-color: {L_SURFACE1};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background-color: {L_BLUE};
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {L_LAVENDER};
}}

QToolTip {{
    background-color: {L_SURFACE0};
    color: {L_TEXT};
    border: 1px solid {L_SURFACE1};
    padding: 4px;
}}
"""
