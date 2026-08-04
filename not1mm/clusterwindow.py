"""
not1mm Contest logger
Email: michael.bridak@gmail.com
GPL V3
Class: ClusterWindow
Purpose: Standalone dock widget for DX cluster traffic.
"""

import logging
import re
from datetime import UTC, datetime

from PyQt6 import QtGui, QtNetwork, uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDockWidget

from not1mm import fsutils
from not1mm.lib.preferences import Preferences

logger = logging.getLogger(__name__)


class ClusterWindow(QDockWidget):
    """The Cluster window."""

    message = pyqtSignal(dict)
    clusterwindow_closed = pyqtSignal()

    def __init__(self, action, parent):
        super().__init__()
        self.action = action
        self.parent = parent

        self.pref = Preferences.data()
        uic.loadUi(fsutils.APP_DATA_PATH / "clusterwindow.ui", self)
        self.setObjectName("cluster-window")
        self.clusterOutput.document().setMaximumBlockCount(1000)
        self.clusterInput.returnPressed.connect(self.input_to_cluster)
        self.connectButton.clicked.connect(self.cluster_connect)

        # wire up the socket
        self.connected = False
        self.socket = QtNetwork.QTcpSocket()
        self.test_for_data = self.socket.bytesAvailable
        self.socket.readyRead.connect(self.cluster_receive)
        self.socket.connected.connect(self.cluster_maybeconnected)
        self.socket.disconnected.connect(self.cluster_disconnected)
        self.socket.errorOccurred.connect(self.cluster_socket_error)

    def append_message(self, message: str) -> None:
        sb = self.clusterOutput.verticalScrollBar()
        # tolerance of 4 px to account for overscroll/elastic scrolling
        at_bottom = sb.value() >= sb.maximum() - 4

        self.clusterOutput.append(message)

        if at_bottom:
            sb.setValue(sb.maximum())

    def cluster_connect(self):
        """Connect to the cluster."""
        if self.connected is True:
            self.close_cluster()
            return
        server = self.pref.get("cluster_server", "dxc.nc7j.com")
        port = self.pref.get("cluster_port", 7373)
        logger.info(f"connecting to dx cluster {server} {port}")
        self.socket.connectToHost(server, port)
        self.test_for_data = self.socket.bytesAvailable
        self.setWindowTitle(f"Cluster: {server}")
        time = datetime.now(UTC).strftime("%H:%M")
        self.append_message(f"[{time}] Connecting.")
        self.connectButton.setText("Connecting")
        self.connected = True

    def cluster_maybeconnected(self) -> None:
        """Update visual state of the connect button."""
        self.connectButton.setText("Connecting")

    def cluster_socket_error(self) -> None:
        """Oopsie"""
        logger.warning(f"Socket error: {self.socket.errorString()}")

    def cluster_disconnected(self) -> None:
        """Called when socket is disconnected."""
        self.connected = False
        self.setWindowTitle("Cluster")
        time = datetime.now(UTC).strftime("%H:%M")
        self.append_message(f"[{time}] Disconnected.")
        self.connectButton.setText("Connect")

    def close_cluster(self) -> None:
        """Close socket connection"""
        if self.socket and self.socket.isOpen():
            self.socket.close()
            self.connected = False

    def cluster_send(self, cmd: str) -> None:
        """Send a command to the cluster."""
        self.append_message(f">>> <b>{cmd}</b>")
        tosend = bytes(cmd + "\r\n", encoding="ascii")
        logger.debug(f">>> {cmd}")
        if self.socket and self.socket.isOpen():
            self.socket.write(tosend)

    def cluster_receive(self) -> None:
        """Process waiting bytes"""
        while self.test_for_data():
            data = self.socket.readLine()

            try:  # strip BEL chars from messages, no one wants these
                data = str(data, "utf-8").replace("\x07", "").strip()
            except UnicodeDecodeError:
                continue

            logger.debug(f"< {data}")
            self.append_message(data)

            if (
                "login:" in data.lower()
                or "call:" in data.lower()
                or "callsign:" in data.lower()
            ):
                login = self.pref.get("cluster_login", "") or self.pref.get(
                    "current_op", ""
                )
                self.cluster_send(login)

            if "password:" in data.lower():
                self.cluster_send(self.pref.get("cluster_password", ""))

            if "HELLO" in data.upper():
                self.test_for_data = self.socket.canReadLine
                self.connectButton.setText("Connected")
                self.cluster_send(self.pref.get("cluster_filter", ""))
                self.cluster_send("set dx extension Section")
                self.cluster_send(
                    "set dx mode " + self.pref.get("cluster_mode", "OPEN")
                )
                self.cluster_send("sh wwv 1")
                logger.debug(f"callsign login acknowledged {data}")

            if "BEACON" in data:
                pass

            if "DX de" in data:
                parts = data.split()
                spotter = parts[2]
                freq = parts[3]
                dx = parts[4]
                _time = parts[-1]
                comment = " ".join(parts[5:-1])
                spot = {}
                spot["cmd"] = "DX"
                spot["ts"] = datetime.now(UTC).isoformat(" ")[:19]
                spot["dx"] = dx
                spot["spotter"] = spotter
                spot["comment"] = comment
                logger.debug(f"{spot}")
                try:
                    spot["freq"] = float(freq)
                    self.message.emit(spot)
                except ValueError:
                    logger.debug(f"couldn't parse freq from datablock {data}")

            # wwv data
            if match := re.search(
                r"(\d{2}-\w{3}-\d{4})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(.*?)\s+<(\w+)>",
                data,
            ):
                cmd = {}
                cmd["cmd"] = "SPACEWEATHER"
                cmd["date"] = match.group(1)
                cmd["hour"] = match.group(2)
                cmd["sfi"] = match.group(3)
                cmd["aindex"] = match.group(4)
                cmd["kindex"] = match.group(5)
                cmd["conditions"] = match.group(6).strip()
                cmd["source"] = match.group(7)
                self.message.emit(cmd)

    def input_to_cluster(self):
        data = self.clusterInput.text()
        self.cluster_send(data)
        self.clusterInput.clear()

    def closeEvent(self, _event: QtGui.QCloseEvent) -> None:
        """Triggered when instance closes. Cluster connection stays open."""
        self.action.setChecked(False)
        _event.accept()
