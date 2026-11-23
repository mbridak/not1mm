"""The report and exchange increment actions, on declared entry boxes."""

from __future__ import annotations

from types import SimpleNamespace

from not1mm import actions


class FakeEdit:
    def __init__(self, text="", focused=False):
        self._text = text
        self._focused = focused
        self._position = 0

    def text(self):
        return self._text

    def setText(self, text):  # noqa: N802 -- Qt spelling
        self._text = text

    def hasFocus(self):  # noqa: N802 -- Qt spelling
        return self._focused

    def cursorPosition(self):  # noqa: N802 -- Qt spelling
        return self._position

    def setCursorPosition(self, position):  # noqa: N802 -- Qt spelling
        self._position = position


def parent(*, reports=(), extras=()):
    fields = SimpleNamespace(report_edits=lambda: reports)
    return SimpleNamespace(
        fields=fields,
        extra_edits=lambda: extras,
    )


def test_the_focused_report_is_incremented():
    sent = FakeEdit("579", focused=True)
    received = FakeEdit("579")
    actions.RST_INCR(parent(reports=(sent, received)))
    assert sent.text() == "589"
    assert received.text() == "579"


def test_the_received_report_is_the_fallback():
    sent = FakeEdit("579")
    received = FakeEdit("579")
    actions.RST_INCR(parent(reports=(sent, received)))
    assert sent.text() == "579"
    assert received.text() == "589"


def test_a_single_report_box_is_used():
    sent = FakeEdit("579")
    actions.RST_INCR(parent(reports=(sent,)))
    assert sent.text() == "589"


def test_no_report_boxes_do_nothing():
    actions.RST_INCR(parent(reports=()))


def test_the_focused_exchange_box_is_incremented():
    sent_nr = FakeEdit("001", focused=True)
    received_nr = FakeEdit("042")
    actions.EXCH_INCR(parent(extras=(sent_nr, received_nr)))
    assert sent_nr.text() == "002"
    assert received_nr.text() == "042"


def test_the_last_exchange_box_is_the_fallback():
    sent_nr = FakeEdit("001")
    received_nr = FakeEdit("042")
    actions.EXCH_INCR(parent(extras=(sent_nr, received_nr)))
    assert sent_nr.text() == "001"
    assert received_nr.text() == "043"


def test_a_non_numeric_exchange_is_left_alone():
    exchange = FakeEdit("ORG")
    actions.EXCH_INCR(parent(extras=(exchange,)))
    assert exchange.text() == "ORG"


def test_no_exchange_boxes_do_nothing():
    actions.EXCH_INCR(parent(extras=()))
