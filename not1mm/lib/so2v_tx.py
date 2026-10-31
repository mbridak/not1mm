"""
Transmit arbiter for SO2V over TCI with one transmitter.
GPL V3

Two receivers, one transmitter. The run radio (trx 0) keeps calling CQ while
the operator works stations on the S&P radio (trx 1); every CW transmission is
routed to the slice it belongs to by moving TX between transmissions.

Rules:
  * TX is only ever moved while nothing is transmitting.
  * A send to the radio that already holds TX goes straight out (CWX appends
    to its own buffer), exactly as before SO2V.
  * A manual send to the other radio interrupts an auto-CQ in progress: the
    CQ is aborted, the send goes out, and on_cq_interrupted fires so the CQ
    can be resumed.
  * Any other send to the other radio waits for the current transmission to
    end, then TX moves and it goes out.
  * When idle, TX is handed back to the focused radio, so voice keying and
    anything else that does not pass through here keys the radio in focus.

Pure Python, no Qt: MainWindow calls tick() from a timer and supplies the
radio operations as callables, so the logic is testable with a fake clock.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("so2v_tx")

# A send that never keys the radio (empty text, radio refused it) must not
# wedge the arbiter.
START_TIMEOUT_S = 2.0
# How long to wait for an aborted CQ to unkey before giving up waiting.
STOP_TIMEOUT_S = 2.0


@dataclass
class Transmission:
    trx: int
    kind: str  # "cq" (auto-CQ) or "manual"
    sent_at: float
    started: bool = False


@dataclass
class So2vTxArbiter:
    is_transmitting: object  # () -> bool
    select_tx: object  # (trx) -> bool, moves the TX slice
    sendcw: object  # (trx, text) -> None, sends through the current TX slice
    stopcw: object  # () -> None, aborts the CW in progress
    clock: object = time.monotonic
    settle_s: float = 0.15  # time for the radio to apply a TX-slice move
    on_cq_interrupted: object = None  # () -> None

    tx_slice: int | None = None
    focus: int = 0
    queue: deque = field(default_factory=deque)
    current: Transmission | None = None
    settle_until: float = 0.0
    abort_until: float = 0.0

    # ---- state ----

    def init_tx(self, trx: int) -> None:
        """Put TX on a known slice at startup."""
        self.focus = int(trx)
        self.select_tx(self.focus)
        self.tx_slice = self.focus
        self.settle_until = self.clock() + self.settle_s

    def set_focus(self, trx: int) -> None:
        """The operator moved to the other radio. TX follows on the next idle
        tick, never mid-transmission."""
        self.focus = int(trx)

    def busy(self) -> bool:
        """True while anything is transmitting, aborting or waiting to go."""
        return (
            self.current is not None
            or bool(self.queue)
            or self.abort_until > 0
            or bool(self.is_transmitting())
        )

    def needs_tick(self) -> bool:
        return self.busy() or (self.tx_slice is not None and self.tx_slice != self.focus)

    def clear(self) -> None:
        """Operator hit stop: drop everything pending."""
        self.queue.clear()
        self.current = None
        self.abort_until = 0.0

    # ---- sending ----

    def send(self, trx: int, text: str, kind: str = "manual") -> None:
        trx = int(trx)
        now = self.clock()
        current = self.current
        if (
            not self.queue
            and self.abort_until == 0
            and self.tx_slice == trx
            and now >= self.settle_until
            and (current is None or current.trx == trx)
        ):
            # Same radio as TX: straight out, CWX buffers it behind anything
            # already sending.
            self.sendcw(trx, text)
            if current is None:
                self.current = Transmission(trx, kind, now)
            elif kind == "manual":
                current.kind = "manual"
            return

        if kind == "manual" and current is not None and current.kind == "cq" and current.trx != trx:
            logger.debug("SO2V: interrupting CQ on trx %d for trx %d", current.trx, trx)
            self.stopcw()
            self.current = None
            self.abort_until = now + STOP_TIMEOUT_S
            # Anything else queued for the CQ radio goes with the CQ.
            self.queue = deque(item for item in self.queue if item[2] != "cq")
            if self.on_cq_interrupted:
                self.on_cq_interrupted()
        self.queue.append((trx, text, kind))

    # ---- driven by a timer ----

    def tick(self) -> None:
        now = self.clock()
        transmitting = bool(self.is_transmitting())

        if self.current is not None:
            if not self.current.started:
                if transmitting:
                    self.current.started = True
                elif now - self.current.sent_at > START_TIMEOUT_S:
                    logger.debug("SO2V: send on trx %d never keyed", self.current.trx)
                    self.current = None
            elif not transmitting:
                self.current = None
        if self.current is not None:
            return

        if self.abort_until:
            if transmitting and now < self.abort_until:
                return
            self.abort_until = 0.0
        if transmitting:
            return  # keyed by something outside the arbiter (paddle, PTT)

        if self.queue:
            trx = self.queue[0][0]
            if self.tx_slice != trx:
                self.move_tx(trx, now)
                return
            if now < self.settle_until:
                return
            _trx, text, kind = self.queue.popleft()
            self.sendcw(trx, text)
            self.current = Transmission(trx, kind, now)
            while self.queue and self.queue[0][0] == trx:
                _trx, more, more_kind = self.queue.popleft()
                self.sendcw(trx, more)
                if more_kind == "manual":
                    self.current.kind = "manual"
            return

        if self.tx_slice != self.focus and now >= self.settle_until:
            self.move_tx(self.focus, now)

    def move_tx(self, trx: int, now: float) -> None:
        logger.debug("SO2V: TX slice -> trx %d", trx)
        self.select_tx(trx)
        self.tx_slice = trx
        self.settle_until = now + self.settle_s
