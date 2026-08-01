import sys

import pytest
from PyQt6.QtCore import QCoreApplication, QTimer

from not1mm.lib.tci_client import TCIClient


@pytest.fixture
def client():
    """A client whose thread never starts, so only the cache logic is exercised.

    autostart=False rather than bypassing __init__: TCIClient is a QObject, and
    building one via __new__ leaves the C++ side uninitialized, which PyQt6
    rejects with "'__init__' method of object's base class not called".
    """
    return TCIClient("127.0.0.1", 50001, autostart=False)


@pytest.fixture(scope="module")
def qt_app():
    """QTimer.start() needs a live QCoreApplication: without one it silently
    no-ops and isActive() never flips true, so schedule_reconnect's isActive()
    guard -- the thing the backoff regression test below depends on -- could
    not be exercised at all."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    return app


@pytest.fixture
def client_with_timer(qt_app):
    """A client with a real QTimer standing in for reconnect_timer, the way
    open_socket() wires it on the TCI thread. Built by hand because
    autostart=False skips open_socket() entirely."""
    reconnecting_client = TCIClient("127.0.0.1", 50001, autostart=False)
    reconnecting_client.reconnect_timer = QTimer()
    reconnecting_client.reconnect_timer.setSingleShot(True)
    reconnecting_client.reconnect_timer.timeout.connect(
        reconnecting_client.connect_to_server
    )
    return reconnecting_client


class RecordingSocket:
    """Stands in for QWebSocket: records what would have been sent."""

    def __init__(self):
        self.sent = []

    def sendTextMessage(self, message):
        self.sent.append(message)


def test_schedule_reconnect_advances_backoff_by_one_per_call(client_with_timer):
    """Regression test for a bug where `self.backoff += 1` lived outside the
    isActive() guard: one connection failure fires both on_error and
    on_disconnected, both call schedule_reconnect(), and the counter
    double-advanced -- turning the intended 1000, 2000, 5000 ms ladder into
    1000, 5000, 5000, skipping the 2000 ms rung entirely. The guard must make
    a second call while the timer from the first is still pending a no-op.
    """
    client = client_with_timer
    assert client.backoff == 0

    client.schedule_reconnect()
    assert client.backoff == 1

    # Simulate on_error and on_disconnected both firing for the same failure
    # while the first call's timer is still pending.
    client.schedule_reconnect()
    assert client.backoff == 1

    client.reconnect_timer.stop()
    client.schedule_reconnect()
    assert client.backoff == 2


def test_write_command_refuses_to_send_while_offline(client):
    """Even with a live socket object, write_command must not touch it until
    the handshake has completed -- an offline client has nothing to write
    to, regardless of whether a socket happens to exist."""
    client.socket = RecordingSocket()
    assert client.online is False

    client.write_command("vfo:0,0,14030000;")

    assert client.socket.sent == []


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


def test_modulations_list_is_normalized(client):
    client.handle_frame("modulations_list", ["cw", "lsb", "usb", "digl"])
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
    client.handle_frame("modulations_list", ["cw", "usb"])
    client.clear_state()
    assert client.get("modes") == ["CW", "USB"]


def test_get_modes_returns_a_copy(client):
    client.handle_frame("modulations_list", ["cw"])
    client.get("modes").append("BOGUS")
    assert client.get("modes") == ["CW"]


def test_on_text_message_applies_every_frame_in_one_payload(client):
    payload = "device:FakeSDR;modulations_list:cw,usb;vfo:0,0,14030000;ready;"
    client.on_text_message(payload)
    assert client.get("modes") == ["CW", "USB"]
    assert client.get("vfo") == "14030000"
    assert client.online is True


def test_on_text_message_skips_unparseable_fragment_without_raising(client):
    # ":bogus" parses to an empty command name -- parse_frame returns None
    # for it -- while the frames around it are valid and must still apply.
    payload = "vfo:0,0,14030000;:bogus;ready;"
    client.on_text_message(payload)
    assert client.get("vfo") == "14030000"
    assert client.online is True


def test_clear_state_resets_ptt(client):
    client.handle_frame("trx", ["0", "true"])
    client.clear_state()
    assert client.get("ptt") == "0"


def test_wait_for_ready_times_out_when_never_online(client):
    assert client.wait_for_ready(100) is False
