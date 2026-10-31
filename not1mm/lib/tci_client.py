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

# Live state TCI reports per transceiver, and its value before any frame for
# that trx has arrived.
PER_TRX_DEFAULTS = {"vfo": "", "mode": "", "bw": "", "ptt": "0"}
PER_TRX_KEYS = frozenset(PER_TRX_DEFAULTS)


class TCIClient(QObject):
    """Websocket transport and state cache for a TCI server."""

    send_requested = pyqtSignal(str)

    def __init__(
        self, host: str, port: int, trx: int = 0, autostart: bool = True
    ) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.init_state()
        # Which transceiver the getters report. TCI addresses every per-radio
        # frame by a leading trx index; AetherSDR maps trx 0/1 to its first
        # two slices. State for every trx is cached regardless, so switching
        # the active trx (set_trx) is instant -- TCI only pushes on change, so
        # a client that tracked one trx would have nothing for the other
        # until its slice happened to move.
        self.trx = str(int(trx))
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
            "modes": [],
            "trx_count": 0,
            "ready": False,
        }
        # trx index (str) -> {"vfo", "mode", "bw", "ptt"}
        self.trx_state = {}

    # ---- cache access: safe to call from any thread ----

    def get(self, key: str, default=""):
        """Read a cached value. Per-trx keys report the active trx."""
        if key in PER_TRX_KEYS:
            return self.get_trx(key, self.trx, default)
        with QMutexLocker(self.mutex):
            value = self.state.get(key, default)
            if isinstance(value, list):
                return list(value)  # copy, so callers cannot mutate the cache
            return value

    def get_trx(self, key: str, trx, default=""):
        """Read a per-trx cached value for a specific trx."""
        with QMutexLocker(self.mutex):
            entry = self.trx_state.get(str(trx))
            if entry is None:
                return PER_TRX_DEFAULTS.get(key, default)
            return entry.get(key, default)

    def set(self, key: str, value) -> None:
        with QMutexLocker(self.mutex):
            self.state[key] = value

    def set_for_trx(self, trx: str, key: str, value) -> None:
        with QMutexLocker(self.mutex):
            entry = self.trx_state.setdefault(trx, dict(PER_TRX_DEFAULTS))
            entry[key] = value

    def set_trx(self, trx: int) -> None:
        """Change which trx the getters report. Safe from any thread."""
        self.trx = str(int(trx))
        logger.debug("TCI active trx now %s", self.trx)

    @property
    def online(self) -> bool:
        """True only once the server has finished its handshake."""
        return bool(self.get("ready", False))

    def clear_state(self) -> None:
        """Drop volatile state on disconnect. The mode list survives: it is a
        device capability, not live state, and re-querying it costs a round
        trip we do not need."""
        with QMutexLocker(self.mutex):
            self.state["ready"] = False
            self.trx_state.clear()

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
        trx = args[0] if args and args[0].isdigit() else None
        if name == "ready":
            logger.debug("TCI handshake complete")
            count = self.get("trx_count", 0)
            if count and int(self.trx) >= count:
                logger.warning(
                    "TCI trx %s selected but server reports only %d trx",
                    self.trx,
                    count,
                )
            self.set("ready", True)
        elif name == "trx_count" and trx is not None:
            self.set("trx_count", int(trx))
        elif name == "vfo" and trx is not None and len(args) >= 3 and args[1] == "0":
            if args[2].isnumeric():  # Radio rejects non-numeric VFO values
                self.set_for_trx(trx, "vfo", args[2])
        elif name == "modulation" and trx is not None and len(args) >= 2:
            self.set_for_trx(trx, "mode", tci_mode_to_not1mm(args[1]))
        elif name == "rx_filter_band" and trx is not None and len(args) >= 3:
            bandwidth = bandwidth_from_filter_band(args[1], args[2])
            if bandwidth:
                self.set_for_trx(trx, "bw", bandwidth)
        elif name == "trx" and trx is not None and len(args) >= 2:
            ptt = "1" if args[1].strip().lower() == "true" else "0"
            self.set_for_trx(trx, "ptt", ptt)
        elif name == "modulations_list":
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
        if not self.reconnect_timer.isActive():
            self.backoff += 1
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
            # Both objects still have affinity to the now-dead TCI thread;
            # deleteLater() (queued in shutdown) handles their destruction on
            # that thread. Drop the Python references so we do not also free
            # them here on the calling thread.
            self.socket = None
            self.reconnect_timer = None

    @pyqtSlot()
    def shutdown(self) -> None:
        if self.reconnect_timer is not None:
            self.reconnect_timer.stop()
            self.reconnect_timer.deleteLater()
        if self.socket is not None:
            self.socket.close()
            self.socket.deleteLater()
