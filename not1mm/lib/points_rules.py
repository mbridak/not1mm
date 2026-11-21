"""Contest points as a rule list, parsed and evaluated.

A contest can spell the points for a contact as a plain number or as a list of
``criterion, points`` pairs (N1MM's ``PointsPerContact`` grammar)::

    40m, 1, 80m, 2, 160m, 3
    MyCountry, 1, SameContinent, 2, OtherContinent, 3
    ExchIsNum, 2, ExchIsNotNum, 1
    Exchange, *

:func:`parse_points` turns the text into a :class:`Points` table;
:class:`~not1mm.lib.contest.ContestBase` evaluates it in ``points()`` when a
contest sets ``PointsRules``, with the contact, the station, the ``cty.dat``
lookup and the sent exchange.  The UDC factory sets the same attribute from a
file.

The rules follow N1MM's help:

* band, mode, country and continent are the criteria; when more than one
  matches the order is **band, mode, country, continent** (the help lists
  continent before country, but that would make ``MyCountry`` unreachable in
  ``MyCountry, 1, SameContinent, 2``, which the files clearly do not mean);
* a more explicit rule (``ExchIs_``, ``SectIs_``, a suffix, ``MyGrid``, ...)
  wins by position, so a file lists those first;
* a value with a leading ``+`` adds to the points instead of replacing them;
* a bare number where a rule would go is the default score;
* a distance table (``1/600/10; 601/1200/13``) replaces the rules with
  kilometres.

N1MM's note that a VHF contest multiplies the distance by a plain
``PointsPerContact`` is *not* implemented; the caller reports that case.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from not1mm.lib.ham_utility import band_mhz_of, distance, get_not1mm_band


class PointsRulesError(ValueError):
    """A ``PointsPerContact`` value the reader cannot understand."""


@dataclass(frozen=True)
class Rule:
    """One criterion and what a matching contact is worth."""

    kind: str
    arg: object = None
    points: int | None = 0  # None = take the number out of the field
    additive: bool = False


@dataclass(frozen=True)
class Points:
    """A parsed ``PointsPerContact`` declaration."""

    raw: str = ""
    default: int = 0
    rules: tuple[Rule, ...] = ()
    distance: tuple[tuple[float, float, int], ...] = ()

    @property
    def is_rules(self) -> bool:
        """True when the value needs the contact to score, not just a number."""
        return bool(self.rules or self.distance)


_MODE_TOKENS = {
    "cw": {"CW", "CW-U", "CW-L", "CW-R", "CWR"},
    "ssb": {"SSB", "USB", "LSB", "PH"},
    "usb": {"USB"},
    "lsb": {"LSB"},
    # DIGI is its own N1MM mode; RTTY and PSK are listed separately when a
    # contest treats them differently, so they are not folded in here.
    "digi": {
        "DIGI",
        "DATA",
        "FT8",
        "FT4",
        "FSK441",
        "MSK144",
        "JT65",
        "JT9",
        "Q65",
        "PKTUSB",
        "PKTLSB",
        "OLIVIA",
        "JS8",
    },
    "rtty": {"RTTY", "RY"},
    "psk": {"PSK", "PSK31"},
    "fm": {"FM"},
    "am": {"AM"},
    "ft8": {"FT8"},
    "ft4": {"FT4"},
}
_CONTINENTS = {"af", "as", "eu", "na", "sa", "oc", "an"}
_BAND_TOKEN = re.compile(r"^\d+(?:\.\d+)?(?:m|cm|mm|mc)$", re.I)
_VALUE = re.compile(r"^(\+?)(\d+)(\*?)$")

# Explicit rules, checked before the prefixed ones.
_EXPLICIT = {
    "ismisc": "is_misc",
    "iscomment": "is_comment",
    "isexch": "exch",
    "exch": "exch",
    "exchange": "exch",
    "misc": "misc",
    "exchisnum": "exch_num",
    "miscisnum": "misc_num",
    "exchisnotnum": "exch_not_num",
    "miscisnotnum": "misc_not_num",
    "exchis_empty": "exch_empty",
    "miscis_empty": "misc_empty",
    "mygrid": "my_grid",
    "mycqzone": "my_cq_zone",
    "myiaruzone": "my_iaru_zone",
    "myexchange": "my_exchange",
    "mycountry": "country",
    "mycontinent": "continent",
}


def _value(token: str) -> tuple[int | None, bool] | None:
    """``(points, additive)`` for a value token, or None if it is not one."""
    if token in ("*", "+*"):
        return None, token.startswith("+")
    match = _VALUE.match(token)
    if match is None:
        return None
    return int(match.group(2)), bool(match.group(1))


def _band(token: str) -> float | None:
    """A band token as MHz, or None when it is not a band.

    ``SameContinent+80`` writes the band without the ``m``, so a bare number
    is read as metres too.
    """
    text = token.strip().casefold()
    if _BAND_TOKEN.match(text):
        return get_not1mm_band(text) or None
    if text.isdigit():
        return get_not1mm_band(text + "m") or None
    return None


def _rule(token: str) -> Rule:
    """One criterion token as a Rule (its points are filled in later)."""
    folded = token.casefold()

    if folded.startswith("/") and len(folded) > 1:
        return Rule("suffix", folded.upper())

    if "+" in folded:
        head, _, band = folded.partition("+")
        if head in ("samecontinent", "othercontinent") and (mhz := _band(band)):
            kind = (
                "same_continent_band"
                if head == "samecontinent"
                else "other_continent_band"
            )
            return Rule(kind, mhz)

    if folded == "isdigi":
        return Rule("mode", _MODE_TOKENS["digi"])

    if folded in _EXPLICIT:
        kind = _EXPLICIT[folded]
        if kind == "continent":
            return Rule("continent", "same")
        if kind == "country":
            return Rule("country", "MY")
        return Rule(kind)

    if folded in _MODE_TOKENS:
        return Rule("mode", _MODE_TOKENS[folded])

    if folded in _CONTINENTS:
        return Rule("continent", folded.upper())

    if folded in ("samecontinent", "othercontinent"):
        return Rule("continent", "same" if folded == "samecontinent" else "other")

    if (mhz := _band(token)) is not None:
        return Rule("band", mhz)

    # SectIs_XXX / ExchIs_XXX / MiscIs_XXX, and ExchIsXXX (contains).
    for prefix, kind in (
        ("sectis_", "sect_is"),
        ("exchis_", "exch_is"),
        ("miscis_", "misc_is"),
    ):
        if folded.startswith(prefix):
            return Rule(kind, token[len(prefix) :].upper())
    if folded.startswith("exchis") and len(token) > len("exchis"):
        return Rule("exch_contains", token[len("exchis") :].upper())

    if token.startswith("+") or token.startswith("-"):
        raise PointsRulesError(f"{token!r} is not a points rule")

    # Anything left is a country prefix from wl_cty.dat.
    return Rule("country", token.upper())


def _distance_table(text: str) -> tuple[tuple[float, float, int], ...]:
    rows = []
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        pieces = [piece.strip() for piece in part.split("/")]
        if len(pieces) != 3:
            raise PointsRulesError(f"{part!r} is not a low/high/points row")
        try:
            low, high, points = (float(pieces[0]), float(pieces[1]), int(pieces[2]))
        except ValueError as exc:
            raise PointsRulesError(f"{part!r} is not a low/high/points row") from exc
        rows.append((low, high, points))
    if not rows:
        raise PointsRulesError("an empty distance table")
    return tuple(rows)


def parse_points(text: str) -> Points:
    """Parse a ``PointsPerContact`` value.

    Raises :class:`PointsRulesError` for a value that is neither a number, a
    distance table nor a well-formed ``rule, points`` list.
    """
    text = str(text).strip()
    if not text:
        return Points(raw=text)

    value = _value(text)
    if value is not None and value[0] is not None:
        return Points(raw=text, default=value[0])

    if "/" in text and "," not in text:
        # One row has no ";" ("1/600/10"), so try the table before the rules
        # and fall through when it is not one (a country prefix with a slash,
        # such as "JD/o").
        try:
            return Points(raw=text, distance=_distance_table(text))
        except PointsRulesError:
            pass

    # Commas are the documented separator, but real files leave them out
    # ("20m 1", "DIGI 3"), and no token may contain a space, so split on both.
    tokens = [token for token in re.split(r"[\s,]+", text) if token]
    rules: list[Rule] = []
    default = 0
    pending: Rule | None = None
    for token in tokens:
        if pending is None:
            value = _value(token)
            if value is not None:
                # A bare number where a rule belongs is the default score
                # ("1, ZS, 5"): one point for everything else.
                if value[0] is None:
                    raise PointsRulesError(f"'*' has no field before it in {text!r}")
                default = value[0] if not value[1] else default + value[0]
                continue
            pending = _rule(token)
            continue

        value = _value(token)
        if value is None:
            raise PointsRulesError(
                f"{pending.kind}{'' if pending.arg is None else f' {pending.arg}'} "
                f"has no points value before {token!r}"
            )
        points, additive = value
        if points is None and pending.kind not in ("exch", "misc"):
            raise PointsRulesError(
                f"'*' is only meaningful for Exchange or Misc, not {token!r}"
            )
        rules.append(replace(pending, points=points, additive=additive))
        pending = None

    if pending is not None:
        raise PointsRulesError(f"{text!r} ends without a points value")
    return Points(raw=text, default=default, rules=tuple(rules))


def _entity(lookup, call) -> dict:
    """The ``cty.dat`` entry for *call*, or an empty dict."""
    if not call or lookup is None:
        return {}
    try:
        result = lookup(call)
    except Exception:  # noqa: BLE001 -- a lookup is a convenience, never a must
        return {}
    if not result:
        return {}
    return result.get(next(iter(result))) or {}


def _text(contact, key) -> str:
    value = contact.get(key, "")
    return "" if value is None else str(value)


def _number(text: str) -> int | None:
    text = text.strip()
    return int(text) if text.isdigit() else None


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _grid4(value) -> str:
    text = "" if value is None else str(value).strip().upper()
    return text[:4] if len(text) >= 4 else ""


def _band_of(contact) -> float:
    return band_mhz_of(contact.get("Band"))


def _context(contact, station, lookup) -> dict:
    """The facts the rules ask about, from the contact and the two calls."""
    his = _entity(lookup, _text(contact, "Call"))
    mine = _entity(lookup, _text(station, "Call"))
    return {
        "contact": contact,
        "band": _band_of(contact),
        "mode": _text(contact, "Mode").upper(),
        "exchange": _text(contact, "Exchange1"),
        "misc": _text(contact, "MiscText"),
        "sect": _text(contact, "Sect"),
        "comment": _text(contact, "Comment"),
        "grid": _grid4(contact.get("GridSquare")),
        "my_grid": _grid4(station.get("GridSquare")),
        "call": _text(contact, "Call").upper(),
        # cty.dat's primary prefix groups a country's calls (K, W, N and AA
        # are all "K"), which is what "same country" means; the logged prefix
        # is the fallback when there is no lookup.
        "country": (
            str(his.get("primary_pfx", "")) or _text(contact, "CountryPrefix")
        ).upper(),
        "continent": (
            _text(contact, "Continent") or str(his.get("continent", ""))
        ).upper(),
        "my_country": (
            str(mine.get("primary_pfx", "")) or _text(station, "CountryPrefix")
        ).upper(),
        "my_continent": (
            _text(station, "Continent") or str(mine.get("continent", ""))
        ).upper(),
        "cq_zone": contact.get("CQZone") or his.get("cq") or 0,
        "itu_zone": contact.get("ITUZone") or his.get("itu") or 0,
        "my_cq_zone": station.get("CQZone") or mine.get("cq") or 0,
        "my_itu_zone": station.get("ITUZone") or mine.get("itu") or 0,
    }


def _matches(rule: Rule, context: dict, sent_exchange: str) -> bool:
    kind = rule.kind
    if kind == "band":
        return abs(context["band"] - float(rule.arg)) < 0.01
    if kind == "mode":
        return context["mode"] in rule.arg
    if kind == "continent":
        if rule.arg == "same":
            return bool(context["continent"]) and (
                context["continent"] == context["my_continent"]
            )
        if rule.arg == "other":
            return bool(context["continent"] and context["my_continent"]) and (
                context["continent"] != context["my_continent"]
            )
        return context["continent"] == rule.arg
    if kind == "country":
        if rule.arg == "MY":
            return (
                bool(context["country"]) and context["country"] == context["my_country"]
            )
        return bool(context["country"]) and context["country"] == rule.arg
    if kind == "suffix":
        return context["call"].endswith(rule.arg)
    if kind == "same_continent_band" or kind == "other_continent_band":
        if abs(context["band"] - float(rule.arg)) >= 0.01:
            return False
        known = bool(context["continent"] and context["my_continent"])
        same = known and context["continent"] == context["my_continent"]
        return same if kind == "same_continent_band" else known and not same
    if kind == "is_misc":
        return bool(context["misc"].strip())
    if kind == "is_comment":
        return bool(context["comment"].strip())
    if kind == "exch":
        return bool(context["exchange"].strip())
    if kind == "misc":
        return bool(context["misc"].strip())
    if kind == "exch_num":
        return _number(context["exchange"]) is not None
    if kind == "misc_num":
        return _number(context["misc"]) is not None
    if kind == "exch_not_num":
        return _number(context["exchange"]) is None
    if kind == "misc_not_num":
        return _number(context["misc"]) is None
    if kind == "exch_empty":
        return not context["exchange"].strip()
    if kind == "misc_empty":
        return not context["misc"].strip()
    if kind == "sect_is":
        return context["sect"].strip().upper() == rule.arg
    if kind == "exch_is":
        return context["exchange"].strip().upper() == rule.arg
    if kind == "misc_is":
        return context["misc"].strip().upper() == rule.arg
    if kind == "exch_contains":
        return rule.arg in context["exchange"].upper()
    if kind == "my_grid":
        return bool(context["grid"]) and context["grid"] == context["my_grid"]
    if kind == "my_cq_zone":
        return _as_int(context["cq_zone"]) != 0 and _as_int(
            context["cq_zone"]
        ) == _as_int(context["my_cq_zone"])
    if kind == "my_iaru_zone":
        return _as_int(context["itu_zone"]) != 0 and _as_int(
            context["itu_zone"]
        ) == _as_int(context["my_itu_zone"])
    if kind == "my_exchange":
        mine = _text(context["contact"], "SentNr") or sent_exchange
        return (
            bool(mine.strip()) and context["exchange"].strip().upper() == mine.upper()
        )
    return False


def _rule_points(rule: Rule, context: dict) -> int:
    if rule.points is not None:
        return rule.points
    field = context["exchange"] if rule.kind == "exch" else context["misc"]
    return _number(field) or 0


# The help lists "band, mode, continent, country", but that would make
# "MyCountry, 1, SameContinent, 2" score a same-country QSO as SameContinent
# (2) and never as MyCountry (1), which is plainly not what the files mean.
# Country first is the reading that makes the corpus's rules coherent.
_CRITERIA = ("band", "mode", "country", "continent")


def score(points: Points, *, contact, station, lookup, sent_exchange: str = "") -> int:
    """The points *contact* is worth under *points*.

    The caller checks for a dupe first: a dupe is worth zero whatever the
    rules say.
    """
    if points.distance:
        his_grid = _grid4(contact.get("GridSquare"))
        my_grid = _grid4(station.get("GridSquare"))
        if not his_grid or not my_grid:
            return 0
        km = distance(my_grid, his_grid)
        for low, high, value in points.distance:
            if low <= km <= high:
                return value
        return 0

    context = _context(contact, station, lookup)
    base: Rule | None = None

    # Explicit rules win by position; that is why a file puts "SectIs_x" first.
    for rule in points.rules:
        if rule.additive or rule.kind in _CRITERIA:
            continue
        if _matches(rule, context, sent_exchange):
            base = rule
            break

    # Otherwise the documented priority: band, mode, continent, country.
    if base is None:
        for kind in _CRITERIA:
            for rule in points.rules:
                if rule.additive or rule.kind != kind:
                    continue
                if _matches(rule, context, sent_exchange):
                    base = rule
                    break
            if base is not None:
                break

    total = _rule_points(base, context) if base is not None else points.default
    for rule in points.rules:
        if rule.additive and _matches(rule, context, sent_exchange):
            total += _rule_points(rule, context)
    return total
