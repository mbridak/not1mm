# TCI Support for not1mm (AetherSDR Compatibility)

**Date:** 2026-08-01
**Status:** Approved design, ready for implementation planning

## Goal

Add TCI (Transceiver Control Interface) as a fourth CAT backend in not1mm, so
AetherSDR can be used as the rig. TCI covers radio state sync, PTT, CW keying,
and — in a second phase — pushing bandmap spots onto the SDR's panadapter.

AetherSDR acts as the TCI **server**, listening on a WebSocket port. not1mm
connects out to it as a client. A live AetherSDR is available for testing.

## Background: the impedance mismatch

TCI is asynchronous and push-based. The server broadcasts state changes
unprompted (`vfo:0,0,14030000;` the moment the user turns the dial), and
responses are not correlated to requests.

not1mm's CAT contract is the opposite. `CAT` (`not1mm/lib/cat_interface.py:15`)
defines synchronous getters, and `Radio.run()` (`not1mm/radio.py:76`) calls them
from a blocking `while` loop with `QThread.msleep(100)` that never returns to a
Qt event loop.

Bridging those two is the central design problem. The chosen solution is a
**state-cache backend**: an async reader keeps a dict of last-known state, and
the synchronous getters read that dict.

### Approaches considered

- **A. State-cache backend — CHOSEN.** Getters return cached values, so they are
  non-blocking and instant. `Radio` and `__main__.py` each change by one `elif`;
  the other three backends are untouched. Cached state is fresher than polling,
  since updates arrive when the SDR changes rather than up to 555 ms later.
- **B. Push-through signals.** `QWebSocket` in the main GUI thread emitting Qt
  signals straight into `poll_radio`, no polling at all. Most Qt-idiomatic and
  lowest latency, but it breaks the abstraction: `Radio` would need a TCI-only
  no-poll path and the `__main__.py` wiring would diverge from the other three
  backends. Rejected — more disruption than the latency gain justifies.
- **C. Synchronous request/reply.** Block on a matching response each poll,
  mimicking `cat_rigctld.py`. Rejected: it fights the protocol. TCI broadcasts,
  replies are not request-correlated, and blocking a poll loop on a shared
  socket invites deadlock.

### Transport decision

`QWebSocket` from `PyQt6.QtWebSockets`, verified importable in the current
install. **No new dependency**, and it matches how `radio.py` and `RTCService`
already use `QThread`. The cost is that the `QWebSocket` must live on a thread
running `QEventLoop.exec()` — a standard but fiddly Qt pattern.

Rejected alternatives: the `websocket-client` PyPI package (simpler code, but
adds a dependency to `pyproject.toml` and `python3-modules.yaml` on a project
that keeps its dependency list tight) and hand-rolled RFC 6455 framing
(~150 lines of fiddly protocol code we would own).

## Architecture

One new file, `not1mm/lib/cat_tci.py`, with two classes:

**`TCIClient(QObject)`** — the transport. Owns a `QWebSocket` on its own
`QThread` running a real `QEventLoop`, so socket signals are actually delivered.
Parses inbound `command:arg1,arg2;` frames and writes them into a state dict
guarded by a `QMutex`. Knows nothing about not1mm.

**`TciCAT(CAT)`** — the backend, subclassing `not1mm/lib/cat_interface.py:15`.
Getters read the state dict; setters serialize a TCI command and hand it to the
client. This is the only class `radio.py` sees.

Separation of concerns: `TCIClient` is testable without not1mm, and its parsing
and serialization functions are testable without a socket.

### Integration points

Each of these is a small, local change:

| File | Change |
|---|---|
| `not1mm/radio.py:56` | `elif self.interface == "tci": self.cat = TciCAT(...)` |
| `not1mm/__main__.py:3835` | `elif self.pref.get("usetci", False) is True:` branch |
| `not1mm/lib/preferences.py:57` | `"usetci": False` default |
| `not1mm/lib/settings.py:126`, `:304` | load/save `usetci` |
| `not1mm/data/configuration.ui:501` | `usetci_radioButton` in the existing group |

## CAT-to-TCI command mapping

| CAT method | TCI command |
|---|---|
| `get_vfo` / `set_vfo` | `vfo:0,0,<hz>;` |
| `get_mode` / `set_mode` | `modulation:0,<mode>;` |
| `get_bw` | `rx_filter_band:0,<low>,<high>;` → `high - low` |
| `get_ptt` / `ptt_on` / `ptt_off` | `trx:0,<true\|false>;` |
| `sendcw` | `cw_msg:` |
| `set_cw_speed` | `cw_macros_speed:<wpm>;` |
| `get_mode_list` | `modulation_list:` from the connect handshake |

TRX index 0 and channel 0 (VFO A) throughout. Multi-receiver and VFO B support
is out of scope.

**Exact argument signatures are to be confirmed against AetherSDR's own
handshake, not assumed.** TCI argument formats vary across protocol versions —
`cw_msg:` in particular differs between revisions. The first implementation step
is to connect to the live AetherSDR, log the full handshake verbatim (including
its `protocol:` / `device:` / `modulation_list:` lines), and pin the mapping
table to what that server actually speaks. The table above fixes *which* TCI
command serves each CAT method; it does not fix argument counts or ordering.

### Two contract traps

**Mode names must be normalized.** TCI uses lowercase names that do not match
not1mm's (`cw`, `digl`, `digu` vs `CW`, `DIGI-L`, `DIGI-U`). `Radio` matches
`cw_list` and `rtty_list` against `get_mode_list()` by exact string
(`not1mm/radio.py:36-42`), so raw passthrough would silently break CW and RTTY
mode detection. `TciCAT` owns a bidirectional mode table normalizing to
not1mm's uppercase convention on the way in and to TCI's lowercase on the way
out.

**`get_vfo` must return bare digits.** `not1mm/radio.py:84` rejects any value
failing `.isnumeric()`, so no units, decimals, or sign.

## PTT and CW require no new plumbing

Both already route through the CAT object, so implementing the backend methods
is sufficient:

- **PTT** — `Radio.ptt_on` / `ptt_off` / `get_ptt` (`not1mm/radio.py:185-197`)
  already delegate to `self.cat`.
- **CW** — `cwtype == 3` is the existing "CW via CAT" mode
  (`usecwviacat_radioButton`, handled at `not1mm/__main__.py:1624`, `:2628`,
  `:3699`), routing to `rig_control.sendcw()` and `set_cw_speed()`. Users select
  that option as they would with flrig or rigctld.

No new configuration keys or code paths for either.

## Configuration

`usetci_radioButton` joins the existing radio-button group next to
`userigctld_radioButton` (`configuration.ui:501`) and `useflrig_radioButton`
(`:535`), reusing the existing `CAT_ip` and `CAT_port` fields. **TCI defaults to
port 50001**, which is what the AetherSDR under test listens on. (40001 is the
common default for other TCI servers such as ExpertSDR; the field is
user-editable either way.) The hint string at `not1mm/lib/settings.py:33` ("Usually 4532 for
rigctld and 12345 for flrig") gains a TCI mention.

## Error handling and recovery

`online` stays `False` until the server sends `ready;` at the end of its
handshake. On disconnect or socket error: clear the cache, set `online = False`,
and reconnect with capped backoff (1s → 2s → 5s). This is the TCI analogue of
`RigctldCAT.reinit()`.

**When offline, getters return `""` — never stale cache.** `not1mm/radio.py:83-97`
only overwrites its values on a truthy result, so returning empty makes the UI
hold last-known values and report `online: False`, exactly matching flrig and
rigctld behavior on failure. Serving stale cache instead would paint a frozen
frequency as though it were live, which during a contest is worse than showing
nothing.

Unknown inbound commands (audio stream control, IQ config, and similar) are
logged at debug level and dropped. A TCI server sends plenty we do not care
about, and this must not be treated as an error.

**Shutdown risk.** `not1mm/__main__.py:3812-3819` tears the radio thread down via
`time_to_quit` + `quit()` + `wait(1000)`. `TciCAT` owns a *second* QThread, so it
needs an explicit close path hooked into that teardown. Without it, the app hangs
on exit. This must be handled deliberately in the implementation plan.

## Testing

**Unit tests, no socket and no Qt required** — this is where the real bugs will
be and the cheapest place to catch them:

- Frame parsing: `vfo:0,0,14030000;` → structured fields
- Command serialization for every mapped command
- The bidirectional mode table, both directions, including unmapped modes
- Bandwidth derived from `rx_filter_band` low/high
- `get_vfo` output satisfies `.isnumeric()`
- Getters return `""` when offline

**Integration:** `not1mm/testing/faketci.py`, a minimal TCI WebSocket server
following the `not1mm/testing/fakeflrig.py` precedent, so the backend can be
exercised without AetherSDR running. Covers connect handshake, `ready;`,
state broadcast, and disconnect/reconnect.

**Manual:** verification against live AetherSDR — frequency and mode tracking in
both directions, PTT, CW keying via "CW via CAT", and recovery after killing and
restarting AetherSDR.

## Phase 2 — spot push

Deferred until phase 1 is working and verified, because it hooks the bandmap
rather than the CAT interface and has no flrig/rigctld equivalent.

`Database.addspot()` (`not1mm/bandmap.py:136`) is the single funnel for every
spot; `delete_spot` (`:303`) and `clear_spots` (`:1002`) map to `spot_delete:`.
Spots go out as `spot:<call>,<mode>,<hz>,<color>,<text>;`, guarded to be a no-op
unless TCI is the active backend.

**Open question to resolve during phase 2 planning:** `BandMapWindow` is a
separate `QDockWidget` communicating over `message` / `cluster_expire` signals
and multicast. It is not confirmed to hold a reference to `rig_control`. If it
does not, a route from bandmap to the TCI client must be designed, and that
routing choice is the bulk of phase 2's work.

## Out of scope

- Multi-receiver / multi-TRX and VFO B
- TCI audio streaming (`start;` / `stop;`, IQ and audio data frames)
- not1mm acting as a TCI *server*
- Changes to the flrig, rigctld, or fake backends
