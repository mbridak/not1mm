#!/usr/bin/env python3
"""
K6GTE Contest logger
Email: michael.bridak@gmail.com
GPL V3
"""

import sys
from PyQt5 import QtNetwork
from PyQt5 import QtWidgets, uic


class MainWindow(QtWidgets.QMainWindow):
    """
    The main window
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("/home/mbridak/Nextcloud/dev/not1mm/not1mm/test.ui", self)
        bandmap_scene = QtWidgets.QGraphicsScene()
        self.socket = QtNetwork.QTcpSocket()
        self.socket.readyRead.connect(self.receive)
        self.socket.connected.connect(self.connected)
        self.socket.errorOccurred.connect(self.socket_error)
        self.socket.connectToHost("hamqth.com", 7300)

    def receive(self):
        """doc"""
        data = self.socket.readAll()
        data = str(data, "utf-8").strip()
        if "login:" in data:
            self.send_command("k6gte")
            self.send_command("reject/spot 0 info FT8")
            self.send_command("accept/spot 0 freq hf/cw")
            self.send_command("accept/spot 1 freq hf/ssb")
        if "DX de" in data:
            parts = data.split()
            spotter = parts[2]
            freq = parts[3]
            dx = parts[4]
            time = parts[-1]
            print(f"{dx} {freq} {time}")

    def connected(self):
        """doc"""
        print("Connected")

    def socket_error(self):
        """doc"""
        print("An Error occurred.")

    def disconnect(self):
        """doc"""
        self.socket.close()

    def send_command(self, cmd: str):
        """doc"""
        cmd += "\r\n"
        tosend = bytes(cmd, encoding="ascii")
        print(f"{tosend}")
        if self.socket:
            if self.socket.isOpen():
                self.socket.write(tosend)

    def clearSpots(self):
        """doc"""

    def zoomIn(self):
        """doc"""

    def zoomOut(self):
        """doc"""

    def spotAgingChanged(self):
        """doc"""

    def showContextMenu(self):
        """doc"""


def run():
    """doc"""
    sys.exit(app.exec())


app = QtWidgets.QApplication(sys.argv)

window = MainWindow()
window.show()
if __name__ == "__main__":
    run()
