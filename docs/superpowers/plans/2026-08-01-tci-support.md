# TCI CAT Backend Implementation Plan (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add TCI as a fourth CAT backend in not1mm so AetherSDR can be used as the rig, covering frequency/mode/bandwidth sync, PTT, and CW keying.

**Architecture:** TCI is asynchronous and push-based; not1mm's `CAT` contract is synchronous and poll-based. A `TCIClient` runs a `QWebSocket` on its own `QThread` with a real event loop and maintains a mutex-guarded cache of last-known radio state. `TciCAT` subclasses `CAT` and serves getters from that cache, so `Radio.run()`'s existing 555 ms poll loop works unmodified.

**Tech Stack:** Python 3.11+, PyQt6 (`QtWebSockets`, `QtCore`), pytest.

**Spec:** `docs/superpowers/specs/2026-08-01-tci-support-design.md`

**Branch:** `add-tci-support` (already created; the spec commit is `411fcfc9`)

## Global Constraints

- **No new runtime dependencies.** `PyQt6.QtWebSockets` is already available. Do not add anything to `pyproject.toml`, `requirements.txt`, or `python3-modules.yaml`.
- **Do not modify** `cat_flrig.py`, `cat_rigctld.py`, or `cat_fake.py`. Their behavior is the reference, not the target.
- **`get_vfo()` must return bare digits.** `not1mm/radio.py:84` discards any value failing `.isnumeric()`.
- **Mode names normalize to not1mm's uppercase convention.** `not1mm/radio.py:36-42` matches `cw_list`/`rtty_list` against `get_mode_list()` by exact string.
- **When offline, getters return `""` — never stale cache.** `not1mm/radio.py:83-97` only overwrites on a truthy result, so `""` makes the UI hold last values and report `online: False`.
- **TRX index 0, channel 0 (VFO A) only.** Multi-receiver and VFO B are out of scope.
- Module docstrings follow the existing house style (author line + `GPL V3`), and every module keeps the `if __name__ == "__main__": print("I'm not the program you are looking for.")` guard used by the other `lib/` modules.
- Test files live in `test/` and follow the existing `<subject>_tests.py` naming (see `test/plugin_wag_tests.py`).

## File Structure

| File | Responsibility |
|---|---|
| `not1mm/lib/tci_protocol.py` | **Create.** Pure functions: frame parse/split, command build, mode translation, bandwidth math. No Qt, no sockets. |
| `not1mm/lib/tci_client.py` | **Create.** `TCIClient` — `QWebSocket` on its own `QThread`, state cache, reconnect backoff, shutdown. |
| `not1mm/lib/cat_tci.py` | **Create.** `TciCAT(CAT)` — maps the CAT contract onto the client. |
| `not1mm/testing/faketci.py` | **Create.** Minimal TCI server for testing without AetherSDR. |
| `not1mm/radio.py` | **Modify.** Dispatch `"tci"`; close the CAT object on loop exit. |
| `not1mm/__main__.py:3835` | **Modify.** `usetci` branch. |
| `not1mm/lib/preferences.py:57` | **Modify.** `"usetci": False` default. |
| `not1mm/lib/settings.py:32-34,126,304` | **Modify.** Port hint, load, save. |
| `not1mm/data/configuration.ui:560` | **Modify.** `usetci_radioButton` in `cat_method_group`. |
| `test/tci_protocol_tests.py` | **Create.** Unit tests for the pure layer. |
| `test/tci_client_tests.py` | **Create.** State-cache tests driving `handle_frame` directly. |
| `test/cat_tci_tests.py` | **Create.** CAT contract tests against a stub client. |

The three-way split is deliberate: the pure protocol layer holds the fiddly string handling and is the highest-value thing to test, and it stays testable without Qt or a socket.

---

### Task 1: Dev environment and AetherSDR handshake capture

The spec requires pinning command signatures to what AetherSDR actually speaks rather than assuming. This task produces that evidence. It also establishes the venv every later task's tests need — the system Python has no pytest.

**Files:**
- Create: `not1mm/testing/tci_probe.py`
- Create: `docs/superpowers/specs/2026-08-01-tci-handshake.md`

**Interfaces:**
- Consumes: nothing.
- Produces: a recorded handshake transcript. Later tasks read it to confirm/correct the `cw_msg` argument signature and the `modulation_list` contents.

- [ ] **Step 1: Create the dev virtualenv**

```bash
cd /Users/stephaneblanchard/dev/not1mm
uv venv
uv pip install -e . pytest
```

- [ ] **Step 2: Verify pytest runs**

Run: `.venv/bin/python -m pytest test/ -q`
Expected: the existing suite collects and passes (`test/plugin_wag_tests.py`, `test/plugin_euhfc_tests.py`).

- [ ] **Step 3: Write the probe script**

Create `not1mm/testing/tci_probe.py`:

```python
"""
Connect to a TCI server and dump every frame it sends, verbatim.

Used to pin not1mm's TCI command mapping to what the server actually speaks,
rather than to what the protocol docs claim. Not part of the application.

Usage: python -m not1mm.testing.tci_probe [host] [port]
"""

import sys

from PyQt6.QtCore import QCoreApplication, QTimer, QUrl
from PyQt6.QtWebSockets import QWebSocket


def main() -> None:
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 40001

    app = QCoreApplication([])
    socket = QWebSocket()

    def on_connected() -> None:
        print(f"--- connected to ws://{host}:{port} ---", flush=True)

    def on_text(payload: str) -> None:
        print(payload, flush=True)

    def on_error(error) -> None:
        print(f"--- error: {error} ---", flush=True)
        app.quit()

    socket.connected.connect(on_connected)
    socket.textMessageReceived.connect(on_text)
    socket.errorOccurred.connect(on_error)
    socket.open(QUrl(f"ws://{host}:{port}"))

    # Capture the handshake plus a window for manual dial/mode/PTT changes.
    QTimer.singleShot(60000, app.quit)
    app.exec()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Capture the handshake against live AetherSDR**

Start AetherSDR with TCI enabled, then:

```bash
.venv/bin/python -m not1mm.testing.tci_probe 127.0.0.1 40001 | tee /tmp/tci-handshake.txt
```

While it runs, exercise the radio manually: turn the VFO dial, change mode to CW and back, change the filter width, and key/unkey PTT. This makes the server emit every frame the backend needs to parse.

- [ ] **Step 5: Record the findings**

Create `docs/superpowers/specs/2026-08-01-tci-handshake.md` containing the verbatim transcript and, extracted from it, these specific answers:

1. The `protocol:` / `device:` lines (TCI version AetherSDR speaks)
2. The full `modulation_list:` contents — the exact lowercase mode names
3. The observed argument order for `vfo:`, `modulation:`, `rx_filter_band:`, `trx:`
4. Whether `cw_msg:` is accepted, and its argument count and order
5. Whether `ready;` terminates the handshake

**If any of these differ from the spec's mapping table, note the difference explicitly** — Tasks 2-4 must be built against the recorded reality, not the spec's assumption.

- [ ] **Step 6: Commit**

```bash
git add not1mm/testing/tci_probe.py docs/superpowers/specs/2026-08-01-tci-handshake.md
git commit -m "test: add TCI probe script and record AetherSDR handshake"
```

---

### Task 2: Pure protocol layer

**Files:**
- Create: `not1mm/lib/tci_protocol.py`
- Test: `test/tci_protocol_tests.py`

**Interfaces:**
- Consumes: the mode names recorded in Task 1 Step 5.
- Produces:
  - `parse_frame(frame: str) -> tuple[str, list[str]] | None`
  - `split_frames(payload: str) -> list[str]`
  - `build_command(name: str, *args) -> str`
  - `tci_mode_to_not1mm(mode: str) -> str`
  - `not1mm_mode_to_tci(mode: str) -> str`
  - `bandwidth_from_filter_band(low: str, high: str) -> str`
  - `TCI_TO_NOT1MM_MODE: dict[str, str]`

- [ ] **Step 1: Write the failing tests**

Create `test/tci_protocol_tests.py`:

```python
import pytest

from not1mm.lib.tci_protocol import (
    bandwidth_from_filter_band,
    build_command,
    not1mm_mode_to_tci,
    parse_frame,
    split_frames,
    tci_mode_to_not1mm,
)


@pytest.mark.parametrize(
    "frame, expected",
    [
        ("vfo:0,0,14030000;", ("vfo", ["0", "0", "14030000"])),
        ("ready;", ("ready", [])),
        ("trx:0,true;", ("trx", ["0", "true"])),
        ("rx_filter_band:0,-500,500;", ("rx_filter_band", ["0", "-500", "500"])),
        ("  vfo:0,0,14030000;  ", ("vfo", ["0", "0", "14030000"])),
        ("VFO:0,0,14030000;", ("vfo", ["0", "0", "14030000"])),
        ("vfo:0,0,14030000", None),  # no terminator
        (";", None),
        ("", None),
        (":1,2;", None),  # empty command name
    ],
)
def test_parse_frame(frame, expected):
    assert parse_frame(frame) == expected


def test_split_frames_handles_multiple_commands_in_one_payload():
    payload = "device:AetherSDR;trx_count:1;ready;"
    assert split_frames(payload) == ["device:AetherSDR;", "trx_count:1;", "ready;"]


def test_split_frames_ignores_trailing_whitespace_fragment():
    assert split_frames("ready;\n") == ["ready;"]


@pytest.mark.parametrize(
    "args, expected",
    [
        (("vfo", 0, 0, 14030000), "vfo:0,0,14030000;"),
        (("modulation", 0, "cw"), "modulation:0,cw;"),
        (("trx", 0, "true"), "trx:0,true;"),
        (("cw_macros_speed", 25), "cw_macros_speed:25;"),
        (("stop",), "stop;"),
    ],
)
def test_build_command(args, expected):
    assert build_command(*args) == expected


def test_build_command_roundtrips_through_parse_frame():
    assert parse_frame(build_command("vfo", 0, 0, 14030000)) == (
        "vfo",
        ["0", "0", "14030000"],
    )


@pytest.mark.parametrize(
    "tci, not1mm",
    [
        ("cw", "CW"),
        ("lsb", "LSB"),
        ("usb", "USB"),
        ("digl", "DIGI-L"),
        ("digu", "DIGI-U"),
        ("nfm", "FM"),
        ("CW", "CW"),  # case insensitive
    ],
)
def test_tci_mode_to_not1mm(tci, not1mm):
    assert tci_mode_to_not1mm(tci) == not1mm


def test_tci_mode_to_not1mm_passes_through_unknown_modes_uppercased():
    assert tci_mode_to_not1mm("someNewMode") == "SOMENEWMODE"


@pytest.mark.parametrize(
    "not1mm, tci",
    [
        ("CW", "cw"),
        ("USB", "usb"),
        ("DIGI-L", "digl"),
        ("RTTY", "digl"),
        ("RTTY-R", "digu"),
        ("FM", "nfm"),
    ],
)
def test_not1mm_mode_to_tci(not1mm, tci):
    assert not1mm_mode_to_tci(not1mm) == tci


def test_mode_translation_roundtrips_for_every_known_tci_mode():
    from not1mm.lib.tci_protocol import TCI_TO_NOT1MM_MODE

    for tci in TCI_TO_NOT1MM_MODE:
        assert not1mm_mode_to_tci(tci_mode_to_not1mm(tci)) == tci


def test_cw_and_data_modes_match_radio_module_expectations():
    """Radio matches get_mode_list() against these lists by exact string."""
    from not1mm.radio import Radio

    assert tci_mode_to_not1mm("cw") in Radio.cw_list
    assert tci_mode_to_not1mm("digl") in Radio.rtty_list


@pytest.mark.parametrize(
    "low, high, expected",
    [
        ("-500", "500", "1000"),
        ("300", "2700", "2400"),
        ("500", "-500", "1000"),  # order independent
        ("0", "0", "0"),
        ("junk", "500", ""),
        ("", "", ""),
    ],
)
def test_bandwidth_from_filter_band(low, high, expected):
    assert bandwidth_from_filter_band(low, high) == expected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest test/tci_protocol_tests.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'not1mm.lib.tci_protocol'`

- [ ] **Step 3: Write the implementation**

Create `not1mm/lib/tci_protocol.py`:

```python
"""
TCI protocol helpers: frame parsing, command building, mode translation.
Email: michael.bridak@gmail.com
GPL V3

Pure functions only -- no sockets, no Qt, no not1mm state. The fiddly string
handling lives here so it stays testable without a running SDR.
"""

import logging

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("tci_protocol")

# TCI modulation names are lowercase and do not match not1mm's conventions.
# Radio.cw_list / Radio.rtty_list (not1mm/radio.py:36-42) match the output of
# get_mode_list() by exact string, so everything is normalized to not1mm's
# uppercase names on the way in.
TCI_TO_NOT1MM_MODE = {
    "cw": "CW",
    "lsb": "LSB",
    "usb": "USB",
    "dsb": "DSB",
    "am": "AM",
    "sam": "SAM",
    "nfm": "FM",
    "wfm": "WFM",
    "digl": "DIGI-L",
    "digu": "DIGI-U",
    "drm": "DRM",
}

NOT1MM_TO_TCI_MODE = {v: k for k, v in TCI_TO_NOT1MM_MODE.items()}
# not1mm uses RTTY as its generic data mode; TCI has no RTTY, so it lands on
# the digital sidebands. Without this, selecting RTTY would send "rtty" and the
# SDR would reject it.
NOT1MM_TO_TCI_MODE["RTTY"] = "digl"
NOT1MM_TO_TCI_MODE["RTTY-R"] = "digu"


def parse_frame(frame: str) -> tuple[str, list[str]] | None:
    """Split one TCI frame into (command, args).

    "vfo:0,0,14030000;" -> ("vfo", ["0", "0", "14030000"])
    "ready;"            -> ("ready", [])

    Returns None for anything malformed. TCI servers emit plenty of commands
    not1mm does not care about, so callers drop None quietly rather than
    treating it as an error.
    """
    frame = frame.strip()
    if not frame.endswith(";"):
        return None
    body = frame[:-1].strip()
    if not body:
        return None
    if ":" not in body:
        return body.lower(), []
    name, _, argstr = body.partition(":")
    name = name.strip().lower()
    if not name:
        return None
    args = [a.strip() for a in argstr.split(",")] if argstr.strip() else []
    return name, args


def split_frames(payload: str) -> list[str]:
    """Split a websocket text payload into individual ';'-terminated frames.

    One payload may carry several commands, which is normal during the connect
    handshake.
    """
    return [chunk + ";" for chunk in payload.split(";") if chunk.strip()]


def build_command(name: str, *args) -> str:
    """Build a TCI command frame.

    build_command("vfo", 0, 0, 14030000) -> "vfo:0,0,14030000;"
    build_command("stop")                -> "stop;"
    """
    if not args:
        return f"{name};"
    return f"{name}:{','.join(str(a) for a in args)};"


def tci_mode_to_not1mm(mode: str) -> str:
    """Normalize a TCI modulation name to not1mm's convention."""
    cleaned = mode.strip()
    return TCI_TO_NOT1MM_MODE.get(cleaned.lower(), cleaned.upper())


def not1mm_mode_to_tci(mode: str) -> str:
    """Translate a not1mm mode name to TCI's convention."""
    cleaned = mode.strip()
    return NOT1MM_TO_TCI_MODE.get(cleaned.upper(), cleaned.lower())


def bandwidth_from_filter_band(low: str, high: str) -> str:
    """Derive filter width in Hz from an rx_filter_band edge pair.

    Returns "" when unparseable, which the caller treats as "no update".
    """
    try:
        return str(abs(int(high) - int(low)))
    except (TypeError, ValueError):
        return ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest test/tci_protocol_tests.py -v`
Expected: PASS, all cases.

- [ ] **Step 5: Reconcile with the recorded handshake**

Open `docs/superpowers/specs/2026-08-01-tci-handshake.md` from Task 1. Compare the recorded `modulation_list:` names against `TCI_TO_NOT1MM_MODE`. Add any AetherSDR mode not in the table and add a test case for it. Remove nothing — unknown modes already pass through uppercased.

- [ ] **Step 6: Commit**

```bash
git add not1mm/lib/tci_protocol.py test/tci_protocol_tests.py
git commit -m "feat: add TCI protocol parsing and mode translation"
```

---

### Task 3: TCIClient websocket transport

**Files:**
- Create: `not1mm/lib/tci_client.py`
- Test: `test/tci_client_tests.py`

**Interfaces:**
- Consumes: `parse_frame`, `split_frames`, `tci_mode_to_not1mm`, `bandwidth_from_filter_band` from Task 2.
- Produces: `TCIClient(host: str, port: int, autostart: bool = True)` with:
  - `get(key: str, default="") -> str | list` — thread-safe cache read
  - `online -> bool` property (True only after `ready;`)
  - `send(command: str) -> None` — thread-safe, queues onto the TCI thread
  - `handle_frame(name: str, args: list) -> None` — pure cache update, socket-free, public for tests
  - `wait_for_ready(timeout_ms: int) -> bool`
  - `close() -> None`
  - State keys: `"vfo"`, `"mode"`, `"bw"`, `"ptt"`, `"modes"`, `"ready"`

- [ ] **Step 1: Write the failing tests**

`handle_frame` is deliberately socket-free so the cache logic is testable without a server. Create `test/tci_client_tests.py`:

```python
import pytest

from not1mm.lib.tci_client import TCIClient


@pytest.fixture
def client():
    """A client whose thread never starts, so only the cache logic is exercised.

    autostart=False rather than bypassing __init__: TCIClient is a QObject, and
    building one via __new__ leaves the C++ side uninitialized, which PyQt6
    rejects with "'__init__' method of object's base class not called".
    """
    return TCIClient("127.0.0.1", 40001, autostart=False)


def test_starts_offline_with_empty_state(client):
    assert client.online is False
    assert client.get("vfo") == ""
    assert client.get("mode") == ""
    assert client.get("modes") == []


def test_ready_frame_brings_client_online(client):
    client.handle_frame("ready", [])
    assert client.online is True


def test_vfo_frame_updates_cache(client):
    client.handle_frame("vfo", ["0", "0", "14030000"])
    assert client.get("vfo") == "14030000"


def test_vfo_value_is_numeric_for_radio_module(client):
    client.handle_frame("vfo", ["0", "0", "14030000"])
    assert client.get("vfo").isnumeric()


def test_non_numeric_vfo_is_rejected(client):
    client.handle_frame("vfo", ["0", "0", "14.030"])
    assert client.get("vfo") == ""


def test_vfo_for_other_trx_is_ignored(client):
    client.handle_frame("vfo", ["1", "0", "14030000"])
    assert client.get("vfo") == ""


def test_vfo_for_channel_b_is_ignored(client):
    client.handle_frame("vfo", ["0", "1", "7020000"])
    assert client.get("vfo") == ""


def test_modulation_frame_is_normalized(client):
    client.handle_frame("modulation", ["0", "cw"])
    assert client.get("mode") == "CW"


def test_rx_filter_band_becomes_bandwidth(client):
    client.handle_frame("rx_filter_band", ["0", "-500", "500"])
    assert client.get("bw") == "1000"


def test_unparseable_filter_band_leaves_bandwidth_untouched(client):
    client.handle_frame("rx_filter_band", ["0", "-500", "500"])
    client.handle_frame("rx_filter_band", ["0", "junk", "500"])
    assert client.get("bw") == "1000"


@pytest.mark.parametrize("value, expected", [("true", "1"), ("false", "0"), ("TRUE", "1")])
def test_trx_frame_sets_ptt(client, value, expected):
    client.handle_frame("trx", ["0", value])
    assert client.get("ptt") == expected


def test_modulation_list_is_normalized(client):
    client.handle_frame("modulation_list", ["cw", "lsb", "usb", "digl"])
    assert client.get("modes") == ["CW", "LSB", "USB", "DIGI-L"]


def test_unknown_frames_are_ignored_without_raising(client):
    client.handle_frame("iq_samplerate", ["48000"])
    client.handle_frame("audio_start", [])
    assert client.get("vfo") == ""


def test_clear_state_drops_everything_including_ready(client):
    client.handle_frame("ready", [])
    client.handle_frame("vfo", ["0", "0", "14030000"])
    client.clear_state()
    assert client.online is False
    assert client.get("vfo") == ""


def test_clear_state_preserves_mode_list(client):
    """Supported modes are a device property, not volatile state."""
    client.handle_frame("modulation_list", ["cw", "usb"])
    client.clear_state()
    assert client.get("modes") == ["CW", "USB"]


def test_get_modes_returns_a_copy(client):
    client.handle_frame("modulation_list", ["cw"])
    client.get("modes").append("BOGUS")
    assert client.get("modes") == ["CW"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest test/tci_client_tests.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'not1mm.lib.tci_client'`

- [ ] **Step 3: Write the implementation**

Create `not1mm/lib/tci_client.py`:

```python
"""
K6GTE, TCI websocket transport
Email: michael.bridak@gmail.com
GPL V3

Owns a QWebSocket on its own QThread running a real event loop, so socket
signals are actually delivered -- Radio.run() blocks in a while loop and never
returns to an event loop, so the socket cannot live there.

TCI pushes state changes unprompted. This class caches them behind a mutex and
the CAT layer reads the cache instead of querying.
"""

import logging

from PyQt6.QtCore import (
    QMetaObject,
    QMutex,
    QMutexLocker,
    QObject,
    Qt,
    QThread,
    QTimer,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtWebSockets import QWebSocket

from not1mm.lib.tci_protocol import (
    bandwidth_from_filter_band,
    parse_frame,
    split_frames,
    tci_mode_to_not1mm,
)

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("tci_client")

RECONNECT_BACKOFF_MS = (1000, 2000, 5000)


class TCIClient(QObject):
    """Websocket transport and state cache for a TCI server."""

    send_requested = pyqtSignal(str)

    def __init__(self, host: str, port: int, autostart: bool = True) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.init_state()
        self.thread = QThread()
        # autostart=False gives tests a cache-only instance with no thread and
        # no socket, while still constructing the QObject properly.
        if autostart:
            self.moveToThread(self.thread)
            self.thread.started.connect(self.open_socket)
            self.send_requested.connect(self.write_command)
            self.thread.start()

    def init_state(self) -> None:
        """Set up the cache."""
        self.socket = None
        self.reconnect_timer = None
        self.backoff = 0
        self.closing = False
        self.mutex = QMutex()
        self.state = {
            "vfo": "",
            "mode": "",
            "bw": "",
            "ptt": "0",
            "modes": [],
            "ready": False,
        }

    # ---- cache access: safe to call from any thread ----

    def get(self, key: str, default=""):
        with QMutexLocker(self.mutex):
            value = self.state.get(key, default)
            if isinstance(value, list):
                return list(value)  # copy, so callers cannot mutate the cache
            return value

    def set(self, key: str, value) -> None:
        with QMutexLocker(self.mutex):
            self.state[key] = value

    @property
    def online(self) -> bool:
        """True only once the server has finished its handshake."""
        return bool(self.get("ready", False))

    def clear_state(self) -> None:
        """Drop volatile state on disconnect. The mode list survives: it is a
        device capability, not live state, and re-querying it costs a round
        trip we do not need."""
        with QMutexLocker(self.mutex):
            self.state.update(
                {"vfo": "", "mode": "", "bw": "", "ptt": "0", "ready": False}
            )

    def send(self, command: str) -> None:
        """Queue a command onto the TCI thread. Safe from any thread -- the
        signal crosses threads as a queued connection."""
        self.send_requested.emit(command)

    def wait_for_ready(self, timeout_ms: int) -> bool:
        """Block until the handshake completes or the timeout expires.

        Called once at construction so get_mode_list() has data before
        Radio.__init__ reads it.
        """
        waited = 0
        while waited < timeout_ms:
            if self.online:
                return True
            QThread.msleep(50)
            waited += 50
        return self.online

    # ---- frame handling: no socket calls, so tests drive it directly ----

    def handle_frame(self, name: str, args: list) -> None:
        """Update the cache from one parsed frame."""
        if name == "ready":
            logger.debug("TCI handshake complete")
            self.set("ready", True)
        elif name == "vfo" and len(args) >= 3 and args[0] == "0" and args[1] == "0":
            if args[2].isnumeric():  # Radio rejects non-numeric VFO values
                self.set("vfo", args[2])
        elif name == "modulation" and len(args) >= 2 and args[0] == "0":
            self.set("mode", tci_mode_to_not1mm(args[1]))
        elif name == "rx_filter_band" and len(args) >= 3 and args[0] == "0":
            bandwidth = bandwidth_from_filter_band(args[1], args[2])
            if bandwidth:
                self.set("bw", bandwidth)
        elif name == "trx" and len(args) >= 2 and args[0] == "0":
            self.set("ptt", "1" if args[1].strip().lower() == "true" else "0")
        elif name == "modulation_list":
            self.set("modes", [tci_mode_to_not1mm(m) for m in args if m])
        else:
            logger.debug("Ignoring TCI frame: %s %s", name, args)

    # ---- everything below runs on the TCI thread ----

    @pyqtSlot()
    def open_socket(self) -> None:
        """Build the socket. Runs on the TCI thread so the socket's parent
        affinity is correct."""
        self.socket = QWebSocket()
        self.socket.connected.connect(self.on_connected)
        self.socket.disconnected.connect(self.on_disconnected)
        self.socket.textMessageReceived.connect(self.on_text_message)
        self.socket.errorOccurred.connect(self.on_error)
        self.reconnect_timer = QTimer()
        self.reconnect_timer.setSingleShot(True)
        self.reconnect_timer.timeout.connect(self.connect_to_server)
        self.connect_to_server()

    @pyqtSlot()
    def connect_to_server(self) -> None:
        if self.closing:
            return
        url = f"ws://{self.host}:{self.port}"
        logger.debug("Connecting to TCI %s", url)
        self.socket.open(QUrl(url))

    @pyqtSlot()
    def on_connected(self) -> None:
        logger.debug("TCI socket open, awaiting handshake")
        self.backoff = 0

    @pyqtSlot()
    def on_disconnected(self) -> None:
        logger.info("TCI socket disconnected")
        self.clear_state()
        self.schedule_reconnect()

    def on_error(self, error) -> None:
        logger.info("TCI socket error: %s", error)
        self.clear_state()
        self.schedule_reconnect()

    def schedule_reconnect(self) -> None:
        if self.closing or self.reconnect_timer is None:
            return
        delay = RECONNECT_BACKOFF_MS[min(self.backoff, len(RECONNECT_BACKOFF_MS) - 1)]
        self.backoff += 1
        if not self.reconnect_timer.isActive():
            logger.debug("Reconnecting to TCI in %d ms", delay)
            self.reconnect_timer.start(delay)

    @pyqtSlot(str)
    def write_command(self, command: str) -> None:
        if self.socket is None or not self.online:
            return
        logger.debug("> %s", command)
        self.socket.sendTextMessage(command)

    @pyqtSlot(str)
    def on_text_message(self, payload: str) -> None:
        for frame in split_frames(payload):
            parsed = parse_frame(frame)
            if parsed is None:
                logger.debug("Unparseable TCI frame: %s", frame)
                continue
            self.handle_frame(*parsed)

    def close(self) -> None:
        """Stop the socket and its thread. Must run before app exit or the
        process hangs on a live thread."""
        self.closing = True
        if self.thread.isRunning():
            QMetaObject.invokeMethod(
                self, "shutdown", Qt.ConnectionType.BlockingQueuedConnection
            )
            self.thread.quit()
            self.thread.wait(500)

    @pyqtSlot()
    def shutdown(self) -> None:
        if self.reconnect_timer is not None:
            self.reconnect_timer.stop()
        if self.socket is not None:
            self.socket.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest test/tci_client_tests.py -v`
Expected: PASS, all cases.

- [ ] **Step 5: Commit**

```bash
git add not1mm/lib/tci_client.py test/tci_client_tests.py
git commit -m "feat: add TCI websocket client with state cache"
```

---

### Task 4: TciCAT backend

**Files:**
- Create: `not1mm/lib/cat_tci.py`
- Test: `test/cat_tci_tests.py`

**Interfaces:**
- Consumes: `TCIClient` (Task 3), `build_command` and `not1mm_mode_to_tci` (Task 2), `CAT` base (`not1mm/lib/cat_interface.py:15`).
- Produces: `TciCAT(host: str, port: int)` implementing the CAT contract, plus `close()`. Task 5 constructs it from `radio.py`.

- [ ] **Step 1: Write the failing tests**

Create `test/cat_tci_tests.py`:

```python
import pytest

from not1mm.lib.cat_tci import TciCAT


class StubClient:
    """Stands in for TCIClient: no thread, no socket, records what was sent."""

    def __init__(self):
        self.sent = []
        self.state = {
            "vfo": "",
            "mode": "",
            "bw": "",
            "ptt": "0",
            "modes": [],
            "ready": False,
        }

    @property
    def online(self):
        return bool(self.state["ready"])

    def get(self, key, default=""):
        value = self.state.get(key, default)
        return list(value) if isinstance(value, list) else value

    def send(self, command):
        self.sent.append(command)

    def wait_for_ready(self, timeout_ms):
        return self.online

    def close(self):
        self.state["ready"] = False


@pytest.fixture
def cat():
    """A TciCAT wired to a stub, bypassing __init__'s real client."""
    instance = TciCAT.__new__(TciCAT)
    instance.interface = "tci"
    instance.host = "127.0.0.1"
    instance.port = 40001
    instance.online = False
    instance.client = StubClient()
    return instance


def go_online(cat, **state):
    cat.client.state["ready"] = True
    cat.client.state.update(state)


# ---- offline behavior: the contract that keeps stale data off the screen ----


@pytest.mark.parametrize("getter", ["get_vfo", "get_mode", "get_bw"])
def test_getters_return_empty_when_offline(cat, getter):
    assert getattr(cat, getter)() == ""


def test_getters_return_empty_even_when_cache_holds_stale_values(cat):
    """Radio only overwrites on truthy results, so empty means 'hold last
    known' rather than painting a frozen frequency as live."""
    cat.client.state.update({"vfo": "14030000", "mode": "CW", "bw": "500"})
    assert cat.get_vfo() == ""
    assert cat.get_mode() == ""
    assert cat.get_bw() == ""


def test_online_flag_tracks_the_client(cat):
    cat.get_vfo()
    assert cat.online is False
    go_online(cat)
    cat.get_vfo()
    assert cat.online is True


def test_setters_send_nothing_when_offline(cat):
    cat.set_vfo("14030000")
    cat.set_mode("CW")
    cat.ptt_on()
    assert cat.client.sent == []


# ---- online behavior ----


def test_get_vfo_returns_cached_numeric_value(cat):
    go_online(cat, vfo="14030000")
    assert cat.get_vfo() == "14030000"
    assert cat.get_vfo().isnumeric()


def test_get_mode_returns_cached_value(cat):
    go_online(cat, mode="CW")
    assert cat.get_mode() == "CW"


def test_get_bw_returns_cached_value(cat):
    go_online(cat, bw="1000")
    assert cat.get_bw() == "1000"


def test_get_ptt_returns_zero_when_offline(cat):
    assert cat.get_ptt() == "0"


def test_get_mode_list_available_regardless_of_online_state(cat):
    cat.client.state["modes"] = ["CW", "USB"]
    assert cat.get_mode_list() == ["CW", "USB"]


def test_set_vfo_sends_tci_command(cat):
    go_online(cat)
    assert cat.set_vfo("14030000") is True
    assert cat.client.sent == ["vfo:0,0,14030000;"]


def test_set_mode_translates_to_tci_naming(cat):
    go_online(cat)
    cat.set_mode("CW")
    cat.set_mode("RTTY")
    assert cat.client.sent == ["modulation:0,cw;", "modulation:0,digl;"]


def test_ptt_on_and_off(cat):
    go_online(cat)
    cat.ptt_on()
    cat.ptt_off()
    assert cat.client.sent == ["trx:0,true;", "trx:0,false;"]


def test_set_cw_speed_sends_macros_speed(cat):
    go_online(cat)
    cat.set_cw_speed(25)
    assert cat.client.sent == ["cw_macros_speed:25;"]


def test_sendcw_sends_text(cat):
    go_online(cat)
    cat.sendcw("CQ TEST")
    assert cat.client.sent == ["cw_msg:0,,,CQ TEST;"]


def test_close_delegates_to_client(cat):
    go_online(cat)
    cat.close()
    assert cat.client.online is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest test/cat_tci_tests.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'not1mm.lib.cat_tci'`

- [ ] **Step 3: Write the implementation**

Create `not1mm/lib/cat_tci.py`:

```python
"""
K6GTE, CAT interface abstraction
Email: michael.bridak@gmail.com
GPL V3

TCI backend, for SDRs such as AetherSDR and ExpertSDR.

Unlike flrig and rigctld, nothing here queries the radio. TCI pushes state
changes and TCIClient caches them, so the getters are cache reads: instant,
non-blocking, and fresher than a poll would be.
"""

import logging

from not1mm.lib.cat_interface import CAT
from not1mm.lib.tci_client import TCIClient
from not1mm.lib.tci_protocol import build_command, not1mm_mode_to_tci

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("cat_tci")

# Long enough for a local SDR's handshake, short enough not to stall startup.
READY_TIMEOUT_MS = 1500


class TciCAT(CAT):
    """CAT control via the TCI protocol"""

    def __init__(self, host: str, port: int) -> None:
        """
        Computer Aided Transceiver abstraction class.
        Offers a normalized interface; this is the TCI class.

        Takes 2 inputs to setup the class.

        A string defining the host, example: 'localhost' or '127.0.0.1'

        An integer defining the network port used. Commonly 40001 for TCI.

        A variable 'online' is set to True once the TCI server completes its
        handshake, otherwise False.
        """
        super().__init__(host, port)
        self.interface = "tci"
        self.client = TCIClient(host, port)
        # Radio.__init__ reads get_mode_list() immediately, so give the
        # handshake a moment to land before returning.
        self.client.wait_for_ready(READY_TIMEOUT_MS)
        self.online = self.client.online

    def refresh_online(self) -> bool:
        """Sync the public online flag with the transport and return it."""
        self.online = self.client.online
        return self.online

    # ---- getters ----
    # Offline returns "" rather than cached values: Radio only overwrites on a
    # truthy result, so "" holds the last known reading and reports offline.
    # Returning stale cache would paint a dead radio as live.

    def get_vfo(self) -> str:
        """Poll the radio for current vfo using the interface"""
        if not self.refresh_online():
            return ""
        return self.client.get("vfo", "")

    def get_mode(self) -> str:
        """Returns the current mode of the radio"""
        if not self.refresh_online():
            return ""
        return self.client.get("mode", "")

    def get_bw(self) -> str:
        """Get current vfo bandwidth"""
        if not self.refresh_online():
            return ""
        return self.client.get("bw", "")

    def get_ptt(self) -> str:
        """Get PTT state"""
        if not self.refresh_online():
            return "0"
        return self.client.get("ptt", "0")

    def get_mode_list(self) -> list:
        """Get a list of modes supported by the radio.

        Served even while offline: it is a device capability captured at
        handshake, and Radio caches it once at construction.
        """
        return self.client.get("modes", [])

    # ---- setters ----

    def set_vfo(self, freq: str) -> bool:
        """Sets the radios VFO. Defaults to VFOA."""
        if not self.refresh_online():
            return False
        self.client.send(build_command("vfo", 0, 0, str(freq)))
        return True

    def set_mode(self, mode: str) -> bool:
        """Sets the radios mode"""
        if not self.refresh_online():
            return False
        self.client.send(build_command("modulation", 0, not1mm_mode_to_tci(mode)))
        return True

    def ptt_on(self) -> bool:
        """turn ptt on"""
        if not self.refresh_online():
            return False
        self.client.send(build_command("trx", 0, "true"))
        return True

    def ptt_off(self) -> bool:
        """turn ptt off"""
        if not self.refresh_online():
            return False
        self.client.send(build_command("trx", 0, "false"))
        return True

    # ---- CW, reached via the existing "CW via CAT" option (cwtype == 3) ----

    def sendcw(self, texttosend) -> None:
        """Send CW text through the radio's keyer"""
        if not self.refresh_online():
            return
        self.client.send(build_command("cw_msg", 0, "", "", texttosend))

    def stopcw(self) -> None:
        """Abort CW transmission"""
        if not self.refresh_online():
            return
        self.client.send(build_command("cw_terminate"))

    def set_cw_speed(self, speed: int) -> None:
        """Set the CW speed in wpm"""
        if not self.refresh_online():
            return
        self.client.send(build_command("cw_macros_speed", int(speed)))

    def close(self) -> None:
        """Shut down the transport thread. Radio.run() calls this on exit."""
        self.client.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest test/cat_tci_tests.py -v`
Expected: PASS, all cases.

- [ ] **Step 5: Reconcile CW commands with the recorded handshake**

Open `docs/superpowers/specs/2026-08-01-tci-handshake.md` from Task 1, item 4. If AetherSDR's `cw_msg:` takes a different argument count or order than `cw_msg:0,,,<text>;`, correct `sendcw` **and** `test_sendcw_sends_text` to match what was recorded. Same for `cw_terminate` — if the recorded transcript shows a different abort command, use that. Re-run the tests after any change.

- [ ] **Step 6: Commit**

```bash
git add not1mm/lib/cat_tci.py test/cat_tci_tests.py
git commit -m "feat: add TciCAT backend implementing the CAT contract over TCI"
```

---

### Task 5: Wire TCI into the application

**Files:**
- Modify: `not1mm/radio.py:12-14` (import), `:56-61` (dispatch), `:75-109` (close on exit)
- Modify: `not1mm/lib/preferences.py:57`
- Modify: `not1mm/lib/settings.py:32-34`, `:126`, `:304`
- Modify: `not1mm/data/configuration.ui:560`
- Modify: `not1mm/__main__.py:3835`

**Interfaces:**
- Consumes: `TciCAT` from Task 4.
- Produces: a running TCI backend selected by the `usetci` preference. No new public API.

- [ ] **Step 1: Add the dispatch branch in radio.py**

Add the import alongside the others at `not1mm/radio.py:12-14`:

```python
from not1mm.lib.cat_tci import TciCAT
```

Then extend the dispatch at `:56-61`:

```python
            if self.interface == "flrig":
                self.cat = FlrigCAT(self.host, self.port)
            elif self.interface == "rigctld":
                self.cat = RigctldCAT(self.host, self.port)
            elif self.interface == "tci":
                self.cat = TciCAT(self.host, self.port)
            else:
                self.cat = FakeCAT(self.host, self.port)
```

- [ ] **Step 2: Close the CAT object when the poll loop exits**

This is the fix for the shutdown hang. `TciCAT` owns a second `QThread`; without this, it outlives the app. Both teardown paths (`__main__.py:2563` on close and `:3813` on settings reload) set `time_to_quit`, so hooking the loop exit covers both and needs no `__main__.py` change.

At the end of `Radio.run()` in `not1mm/radio.py`, after the `while` loop:

```python
    def run(self):
        while not self.time_to_quit:
            ...
            QThread.msleep(100)
        # Backends owning their own threads (TCI) must be torn down here, or
        # the app hangs on exit. The others have no close() and no-op.
        close = getattr(self.cat, "close", None)
        if close is not None:
            close()
```

The timing fits the existing budget: the loop wakes every 100 ms and `TCIClient.close()` waits at most 500 ms, well inside `radio_thread.wait(1000)`.

- [ ] **Step 3: Add the preference default**

In `not1mm/lib/preferences.py`, after line 58 (`"useflrig": False,`):

```python
        "usetci": False,
```

- [ ] **Step 4: Add the radio button to configuration.ui**

In `not1mm/data/configuration.ui`, insert a new `<item>` between the `useflrig_radioButton` item ending at line 560 and the `radioButton` ("None") item starting at line 561. It must carry the `cat_method_group` buttonGroup attribute or it will not be mutually exclusive with the others:

```xml
         <item>
          <widget class="QRadioButton" name="usetci_radioButton">
           <property name="font">
            <font>
             <family>JetBrains Mono</family>
             <weight>100</weight>
             <pointsize>12</pointsize>
             <strikeout>false</strikeout>
            </font>
           </property>
           <property name="accessibleName">
            <string>t c i</string>
           </property>
           <property name="accessibleDescription">
            <string>use t c i</string>
           </property>
           <property name="styleSheet">
            <string notr="true"/>
           </property>
           <property name="text">
            <string>TCI</string>
           </property>
           <attribute name="buttonGroup">
            <string notr="true">cat_method_group</string>
           </attribute>
          </widget>
         </item>
```

Also add it to the tab order, after the `useflrig_radioButton` entry at line 2869:

```xml
  <tabstop>usetci_radioButton</tabstop>
```

- [ ] **Step 5: Load and save the preference in settings.py**

Update the port hint at `not1mm/lib/settings.py:32-34`:

```python
        self.rigcontrolport_field.setToolTip(
            "Usually 4532 for rigctld, 12345 for flrig, and 40001 for TCI."
        )
```

Add the load line after `:127`:

```python
        self.usetci_radioButton.setChecked(bool(self.preference.get("usetci")))
```

Add the save line after `:305`:

```python
        self.preference["usetci"] = self.usetci_radioButton.isChecked()
```

- [ ] **Step 6: Add the branch in __main__.py**

In `not1mm/__main__.py`, after the `userigctld` branch ending at line 3844 and before the `else:` at 3846:

```python
        elif self.pref.get("usetci", False) is True:
            logger.debug(
                "Using TCI: %s",
                f"{self.pref.get('CAT_ip')} {self.pref.get('CAT_port')}",
            )
            self.rig_control = Radio(
                "tci",
                self.pref.get("CAT_ip", "127.0.0.1"),
                int(self.pref.get("CAT_port", 40001)),
            )
```

- [ ] **Step 7: Verify nothing regressed**

Run: `.venv/bin/python -m pytest test/ -v`
Expected: PASS — all tests including the three new files.

Then confirm the UI file still parses and the new widget exists:

```bash
.venv/bin/python -c "
import xml.etree.ElementTree as ET
tree = ET.parse('not1mm/data/configuration.ui')
names = [w.get('name') for w in tree.iter('widget')]
assert 'usetci_radioButton' in names, 'radio button missing'
print('configuration.ui OK')
"
```

Expected: `configuration.ui OK`

- [ ] **Step 8: Commit**

```bash
git add not1mm/radio.py not1mm/__main__.py not1mm/lib/preferences.py \
        not1mm/lib/settings.py not1mm/data/configuration.ui
git commit -m "feat: wire TCI backend into radio dispatch, settings, and UI"
```

---

### Task 6: Fake TCI server for integration testing

**Files:**
- Create: `not1mm/testing/faketci.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (deliberately independent, so a bug here cannot be mistaken for a backend bug).
- Produces: a runnable TCI server on a configurable port, following the `not1mm/testing/fakeflrig.py` precedent.

- [ ] **Step 1: Write the fake server**

Create `not1mm/testing/faketci.py`:

```python
"""
A minimal TCI server, for exercising not1mm's TCI backend without an SDR.

Sends a plausible handshake, then accepts and echoes state changes the way a
real TCI server does. Deliberately shares no code with the client, so a bug
here cannot masquerade as a backend bug.

Usage: python -m not1mm.testing.faketci [port]
"""

import sys

from PyQt6.QtCore import QCoreApplication, QTimer
from PyQt6.QtWebSockets import QWebSocketServer

HANDSHAKE = [
    "protocol:ExpertSDR3,1.9;",
    "device:FakeSDR;",
    "trx_count:1;",
    "modulation_list:am,sam,dsb,lsb,usb,cw,nfm,digl,digu,wfm,drm;",
    "vfo:0,0,14030000;",
    "modulation:0,cw;",
    "rx_filter_band:0,-500,500;",
    "trx:0,false;",
    "ready;",
]


class FakeTCIServer:
    def __init__(self, port: int) -> None:
        self.clients = []
        self.server = QWebSocketServer(
            "FakeTCI", QWebSocketServer.SslMode.NonSecureMode
        )
        if not self.server.listen(port=port):
            print(f"Failed to listen on {port}", flush=True)
            raise SystemExit(1)
        self.server.newConnection.connect(self.on_new_connection)
        print(f"FakeTCI listening on ws://127.0.0.1:{port}", flush=True)

    def on_new_connection(self) -> None:
        socket = self.server.nextPendingConnection()
        socket.textMessageReceived.connect(
            lambda message: self.on_message(socket, message)
        )
        socket.disconnected.connect(lambda: self.on_disconnected(socket))
        self.clients.append(socket)
        print("client connected, sending handshake", flush=True)
        for frame in HANDSHAKE:
            socket.sendTextMessage(frame)

    def on_message(self, socket, message: str) -> None:
        print(f"< {message}", flush=True)
        # A real TCI server echoes accepted state changes back to all clients.
        for frame in [f + ";" for f in message.split(";") if f.strip()]:
            for client in self.clients:
                client.sendTextMessage(frame)

    def on_disconnected(self, socket) -> None:
        print("client disconnected", flush=True)
        if socket in self.clients:
            self.clients.remove(socket)
        socket.deleteLater()


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 40001
    app = QCoreApplication([])
    server = FakeTCIServer(port)
    QTimer.singleShot(600000, app.quit)
    app.exec()
    del server


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the fake server and backend talk to each other**

In one terminal:

```bash
.venv/bin/python -m not1mm.testing.faketci 40001
```

In another:

```bash
.venv/bin/python -c "
from PyQt6.QtCore import QCoreApplication, QThread
from not1mm.lib.cat_tci import TciCAT

app = QCoreApplication([])
cat = TciCAT('127.0.0.1', 40001)
print('online:', cat.online)
print('modes:', cat.get_mode_list())
print('vfo:', cat.get_vfo())
print('mode:', cat.get_mode())
print('bw:', cat.get_bw())
cat.set_vfo('7020000')
QThread.msleep(300)
print('vfo after set:', cat.get_vfo())
cat.close()
"
```

Expected output:

```
online: True
modes: ['AM', 'SAM', 'DSB', 'LSB', 'USB', 'CW', 'FM', 'DIGI-L', 'DIGI-U', 'WFM', 'DRM']
vfo: 14030000
mode: CW
bw: 1000
vfo after set: 7020000
```

The command must also exit cleanly rather than hanging — that confirms `close()` tears the thread down.

- [ ] **Step 3: Verify offline behavior**

With the fake server **stopped**, run the same snippet. Expected: `online: False`, and `vfo`, `mode`, `bw` all empty strings — never stale values. The process must still exit cleanly.

- [ ] **Step 4: Verify reconnection**

Start the fake server, run a longer-lived client, kill the server mid-run, then restart it:

```bash
.venv/bin/python -c "
from PyQt6.QtCore import QCoreApplication, QThread
from not1mm.lib.cat_tci import TciCAT

app = QCoreApplication([])
cat = TciCAT('127.0.0.1', 40001)
for _ in range(30):
    QThread.msleep(1000)
    print('online:', cat.online, 'vfo:', repr(cat.get_vfo()), flush=True)
cat.close()
"
```

Expected: online `True` with a frequency, then `False` with `''` after the kill, then back to `True` with a frequency within ~5 s of the restart.

- [ ] **Step 5: Commit**

```bash
git add not1mm/testing/faketci.py
git commit -m "test: add fake TCI server for integration testing"
```

---

### Task 7: Verify against live AetherSDR and document

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `Working_Contests.md` — **only if** it documents rig interfaces; check first, and skip this file if it does not.

**Interfaces:**
- Consumes: everything from Tasks 2-6.
- Produces: nothing consumed by later tasks. This is the acceptance gate for phase 1.

- [ ] **Step 1: Reinstall and launch against AetherSDR**

```bash
uv build
uv tool install --force ./dist/not1mm-*-py3-none-any.whl
```

Start AetherSDR with TCI enabled, then launch not1mm, open Settings, select **TCI** on the rig-control tab, set the address to `127.0.0.1` and the port to `40001`, and save.

- [ ] **Step 2: Verify radio state sync**

Confirm each of these in the running app:

1. not1mm's frequency display tracks AetherSDR's VFO when you turn the dial
2. Changing mode on the SDR updates not1mm's mode
3. Changing the filter width updates not1mm's bandwidth
4. Typing a frequency in not1mm moves the SDR's VFO
5. Changing band/mode in not1mm changes the SDR's mode

- [ ] **Step 3: Verify PTT and CW**

In Settings, select **CW via CAT** on the CW tab. Then confirm:

1. A CW macro (F1) keys AetherSDR and sends the text
2. The CW speed control changes the keyer speed
3. Escape aborts a transmission in progress
4. PTT engages and releases the SDR's transmitter

- [ ] **Step 4: Verify failure and recovery**

1. Close AetherSDR while not1mm is running. not1mm must show the radio offline and **hold** the last frequency rather than showing a live-looking frozen one.
2. Restart AetherSDR. not1mm must reconnect within ~5 s without a restart.
3. Quit not1mm while connected. **The process must exit cleanly with no hang** — this is the shutdown risk from the spec, and the specific thing to watch for.

- [ ] **Step 5: Confirm no regression on the other backends**

Switch to **None** (fake) in Settings and confirm the app still runs normally. If flrig or rigctld is available, switch to it and confirm it still works — none of their code was touched, but the shared `Radio.run()` exit path was.

- [ ] **Step 6: Update the changelog**

Add an entry to `CHANGELOG.md` in the existing format at the top of the file:

```
Added TCI rig control support, for SDRs such as AetherSDR and ExpertSDR.
Select TCI in the settings rig control tab; the default port is 40001.
CW keying over TCI works by also selecting "CW via CAT" on the CW tab.
```

- [ ] **Step 7: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: note TCI rig control support in changelog"
```

---

## Out of Scope for This Plan

- **Phase 2, bandmap spot push.** Hooks `Database.addspot()` (`not1mm/bandmap.py:136`) rather than the CAT interface, and still has an unresolved routing question: `BandMapWindow` is a separate `QDockWidget` communicating over signals and multicast, and is not confirmed to hold a `rig_control` reference. It gets its own spec-to-plan cycle once phase 1 is verified.
- Multi-receiver / multi-TRX and VFO B.
- TCI audio and IQ streaming.
- not1mm acting as a TCI server.
