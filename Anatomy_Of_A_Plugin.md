# Contents of a plugin

This file gives a brief overview of what a plugin contains and how the pieces
fit together. If you are attempting to create your own plugin, this guide will
give you a headstart.

A plugin is a module in `not1mm/plugins/` that defines one class:

```python
from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    DisplayName = "ARI International DX"
    CabrilloName = "ARI-DX"
    ...
```

The class *is* the plugin. Everything it shares with every other contest comes
from `ContestBase` in `not1mm/lib/contest.py`; the file holds only what makes
this contest different.

## How it got this way

Two refactors shaped the current shape, in case you are reading older plugins
or older notes:

- **`df7cb/contest-refactor`** turned the plugins from modules of ~20 functions
  (`interface()`, `set_tab_next()`, `output_cabrillo_line()`, …) into classes
  with a shared base. Attribute names follow N1MM's UDC parameters where the
  concept exists (`DisplayName`, `CabrilloName`, `Mode`, `DupeType`, `LogInfo`,
  `EntryWindowInfo`, `FrameText`, `Multiplier1Name`, …). The boilerplate moved
  into the base, the test corpus in `not1mm/contest/` became the behaviour
  contract, and the contest picker is built from the discovered classes.
- **The UDC-multis branch** replaced the fixed five-widget row (`callsign,
  sent, receive, other_1, other_2`) with the boxes a contest declares in
  `EntryWindowInfo`, named after N1MM's fields (`SNTText`, `RcvNrText`,
  `Exchange1Text`, …) and addressed through `parent.fields`. `interface()` no
  longer shows or hides fixed widgets, the `TabOrder`/`TabOrderPrev`
  declarations, `set_tab_prev()` and the per-plugin `next_field` are gone, and
  the base `set_contact_vars()` fills a box's contact column from its
  declaration.

## Variables that define the contest

`DisplayName` is what appears at the top of the main window and in the New
Contest picker, e.g. `ARI International DX`.

`CabrilloName` is the identifier saved in the database and written as the
Cabrillo `CONTEST:` value and the ADIF `CONTEST_ID`, e.g. `ARI-DX`.

`ContestName` overrides the identifier for the few contests that share a
Cabrillo name but are not interchangeable; leave it unset otherwise.

`SortOrder` places the contest in the picker (lower first, then by display
name). It defaults to `100`; General Logging sets `50` to stay on top.

`Mode` is `CW`, `SSB`, `BOTH` or `RTTY`, and decides the band/mode indicators
on the left of the main window.

`DupeType` selects the duplicate rule: `1` once in the contest, `2` once per
band, `3` once per band and mode, `4` no checking, `5` the plugin decides
(then override `specific_contest_check_dupe()`).

`LogInfo` is the list of columns shown in the log window, in order.

`EXCHANGE_HINT` is the placeholder in the contest setup dialog for the sent
exchange; `DefaultContestExchange` is what to send when the operator leaves it
empty (a serial is `"#"`, a fixed exchange is the text). Both are optional.

`Bands` lists the bands in MHz. It documents the contest and lets a test
reject an off-band log.

`PointsPerContact` is the points for one valid contact. A contest whose points
depend on where the operator is, or on the contact, overrides `points()`
instead.

`SupportsFT8`, `WritesEDI`, `WritesGridLocator`, `SendsRTCScore` and `UsesESM`
are capability flags; several replace what used to be `hasattr()` probes.

## The entry window: `EntryWindowInfo` and `FrameText`

There is no fixed set of entry widgets. Each contest declares the boxes it
wants, as N1MM's flat name/width list:

```python
EntryWindowInfo = ("SNTText", 450, "RCVText", 450,
                   "SntNrText", 625, "RcvNrText", 625)
FrameText = ("SNT", "RCV", "SentNR", "RcvNR")
AccessibleNames = ("RST Sent", "RST Received",
                   "Sent Number", "Received Number")
```

`FrameText` has one label per declared box, in the same order; an empty string
leaves that label blank. `AccessibleNames` is the screen-reader name for each
box, also optional and positional. The width is N1MM's relative layout width,
not pixels.

The boxes available to a declaration are:

| name | contact column | typical label |
|---|---|---|
| `SNTText` | `SNT` | RST sent |
| `RCVText` | `RCV` | RST received |
| `SntNrText` | `SentNr` | sent serial |
| `RcvNrText` | `NR` | received serial |
| `Exchange1Text` | `Exchange1` | exchange |
| `MiscText` | `MiscText` | misc |
| `SectText` | `Sect` | section |
| `GridSquareText` | `GridSquare` | grid square |
| `NameText` | `Name` | name |
| `CommentText` | `Comment` | comment |

The callsign is not declared and is always shown. The names are N1MM's; the
column is how not1mm stores the value, which is not always the same spelling
(N1MM's callsign column is `CallSign`, not1mm's is `Call`).

Plugin code reaches the widgets through the main window:

```python
fields = self.parent.fields
fields.RcvNrText.text()
fields.SectText.setText("OH")
fields.callsign            # the callsign box (also self.parent.callsign)
```

### Focus and TAB order

`TAB` walks every box the contest shows, callsign first, then the exchange
boxes in declaration order, then back to `cw_entry`. Qt's own focus chain does
this, so a plugin declares no TAB order; the base's `set_tab_next()` only
builds the map `SPACE` walks.

`SPACE` moves to the next box, the same way `TAB` does, except where the space
is part of the text. A contest whose exchange contains spaces lists those boxes
in `SpaceKeepsFocus`, so a space is data rather than a step:

```python
SpaceKeepsFocus = ("NameText", "SectText")
```

`CommentText` never advances by default. In the callsign, `SPACE` ends the call
and runs what was typed, so it stays a callsign key.

`NextField` (where the focus lands after a callsign lookup) and
`ESMExchangeField` (which box finishes the contact) are derived rather than
declared: the first box that is neither a report nor the sent serial, and the
last box. Set either only when the derived choice is wrong.

`interface()` still exists, and the base implements it: it shows exactly the
declared boxes and applies their labels. Override it only for UI a declaration
cannot express (a General Logging box with mixed case, an extra dialog field),
and call `super().interface()` first.

`call_parse_exchange_on_edit = True` calls the contest's `parse_exchange()` as
the box is typed, for contests whose received exchange is several fields in one
box (Sweepstakes' `sn prec ck sec`).

## Logging a contact: `set_contact_vars()`

The base implementation writes every declared box into the contact column its
declaration names, then marks the multipliers:

```python
for field in self.parent.fields:
    if field.spec.column:
        self.parent.contact[field.spec.column] = field.edit.text()
self.mark_multipliers()
```

So a contest with an ordinary exchange needs no method at all. Override it
when the value is parsed, normalised, derived, or stored somewhere the
declaration does not name:

```python
def set_contact_vars(self):
    parent = self.parent
    parent.contact["SNT"] = parent.fields.SNTText.text()
    parent.contact["RCV"] = parent.fields.RCVText.text()
    parent.contact["SentNr"] = parent.fields.SntNrText.text()
    # RcvNrText holds "599 03"; the zone is the second half.
    parent.contact["NR"] = parent.fields.RcvNrText.text().split()[-1]
    self.mark_multipliers()
```

`mark_multipliers()` sets `IsMultiplier1..3` on the contact that is being
logged. A contest with no multipliers inherits a no-op.

## Multipliers

Up to three multipliers, declared the UDC way:

```python
NumMults = 2
Multiplier1Name = "NR"
MultSqlString = "NR"        # the kind of key
IsMult1Per = 1              # once per band
Multiplier2Name = "CountryPrefix"
MultSqlString2 = "CountryPrefix"
IsMult2Per = 1
```

`MultSqlString` names a kind of key from `MULT_KEYS` in
`not1mm/lib/contest.py` (`NR`, `Sect`, `Grid`, `CountryPrefix`, `WPXPrefix`,
`CQZONE`, `IARUZONE`, `Misc`, `Exchange`, `CallSign`, …), and `IsMultNPer`
says how it is counted (`1` band, `2` band+mode, `4` contest, …). The base
turns those into the SQL that counts the log (`show_mults()`), the value a
contact contributes (`mult_value()`), and the mark on the first contact of each
multiplier (`recalculate_mults()`).

Override `mult_value()` and `mult_sql()` when the key is conditional — a
province only when the received exchange is a code rather than a serial, for
example — and `get_mults()` when the score page needs more than the counts.
The score itself is `calc_score()`: points times multipliers, or just points
when there are none.

## Enter Sends Message (ESM)

`process_esm()` is the state machine; the base handles a contest with report
and exchange boxes, and `UsesESM = False` turns it off.

`QsoErrorString` is UDC's completeness declaration for the received exchange:

```python
QsoErrorString = "SntNrText_Any_not_Empty, RcvNrText_Any_not_Empty"
```

Each item is `<box>_<rule>`, comma-separated; the box name may be left off, in
which case it is `ESMExchangeField`. The rules are `Any`, `Any_not_Empty`,
`Numeric`, `Numeric_not_Empty` and `Grid` (a grid must not be empty). It
decides when ESM stops asking for a repeat and moves on to the QRZ/TU macro and
`LOGIT`. `None` (the default) keeps the old single-box check on
`ESMExchangeField`; `""` means nothing is checked. A contest whose completeness
depends on the station (NAQP's name plus optional location, ARRL 160's DX/W-VE
split) overrides `esm_exchange_ready()` and keeps the base's response.

The RTTY contests override `process_esm()` itself, because their macros are
fldigi strings rather than function-key messages; the NAQP/NA Sprint/SSA MT
family and the general-logging modes override it because their field flow
differs.

## The functions or methods

Most of these exist in the base; override only the ones that differ.

`points()` returns the point value of the contact being logged. Point
assignment is often complicated by continents, countries, zones, power, etc.

`predupe()` is called when the callsign is entered and checked. The CWT plugin
uses this to query the DB for a matching callsign, allowing it to automatically
populate the contact Name and CWOp #/State/DX fields.

`prefill()` is called as the callsign is typed (once it has three characters)
and on a mode change. The base fills the sent exchange from the contest setup,
or `DefaultContestExchange` when that is empty, unless the operator has already
typed one; a contest with derived sent data overrides it.

`prefill_contact(call)` returns what is known about a call — its location and
its multiplier values — recalled from a previous QSO, the call history file and
`cty.dat`. The callsign box uses it for everything it shows while a call is
typed.

`populate_history_info_line()` and `check_call_history()` show and apply the
call history file's data for the typed call.

`show_mults()` returns the current multiplier count, `show_qso()` the number of
valid contacts and `calc_score()` the score. Each is derived from the log for a
declaratively-scored contest.

`get_mults()` builds the entries the online score page publishes.

`recalculate_mults()` re-marks the multipliers when a logged contact is edited.
`after_recalculate_mults()` is the hook for a contest that has to poke the UI
afterwards.

`cabrillo_qso_line(contact)` returns one Cabrillo `QSO:` line; the header, the
file and the ADIF log come from the base. `cabrillo()` and `adif()` are only
overridden when the whole file differs (EDI, a sponsor-specific summary).

`ft8_handler(packet)` accepts a QSO from WSJT-X or fldigi over UDP; set
`SupportsFT8 = True` when you implement it.

`edi()` writes the VHF/UHF EDI export. There is no base implementation: a VHF
contest defines it and sets `WritesEDI = True`.

## Retrieving contact station information

Most of what a plugin wants to know about a call is assembled by
`not1mm/lib/contact_info.py`. It recalls the fields from a previous QSO in this
contest, the call history file and `cty.dat` (in that order of authority), works
out the bearing and distance from your grid, and asks the contest its dupe and
multiplier questions. A contest exposes it as `contact_info()`:

```python
info = self.contact_info(self.parent.callsign.text())
info.prefix      # CountryPrefix, e.g. "G"
info.entity      # "England"
info.continent   # "EU"
info.cq_zone     # 14
info.itu_zone    # 27
info.zone        # whichever zone the contest exchanges (its ZoneType)
info.grid        # the grid the bearing came from; "" = the entity centre
info.beam        # degrees, or None
info.distance    # km, or None
info.is_dupe     # as the contest's DupeType sees it
info.mults       # tuple of MultInfo(name, type, value, is_new)
```

`MultInfo.value` is the multiplier key the call is worth, and `is_new` says
whether it is already in the log. A call-derived key answers from the callsign
alone; an exchange-derived one stays `None` until the exchange is known.

When you need the raw contact fields rather than the summary — to prefill a box,
for example — `self.prefill_contact(call, band, mode)` returns the recalled
dict (`GridSquare`, `Sect`, `State`, `NR`, `Exchange1`, `MiscText`, `Name`,
`ZN`, plus the private `_lat`/`_lon`/`_entity` the bearing uses). Values already
set in the dict are never overwritten, so the most authoritative source wins.

The pieces are also usable on their own: `contact_info.recall()` returns the
dict without the dupe and multiplier answers, and `contact_info.bearing_to()`
takes a grid or a latitude/longitude.

If you only need the `cty.dat` entry, ask for it directly:

```python
result = self.parent.cty_lookup(self.parent.contact.get("Call", ""))
if result is not None:
    item = result.get(next(iter(result)))
    hiscountry = item.get("entity", "")
    hiscontinent = item.get("continent", "")
    hiscqzone = item.get("cq", "")
    hisituzone = item.get("itu", "")
    hisprimary_pfx = item.get("primary_pfx", "")
```

The same call with `self.parent.station.get("Call", "")` describes your own
station. The dict is keyed by the matching callsign, hence the
`next(iter(result))`.

## Making a new plugin by modifying an existing one

A straightforward way to create a new contest plugin is finding an existing
plugin with the same or similar exchange and modifying it as necessary. [Here](./contest_exchanges.md) is a pretty good list of contests and their exchange types.

Name the file after the contest (`not1mm/plugins/my_contest.py`), keep the
`class Contest(ContestBase)` name, and set `DisplayName`, `CabrilloName`,
`Mode`, `DupeType`, `LogInfo` and the `EntryWindowInfo`/`FrameText` pair first
— the rest of the class usually follows from a diff against the model.

A new plugin also needs a fixture directory, `not1mm/contest/<plugin>/`, with
at least one log: `<case>.adif` (input QSOs), `<case>.json` (station, settings
and expected qsos/mults/score/dupes) and `<case>.log` or `<case>.edi` (the
golden export). `python3 test/gen_contest_fixtures.py` generates them through
the real import and export code; the files are committed, and re-running the
script reproduces them byte for byte unless behaviour changed. A plugin without
a fixture directory fails `test_contest_logs`'s
`test_every_plugin_has_a_fixture_directory`.

Then run:

```
QT_QPA_PLATFORM=offscreen PYTHONPATH=$PWD python3.14 -m pytest -q
```

The per-plugin tests are parameterised over every plugin, so a field the
contest declares but never reads, or a multiplier column nothing fills, fails
there too.

## Macros

Contest messages (`DefaultContestExchange`, the ESM messages, the function-key
macros) go through `process_macro()`:

- `{MYCALL}`, `{MYGRID}`, `{HISCALL}`
- `#` (or UDC's `001`) is the next serial, `{SENTNR}` the sent serial from its
  box, `{SNT}` the sent RST
- per-box text: `{RCV}`, `{RCVNR}`, `{EXCHANGE1}`, `{MISC}`, `{SECT}`,
  `{GRID}`, `{NAME}`, `{COMMENT}`
- `{OTHER1}`/`{OTHER2}` are the first/second box after the reports
- `{EXCH}`, `{PREVNR}`, `{PREVCALL}`, `{TX}`, `{RX}`, `{TX/RX}`

A placeholder only expands when the contest declares that box; otherwise it is
left in the text as typed, so keep a contest's messages to the boxes it
declares.

## Contests defined by a UDC file

A contest does not have to be a Python class. A `.udc` file is read when the
contest list is built, turned into the same `ContestBase` subclass a plugin
describes, and offered in the picker beside the plugins. The reference for the format and for what the
loader applies is `UDC-FIELDS.md` (it lives next to the repository, not in it).

Files come from `not1mm/data/udc/` (shipped) and the user's `udc/` directory
under the app-data path; a user file whose name matches a bundled one overrides
it. The file stem is the contest's identifier, because the UDC `Name` is not
unique (`AGCW-YLCWP-om.udc` and `AGCW-YLCWP-yl.udc` share one).

Identity, the entry window and labels, `LogInfo`, the multipliers and their
counting, `DefaultContestExchange`, a basic `QsoErrorString`, an integer
`PointsPerContact` and the Cabrillo line are applied. A parameter not1mm only
parses is reported when the contest is opened and listed in
`UdcUnimplemented` on the class; nothing is silently ignored.

## Adding a new contest to the dropdown list

There is nothing to add by hand. The New Contest dropdown is built from the
`plugins` directory and the `.udc` files: every `not1mm/plugins/*.py` that
defines a `class Contest(ContestBase)`, and every User Defined Contest, shows
up in the list, labelled with its `DisplayName` -- and with its `CabrilloName`
in parentheses when the two names really differ, e.g.
`ARI International DX (ARI-DX)`. A dropdown entry therefore always matches the
definition that will be loaded, and a new plugin or UDC needs no change to
`new_contest.ui`.

Contests are listed lowest `SortOrder` first and then by display name.
`SortOrder` defaults to `100`; General Logging sets `50` to keep the non-contest
mode at the top.

`CabrilloName` is also the identifier saved in the database (unless the plugin
overrides it with `ContestName`), so the picker and the log agree on what the
contest is called.
