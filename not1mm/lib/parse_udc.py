"""Read, validate and turn N1MM User Defined Contest (.udc) files into a contest.

A ``.udc`` file is an INI-ish text file in three sections:

    [Author]   who wrote it
    [File]     revision, date, description
    [Contest]  the declarations that decide behaviour

:func:`parse_udc` reads one into a :class:`Udc`, :func:`validate_udc` reports
what is wrong with it, and :func:`contest_from_udc` builds the ``Contest``
class :class:`~not1mm.lib.contest.ContestBase` expects.

The field-by-field reference, including which parameters not1mm applies and
which it only parses, is ``UDC-FIELDS.md`` next to the repository.  Keep the
two in step: the key list here is the loader's, and a new parameter belongs in
both.

Identity
--------

A UDC's ``Name`` is **not** unique: ``AGCW-YLCWP-om.udc`` and
``AGCW-YLCWP-yl.udc`` both declare ``Name = AGCW-YLCWP`` and the same
``CabrilloName``.  A not1mm contest therefore takes its identifier from the
file: the ``.udc``'s stem, which is what the user picks and what distinguishes
the two.  ``UdcName`` keeps N1MM's ``Name`` as metadata, and ``CabrilloName``
still decides the ``CONTEST:`` line, because that is the sponsor's name for
the contest rather than ours.

What is applied
---------------

This is the first phase: identity, entry window, multipliers and the simple
declarations.  A parameter that is parsed but not applied (a rule list in
``PointsPerContact``, a section list in ``MultWindowType``, a hand-coded
``CabrilloString``) is recorded on the class in ``UdcUnimplemented`` so the
application can warn about it and a later phase can find it.  Nothing is
silently dropped.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from not1mm.lib.contest import MULT_KEYS, ContestBase, parse_qso_error_string
from not1mm.lib.fields import DEFAULT_ENTRY_WINDOW, FIELD_SPECS

logger = logging.getLogger("parse_udc")


class UdcError(ValueError):
    """A UDC file that cannot be read, or declares something impossible."""


@dataclass(frozen=True)
class UdcIssue:
    """One thing wrong with a UDC file: an error, or a warning."""

    level: str  # "error" or "warning"
    key: str  # the parameter, or "" for something about the file
    message: str

    def __str__(self) -> str:
        if self.key:
            return f"{self.level}: {self.key}: {self.message}"
        return f"{self.level}: {self.message}"


# -- the parameters --------------------------------------------------------
# The [Author] and [File] sections are metadata: read, kept, and not applied.
AUTHOR_KEYS = ("AuthorName", "Callsign", "Email")
FILE_KEYS = ("Revision", "LastUpdate", "Description", "Note")

# Every [Contest] parameter N1MM documents (see UDC-FIELDS.md).  A file may
# carry keys that are not here -- a newer N1MM -- and they are kept and
# reported, never rejected.
CONTEST_KEYS = (
    "BandChangesPerPeriod",
    "BonusPoints",
    "BonusPoints2",
    "CQZoneMultContest",
    "CabrilloFormat",
    "CabrilloName",
    "CabrilloString",
    "CabrilloVersion",
    "CountBandChangesPerContest",
    "CountBandChangesPerPeriod",
    "CountBandOrModeChange",
    "CountMultOnlyFor",
    "CountMultOnlyFor2",
    "CountMultOnlyFor3",
    "CountMultOnlyForSec",
    "CountMultOnlyForSec2",
    "CountMultOnlyForSec3",
    "DefaultContestExchange",
    "DigitalModeSqlString",
    "DisplayName",
    "DoNotCountMeAsMult",
    "DoNotCountMeAsMult2",
    "DoNotCountMeAsMult3",
    "DoNotCountMultOnlyFor",
    "DoNotCountMultOnlyFor2",
    "DoNotCountMultOnlyFor3",
    "DupeQSOMinutesAgo",
    "DupeSqlString",
    "DupeType",
    "EndOfContest",
    "EntryWindowInfo",
    "FrameText",
    "GenericPrintString",
    "GenericPrintStringHeader",
    "IsMult1Per",
    "IsMult2Per",
    "IsMult3Per",
    "IsMultPer",
    "IsWorkable",
    "LogInfo",
    "MOBandChangeCountMax",
    "MOBandChangeTimerDuration",
    "MinimumOffTime",
    "Mode",
    "MultMult",
    "MultMult2",
    "MultMult3",
    "MultSqlString",
    "MultSqlString2",
    "MultSqlString3",
    "MultWindowType",
    "MultiOpCountableBandChange",
    "MultipleSessions",
    "Multiplier1Name",
    "Multiplier2Name",
    "Multiplier3Name",
    "MultiplierBands",
    "Name",
    "NumMults",
    "OverlayCategory",
    "Period",
    "PointsMultAtTimeGMT",
    "PointsMultAtTimeLocal",
    "PointsMultByBand",
    "PointsMultByCategory",
    "PointsMultByContinent",
    "PointsMultByCountry",
    "PointsMultByMode",
    "PointsPerContact",
    "PowerMult",
    "QsoErrorString",
    "QsoNumbersByBand",
    "ResetMultsEverySession",
    "ResetSNEverySession",
    "SOBandChangeCountMax",
    "SOBandChangeTimerDuration",
    "ScoreSummaryMultNames",
    "SelfSpotAllowed",
    "SetSentTimeForContact",
    "ShowMyCountryStations",
    "ShowWarcBands",
    "SingleOpCountableBandChange",
    "SpecialInstructions",
    "StartOfContest",
    "UsesLASTEXCHmacro",
    "UsesWAECountries",
    "WebAddress",
    "ZoneType",
)  # fmt: skip

# The parameters this phase applies (or applies partly, and reports itself).
APPLIED_KEYS = frozenset(
    {
        "Name",
        "DisplayName",
        "CabrilloName",
        "CabrilloFormat",
        "CabrilloVersion",
        "Mode",
        "DupeType",
        "ZoneType",
        "NumMults",
        "Multiplier1Name",
        "Multiplier2Name",
        "Multiplier3Name",
        "MultSqlString",
        "MultSqlString2",
        "MultSqlString3",
        "IsMultPer",
        "IsMult1Per",
        "IsMult2Per",
        "IsMult3Per",
        "EntryWindowInfo",
        "FrameText",
        "LogInfo",
        "DefaultContestExchange",
        "QsoErrorString",
        "PointsPerContact",
    }
)

# N1MM's own template spells these without the plural "s", and 14 of the 27
# sample files follow the template.  Accept both spellings.
KEY_ALIASES = {
    "pointmultattimelocal": "PointsMultAtTimeLocal",
    "pointmultattimegmt": "PointsMultAtTimeGMT",
}

SECTION_NAMES = {name.casefold(): name for name in ("Author", "File", "Contest")}
KEY_NAMES = {
    name.casefold(): name for name in (*AUTHOR_KEYS, *FILE_KEYS, *CONTEST_KEYS)
}
KEY_NAMES.update(KEY_ALIASES)
KNOWN_KEYS = set(KEY_NAMES.values())

_INTEGER = re.compile(r"[+-]?\d+")
_MODE_NAMES = {
    "cw": "CW",
    "ssb": "SSB",
    "both": "BOTH",
    "mixed": "BOTH",
    "rtty": "RTTY",
    # Real files use these for FT4/FT8 events.  N1MM's documented set is CW,
    # SSB, BOTH and RTTY, but rejecting the files would help nobody.
    "digital": "DIGITAL",
    "digi": "DIGITAL",
}
# N1MM's help says "IARU", but the zones are ITU zones and real files say ITU;
# both mean the same to not1mm, and neither is worth a warning.
_ZONE_TYPES = {"cq": "CQ", "iaru": "IARU", "itu": "IARU"}
_DUPE_TYPES = (1, 2, 3, 4)
_MULT_PER_VALUES = (0, 1, 2, 3, 4)
_CABRILLO_FORMATS = (0, 1, 2, 3, 4, 5, 99)
_MULT_KINDS = {name.casefold(): name for name in MULT_KEYS}
# Spellings the sample files use for a kind the documentation names differently.
# Accepted because dropping the multiplier would be worse, but reported: the
# files are user-contributed and not the specification.
_MULT_KIND_ALIASES = {
    "country": "CountryPrefix",
    "misctext": "Misc",
    "exchange1": "Exchange",
}

# The log window always shows these.  UDC's LogInfo only lists the *extra*
# columns an author can choose (its table is all exchange fields), so a file
# that names neither the date, the call nor the frequency must not hide them.
LOG_INFO_BASE = ("YYYY-MM-DD HH:MM:SS", "Call", "Freq (KHz)", "Mode")

# UDC's LogInfo names, and the log-window column each one means.  Names with
# no not1mm column are dropped (with a warning) rather than invented.
_LOG_COLUMNS = {
    "sentreport": "Snt",
    "sentnr": "SentNr",
    "receivereport": "Rcv",
    "nr": "RcvNr",
    "ismultiplier1": "M1",
    "ismultiplier2": "M2",
    "countryprefix": "PFX",
    "exchange1": "Exchange1",
    "points": "PTS",
    "opname": "Operator",
    "comment": "Comment",
    "sectiontext": "Sect",
    "mode": "Mode",
    "call": "Call",
}

# Labels that make N1MM prefill the received zone into Exchange1Text.
_ZONE_LABELS = ("cqzone", "iaruzone")


@dataclass
class Udc:
    """One parsed UDC file.

    ``source`` is the file stem: not1mm's identifier for the contest, unique
    even when the UDC's ``Name`` is not.  ``sections`` holds every key we read,
    canonicalised where it is known and as written otherwise, so nothing in the
    file is lost.
    """

    source: str
    path: Path | None = None
    sections: dict[str, dict[str, str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def section(self, name: str) -> dict[str, str]:
        """The keys of one section, by its canonical name."""
        canonical = SECTION_NAMES.get(str(name).casefold(), name)
        return self.sections.get(canonical, {})

    def get(self, key: str, default: str = "") -> str:
        """A ``[Contest]`` value by its documented name, case-insensitively."""
        canonical = KEY_NAMES.get(str(key).casefold(), key)
        return self.section("Contest").get(canonical, default)

    @property
    def name(self) -> str:
        """N1MM's short name, e.g. ``AGCW-YLCWP``.  Not unique."""
        return self.get("Name")

    @property
    def display_name(self) -> str:
        """What the picker shows, falling back to ``Name`` and the file stem."""
        return self.get("DisplayName") or self.name or self.source

    @property
    def cabrillo_name(self) -> str:
        """The ``CONTEST:`` value, falling back to ``Name`` and the file stem."""
        return self.get("CabrilloName") or self.name or self.source


def _decode(data: bytes, path: Path | None) -> str:
    """Text from a UDC file: UTF-8 (often with a BOM), or Windows-1252."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UdcError(f"{path or '<text>'}: not UTF-8 or CP1252")


def parse_udc(path: str | Path, *, source: str | None = None) -> Udc:
    """Parse the ``.udc`` file at *path*.

    *source* overrides the identifier (the file stem is the default), for a
    caller that has to disambiguate two files with the same name.
    """
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise UdcError(f"{path}: {exc.strerror or exc}") from exc
    return parse_udc_text(_decode(data, path), source or path.stem, path=path)


def parse_udc_text(text: str, source: str, path: Path | None = None) -> Udc:
    """Parse UDC text, as :func:`parse_udc` does from a file.

    Tolerates what the editor and the hand-edited files do: a BOM, CRLF, no
    space around ``=``, mixed case in keys and values, empty values, comment
    lines starting with ``;`` or ``#``, and unknown keys or sections (kept and
    warned about, never rejected).
    """
    udc = Udc(source=source, path=path)
    section: str | None = None

    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip().lstrip("\ufeff")
        if not line or line[0] in ";#":
            continue
        if line.startswith("[") and line.endswith("]"):
            written = line[1:-1].strip()
            if any(character in written for character in ",;="):
                # A parameter's value list pasted where a header belongs
                # (WIA_VHFUHF.udc has "[AllowableTime, CompareToSecond, ...]").
                # Keeping the current section is better than losing every key
                # below it to a section that cannot exist.
                udc.warnings.append(
                    f"line {number}: not a section header: {line!r}; ignored"
                )
                continue
            canonical = SECTION_NAMES.get(written.casefold())
            if canonical is None:
                udc.warnings.append(f"line {number}: unknown section [{written}]")
                section = written  # keep its keys, they are still data
            else:
                section = canonical
            udc.sections.setdefault(section, {})
            continue
        if section is None:
            udc.warnings.append(f"line {number}: {line!r} is outside a section")
            continue
        if "=" not in line:
            udc.warnings.append(f"line {number}: no '=' in {line!r}")
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            udc.warnings.append(f"line {number}: missing key before '='")
            continue
        name = KEY_NAMES.get(key.casefold(), key)
        if name not in KNOWN_KEYS:
            udc.warnings.append(f"line {number}: unknown key {key!r} in [{section}]")
        bucket = udc.sections[section]
        if name in bucket:
            # N1MM's documentation never mentions a repeated key, so which one
            # N1MM reads is undocumented.  The editor writes its defaults after
            # the values, so a file that was once a template can end up with
            # the same key twice (ARIRTTY.UDC: "IsMultPer =1", later an empty
            # "IsMultPer =").  Keep the first non-empty value -- the author's --
            # and never let an empty repeat erase it.  Warn either way.
            if not value:
                udc.warnings.append(
                    f"line {number}: {name} repeats empty; " f"keeping {bucket[name]!r}"
                )
            elif not bucket[name]:
                bucket[name] = value
                udc.warnings.append(
                    f"line {number}: {name} had no value; using {value!r}"
                )
            elif bucket[name] != value:
                udc.warnings.append(
                    f"line {number}: {name} repeats; "
                    f"keeping {bucket[name]!r}, ignoring {value!r}"
                )
            continue
        bucket[name] = value

    if "Contest" not in udc.sections:
        raise UdcError(f"{source}: no [Contest] section")
    return udc


# -- where the files live --------------------------------------------------
# UDCs shipped with not1mm, and the user's own.  A user file wins when the two
# have the same name (stem), because that is how a user overrides a bundled
# contest without editing the package.
BUNDLED_UDC_DIR = Path(__file__).resolve().parents[1] / "data" / "udc"


def udc_directories() -> tuple[Path, ...]:
    """The directories .udc files are read from, in precedence order."""
    from not1mm import fsutils

    return (BUNDLED_UDC_DIR, Path(fsutils.UDC_PATH))


def udc_files(directories=None) -> dict[str, Path]:
    """``stem -> path`` for every .udc file found.

    *directories* defaults to :func:`udc_directories`.  Later directories win,
    so the user's copy of a name replaces the bundled one.
    """
    found: dict[str, Path] = {}
    for directory in udc_directories() if directories is None else directories:
        directory = Path(directory)
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
            if path.is_file() and path.suffix.casefold() == ".udc":
                found[path.stem] = path
    return found


# -- the value grammars ----------------------------------------------------


def _boxes(value: str) -> tuple:
    """``EntryWindowInfo`` as not1mm's flat ``(name, width, ...)`` tuple."""
    items = [item.strip() for item in value.split(",")]
    while items and not items[-1]:
        items.pop()
    if not items:
        return ()
    if len(items) % 2:
        raise ValueError(
            f"EntryWindowInfo needs name/width pairs, got {len(items)} entries"
        )
    # N1MM names are not case-sensitive, and files write "SntText".
    canonical = {name.casefold(): name for name in FIELD_SPECS}
    names = []
    for written in items[::2]:
        name = canonical.get(written.casefold())
        if name is None:
            raise ValueError(
                f"unknown box {written!r}; expected one of {', '.join(FIELD_SPECS)}"
            )
        names.append(name)
    if len(set(names)) != len(names):
        raise ValueError("a box is declared twice")
    pairs = []
    for name, width in zip(names, items[1::2]):
        try:
            pairs.append((name, int(width)))
        except ValueError:
            raise ValueError(f"width for {name} is not a number: {width!r}") from None
    return tuple(item for pair in pairs for item in pair)


def _labels(value: str, count: int) -> tuple:
    """``FrameText`` as one label per box; missing labels are blank."""
    labels = tuple(value.split())
    return labels + ("",) * max(0, count - len(labels))


def _log_columns(value: str) -> tuple[list[str], list[str]]:
    """``LogInfo`` as not1mm column names, plus the names we cannot show."""
    items = [item.strip() for item in value.split(",")]
    while items and not items[-1]:
        items.pop()
    if not items:
        return [], []
    if len(items) % 2:
        raise ValueError(f"LogInfo needs name/width pairs, got {len(items)} entries")
    columns: list[str] = []
    unsupported: list[str] = []
    for name in items[::2]:
        column = _LOG_COLUMNS.get(name.casefold())
        if column is None:
            unsupported.append(name)
        elif column not in columns:
            columns.append(column)
    return columns, unsupported


def _mult_kind(value: str) -> tuple[str | None, bool]:
    """``MultSqlString`` as a not1mm key.  The flag says whether we know it."""
    text = value.strip()
    folded = text.casefold()
    if not text or folded in ("n/a", "na", "none"):
        return None, True
    folded = _MULT_KIND_ALIASES.get(folded, folded)
    return _MULT_KINDS.get(folded.casefold()), folded.casefold() in _MULT_KINDS


def _number(value: str, default: int, allowed: tuple | None = None) -> int:
    """An integer parameter, with N1MM's default for an empty value."""
    text = str(value).strip()
    if not text:
        return default
    number = int(text)
    if allowed is not None and number not in allowed:
        raise ValueError(f"{number} is not one of {', '.join(map(str, allowed))}")
    return number


def _safe_number(value: str, default: int, allowed: tuple | None = None) -> int:
    """As :func:`_number`, but a bad value falls back to the default."""
    try:
        return _number(value, default, allowed)
    except (TypeError, ValueError):
        return default


# -- validation ------------------------------------------------------------


def validate_udc(udc: Udc) -> list[UdcIssue]:
    """Everything wrong with *udc*.

    An ``error`` stops :func:`contest_from_udc`; a ``warning`` is a parameter
    that is unimplemented, ignored, or filled in from a default.
    """
    issues = [UdcIssue("warning", "", message) for message in udc.warnings]

    def error(key: str, message: str) -> None:
        issues.append(UdcIssue("error", key, message))

    def warn(key: str, message: str) -> None:
        issues.append(UdcIssue("warning", key, message))

    contest = udc.section("Contest")
    if not contest:
        error("", "no [Contest] section")
        return issues

    if not udc.get("Name").strip():
        error("Name", "a UDC contest needs a Name")
    if not udc.get("DisplayName").strip():
        warn("DisplayName", f"empty; the picker will show {udc.display_name!r}")
    if not udc.get("CabrilloName").strip():
        warn("CabrilloName", f"empty; CONTEST: will be {udc.cabrillo_name!r}")

    mode = udc.get("Mode").strip()
    if mode and mode.casefold() not in _MODE_NAMES:
        error("Mode", f"{mode!r} is not CW, SSB, BOTH or RTTY")

    zone = udc.get("ZoneType").strip()
    if zone and zone.casefold() not in _ZONE_TYPES:
        error("ZoneType", f"{zone!r} is not CQ or IARU")

    for key, default, allowed in (
        ("DupeType", 2, _DUPE_TYPES),
        ("NumMults", 1, (0, 1, 2, 3)),
        ("IsMultPer", 4, _MULT_PER_VALUES),
        ("IsMult1Per", None, _MULT_PER_VALUES),
        ("IsMult2Per", None, _MULT_PER_VALUES),
        ("IsMult3Per", None, _MULT_PER_VALUES),
        ("CabrilloFormat", 1, _CABRILLO_FORMATS),
    ):
        text = udc.get(key).strip()
        if not text:
            continue
        try:
            _number(text, 0 if default is None else default, allowed)
        except ValueError as exc:
            error(key, str(exc))

    if (
        udc.get("IsMultPer").strip()
        and _safe_number(udc.get("IsMultPer"), 4, _MULT_PER_VALUES) == 0
        and udc.get("NumMults").strip()
    ):
        warn("IsMultPer", "0 means no multipliers; NumMults is ignored")

    boxes = ()
    if udc.get("EntryWindowInfo").strip():
        try:
            boxes = _boxes(udc.get("EntryWindowInfo"))
            if not boxes:
                error("EntryWindowInfo", "declares no boxes")
        except ValueError as exc:
            error("EntryWindowInfo", str(exc))
    else:
        warn("EntryWindowInfo", "empty; the standard four boxes are used")

    if boxes:
        count = len(boxes) // 2
        labels = tuple(udc.get("FrameText").split())
        if len(labels) > count:
            warn(
                "FrameText",
                f"{len(labels)} labels for {count} boxes; the extras are ignored",
            )

    if udc.get("LogInfo").strip():
        try:
            _columns, dropped = _log_columns(udc.get("LogInfo"))
        except ValueError as exc:
            error("LogInfo", str(exc))
        else:
            if dropped:
                warn(
                    "LogInfo",
                    f"no log-window column for {', '.join(dropped)}; dropped",
                )

    points = udc.get("PointsPerContact").strip()
    if points and not _INTEGER.fullmatch(points):
        warn(
            "PointsPerContact",
            "rule lists are not implemented yet; contacts will score 1 point",
        )

    for slot, key in (
        (1, "MultSqlString"),
        (2, "MultSqlString2"),
        (3, "MultSqlString3"),
    ):
        text = udc.get(key).strip()
        if not text:
            continue
        _kind, known = _mult_kind(text)
        if not known:
            warn(
                key,
                f"{text!r} is not a multiplier kind not1mm knows; "
                f"multiplier {slot} will have none",
            )
        elif text.casefold() in _MULT_KIND_ALIASES:
            warn(
                key,
                f"{text!r} is not the documented spelling; "
                f"read as {_MULT_KIND_ALIASES[text.casefold()]!r}",
            )

    # NumMults counts multiplier *types*, so a file that declares one but gives
    # no key has none at all -- not "one multiplier that is always zero".
    declared = _safe_number(udc.get("NumMults"), 1, (0, 1, 2, 3))
    with_key = [
        slot
        for slot, key in (
            (1, "MultSqlString"),
            (2, "MultSqlString2"),
            (3, "MultSqlString3"),
        )
        if _mult_kind(udc.get(key))[0] is not None
    ]
    if declared and not with_key:
        warn("NumMults", f"{declared} declared, but no MultSqlString has a key")
    elif with_key and max(with_key) > declared:
        warn(
            "NumMults",
            f"{declared} declared, but MultSqlString{max(with_key)} has a key; "
            "that multiplier is ignored",
        )
    elif declared > len(with_key):
        warn(
            "NumMults",
            f"{declared} declared, but only {len(with_key)} have a key",
        )

    cabrillo_format = udc.get("CabrilloFormat").strip()
    if cabrillo_format and cabrillo_format != "1":
        warn(
            "CabrilloFormat",
            f"{cabrillo_format} is not implemented; not1mm writes the "
            "standard QSO line",
        )

    cabrillo_version = udc.get("CabrilloVersion").strip()
    if cabrillo_version and cabrillo_version not in ("3", "3.0"):
        warn(
            "CabrilloVersion",
            f"{cabrillo_version} is not implemented; not1mm always writes "
            "START-OF-LOG: 3.0",
        )

    qso_error = udc.get("QsoErrorString").strip()
    if qso_error:
        default_box = boxes[-2] if boxes else "Exchange1Text"
        try:
            parse_qso_error_string(qso_error, default_box)
        except ValueError as exc:
            message = str(exc).removeprefix("QsoErrorString: ")
            warn(
                "QsoErrorString",
                f"{message}; the received exchange will not be checked",
            )

    for key in CONTEST_KEYS:
        if key in APPLIED_KEYS:
            continue
        if udc.get(key).strip():
            warn(key, "parsed, but not applied by not1mm yet")

    return issues


# -- the contest factory ---------------------------------------------------


def _multiplier_attributes(udc: Udc, unimplemented: list[str]) -> dict:
    """The ``NumMults``/``MultiplierN``/``IsMultNPer`` attributes."""
    declared = _safe_number(udc.get("NumMults"), 1, (0, 1, 2, 3))
    per_default_text = udc.get("IsMultPer").strip()
    per_default = _safe_number(per_default_text, 4, _MULT_PER_VALUES)

    attributes = {"NumMults": declared, "IsMultPer": per_default}
    highest = 0
    for slot in (1, 2, 3):
        key = "MultSqlString" if slot == 1 else f"MultSqlString{slot}"
        kind, known = _mult_kind(udc.get(key))
        if udc.get(key).strip() and not known:
            unimplemented.append(key)
        if kind is not None:
            highest = slot
        per = _safe_number(udc.get(f"IsMult{slot}Per"), per_default, _MULT_PER_VALUES)
        attributes[f"Multiplier{slot}Name"] = udc.get(f"Multiplier{slot}Name") or None
        attributes[key] = kind
        attributes[f"IsMult{slot}Per"] = per

    # A declared multiplier with no key would make calc_score() multiply by
    # zero, so the number of multipliers is what the keys actually say, up to
    # what NumMults allows.  IsMultPer = 0 is UDC's "no multipliers".
    attributes["NumMults"] = 0 if per_default == 0 else min(declared, highest)
    return attributes


def contest_from_udc(udc: Udc) -> type[ContestBase]:
    """The ``Contest`` class *udc* describes.

    The class's identifier is ``udc.source`` (the file stem), so two files that
    share a UDC ``Name`` still get distinct contests.  Anything not applied in
    this phase is listed in ``UdcUnimplemented``; ``UdcRaw`` keeps the whole
    ``[Contest]`` section for later phases.
    """
    errors = [issue for issue in validate_udc(udc) if issue.level == "error"]
    if errors:
        raise UdcError(f"{udc.source}: " + "; ".join(str(issue) for issue in errors))

    unimplemented: list[str] = []

    mode = _MODE_NAMES.get(udc.get("Mode").strip().casefold(), "CW")
    dupe_type = _safe_number(udc.get("DupeType"), 2, _DUPE_TYPES)
    zone_type = _ZONE_TYPES.get(udc.get("ZoneType").strip().casefold(), "CQ")

    boxes = ()
    if udc.get("EntryWindowInfo").strip():
        boxes = _boxes(udc.get("EntryWindowInfo"))
    if not boxes:
        boxes = DEFAULT_ENTRY_WINDOW
    count = len(boxes) // 2
    labels = _labels(udc.get("FrameText"), count)[:count]
    if any(label.casefold() in _ZONE_LABELS for label in labels):
        unimplemented.append("FrameText")  # the CQZone/IARUZone prefill

    if udc.get("LogInfo").strip():
        declared, dropped = _log_columns(udc.get("LogInfo"))
        columns = list(LOG_INFO_BASE)
        for column in declared:
            if column not in columns:
                columns.append(column)
    else:
        dropped = []
        columns = list(ContestBase.LogInfo)
    unimplemented.extend(f"LogInfo:{name}" for name in dropped)

    box_names = boxes[::2]
    box_columns = [FIELD_SPECS[name].column for name in box_names]
    received_column = next(
        (column for column in reversed(box_columns) if column not in ("SNT", "RCV")),
        "NR",
    )
    sent_column = "SentNr" if "SentNr" in box_columns else ""

    points_text = udc.get("PointsPerContact").strip()
    if points_text and not _INTEGER.fullmatch(points_text):
        unimplemented.append("PointsPerContact")
        points = 1  # UDC's default, until the rule grammar lands
    else:
        points = _safe_number(points_text, 1)

    cabrillo_format = udc.get("CabrilloFormat").strip()
    if cabrillo_format and cabrillo_format != "1":
        unimplemented.append("CabrilloFormat")
    cabrillo_version = udc.get("CabrilloVersion").strip()
    if cabrillo_version and cabrillo_version not in ("3", "3.0"):
        unimplemented.append("CabrilloVersion")

    qso_error = udc.get("QsoErrorString").strip() or None
    if qso_error:
        default_box = boxes[-2]
        try:
            parse_qso_error_string(qso_error, default_box)
        except ValueError:
            # A section-list name; the base then keeps its single-box check.
            unimplemented.append("QsoErrorString")
            qso_error = None

    for key in CONTEST_KEYS:
        if key in APPLIED_KEYS:
            continue
        if udc.get(key).strip() and key not in unimplemented:
            unimplemented.append(key)

    attributes = {
        "DisplayName": udc.display_name,
        "CabrilloName": udc.cabrillo_name,
        "ContestName": udc.source,
        "Mode": mode,
        "DupeType": dupe_type,
        "ZoneType": zone_type,
        "PointsPerContact": points,
        "EntryWindowInfo": boxes,
        "FrameText": labels,
        "LogInfo": columns,
        "DefaultContestExchange": udc.get("DefaultContestExchange"),
        "QsoErrorString": qso_error,
        "UdcName": udc.name,
        "UdcPath": str(udc.path) if udc.path else "",
        "UdcAuthor": dict(udc.section("Author")),
        "UdcFile": dict(udc.section("File")),
        "UdcReceivedColumn": received_column,
        "UdcSentColumn": sent_column,
        "cabrillo_qso_line": _udc_cabrillo_qso_line,
        "UdcRaw": dict(udc.section("Contest")),
    }
    attributes.update(_multiplier_attributes(udc, unimplemented))
    attributes["UdcUnimplemented"] = tuple(dict.fromkeys(unimplemented))

    contest_class = type("Contest", (ContestBase,), attributes)
    contest_class.__module__ = __name__
    contest_class.__qualname__ = f"UdcContest[{udc.source}]"
    return contest_class


def _udc_cabrillo_qso_line(self, contact) -> str:
    """The standard ``QSO:`` line, with the UDC's own exchange columns.

    :meth:`ContestBase.cabrillo_qso_line` always prints ``SentNr`` and ``NR``;
    a UDC puts the received exchange where its declaration says (``Exchange1``,
    ``MiscText``, ``Sect``, ``GridSquare``).  The factory records the last
    declared exchange box, because that is the received exchange -- the same
    box ESM treats as the one that finishes the contact.
    """
    the_date_and_time = contact.get("TS", "")
    loggeddate = the_date_and_time[:10]
    loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
    frequency = str(round(contact.get("Freq", "0"))).rjust(5)
    sent = str(contact.get(self.UdcSentColumn, ""))
    received = str(contact.get(self.UdcReceivedColumn, ""))
    return (
        f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
        f"{loggeddate} {loggedtime} "
        f"{contact.get('StationPrefix', '').ljust(13)} "
        f"{str(contact.get('SNT', '')).ljust(3)} "
        f"{sent.ljust(6)} "
        f"{contact.get('Call', '').ljust(13)} "
        f"{str(contact.get('RCV', '')).ljust(3)} "
        f"{received.ljust(6)}"
    )


def load_udc(path: str | Path, parent) -> ContestBase:
    """Parse the ``.udc`` file at *path* and bind its contest to *parent*."""
    return contest_from_udc(parse_udc(path))(parent)
