"""RandomGram: the score, and the sent-group prefill from rg.txt.

The event's N1MM UDC (RANDOMGRAM.udc) gives "PointsPerContact = IsComment, 1,
SameContinent, 2, OtherContinent, 2" and "NumMults = 0", and the rules allow a
station to be worked again on the same band (DupeType = 4).

References:
  https://n1mmwp.hamdocs.com/mmfiles/randomgram-udc/
  https://masteringmorse.com/randomgrams/
"""

from types import SimpleNamespace

from not1mm.plugins import randomgram


def test_points_are_two_a_contact():
    assert randomgram.points(SimpleNamespace()) == 2


def test_there_are_no_multipliers():
    assert randomgram.show_mults(SimpleNamespace()) == 0


def test_calc_score_returns_the_points():
    # calc_score used to compute the sum and then drop it, returning None.
    ctx = SimpleNamespace(
        database=SimpleNamespace(fetch_points=lambda: {"Points": 6})
    )
    assert randomgram.calc_score(ctx) == 6


def test_calc_score_of_an_empty_log_is_zero():
    ctx = SimpleNamespace(
        database=SimpleNamespace(fetch_points=lambda: {"Points": None})
    )
    assert randomgram.calc_score(ctx) == 0


class _Field:
    def __init__(self):
        self._text = ""

    def text(self):
        return self._text

    def setText(self, text):  # noqa: N802
        self._text = text


def test_prefill_strips_the_newline(monkeypatch):
    monkeypatch.setattr(randomgram, "rgGroups", ["A7N67\n", "9RIB6\n"])
    monkeypatch.setattr(randomgram, "show_qso", lambda self: 0)
    ctx = SimpleNamespace(other_1=_Field())
    randomgram.prefill(ctx)
    assert ctx.other_1.text() == "A7N67"


def test_prefill_takes_the_next_group(monkeypatch):
    monkeypatch.setattr(randomgram, "rgGroups", ["A7N67\n", "9RIB6\n"])
    monkeypatch.setattr(randomgram, "show_qso", lambda self: 1)
    ctx = SimpleNamespace(other_1=_Field())
    randomgram.prefill(ctx)
    assert ctx.other_1.text() == "9RIB6"


def test_prefill_stops_when_the_list_runs_out(monkeypatch):
    monkeypatch.setattr(randomgram, "rgGroups", ["A7N67\n"])
    monkeypatch.setattr(randomgram, "show_qso", lambda self: 5)
    ctx = SimpleNamespace(other_1=_Field())
    randomgram.prefill(ctx)
    assert ctx.other_1.text() == ""
