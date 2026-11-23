"""N1MM's ``CabrilloString``: a hand-coded Cabrillo QSO line.

A UDC can replace the standard QSO line with a list of ``field, width`` pairs::

    CabrilloString = SNT, 4, SentNr, 4, CallSign, 13, RCV, 4, RcvNr, 4

The fixed part — ``QSO:``, frequency, mode, date, time and the station call —
comes from the log; the string lays out everything after it.  A field is
left-justified and padded (or truncated) to its width, ``Space`` pads with that
many blanks, and a name not1mm does not know is rendered blank so the columns
after it still line up.

``ContestBase`` builds the line when a contest sets :attr:`CabrilloString`,
whether the contest is a plugin or a UDC.
"""

from __future__ import annotations

from dataclasses import dataclass


class CabrilloStringError(ValueError):
    """A CabrilloString that cannot be parsed."""


@dataclass(frozen=True)
class Field:
    """One column: a value name (None for blanks) and its width."""

    name: str | None
    width: int


@dataclass(frozen=True)
class CabrilloFormat:
    """A parsed CabrilloString."""

    fields: tuple[Field, ...]
    unknown: tuple[str, ...] = ()


# The names the format may use, keyed by their casefolded spelling.
_NAMES = {
    "snt": "SNT",
    "sentnr": "SentNr",
    "callsign": "CallSign",
    "rcv": "RCV",
    "rcvnr": "RcvNr",
    "comment": "Comment",
    "gridsquare": "GridSquare",
    "exchange1": "Exchange1",
    "name": "Name",
    "sentexch": "SentExch",
    "sentexchpart1": "SentExchPart1",
    "sentexchpart2": "SentExchPart2",
    "sentexchpart3": "SentExchPart3",
    "space": "Space",
    # Spellings real UDCs use.
    "sent": "SNT",
    "sntexchpart2": "SentExchPart2",
    "misc": "MiscText",
    "sect": "Sect",
    # N1MM's {LASTEXCH}; not1mm has no previous-exchange store for now.
    "lastexch": None,
}


def parse_cabrillostring(text: str) -> CabrilloFormat:
    """Parse a ``field, width`` list.

    Raises :class:`CabrilloStringError` for an odd list or a width that is not
    a number; an unknown field name is kept as a blank column and reported in
    :attr:`CabrilloFormat.unknown`.
    """
    items = [item.strip() for item in str(text).split(",")]
    while items and not items[-1]:
        items.pop()
    if not items:
        return CabrilloFormat(())
    if len(items) % 2:
        raise CabrilloStringError(
            f"CabrilloString needs name/width pairs, got {len(items)} entries"
        )
    fields = []
    unknown = []
    for name, width in zip(items[::2], items[1::2]):
        try:
            number = int(width)
        except ValueError:
            raise CabrilloStringError(
                f"width for {name!r} is not a number: {width!r}"
            ) from None
        canonical = _NAMES.get(name.casefold(), name)
        if canonical is None:
            unknown.append(name)
            fields.append(Field(None, number))
        elif canonical not in _NAMES.values():
            unknown.append(name)
            fields.append(Field(None, number))
        else:
            fields.append(Field(canonical, number))
    return CabrilloFormat(tuple(fields), tuple(unknown))


def _value(name: str, contact, sent_exchange: str) -> str:
    if name == "SNT":
        return str(contact.get("SNT", ""))
    if name == "SentNr":
        return str(contact.get("SentNr", ""))
    if name == "CallSign":
        return str(contact.get("Call", ""))
    if name == "RCV":
        return str(contact.get("RCV", ""))
    if name == "RcvNr":
        return str(contact.get("NR", ""))
    if name == "Comment":
        return str(contact.get("Comment", ""))
    if name == "GridSquare":
        return str(contact.get("GridSquare", ""))
    if name == "Exchange1":
        return str(contact.get("Exchange1", ""))
    if name == "Name":
        return str(contact.get("Name", ""))
    if name == "MiscText":
        return str(contact.get("MiscText", ""))
    if name == "Sect":
        return str(contact.get("Sect", ""))
    if name == "SentExch":
        return sent_exchange
    if name.startswith("SentExchPart"):
        parts = sent_exchange.split()
        index = int(name[-1]) - 1
        return parts[index] if index < len(parts) else ""
    return ""


def qso_line(
    cabrillo: CabrilloFormat,
    contact,
    *,
    my_call: str,
    mode: str,
    sent_exchange: str = "",
) -> str:
    """One ``QSO:`` line, with the fields laid out by *cabrillo*."""
    stamp = str(contact.get("TS", ""))
    loggeddate = stamp[:10]
    loggedtime = stamp[11:13] + stamp[14:16]
    frequency = str(round(contact.get("Freq", "0"))).rjust(5)
    columns = []
    for field in cabrillo.fields:
        if field.name is None:
            columns.append(" " * field.width)
        else:
            text = _value(field.name, contact, sent_exchange)
            columns.append(text[: field.width].ljust(field.width))
    return (
        f"QSO: {frequency} {mode} {loggeddate} {loggedtime} "
        f"{str(my_call).ljust(13)}" + "".join(columns)
    )
