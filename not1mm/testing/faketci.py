"""
A minimal TCI server, for exercising not1mm's TCI backend without an SDR.

Sends a plausible handshake, then accepts and echoes state changes the way a
real TCI server does. Deliberately shares no code with the client, so a bug
here cannot masquerade as a backend bug.

Usage: python -m not1mm.testing.faketci [port]
"""

import sys

from PyQt6.QtCore import QCoreApplication, QTimer
from PyQt6.QtWebSockets import QWebSocketServer

# Mirrors a real AetherSDR handshake captured 2026-08-01, including the noise
# frames, so the client's ignore path gets exercised too. See
# docs/superpowers/specs/2026-08-01-tci-handshake.md.
HANDSHAKE = [
    "vfo_limits:1000,75000000;",
    "if_limits:-48000,48000;",
    "trx_count:1;",
    "channels_count:2;",
    "device:FakeSDR;",
    "receive_only:false;",
    "modulations_list:usb,lsb,cw,cwr,am,sam,fm,nfm,digu,digl,rtty;",
    "protocol:ExpertSDR3,1.5;",
    "vfo:0,0,14030000;",
    "vfo:0,1,14030000;",
    "dds:0,14176580;",
    "modulation:0,cw;",
    "rx_filter_band:0,-500,500;",
    "agc_mode:0,fast;",
    "trx:0,false;",
    "iq_samplerate:48000;",
    "ready;",
    "start;",
]


class FakeTCIServer:
    def __init__(self, port: int) -> None:
        self.clients = []
        self.server = QWebSocketServer(
            "FakeTCI", QWebSocketServer.SslMode.NonSecureMode
        )
        if not self.server.listen(port=port):
            print(f"Failed to listen on {port}", flush=True)
            raise SystemExit(1)
        self.server.newConnection.connect(self.on_new_connection)
        print(f"FakeTCI listening on ws://127.0.0.1:{port}", flush=True)

    def on_new_connection(self) -> None:
        socket = self.server.nextPendingConnection()
        socket.textMessageReceived.connect(
            lambda message: self.on_message(socket, message)
        )
        socket.disconnected.connect(lambda: self.on_disconnected(socket))
        self.clients.append(socket)
        print("client connected, sending handshake", flush=True)
        for frame in HANDSHAKE:
            socket.sendTextMessage(frame)

    def on_message(self, socket, message: str) -> None:
        print(f"< {message}", flush=True)
        # A real TCI server echoes accepted state changes back to all clients.
        for frame in [f + ";" for f in message.split(";") if f.strip()]:
            for client in self.clients:
                client.sendTextMessage(frame)

    def on_disconnected(self, socket) -> None:
        print("client disconnected", flush=True)
        if socket in self.clients:
            self.clients.remove(socket)
        socket.deleteLater()


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 50001
    app = QCoreApplication([])
    server = FakeTCIServer(port)
    QTimer.singleShot(600000, app.quit)
    app.exec()
    del server


if __name__ == "__main__":
    main()
