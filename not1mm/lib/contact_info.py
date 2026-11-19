"""What is known about a callsign, and what the contest makes of it.

The call field, the rotator and the bandmap all want the same facts about a
call: where it is -- the country, the zones, a bearing -- and what the contest
makes of it -- is it a dupe, is it a new multiplier?  :class:`ContactInfo` is
that answer.

A contest builds it with :meth:`not1mm.lib.contest.ContestBase.contact_info`,
which recalls the fields from a previous QSO in this contest, the call history
file and cty.dat, and then asks its own rules about the dupe and the
multipliers.  The recall has to come first: the call history or a previous QSO
can carry the correspondent's grid, and a bearing taken from a real grid beats
one taken from the centre of the DXCC entity.
"""

from __future__ import annotations

from dataclasses import dataclass

from not1mm.lib.ham_utility import (
    bearing,
    bearing_with_latlon,
    calculate_wpx_prefix,
    distance,
    distance_with_latlon,
    get_logged_band,
)

# A grid shorter than this cannot give a meaningful bearing.
_MIN_GRID = 4


@dataclass(frozen=True)
class MultInfo:
    """One multiplier a call is worth."""

    name: str  # Multiplier1Name, for display
    type: str  # the score page's id
    value: str | None  # the key, when the context can produce one
    is_new: bool  # would be a new multiplier in the log


@dataclass(frozen=True)
class ContactInfo:
    """What the call field, the rotator and the bandmap ask about a call."""

    call: str
    prefix: str = ""  # CountryPrefix
    entity: str = ""
    continent: str = ""
    cq_zone: int = 0
    itu_zone: int = 0
    zone: int = 0  # whichever the contest exchanges (its ZoneType)
    grid: str = ""  # the grid the bearing came from; "" = the entity centre
    beam: float | None = None
    distance: float | None = None
    is_dupe: bool = False
    mults: tuple[MultInfo, ...] = ()


def usable_grid(grid) -> str:
    """*grid* if it is long enough to give a bearing, else an empty string."""
    text = str(grid or "").strip().upper()
    return text if len(text) >= _MIN_GRID else ""


def bearing_to(station_grid, grid=None, lat=None, lon=None):
    """Bearing and distance from my grid to a grid, or to a latitude/longitude.

    A real grid wins over an entity centre.  cty.dat stores longitudes
    inverted, so the sign is flipped here, as it always was.
    """
    station = usable_grid(station_grid)
    if not station:
        return None, None
    target = usable_grid(grid)
    if target:
        return bearing(station, target), distance(station, target)
    if lat not in (None, "") and lon not in (None, ""):
        return (
            bearing_with_latlon(station, float(lat), -float(lon)),
            distance_with_latlon(station, float(lat), -float(lon)),
        )
    return None, None


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _fill(contact, key, value) -> None:
    """Set ``contact[key]`` from a source, unless it is empty or already set."""
    if value in (None, "", 0):
        return
    if contact.get(key) in (None, ""):
        contact[key] = value


def _zone_of(contact, zone_type) -> int:
    """The zone the contest exchanges: CQ by default, IARU for a few."""
    if zone_type == "IARU":
        return _as_int(contact.get("ITUZone")) or _as_int(contact.get("CQZone"))
    return _as_int(contact.get("CQZone")) or _as_int(contact.get("ITUZone"))


def _recall_from_call(call, contact) -> None:
    """What the callsign itself tells us, before any lookup."""
    _fill(contact, "WPXPrefix", calculate_wpx_prefix(call))


def _recall_cty(parent, call, contact) -> None:
    """Country, continent, zones and the entity centre, from cty.dat."""
    result = parent.cty_lookup(call)
    if not result:
        return
    item = result.get(next(iter(result)))
    if not item:
        return
    _fill(contact, "CountryPrefix", item.get("primary_pfx", ""))
    _fill(contact, "Continent", item.get("continent", ""))
    _fill(contact, "CQZone", _as_int(item.get("cq")))
    _fill(contact, "ITUZone", _as_int(item.get("itu")))
    if contact.get("_lat") in (None, ""):
        contact["_lat"] = item.get("lat")
        contact["_lon"] = item.get("long")
    if not contact.get("_entity"):
        contact["_entity"] = item.get("entity", "")


def _recall_call_history(parent, call, contact) -> None:
    """Grid, section, zone and exchange for a known call."""
    if not parent.pref.get("use_call_history", False):
        return
    result = parent.database.fetch_call_history(call)
    if not result:
        return
    _fill(contact, "GridSquare", result.get("Loc1", ""))
    _fill(contact, "Sect", result.get("Sect", ""))
    _fill(contact, "State", result.get("State", ""))
    _fill(contact, "Name", result.get("Name", ""))
    _fill(contact, "CQZone", _as_int(result.get("CqZone")))
    _fill(contact, "ITUZone", _as_int(result.get("ITUZone")))
    _fill(contact, "NR", result.get("Exch1", ""))
    _fill(contact, "MiscText", result.get("Misc", ""))


def _recall_previous_qso(parent, call, contact) -> None:
    """Whatever this contest already logged for the same station."""
    result = parent.database.fetch_previous_qso(call)
    if not result:
        return
    for key in (
        "GridSquare",
        "Sect",
        "State",
        "NR",
        "Exchange1",
        "MiscText",
        "Name",
        "ZN",
    ):
        _fill(contact, key, result.get(key))


def recall(parent, call, zone_type="CQ", band=None, mode=None) -> dict:
    """The best-known contact fields for *call*, from every source.

    In order of authority: a previous QSO in this contest, the call history
    file, then cty.dat.  Returns a contact-shaped dict, plus the private
    ``_lat``/``_lon``/``_entity`` the bearing and the display need.
    """
    contact = {"Call": call}
    _recall_from_call(call, contact)
    _recall_previous_qso(parent, call, contact)
    _recall_call_history(parent, call, contact)
    _recall_cty(parent, call, contact)
    if contact.get("ZN") in (None, ""):
        contact["ZN"] = _zone_of(contact, zone_type)
    return contact


def current_band_mode(parent, band=None, mode=None):
    """Fill in the band and mode from the rig when the caller has none."""
    radio = getattr(parent, "radio_state", {}) or {}
    if band is None:
        band = float(get_logged_band(str(radio.get("vfoa", 0.0))))
    if mode is None:
        mode = radio.get("mode", "")
    return band, mode


def build(parent, contest, call, band=None, mode=None, contact=None) -> ContactInfo:
    """Assemble a :class:`ContactInfo` for *call*.

    *contest* supplies the recall, the dupe answer and the multipliers.  With
    no contest at all there is still the country and the bearing.
    """
    if contest is None:
        fields = contact if contact is not None else recall(parent, call)
    else:
        fields = (
            contact
            if contact is not None
            else contest.prefill_contact(call, band, mode)
        )
    fields.setdefault("Call", call)
    if band is None or mode is None:
        band, mode = current_band_mode(parent, band, mode)
    grid = fields.get("GridSquare", "")
    beam, kilometers = bearing_to(
        parent.station.get("GridSquare", ""),
        grid,
        fields.get("_lat"),
        fields.get("_lon"),
    )
    return ContactInfo(
        call=call,
        prefix=fields.get("CountryPrefix", ""),
        entity=fields.get("_entity", ""),
        continent=fields.get("Continent", ""),
        cq_zone=_as_int(fields.get("CQZone")),
        itu_zone=_as_int(fields.get("ITUZone")),
        zone=_as_int(fields.get("ZN")),
        grid=usable_grid(grid),
        beam=beam,
        distance=kilometers,
        is_dupe=False if contest is None else contest.is_dupe(call, band, mode),
        mults=() if contest is None else contest.contact_mults(fields),
    )
