import socket
import threading
import time

import pytest

from not1mm.lib.flexcat_tx import FlexCatTxSelect


class FakeFlexCat:
    """A TCP listener that records what each connection sends."""

    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("127.0.0.1", 0))
        self.server.listen()
        self.port = self.server.getsockname()[1]
        self.received = []
        self.connections = []
        self.lock = threading.Lock()
        threading.Thread(target=self.accept_loop, daemon=True).start()

    def accept_loop(self):
        while True:
            try:
                conn, _ = self.server.accept()
            except OSError:
                return
            with self.lock:
                self.connections.append(conn)
            threading.Thread(target=self.read_loop, args=(conn,), daemon=True).start()

    def read_loop(self, conn):
        while True:
            try:
                data = conn.recv(1024)
            except OSError:
                return
            if not data:
                return
            with self.lock:
                self.received.append(data.decode())

    def text(self, wait=0.3):
        deadline = time.time() + wait
        while time.time() < deadline:
            time.sleep(0.02)
        with self.lock:
            return "".join(self.received)

    def drop_clients(self):
        with self.lock:
            for conn in self.connections:
                conn.close()
            self.connections.clear()

    def close(self):
        self.drop_clients()
        self.server.close()


@pytest.fixture
def flexcat():
    server = FakeFlexCat()
    yield server
    server.close()


def test_command_for_each_trx():
    assert FlexCatTxSelect.command_for(1) == "FT1;"
    assert FlexCatTxSelect.command_for(0) == "FT0;"


def test_select_tx_sends_ft_commands(flexcat):
    selector = FlexCatTxSelect("127.0.0.1", flexcat.port)
    assert selector.select_tx(1) is True
    assert selector.select_tx(0) is True
    assert flexcat.text() == "FT1;FT0;"
    selector.close()


def test_connection_is_kept_open_between_selects(flexcat):
    """AetherSDR undoes FT1 when the sending CAT client disconnects."""
    selector = FlexCatTxSelect("127.0.0.1", flexcat.port)
    selector.select_tx(1)
    selector.select_tx(0)
    selector.select_tx(1)
    flexcat.text()
    assert len(flexcat.connections) == 1
    selector.close()


def test_reconnects_after_server_drops_connection(flexcat):
    selector = FlexCatTxSelect("127.0.0.1", flexcat.port)
    selector.select_tx(1)
    flexcat.text()
    flexcat.drop_clients()
    time.sleep(0.1)
    assert selector.select_tx(0) is True
    assert flexcat.text().endswith("FT0;")
    selector.close()


def test_unreachable_port_returns_false_and_warns_once(caplog):
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()  # nothing listens here now
    selector = FlexCatTxSelect("127.0.0.1", port)
    assert selector.select_tx(1) is False
    assert selector.select_tx(0) is False
    warnings = [r for r in caplog.records if "cannot reach" in r.getMessage()]
    assert len(warnings) == 1
