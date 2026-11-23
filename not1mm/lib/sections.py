"""N1MM section lists: the ``.sec`` files.

A section list is a text file with a type line and then one code per line::

    Type=ARI_SEZ  SubType=
    A01
    A02

N1MM calls the whole thing a section list.  A UDC's ``MultWindowType`` names
one and ``QsoErrorString`` can validate the received exchange against it.  The
files are read from ``not1mm/data/sec/`` (shipped) and the user's
``fsutils.SEC_PATH``; a user file with the same name wins, as for UDC files.

A contest names the list it wants with ``ContestBase.MultWindowType`` and reads
the codes from ``section_list``.  The name is the **file name**: N1MM's
``Type=`` line is metadata (what the codes mean), never a lookup key, because
generically named lists (``Section.sec``) would then collide between packages.
The module knows nothing about any particular list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


class SectionListError(ValueError):
    """A .sec file that cannot be read or holds no codes."""


@dataclass(frozen=True)
class SectionList:
    """One .sec file: its type name, sub-type and codes."""

    name: str
    subtype: str
    codes: frozenset[str]
    path: Path | None = None

    def __contains__(self, code) -> bool:
        return str(code).strip().upper() in self.codes


BUNDLED_SEC_DIR = Path(__file__).resolve().parents[1] / "data" / "sec"

_TYPE_LINE = re.compile(r"^\s*type\s*=\s*(\S+)(?:\s+subtype\s*=\s*(\S*))?\s*$", re.I)


def _decode(data: bytes, path: Path | None) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise SectionListError(f"{path or '<text>'}: not UTF-8 or CP1252")


def parse_sec_text(text: str, source: str, path: Path | None = None) -> SectionList:
    """Parse .sec text.  The type line is optional; *source* names the list then."""
    name = source
    subtype = ""
    codes: set[str] = set()
    first = True
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line:
            continue
        if first:
            first = False
            match = _TYPE_LINE.match(line)
            if match:
                name = match.group(1)
                subtype = match.group(2) or ""
                continue
        codes.add(line.upper())
    if not codes:
        raise SectionListError(f"{source}: no codes")
    return SectionList(name=name, subtype=subtype, codes=frozenset(codes), path=path)


def parse_sec(path: str | Path, *, source: str | None = None) -> SectionList:
    """Parse the .sec file at *path*."""
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SectionListError(f"{path}: {exc.strerror or exc}") from exc
    return parse_sec_text(_decode(data, path), source or path.stem, path=path)


def sec_directories() -> tuple[Path, ...]:
    """The directories .sec files are read from, in precedence order."""
    from not1mm import fsutils

    return (BUNDLED_SEC_DIR, Path(fsutils.SEC_PATH))


def sec_files(directories=None) -> dict[str, Path]:
    """``name -> path`` for every .sec file; a later directory wins."""
    found: dict[str, Path] = {}
    for directory in sec_directories() if directories is None else directories:
        directory = Path(directory)
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
            if path.is_file() and path.suffix.casefold() == ".sec":
                found[path.stem.casefold()] = path
    return found


@lru_cache(maxsize=256)
def _cached(path: Path) -> SectionList:
    return parse_sec(path)


def load_sec(name: str, directories=None) -> SectionList | None:
    """The .sec file called *name*, by its file name only.

    The ``Type`` line is metadata: it says what the codes mean, not where to
    find them.  Loading a list by its Type would make a generic ``Section``
    resolve to whichever package happened to ship one.
    """
    if not name:
        return None
    path = sec_files(directories).get(str(name).strip().casefold())
    return _cached(path) if path is not None else None


def clear_cache() -> None:
    """Forget parsed files (used when a list is edited or a test replaces one)."""
    _cached.cache_clear()
