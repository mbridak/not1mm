#!/usr/bin/env python3
"""
K6GTE Contest logger
Email: michael.bridak@gmail.com
GPL V3
"""

# pylint: disable=unused-import, c-extension-no-member, no-member, invalid-name, too-many-lines

import sys
from PyQt5 import QtCore, QtGui
from PyQt5 import QtNetwork
from PyQt5 import QtWidgets, uic

PIXELSPERSTEP = 10


class Band:
    start = 14000000
    end = 14350000


class MainWindow(QtWidgets.QMainWindow):
    """
    The main window
    """

    zoom = "ZOOM_100HZ"
    currentBand = Band()
    txMark = None
    rxMark = None
    something = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("/home/mbridak/Nextcloud/dev/not1mm/not1mm/test.ui", self)
        self.bandmap_scene = QtWidgets.QGraphicsScene()
        self.socket = QtNetwork.QTcpSocket()
        self.socket.readyRead.connect(self.receive)
        self.socket.connected.connect(self.connected)
        self.socket.errorOccurred.connect(self.socket_error)
        self.socket.connectToHost("hamqth.com", 7300)
        self.bandmap_scene.clear()
        self.bandmap_scene.setFocusOnTouch(False)
        self.freq = 0.0
        self.keepRXCenter = False
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.updateStationTimer)
        self.update_timer.start(1000)
        self.update()

    def updateStationTimer(self):
        """doc"""

    def update(self):
        """doc"""
        self.update_timer.setInterval(1000)
        self.clearAllCallsignFromScene()
        self.clearFreqMark(self.rxMark)
        self.clearFreqMark(self.txMark)
        self.bandmap_scene.clear()

        step, digits = self.determineStepDigits()
        print(f"*********Step {step}")
        steps = int(round((self.currentBand.end - self.currentBand.start) / step))
        print(f"*******Steps: {steps}")
        self.graphicsView.setFixedSize(330, steps * PIXELSPERSTEP + 30)

        for i in range(steps):
            length = 10
            if i % 5 == 0:
                length = 15
            self.bandmap_scene.addLine(
                0,
                i * PIXELSPERSTEP,
                length,
                i * PIXELSPERSTEP,
                QtGui.QPen(QtGui.QColor(192, 192, 192)),
            )
            if i % 5 == 0:
                self.something = self.bandmap_scene.addText("TEST")
                self.something.setPos(
                    -(self.something.boundingRect().width()) - 10,
                    i * PIXELSPERSTEP - (self.something.boundingRect().height() / 2),
                )

        # QString endFreqDigits= QString::number(currentBand.end + step*steps, 'f', digits)
        endFreqDigits = "TEST"
        self.bandmap_scene.setSceneRect(
            160 - (len(endFreqDigits) * PIXELSPERSTEP), 0, 0, steps * PIXELSPERSTEP + 20
        )

    def determineStepDigits(self):
        """doc"""

        return_zoom = {
            "ZOOM_100HZ": (0.0001, 4),
            "ZOOM_250HZ": (0.00025, 4),
            "ZOOM_500HZ": (0.0005, 4),
            "ZOOM_1KHZ": (0.001, 3),
            "ZOOM_2K5HZ": (0.0025, 3),
            "ZOOM_5KHZ": (0.005, 3),
            "ZOOM_10KHZ": (0.01, 2),
        }

        return return_zoom.get(self.zoom, (0.0001, 4))

    def setBand(self, band, savePrevBandZoom: bool):
        """doc"""
        if savePrevBandZoom:
            self.saveCurrentZoom()
        self.currentBand = Band()
        self.zoom = self.savedZoom(band)

    def clearAllCallsignFromScene(self):
        """doc"""

    def clearFreqMark(self, currentPolygon):
        """doc"""
        if currentPolygon:
            self.bandmap_scene.removeItem(currentPolygon)

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
