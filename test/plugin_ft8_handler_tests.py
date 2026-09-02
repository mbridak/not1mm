"""Tests for the UDP ADIF (ft8_handler) entry point of the CW sprint plugins."""

import pytest

from not1mm.plugins import cwo, cwt, icwc_mst, k1usn_sst

BASE_PACKET = {
    "CALL": "DL2DSL",
    "MODE": "CW",
    "FREQ": "7.029500",
    "BAND": "40M",
    "RST_SENT": "599",
    "RST_RCVD": "599",
    "QSO_DATE": "20240904",
    "TIME_ON": "212800",
}


class FakeLineEdit:
    """Stands in for a QLineEdit."""

    def __init__(self, text=""):
        self._text = text

    def text(self):
        """Return the field contents."""
        return self._text

    def setText(self, text):  # pylint: disable=invalid-name
        """Set the field contents."""
        self._text = text


class FakeDatabase:
    """Just enough database for the plugins' set_contact_vars()."""

    @staticmethod
    def fetch_call_exists(_call):
        """Callsign has not been worked yet."""
        return {"call_count": 0}

    @staticmethod
    def fetch_sect_band_exists(_sect, _band):
        """Section has not been worked on this band yet."""
        return {"sect_count": 0}


class FakeMainWindow:
    """Stands in for the not1mm main window the plugins are handed."""

    def __init__(self, plugin):
        self.plugin = plugin
        self.callsign = FakeLineEdit()
        self.sent = FakeLineEdit("599")
        self.receive = FakeLineEdit("599")
        self.other_1 = FakeLineEdit()
        self.other_2 = FakeLineEdit()
        self.contact = {}
        self.contest_settings = {"SentExchange": "JOE 5678"}
        self.contact_is_dupe = 0
        self.database = FakeDatabase()
        self.saved = None

    def save_contact(self):
        """Mimic the part of the real save_contact() the plugins rely on."""
        self.plugin.set_contact_vars(self)
        self.contact["Points"] = self.plugin.points(self)
        self.saved = dict(self.contact)


def log_packet(plugin, **fields):
    """Feed one ADIF packet to the plugin and return the stored contact."""
    window = FakeMainWindow(plugin)
    plugin.set_self(window)
    plugin.ft8_handler({**BASE_PACKET, **fields})
    return window.saved


@pytest.mark.parametrize("plugin", [cwt, k1usn_sst, icwc_mst, cwo])
def test_common_fields(plugin):
    """Every plugin logs the call, mode, frequency and band."""
    contact = log_packet(plugin, NAME="BOB", SRX="1234", SRX_STRING="1234", STX="5678")
    assert contact["Call"] == "DL2DSL"
    assert contact["Mode"] == "CW"
    assert contact["Freq"] == 7029.5
    assert contact["QSXFreq"] == 7029.5
    assert contact["Band"] == "7.0"
    assert contact["Points"] == 1


def test_cwt_name_and_number():
    """CWT stores the name in Name and 'name number' in NR."""
    contact = log_packet(cwt, NAME="BOB", SRX_STRING="1234")
    assert contact["Name"] == "BOB"
    assert contact["NR"] == "BOB 1234"
    assert contact["SentNr"] == "JOE 5678"
    assert contact["IsMultiplier1"] == 1
    assert contact["SNT"] == "599"
    assert contact["RCV"] == "599"


def test_cwt_falls_back_to_srx():
    """CWT accepts the member number in SRX when SRX_STRING is absent."""
    contact = log_packet(cwt, NAME="BOB", SRX="1234")
    assert contact["NR"] == "BOB 1234"


def test_cwt_cwa():
    """CWT accepts a non member 'CWA' or state in place of the number."""
    contact = log_packet(cwt, NAME="BOB", SRX_STRING="CWA")
    assert contact["NR"] == "BOB CWA"


def test_sst_name_and_spc():
    """SST stores the name in Name and the state/province/country in Sect."""
    contact = log_packet(k1usn_sst, NAME="BOB", STATE="CA")
    assert contact["Name"] == "BOB"
    assert contact["Sect"] == "CA"
    assert contact["IsMultiplier1"] == 1


def test_sst_srx_string_and_dx_default():
    """SST falls back to SRX_STRING, then to DX."""
    assert log_packet(k1usn_sst, NAME="BOB", SRX_STRING="ON")["Sect"] == "ON"
    assert log_packet(k1usn_sst, NAME="BOB")["Sect"] == "DX"


def test_mst_name_number_and_sent_serial():
    """MST splits their name and number, and keeps our sent serial."""
    contact = log_packet(icwc_mst, NAME="BOB", SRX_STRING="1234", STX="5678")
    assert contact["Name"] == "BOB"
    assert contact["NR"] == "1234"
    assert contact["SentNr"] == "5678"
    assert contact["SNT"] == "599"
    assert contact["RCV"] == "599"


def test_mst_name_only():
    """MST copes with a name and no member number."""
    contact = log_packet(icwc_mst, NAME="BOB", STX="5678")
    assert contact["Name"] == "BOB"


def test_cwo_serial_and_name():
    """CW Open stores their serial in NR and their name in Name."""
    contact = log_packet(cwo, NAME="BOB", SRX="1234", STX="5678")
    assert contact["NR"] == "1234"
    assert contact["Name"] == "BOB"
    assert contact["SentNr"] == "5678"
    assert contact["IsMultiplier1"] == 1


def test_mst_srx_string_holding_whole_exchange():
    """MST copes with a logger that puts the whole exchange in SRX_STRING."""
    contact = log_packet(icwc_mst, NAME="BOB", SRX_STRING="BOB 1234", STX="5678")
    assert contact["Name"] == "BOB"
    assert contact["NR"] == "1234"


def test_cwo_partial_exchange_is_still_logged():
    """CW Open still logs the serial when no name was copied."""
    contact = log_packet(cwo, SRX="1234", STX="5678")
    assert contact["NR"] == "1234"
    assert contact["Name"] == ""


def test_cwo_falls_back_to_srx_string():
    """CW Open reads the serial from SRX_STRING like the other sprint plugins."""
    contact = log_packet(cwo, NAME="BOB", SRX_STRING="1234", STX="5678")
    assert contact["NR"] == "1234"
    assert contact["Name"] == "BOB"


def test_cwo_srx_string_holding_whole_exchange():
    """CW Open copes with a logger that puts the whole exchange in SRX_STRING."""
    contact = log_packet(cwo, SRX_STRING="1234 BOB", STX="5678")
    assert contact["NR"] == "1234"
    assert contact["Name"] == "BOB"


def test_cwo_does_not_leak_previous_exchange():
    """A partial packet must not reuse the exchange left over from the last QSO."""
    window = FakeMainWindow(cwo)
    cwo.set_self(window)
    cwo.ft8_handler({**BASE_PACKET, "NAME": "BOB", "SRX": "1234", "STX": "5678"})
    assert window.saved["Name"] == "BOB"
    assert window.saved["NR"] == "1234"

    cwo.ft8_handler({**BASE_PACKET, "CALL": "K6GTE", "NAME": "MIKE", "STX": "5679"})
    assert window.other_2.text() == ""
    assert window.saved["Call"] == "K6GTE"
    assert window.saved["Name"] == "MIKE"
    assert window.saved["NR"] == ""


def test_mst_number_only():
    """MST must not store a received serial as the name when no name was copied."""
    contact = log_packet(icwc_mst, SRX="1234", STX="5678")
    assert contact["Name"] == ""
    assert contact["NR"] == "1234"


def test_mst_srx_string_number_first():
    """MST accepts the whole exchange in SRX_STRING in either order."""
    contact = log_packet(icwc_mst, SRX_STRING="1234 BOB", STX="5678")
    assert contact["Name"] == "BOB"
    assert contact["NR"] == "1234"
