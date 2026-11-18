"""The entry window's exchange fields, named the way N1MM names them.

A contest declares the boxes it wants with ``EntryWindowInfo``, N1MM's
name/width pair list; this module builds them, keeps them in step when the
contest changes, and gives the rest of the application a named handle on each
one::

    fields.Exchange1Text.text()

The names and defaults come from N1MM's User Defined Contest ``EntryWindowInfo``
table, so a .udc file can later be turned into the same kind of declaration
without inventing a second vocabulary.  ``column`` is the contact column the
box carries in not1mm; N1MM's name for it is in the comment, and the two differ
only for the callsign (N1MM's ``CallSign``, not1mm's ``Call``).

Which fields exist is the contest's business: the module never adds or hides a
box by itself.  A contest that has not migrated yet passes the four legacy
boxes (``LEGACY_NAMES``) and asks for ``legacy=True``; that makes the old
positional names (``sent``, ``receive``, ``other_1``, ``other_2``) work until
every plugin has moved over.

One instance is one entry window's worth of boxes.  The class is not tied to
``MainWindow`` or the database, so a second station (SO2R) can own a second
instance later.
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


@dataclass(frozen=True)
class FieldSpec:
    """One kind of entry-window box."""

    name: str  # N1MM's EntryWindowInfo name; also the QLineEdit objectName
    column: str  # the not1mm contact column the box carries
    label: str  # default frame label
    accessible: str = ""  # default screen-reader name
    max_length: int = 0  # 0 = no limit
    width: int = 1  # relative layout width
    space_advances: bool = True  # False: a space is part of the text
    description: str = ""  # default screen-reader description
    # Which translation context the label lives in.  The exchange labels have
    # always used ContestPlugin; the callsign came from main.ui.
    context: str = "ContestPlugin"


# The exchange boxes, exactly N1MM's table.  `column` is not1mm's contact
# column; where N1MM spells it differently the UDC name is in the comment.
_EXCHANGE_SPECS = (
    FieldSpec("SNTText", "SNT", "SNT", "RST Sent", 10, 450),
    FieldSpec("RCVText", "RCV", "RCV", "RST Received", 15, 450),
    FieldSpec("SntNrText", "SentNr", "SentNR", "Sent Number", 5, 625),
    FieldSpec("RcvNrText", "NR", "RcvNR", "Received Number", 5, 625),
    FieldSpec("Exchange1Text", "Exchange1", "Exch", "Exchange", 12, 615),
    FieldSpec("MiscText", "MiscText", "Misc", "Misc", 15, 600),
    FieldSpec("SectText", "Sect", "Sect", "Section", 15, 600),
    FieldSpec("GridSquareText", "GridSquare", "Grid", "Grid Square", 6, 600),
    FieldSpec("NameText", "Name", "Name", "Name", 20, 855),
    FieldSpec(
        "CommentText",
        "Comment",
        "Comment",
        "Comment",
        60,
        1695,
        space_advances=False,
    ),
)
FIELD_SPECS = {spec.name: spec for spec in _EXCHANGE_SPECS}

# The callsign box is not part of EntryWindowInfo: N1MM always shows it.
# N1MM calls the column CallSign; not1mm stores it in Call.
CALLSIGN_SPEC = FieldSpec(
    "CallSignText",
    "Call",
    "Callsign",
    "callsign",
    width=900,
    description="enter callsign here",
    context="MainWindow",
)

# The default declaration: what a contest with an ordinary RST/serial exchange
# shows, in the old window's order.
DEFAULT_ENTRY_WINDOW = (
    "SNTText",
    450,
    "RCVText",
    450,
    "SntNrText",
    625,
    "RcvNrText",
    625,
)

# The four boxes the old fixed window had, in its order, and the old attribute
# names.  A plugin that has not migrated is described with these.
LEGACY_NAMES = ("SNTText", "RCVText", "SntNrText", "RcvNrText")
LEGACY_ALIASES = {
    "sent": "SNTText",
    "receive": "RCVText",
    "other_1": "SntNrText",
    "other_2": "RcvNrText",
}
# What main.ui used to put above the four boxes before any contest ran.
LEGACY_LABELS = ("SNT", "RCV", "OTHER_1", "OTHER_2")
LEGACY_ACCESSIBLE = (
    "RST Sent",
    "",
    "Sent Number",
    "Received Number",
)
# The labels the old ContestBase put on the four boxes when a plugin did not
# name them itself.
LEGACY_FRAME_TEXT = ("SNT", "SentNR", "RcvNR")


@dataclass
class FieldBox:
    """One box to build: a spec plus this contest's choices for it."""

    spec: FieldSpec
    width: int
    visible: bool = True
    label: str | None = None  # None = the spec's default
    accessible: str | None = None  # None = the spec's default; "" = none


def parse_entry_window_info(info) -> tuple[FieldBox, ...]:
    """N1MM's flat ``(name, width, name, width, ...)`` list as boxes.

    Raises ``ValueError`` for a name that is not an exchange box, a repeated
    name, or an odd-length list -- a typo here would otherwise become a
    silently missing box.
    """
    items = tuple(info)
    if len(items) % 2:
        raise ValueError(
            f"EntryWindowInfo needs name/width pairs, got {len(items)} entries"
        )
    boxes = []
    seen = set()
    for name, width in zip(items[::2], items[1::2]):
        spec = FIELD_SPECS.get(name)
        if spec is None:
            raise ValueError(
                f"EntryWindowInfo: unknown box {name!r}; "
                f"expected one of {', '.join(FIELD_SPECS)}"
            )
        if name in seen:
            raise ValueError(f"EntryWindowInfo: {name} is declared twice")
        seen.add(name)
        try:
            width = int(width)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"EntryWindowInfo: width for {name} is not a number: {width!r}"
            ) from exc
        if width <= 0:
            raise ValueError(f"EntryWindowInfo: width for {name} must be positive")
        boxes.append(FieldBox(spec, width))
    return tuple(boxes)


def legacy_entry_boxes(entry_fields, frame_text=(), rcv_label="", accessible_names=()):
    """The four old boxes, described the way the old window showed them.

    *entry_fields* is the plugin's ``EntryFields`` (the frames it shows);
    *frame_text* is its three-entry ``FrameText`` (sent, other, exchange);
    *rcv_label* overrides the received-report label; *accessible_names* is its
    four-entry ``AccessibleNames``.  An empty FrameText entry keeps the old
    window's default label for that box, which is what it showed when the
    label was not set.
    """
    visible = set(entry_fields)
    widgets = ("field1", "field2", "field3", "field4")
    labels = list(LEGACY_LABELS)
    if not frame_text:
        frame_text = LEGACY_FRAME_TEXT
    if frame_text[0]:
        labels[0] = frame_text[0]
    if len(frame_text) > 1 and frame_text[1]:
        labels[2] = frame_text[1]
    if len(frame_text) > 2 and frame_text[2]:
        labels[3] = frame_text[2]
    if rcv_label:
        labels[1] = rcv_label
    boxes = []
    for index, (name, widget) in enumerate(zip(LEGACY_NAMES, widgets)):
        spec = FIELD_SPECS[name]
        accessible = (
            accessible_names[index]
            if index < len(accessible_names)
            else LEGACY_ACCESSIBLE[index]
        )
        boxes.append(
            FieldBox(
                spec,
                spec.width,
                visible=widget in visible,
                label=labels[index],
                accessible=accessible,
            )
        )
    return tuple(boxes)


class EntryField:
    """One box: a frame holding a label and a line edit."""

    def __init__(self, box: FieldBox, parent: QtWidgets.QWidget, edit_font=None):
        self.box = box
        self.spec = box.spec
        self.name = self.spec.name
        self.frame = QtWidgets.QFrame(parent)
        self.frame.setObjectName(f"{self.name}Frame")
        layout = QtWidgets.QVBoxLayout(self.frame)
        layout.setObjectName(f"{self.name}Layout")
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QtWidgets.QLabel(self.frame)
        self.label.setObjectName(f"{self.name}Label")
        self.label.setAlignment(
            Qt.AlignmentFlag.AlignBottom
            | Qt.AlignmentFlag.AlignLeading
            | Qt.AlignmentFlag.AlignLeft
        )
        self.edit = QtWidgets.QLineEdit(self.frame)
        self.edit.setObjectName(self.name)
        self.edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if self.spec.max_length:
            self.edit.setMaxLength(self.spec.max_length)
        if edit_font is not None:
            self.edit.setFont(edit_font)
        if self.spec.description:
            self.edit.setAccessibleDescription(
                QtWidgets.QApplication.translate(
                    self.spec.context, self.spec.description
                )
            )
        self.edit.setStyleSheet("text-transform: uppercase;")
        layout.addWidget(self.label)
        layout.addWidget(self.edit)
        self.set_label(box.label)
        self.set_accessible(box.accessible)

    def set_label(self, text: str | None) -> None:
        """Show *text* above the box; None keeps the default, "" blanks it."""
        if text is None:
            text = self.spec.label
        self.label.setText(QtWidgets.QApplication.translate(self.spec.context, text))

    def set_accessible(self, name: str | None) -> None:
        """Name the line edit for a screen reader; "" clears the name."""
        if name is None:
            name = self.spec.accessible
        self.edit.setAccessibleName(name)

    def set_visible(self, visible: bool) -> None:
        self.box.visible = visible
        self.frame.setVisible(visible)

    def apply_font(self, family: str, label_point: int, edit_point: int) -> None:
        self.label.setFont(QFont(family, label_point, QFont.Weight.Thin))
        self.edit.setFont(QFont(family, edit_point, QFont.Weight.Thin))

    def apply_palette(self, palette) -> None:
        self.edit.setPalette(palette)

    def set_upper(self, upper: bool = True) -> None:
        self.edit.setStyleSheet(
            "text-transform: uppercase;" if upper else "text-transform: none;"
        )

    def clear(self) -> None:
        self.edit.clear()


class Fields:
    """The entry window's boxes: the callsign, then the contest's exchange."""

    def __init__(
        self, layout: QtWidgets.QBoxLayout, callsign_frame=None, edit_font=None
    ):
        self.layout = layout
        self._boxes: dict[str, EntryField] = {}
        self._key: tuple | None = None
        self._legacy = True
        self._font: tuple | None = None
        self._palette = None
        self._edit_font = edit_font
        self._callsign = self._build_callsign(callsign_frame)
        self.callsign = self._callsign.edit
        self.callsign_label = self._callsign.label
        self.callsign_frame = self._callsign.frame
        # Start with the ordinary four boxes so the window is usable before a
        # contest has been loaded.
        self.configure(legacy_entry_boxes(("field1", "field2", "field3", "field4")))

    # -- the callsign ------------------------------------------------------
    def _build_callsign(self, placeholder) -> EntryField:
        """Build the callsign box, after main.ui's placeholder.

        main.ui keeps a callsign box so Qt Designer shows the entry row, but it
        is created before everything else and so would come first in the TAB
        cycle.  It is removed here and the real box is built with the other
        fields, which puts the callsign after ``cw_entry`` and before the
        exchange boxes -- exactly the intended cycle, without setTabOrder().
        """
        if placeholder is not None:
            self.layout.removeWidget(placeholder)
            placeholder.setParent(None)
            placeholder.deleteLater()
        field = EntryField(
            FieldBox(CALLSIGN_SPEC, CALLSIGN_SPEC.width),
            self.layout.parentWidget(),
            edit_font=self._edit_font,
        )
        field.set_label(None)
        self.layout.insertWidget(0, field.frame, CALLSIGN_SPEC.width)
        return field

    # -- building ----------------------------------------------------------
    def configure(self, boxes, legacy: bool = False) -> bool:
        """Show *boxes*; return True when the widgets themselves were rebuilt.

        Labels, visibility and accessible names are updated in place, so a
        language switch or a contest that hides a field keeps what the operator
        typed.  A different set of boxes (or widths) is rebuilt, because the
        focus chain and the layout have to follow the new row.
        """
        boxes = tuple(boxes)
        self._legacy = legacy
        key = tuple((box.spec.name, box.width) for box in boxes)
        rebuilt = key != self._key
        if rebuilt:
            self._remove_boxes()
            for index, box in enumerate(boxes):
                field = EntryField(
                    box, self.layout.parentWidget(), edit_font=self._edit_font
                )
                self.layout.insertWidget(index + 1, field.frame, box.width)
                self._boxes[field.name] = field
                if self._font is not None:
                    field.apply_font(*self._font)
                if self._palette is not None:
                    field.apply_palette(self._palette)
            self._key = key
        # Re-apply the callsign's own label/name too: a language switch calls
        # this path, and the designer's widgets it came from are gone.
        self._callsign.set_label(None)
        self._callsign.set_accessible(None)
        for box in boxes:
            field = self._boxes[box.spec.name]
            field.box = box
            field.set_visible(box.visible)
            field.set_label(box.label)
            field.set_accessible(box.accessible)
        return rebuilt

    def _remove_boxes(self) -> None:
        for field in self._boxes.values():
            self.layout.removeWidget(field.frame)
            field.frame.setParent(None)
            field.frame.deleteLater()
        self._boxes = {}

    # -- looking a box up --------------------------------------------------
    def __getattr__(self, name: str) -> QtWidgets.QLineEdit:
        """``fields.Exchange1Text`` is that box's line edit."""
        if name in ("callsign", CALLSIGN_SPEC.name):
            callsign = self.__dict__.get("callsign")
            if callsign is not None:
                return callsign
        boxes = self.__dict__.get("_boxes", {})
        if name in boxes:
            return boxes[name].edit
        raise AttributeError(
            f"{name!r} is not a field here; "
            f"have {', '.join(boxes) if boxes else 'none'}"
        )

    def __iter__(self):
        """Every exchange box, in declaration order (hidden ones included)."""
        return iter(self._boxes.values())

    def __len__(self) -> int:
        return len(self._boxes)

    def edit(self, name: str, default=None):
        """The line edit for a box name or an old positional name."""
        if name in ("callsign", CALLSIGN_SPEC.name):
            return self.callsign
        field = self._boxes.get(name)
        if field is not None:
            return field.edit
        if name in LEGACY_ALIASES:
            legacy = self.legacy_edit(name)
            return legacy if legacy is not None else default
        return default

    def field(self, name: str) -> EntryField | None:
        return self._boxes.get(name)

    def names(self) -> tuple:
        """The visible exchange boxes, in display order."""
        return tuple(field.name for field in self._boxes.values() if field.box.visible)

    def all_names(self) -> tuple:
        """Every exchange box, visible or not, in display order."""
        return tuple(self._boxes)

    def display_order(self) -> tuple:
        """The callsign then the visible exchange edits, in display order."""
        return (self.callsign,) + tuple(
            field.edit for field in self._boxes.values() if field.box.visible
        )

    def all_order(self) -> tuple:
        """The callsign then every exchange edit, visible or not."""
        return (self.callsign,) + tuple(field.edit for field in self._boxes.values())

    def index(self, edit) -> int | None:
        """Where *edit* sits in the old positional scheme (0 = callsign)."""
        try:
            return self.all_order().index(edit)
        except ValueError:
            return None

    def last_field(self) -> EntryField | None:
        for field in reversed(self._boxes.values()):
            return field
        return None

    def last_edit(self):
        field = self.last_field()
        return field.edit if field is not None else self.callsign

    def report_edits(self) -> tuple:
        """The sent and received report edits this contest has."""
        return tuple(
            self._boxes[name].edit
            for name in ("SNTText", "RCVText")
            if name in self._boxes
        )

    def by_column(self, column: str) -> EntryField | None:
        for field in self._boxes.values():
            if field.spec.column == column:
                return field
        return None

    # -- the old positional names -----------------------------------------
    def legacy_edit(self, name: str):
        """Resolve ``other_1`` and friends.

        A migrated contest has no fixed slots, so the first and second box that
        is neither report stands in for ``other_1``/``other_2`` -- the same
        boxes in every contest shape the old window could describe.
        """
        if name not in LEGACY_ALIASES:
            return None
        if self._legacy:
            field = self._boxes.get(LEGACY_ALIASES[name])
            return field.edit if field is not None else None
        extras = [
            field
            for field in self._boxes.values()
            if field.spec.column not in ("SNT", "RCV")
        ]
        index = 0 if name == "other_1" else 1
        if index < len(extras):
            return extras[index].edit
        return None

    def legacy_text(self, name: str) -> str:
        edit = self.legacy_edit(name)
        return edit.text() if edit is not None else ""

    def inputs(self) -> dict:
        """The old ``inputs_dict``: line edit -> the name the ESM code uses."""
        if self._legacy:
            names = ("callsign", "sent", "receive", "other_1", "other_2")
        else:
            names = ("CallSignText",) + self.all_names()
        return dict(zip(self.all_order(), names))

    # -- presentation ------------------------------------------------------
    def apply_font(self, family: str, label_point: int = 13, edit_point: int = 20):
        """Use one font for the call box and every exchange box."""
        self._font = (family, label_point, edit_point)
        self._callsign.apply_font(family, label_point, edit_point)
        for field in self._boxes.values():
            field.apply_font(family, label_point, edit_point)

    def apply_palette(self, palette) -> None:
        self._palette = palette
        self._callsign.apply_palette(palette)
        for field in self._boxes.values():
            field.apply_palette(palette)

    def apply_upper(self) -> None:
        """Put the forced upper case back, e.g. after General Logging."""
        for field in self._boxes.values():
            field.set_upper(True)

    def clear_exchange(self) -> None:
        """Clear every exchange box except the two reports."""
        for field in self._boxes.values():
            if field.name not in ("SNTText", "RCVText"):
                field.clear()
