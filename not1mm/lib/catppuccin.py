"""
Catppuccin Mocha theme for not1mm.

Provides a QPalette and Qt stylesheet using the Catppuccin Mocha palette.
See https://github.com/catppuccin/catppuccin for color definitions.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette

# ── Catppuccin Mocha colours ──────────────────────────────────────────────

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


def _qcolor(hex_str: str) -> QColor:
    """Convert a '#rrggbb' string to QColor."""
    return QColor(hex_str)


# ── Palette ───────────────────────────────────────────────────────────────

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

    p.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        _qcolor(OVERLAY1),
    )
    p.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.HighlightedText,
        _qcolor(OVERLAY1),
    )
    p.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        _qcolor(OVERLAY1),
    )

    return p


# ── Stylesheet ────────────────────────────────────────────────────────────

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
