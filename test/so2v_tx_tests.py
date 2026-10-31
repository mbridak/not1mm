import pytest

from not1mm.lib.so2v_tx import So2vTxArbiter


class FakeRadio:
    """One transmitter. Records every operation in order."""

    def __init__(self):
        self.log = []
        self.transmitting = False
        self.t = 0.0

    def clock(self):
        return self.t

    def advance(self, seconds, arbiter=None, step=0.05):
        end = self.t + seconds
        while self.t < end:
            self.t = round(self.t + step, 6)
            if arbiter:
                arbiter.tick()

    def select_tx(self, trx):
        self.log.append(f"FT{trx}")
        return True

    def sendcw(self, trx, text):
        self.log.append(f"cw:{text}")

    def stopcw(self):
        self.log.append("stop")


@pytest.fixture
def radio():
    return FakeRadio()


@pytest.fixture
def arb(radio):
    interrupted = []
    a = So2vTxArbiter(
        is_transmitting=lambda: radio.transmitting,
        select_tx=radio.select_tx,
        sendcw=radio.sendcw,
        stopcw=radio.stopcw,
        clock=radio.clock,
        settle_s=0.15,
        on_cq_interrupted=lambda: interrupted.append(radio.t),
    )
    a.interrupted = interrupted
    a.init_tx(0)
    radio.advance(0.2, a)
    radio.log.clear()
    return a


def key(radio, arb, seconds):
    """Radio transmits for `seconds`, then unkeys."""
    radio.transmitting = True
    radio.advance(seconds, arb)
    radio.transmitting = False
    radio.advance(0.1, arb)


def test_send_to_tx_radio_goes_straight_out(radio, arb):
    arb.send(0, "CQ")
    assert radio.log == ["cw:CQ"]


def test_same_radio_sends_append_while_transmitting(radio, arb):
    arb.send(0, "CQ", "cq")
    radio.transmitting = True
    radio.advance(0.2, arb)
    arb.send(0, "TU")
    assert radio.log == ["cw:CQ", "cw:TU"]


def test_cq_from_run_while_focus_on_sp_borrows_tx_and_returns_it(radio, arb):
    arb.set_focus(1)
    radio.advance(0.3, arb)
    assert radio.log == ["FT1"]  # idle: TX follows focus
    radio.log.clear()

    arb.send(0, "CQ", "cq")
    radio.advance(0.3, arb)
    assert radio.log == ["FT0", "cw:CQ"]  # moved, settled, sent
    key(radio, arb, 2.0)
    radio.advance(0.3, arb)
    assert radio.log == ["FT0", "cw:CQ", "FT1"]  # handed back after the CQ


def test_tx_never_moves_while_transmitting(radio, arb):
    arb.send(0, "CQ", "cq")
    radio.transmitting = True
    arb.set_focus(1)
    radio.advance(1.0, arb)
    assert "FT1" not in radio.log
    radio.transmitting = False
    radio.advance(0.3, arb)
    assert radio.log[-1] == "FT1"


def test_manual_sp_send_interrupts_cq_then_cq_can_resume(radio, arb):
    arb.set_focus(1)
    radio.advance(0.3, arb)
    arb.send(0, "CQ", "cq")
    radio.advance(0.3, arb)
    radio.transmitting = True
    radio.advance(0.5, arb)  # CQ going out on the run radio
    radio.log.clear()

    arb.send(1, "K0RX")  # operator answers on the S&P radio
    assert radio.log == ["stop"]
    assert arb.interrupted, "CQ interruption reported for resume"
    radio.advance(0.3, arb)
    assert radio.log == ["stop"]  # still waiting for the CQ to unkey
    radio.transmitting = False
    radio.advance(0.4, arb)
    assert radio.log == ["stop", "FT1", "cw:K0RX"]


def test_manual_send_waits_for_other_radios_manual_transmission(radio, arb):
    arb.send(0, "5NN 123")  # run exchange going out
    radio.transmitting = True
    radio.advance(0.2, arb)
    arb.set_focus(1)
    arb.send(1, "K0RX")
    assert "stop" not in radio.log  # a manual send is never cut off
    radio.advance(1.0, arb)
    assert "cw:K0RX" not in radio.log
    radio.transmitting = False
    radio.advance(0.4, arb)
    assert radio.log == ["cw:5NN 123", "FT1", "cw:K0RX"]


def test_queued_sends_for_same_radio_go_together(radio, arb):
    arb.send(0, "CQ", "cq")
    radio.transmitting = True
    radio.advance(0.1, arb)
    arb.send(1, "K0RX")  # interrupts the CQ
    arb.send(1, "5NN")
    radio.transmitting = False
    radio.advance(0.5, arb)
    assert radio.log == ["cw:CQ", "stop", "FT1", "cw:K0RX", "cw:5NN"]


def test_send_that_never_keys_does_not_wedge(radio, arb):
    arb.send(0, "")
    radio.advance(2.5, arb)
    assert not arb.busy()
    arb.set_focus(1)
    radio.advance(0.3, arb)
    assert radio.log[-1] == "FT1"


def test_busy_reflects_queue_and_transmit(radio, arb):
    assert not arb.busy()
    radio.transmitting = True
    assert arb.busy()
    radio.transmitting = False
    arb.send(1, "X")  # needs a TX move: queued
    assert arb.busy()


def test_clear_drops_pending(radio, arb):
    arb.send(1, "X")
    arb.clear()
    radio.advance(0.5, arb)
    assert "cw:X" not in radio.log


def test_outside_keying_blocks_moves(radio, arb):
    """Paddle or PTT keying that the arbiter did not start still pins TX."""
    radio.transmitting = True
    arb.send(1, "K0RX")
    radio.advance(1.0, arb)
    assert radio.log == []
    radio.transmitting = False
    radio.advance(0.4, arb)
    assert radio.log == ["FT1", "cw:K0RX"]
