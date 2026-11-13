"""RandomGram: the score, and the sent-group prefill from rg.txt.

The event's N1MM UDC (RANDOMGRAM.udc) gives "PointsPerContact = IsComment, 1,
SameContinent, 2, OtherContinent, 2" and "NumMults = 0", and the rules allow a
station to be worked again on the same band (DupeType = 4).

References:
  https://n1mmwp.hamdocs.com/mmfiles/randomgram-udc/
  https://masteringmorse.com/randomgrams/
"""

from types import SimpleNamespace

from not1mm.lib.contest import load_contest
from not1mm.plugins import randomgram


class _Database:
    """Just the two queries the contest asks the log."""

    def __init__(self, points=None, qsos=0):
        self.points = points
        self.qsos = qsos

    def fetch_points(self):
        return {"Points": self.points}

    def fetch_qso_count(self):
        return {"qsos": self.qsos}


class _Field:
    def __init__(self):
        self._text = ""

    def text(self):
        return self._text

    def setText(self, text):  # noqa: N802
        self._text = text


def _contest(**parent):
    return load_contest("randomgram", SimpleNamespace(**parent))


def test_points_are_two_a_contact():
    assert _contest(contact_is_dupe=0).points() == 2


def test_a_dupe_scores_nothing():
    # DupeType = 4 means the application never sets the flag, but the base's
    # points() still answers 0 when it is set.
    assert _contest(contact_is_dupe=1).points() == 0


def test_there_are_no_multipliers():
    assert _contest().show_mults() == 0


def test_calc_score_returns_the_points():
    contest = _contest(database=_Database(points=6), contact_is_dupe=0)
    assert contest.calc_score() == 6


def test_calc_score_of_an_empty_log_is_zero():
    contest = _contest(database=_Database(points=None), contact_is_dupe=0)
    assert contest.calc_score() == 0


def _prefilled(monkeypatch, groups, qsos):
    monkeypatch.setattr(randomgram, "rgGroups", groups)
    parent = SimpleNamespace(other_1=_Field(), database=_Database(qsos=qsos))
    load_contest("randomgram", parent).prefill()
    return parent.other_1.text()


def test_prefill_strips_the_newline(monkeypatch):
    assert _prefilled(monkeypatch, ["A7N67\n", "9RIB6\n"], 0) == "A7N67"


def test_prefill_takes_the_next_group(monkeypatch):
    assert _prefilled(monkeypatch, ["A7N67\n", "9RIB6\n"], 1) == "9RIB6"


def test_prefill_stops_when_the_list_runs_out(monkeypatch):
    assert _prefilled(monkeypatch, ["A7N67\n"], 5) == ""
