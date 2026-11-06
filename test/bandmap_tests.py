from types import MethodType, SimpleNamespace

from not1mm.bandmap import BandMapWindow, Database


def _spot(call, freq):
    return {
        "ts": "2099-01-01 00:00:00",
        "callsign": call,
        "freq": freq,
        "band": "40",
        "mode": "CW",
        "spotter": "TEST",
        "comment": "",
    }


def _bandmap(spots, rx_freq, worked):
    """A stand-in for BandMapWindow with the parts the jumps use."""
    bandmap = SimpleNamespace(
        active=True,
        isVisible=lambda: True,
        spots=spots,
        rx_freq=rx_freq,
        worked_list=worked,
        bandwidth=0,
        spot_near=("", False),
        currentBand=SimpleNamespace(band_mhz=7.0, start=7000.0, end=7300.0),
        tuned=[],
    )
    for name in (
        "msg_from_main",
        "is_dupe",
        "spots_after",
        "tune_to_spot",
        "set_spot_near",
        "send_spot_near",
    ):
        setattr(bandmap, name, MethodType(getattr(BandMapWindow, name), bandmap))
    bandmap.message = SimpleNamespace(emit=bandmap.tuned.append)
    return bandmap


def _jump(bandmap, cmd, call=""):
    """Send NEXTSPOT or PREVSPOT and return the call tuned to, or None."""
    bandmap.tuned.clear()
    bandmap.msg_from_main({"cmd": cmd, "call": call})
    if not bandmap.tuned:
        return None
    bandmap.rx_freq = bandmap.tuned[0]["freq"]
    return bandmap.tuned[0]["spot"]


def test_jumps_skip_dupes():
    spots = Database()
    for call, freq in (("AA1A", 7020.0), ("BB1B", 7021.0), ("CC1C", 7022.0)):
        spots.addspot(_spot(call, freq))
    bandmap = _bandmap(spots, 7019.0, {"BB1B": [7.0]})
    assert _jump(bandmap, "NEXTSPOT") == "AA1A"
    assert _jump(bandmap, "NEXTSPOT", "AA1A") == "CC1C"
    assert _jump(bandmap, "NEXTSPOT", "CC1C") is None
    assert _jump(bandmap, "PREVSPOT", "CC1C") == "AA1A"


def test_dupe_on_another_band_is_not_skipped():
    spots = Database()
    spots.addspot(_spot("AA1A", 7020.0))
    bandmap = _bandmap(spots, 7019.0, {"AA1A": [14.0]})
    assert _jump(bandmap, "NEXTSPOT") == "AA1A"


def test_jumps_go_through_spots_on_one_frequency():
    spots = Database()
    for call in ("CC1C", "AA1A", "BB1B", "DD1D"):
        spots.addspot(_spot(call, 7020.0))
    # BB1B is a dupe on the same frequency, it must not hide CC1C.
    bandmap = _bandmap(spots, 7019.0, {"BB1B": [7.0]})
    assert _jump(bandmap, "NEXTSPOT") == "AA1A"
    assert _jump(bandmap, "NEXTSPOT", "AA1A") == "CC1C"
    assert _jump(bandmap, "NEXTSPOT", "CC1C") == "DD1D"
    assert _jump(bandmap, "NEXTSPOT", "DD1D") is None
    assert _jump(bandmap, "PREVSPOT", "DD1D") == "CC1C"
    assert _jump(bandmap, "PREVSPOT", "CC1C") == "AA1A"
    assert _jump(bandmap, "PREVSPOT", "AA1A") is None


def test_vfo_one_hz_below_the_spot():
    spots = Database()
    spots.addspot(_spot("AA1A", 7020.05))
    spots.addspot(_spot("BB1B", 7020.05))
    # TUNE cuts 7020.05 kHz to 7020049 Hz.
    bandmap = _bandmap(spots, 7020.049, {})
    assert _jump(bandmap, "NEXTSPOT", "AA1A") == "BB1B"
    assert _jump(bandmap, "PREVSPOT", "BB1B") == "AA1A"


def test_manual_tune_onto_spots_passes_them():
    spots = Database()
    spots.addspot(_spot("AA1A", 7020.0))
    spots.addspot(_spot("BB1B", 7021.0))
    bandmap = _bandmap(spots, 7020.0, {})
    assert _jump(bandmap, "NEXTSPOT") == "BB1B"


def test_tune_to_spot_tunes_to_a_dupe():
    bandmap = _bandmap(Database(), 7019.0, {"AA1A": [7.0]})
    bandmap.tune_to_spot(_spot("AA1A", 7020.0))
    assert bandmap.tuned == [{"cmd": "TUNE", "freq": 7020.0, "spot": "AA1A"}]


def _near(bandmap, mode="CW"):
    """Send the spot near the RX frequency and return the messages."""
    bandmap.tuned.clear()
    bandmap.send_spot_near(mode)
    return [(msg["call"], msg["dupe"]) for msg in bandmap.tuned]


def test_spot_near_nearest_wins():
    spots = Database()
    spots.addspot(_spot("AA1A", 7020.0))
    spots.addspot(_spot("BB1B", 7020.2))
    bandmap = _bandmap(spots, 7020.15, {})
    assert _near(bandmap) == [("BB1B", False)]
    bandmap.rx_freq = 7020.05
    assert _near(bandmap) == [("AA1A", False)]
    bandmap.rx_freq = 7021.0
    assert _near(bandmap) == [("", False)]


def test_spot_near_prefers_non_dupe_on_one_freq():
    spots = Database()
    for call in ("AA1A", "BB1B", "CC1C"):
        spots.addspot(_spot(call, 7020.0))
    bandmap = _bandmap(spots, 7020.0, {"AA1A": [7.0]})
    assert _near(bandmap) == [("BB1B", False)]
    bandmap.worked_list = {"AA1A": [7.0], "BB1B": [7.0], "CC1C": [7.0]}
    assert _near(bandmap) == [("AA1A", True)]


def test_spot_near_sent_on_change_only():
    spots = Database()
    spots.addspot(_spot("AA1A", 7020.0))
    bandmap = _bandmap(spots, 7020.0, {})
    assert _near(bandmap) == [("AA1A", False)]
    assert _near(bandmap) == []
    bandmap.worked_list = {"AA1A": [7.0]}
    assert _near(bandmap) == [("AA1A", True)]


def test_spot_near_tolerance():
    spots = Database()
    spots.addspot(_spot("AA1A", 7020.0))
    bandmap = _bandmap(spots, 7020.4, {})
    assert _near(bandmap, "USB") == [("AA1A", False)]  # phone: 0.5 kHz
    assert _near(bandmap, "CW") == [("", False)]  # no bandwidth: 0.25 kHz
    bandmap.rx_freq = 7020.6
    assert _near(bandmap, "USB") == []  # still none in 0.5 kHz
    bandmap.bandwidth = 1500
    assert _near(bandmap, "CW") == [("AA1A", False)]  # half the bandwidth
