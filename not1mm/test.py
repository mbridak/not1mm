#!/usr/bin/env python3
"""
K6GTE Contest logger
Email: michael.bridak@gmail.com
GPL V3
"""

# pylint: disable=unused-import, c-extension-no-member, no-member, invalid-name, too-many-lines

from datetime import datetime

import sys
import sqlite3
from PyQt5 import QtCore, QtGui
from PyQt5 import QtNetwork
from PyQt5 import QtWidgets, uic

PIXELSPERSTEP = 10


class Band:
    """the band"""

    bands = {
        "160m": (1.8, 2),
        "80m": (3.5, 4),
        "60m": (5.102, 5.4065),
        "40m": (7.0, 7.3),
        "30m": (10.1, 10.15),
        "20m": (14.0, 14.35),
        "15m": (21.0, 21.45),
        "10m": (28.0, 29.7),
        "6m": (50.0, 54.0),
        "4m": (70.0, 71.0),
        "2m": (144.0, 148.0),
    }

    def __init__(self, band: str) -> None:
        self.start, self.end = self.bands.get(band, (0.0, 1.0))
        self.name = band


class Database:
    """spot database"""

    def __init__(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = self.row_factory
        self.cursor = self.db.cursor()
        sql_command = (
            "create table spots("
            "ts DATETIME NOT NULL, "
            "callsign VARCHAR(15) NOT NULL, "
            "freq DOUBLE NOT NULL, "
            "band VARCHAR(6), "
            "mode VARCHAR(6), "
            "spotter VARCHAR(15) NOT NULL, "
            "comment VARCHAR(45));"
        )
        self.cursor.execute(sql_command)
        self.db.commit()

    @staticmethod
    def row_factory(cursor, row):
        """
        cursor.description:
        (name, type_code, display_size,
        internal_size, precision, scale, null_ok)
        row: (value, value, ...)
        """
        return {
            col[0]: row[idx]
            for idx, col in enumerate(
                cursor.description,
            )
        }

    def addspot(self, spot):
        """doc"""
        delete_call = f"delete from spots where callsign = '{spot.get('callsign')}';"
        self.cursor.execute(delete_call)
        self.db.commit()

        pre = "INSERT INTO spots("
        values = []
        columns = ""
        placeholders = ""
        for key in spot.keys():
            columns += f"{key},"
            values.append(spot[key])
            placeholders += "?,"
        post = f") VALUES({placeholders[:-1]});"

        sql = f"{pre}{columns[:-1]}{post}"
        self.cursor.execute(sql, tuple(values))
        self.db.commit()

    def getspots(self) -> list:
        """returns a list of dicts."""
        try:
            self.cursor.execute("select * from spots order by freq ASC;")
            return self.cursor.fetchall()
        except sqlite3.OperationalError:
            return ()

    def getspotsinband(self, start: float, end: float) -> list:
        """ "return a list of dict where freq range is defined"""
        self.cursor.execute(
            f"select * from spots where freq >= {start} and freq <= {end} order by freq ASC;"
        )
        return self.cursor.fetchall()

    def delete_spots(self, minutes: int):
        """doc"""
        self.cursor.execute(
            f"delete from spots where ts < datetime('now', '-{minutes} minutes');"
        )


class MainWindow(QtWidgets.QMainWindow):
    """
    The main window
    """

    zoom = "ZOOM_2K5HZ"
    currentBand = Band("40m")
    txMark = None
    rxMark = None
    something = None
    lineitemlist = []
    textItemList = []
    agetime = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("/home/mbridak/Nextcloud/dev/not1mm/not1mm/test.ui", self)
        self.clear_spot_olderSpinBox.valueChanged.connect(self.spotAgingChanged)
        self.clearButton.clicked.connect(self.clearSpots)
        self.spots = Database()
        self.bandmap_scene = QtWidgets.QGraphicsScene()
        self.socket = QtNetwork.QTcpSocket()
        self.socket.readyRead.connect(self.receive)
        self.socket.connected.connect(self.connected)
        self.socket.errorOccurred.connect(self.socket_error)
        # self.socket.connectToHost("hamqth.com", 7300)
        self.socket.connectToHost("dxc.nc7j.com", 7373)

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
        self.updateStations()

    def update(self):
        """doc"""
        self.update_timer.setInterval(1000)
        self.clearAllCallsignFromScene()
        self.clearFreqMark(self.rxMark)
        self.clearFreqMark(self.txMark)
        self.bandmap_scene.clear()

        step, digits = self.determineStepDigits()
        steps = int(round((self.currentBand.end - self.currentBand.start) / step))
        self.graphicsView.setFixedSize(330, steps * PIXELSPERSTEP + 30)
        self.graphicsView.setScene(self.bandmap_scene)
        for i in range(steps):
            length = 10
            if i % 5 == 0:
                length = 15
            self.bandmap_scene.addLine(
                10,
                i * PIXELSPERSTEP,
                length + 10,
                i * PIXELSPERSTEP,
                QtGui.QPen(QtGui.QColor(192, 192, 192)),
            )
            if i % 5 == 0:
                freq = self.currentBand.start + step * i
                text = f"{freq:.3f}"
                self.something = self.bandmap_scene.addText(text)
                self.something.setPos(
                    -(self.something.boundingRect().width()) + 10,
                    i * PIXELSPERSTEP - (self.something.boundingRect().height() / 2),
                )

        freq = self.currentBand.end + step * steps
        endFreqDigits = f"{freq:.3f}"
        self.bandmap_scene.setSceneRect(
            160 - (len(endFreqDigits) * PIXELSPERSTEP), 0, 0, steps * PIXELSPERSTEP + 20
        )

        self.drawTXRXMarks(step)

        self.updateStations()

    def drawTXRXMarks(self, step):
        """doc"""

    def updateStations(self):
        """doc"""
        self.update_timer.setInterval(1000)
        self.clearAllCallsignFromScene()
        self.spotAging()
        step, digits = self.determineStepDigits()

        result = self.spots.getspotsinband(self.currentBand.start, self.currentBand.end)
        if result:
            min_y = 0.0
            for items in result:
                freq_y = (
                    (items.get("freq") - self.currentBand.start) / step
                ) * PIXELSPERSTEP
                text_y = max(min_y + 5, freq_y)
                self.lineitemlist.append(
                    self.bandmap_scene.addLine(
                        17, freq_y, 40, text_y, QtGui.QPen(QtGui.QColor(192, 192, 192))
                    )
                )
                text = self.bandmap_scene.addText(
                    items.get("callsign") + " @ " + items.get("ts").split()[1][:-3]
                )
                text.document().setDocumentMargin(0)
                text.setPos(40, text_y - (text.boundingRect().height() / 2))
                text.setFlags(
                    QtWidgets.QGraphicsItem.ItemIsFocusable
                    | QtWidgets.QGraphicsItem.ItemIsSelectable
                    | text.flags()
                )
                text.setProperty("freq", items.get("freq"))
                text.setToolTip(items.get("comment", ""))

                min_y = text_y + text.boundingRect().height() / 2

                # textColor = Data::statusToColor(lower.value().status, qApp->palette().color(QPalette::Text));
                # text->setDefaultTextColor(textColor);
                self.textItemList.append(text)

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
        step, digits = return_zoom.get(self.zoom, (0.0001, 4))

        if self.currentBand.start >= 28.0 and self.currentBand.start < 420.0:
            step = step * 10
            return (step, digits)

        if self.currentBand.start >= 420.0 and self.currentBand.start < 2300.0:
            step = step * 100

        return (step, digits)

    def setBand(self, band: str, savePrevBandZoom: bool):
        """doc"""
        if savePrevBandZoom:
            self.saveCurrentZoom()
        self.currentBand = Band(band)
        self.zoom = self.savedZoom(band)

    def spotAging(self):
        """doc"""
        if self.agetime:
            self.spots.delete_spots(self.agetime)

    def clearAllCallsignFromScene(self):
        """doc"""
        for items in self.textItemList:
            self.bandmap_scene.removeItem(items)
        self.textItemList.clear()
        for items in self.lineitemlist:
            self.bandmap_scene.removeItem(items)
        self.lineitemlist.clear()

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
            self.send_command("Set DX Filter Not Skimmer AND SpotterCont=NA")
            # self.send_command("reject/spot 0 info FT8")
            # self.send_command("accept/spot 0 freq hf/cw")
            # self.send_command("accept/spot 1 freq hf/ssb")
        if "DX de" in data:
            parts = data.split()
            spotter = parts[2]
            freq = parts[3]
            dx = parts[4]
            time = parts[-1]
            # spot = DxSpot()
            spot = {}
            spot["ts"] = datetime.utcnow().isoformat(" ")[:19]
            spot["callsign"] = dx
            spot["spotter"] = spotter
            spot["freq"] = float(freq) / 1000
            self.spots.addspot(spot)

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
        self.spots.delete_spots(0)

    def zoomIn(self):
        """doc"""

    def zoomOut(self):
        """doc"""

    def spotAgingChanged(self):
        """doc"""
        self.agetime = self.clear_spot_olderSpinBox.value()

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
