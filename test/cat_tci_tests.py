import pytest

from not1mm.lib.cat_tci import TciCAT


class StubClient:
    """Stands in for TCIClient: no thread, no socket, records what was sent."""

    def __init__(self):
        self.sent = []
        self.close_called = False
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

    trx_state = {}

    def get_trx(self, key, trx, default=""):
        return self.trx_state.get(str(trx), {}).get(key, default)

    def send(self, command):
        self.sent.append(command)

    def set_for_trx(self, trx, key, value):
        self.trx_state.setdefault(str(trx), {})[key] = value

    def set_trx(self, trx):
        self.trx = int(trx)

    def wait_for_ready(self, timeout_ms):
        return self.online

    def close(self):
        self.close_called = True
        self.state["ready"] = False


@pytest.fixture
def cat():
    """A TciCAT wired to a stub, bypassing __init__'s real client."""
    instance = TciCAT.__new__(TciCAT)
    instance.interface = "tci"
    instance.host = "127.0.0.1"
    instance.port = 50001
    instance.online = False
    instance.trx = 0
    instance.client = StubClient()
    return instance


@pytest.fixture
def cat_trx1(cat):
    """The same stubbed TciCAT, pointed at the second transceiver."""
    cat.trx = 1
    return cat


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
    assert cat.client.sent == ["cw_macros:0,CQ TEST;"]


def test_close_delegates_to_client(cat):
    go_online(cat)
    cat.close()
    assert cat.client.close_called is True


# ---- trx 1: every per-radio command carries the selected trx index ----


def test_trx1_set_vfo_addresses_trx1(cat_trx1):
    go_online(cat_trx1)
    cat_trx1.set_vfo("7025000")
    assert cat_trx1.client.sent == ["vfo:1,0,7025000;"]


def test_trx1_set_mode_addresses_trx1(cat_trx1):
    go_online(cat_trx1)
    cat_trx1.set_mode("USB")
    assert cat_trx1.client.sent == ["modulation:1,usb;"]


def test_trx1_ptt_addresses_trx1(cat_trx1):
    go_online(cat_trx1)
    cat_trx1.ptt_on()
    cat_trx1.ptt_off()
    assert cat_trx1.client.sent == ["trx:1,true;", "trx:1,false;"]


def test_trx1_sendcw_addresses_trx1(cat_trx1):
    go_online(cat_trx1)
    cat_trx1.sendcw("TEST")
    assert cat_trx1.client.sent == ["cw_macros:1,TEST;"]


def test_cw_speed_and_stop_are_global(cat_trx1):
    """cw_macros_speed and the stop commands take no trx argument."""
    go_online(cat_trx1)
    cat_trx1.set_cw_speed(30)
    cat_trx1.stopcw()
    assert cat_trx1.client.sent == [
        "cw_macros_speed:30;",
        "cw_terminate;",
        "cw_macros_stop;",
    ]


def test_set_trx_retargets_commands_and_client(cat):
    go_online(cat)
    cat.set_trx(1)
    assert cat.client.trx == 1
    cat.set_vfo("14250000")
    cat.set_mode("USB")
    cat.set_trx(0)
    cat.set_vfo("14030000")
    assert cat.client.sent == [
        "vfo:1,0,14250000;",
        "modulation:1,usb;",
        "vfo:0,0,14030000;",
    ]


# ---- transmit lockout for SO2V swaps ----


def test_is_transmitting_false_when_offline(cat):
    cat.client.trx_state = {"0": {"ptt": "1"}}
    assert cat.is_transmitting() is False


def test_is_transmitting_sees_either_trx(cat):
    go_online(cat)
    cat.client.trx_state = {"0": {"ptt": "0"}, "1": {"ptt": "1"}}
    assert cat.is_transmitting() is True
    cat.client.trx_state = {"0": {"ptt": "0"}, "1": {"ptt": "0"}}
    assert cat.is_transmitting() is False


# ---- per-trx receive audio for SO2V ----


def test_set_rx_audio_sends_balance_and_mute(cat_trx1):
    go_online(cat_trx1)
    cat_trx1.set_rx_audio(0, 20, False)
    cat_trx1.set_rx_audio(1, 80, True)
    assert cat_trx1.client.sent == [
        "rx_balance:0,-30;",
        "rx_mute:0,false;",
        "rx_balance:1,30;",
        "rx_mute:1,true;",
    ]


def test_set_rx_audio_centre_and_clamping(cat):
    go_online(cat)
    cat.set_rx_audio(0, 50, False)
    cat.set_rx_audio(0, -10, False)
    cat.set_rx_audio(0, 150, False)
    balances = [c for c in cat.client.sent if c.startswith("rx_balance")]
    assert balances == ["rx_balance:0,0;", "rx_balance:0,-50;", "rx_balance:0,50;"]


def test_set_rx_audio_sends_nothing_offline(cat):
    assert cat.set_rx_audio(0, 50, False) is False
    assert cat.client.sent == []


def test_set_vfo_updates_cache_before_the_echo(cat_trx1):
    """No stale-frequency window between set_vfo and the server's echo."""
    go_online(cat_trx1)
    cat_trx1.client.trx_state = {"1": {"vfo": "7025000"}}
    cat_trx1.set_vfo("7030000")
    assert cat_trx1.client.get_trx("vfo", 1) == "7030000"
