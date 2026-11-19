"""
Connect to a TCI server and dump every frame it sends, verbatim.

Used to pin not1mm's TCI command mapping to what the server actually speaks,
rather than to what the protocol docs claim. Not part of the application.

Usage: python -m not1mm.testing.tci_probe [host] [port]
"""

import sys

from PyQt6.QtCore import QCoreApplication, QTimer, QUrl
from PyQt6.QtWebSockets import QWebSocket


def main() -> None:
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 50001

    app = QCoreApplication([])
    socket = QWebSocket()

    def on_connected() -> None:
        print(f"--- connected to ws://{host}:{port} ---", flush=True)

    def on_text(payload: str) -> None:
        print(payload, flush=True)

    def on_error(error) -> None:
        print(f"--- error: {error} ---", flush=True)
        app.quit()

    socket.connected.connect(on_connected)
    socket.textMessageReceived.connect(on_text)
    socket.errorOccurred.connect(on_error)
    socket.open(QUrl(f"ws://{host}:{port}"))

    # Capture the handshake plus a window for manual dial/mode/PTT changes.
    QTimer.singleShot(60000, app.quit)
    app.exec()


if __name__ == "__main__":
    main()
