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
    instance.port = 50001
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
    assert cat.client.sent == ["modulation:0,cw;", "modulation:0,rtty;"]


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
