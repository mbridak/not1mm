#!/usr/bin/env python3
"""
K6GTE Contest logger
Email: michael.bridak@gmail.com
GPL V3
"""

# pylint: disable=unused-import, c-extension-no-member, no-member, invalid-name, too-many-lines

from datetime import datetime
from decimal import Decimal
from json import JSONDecodeError, loads, dumps
from pathlib import Path

import logging
import os
import pkgutil
import platform
import sys
import sqlite3

from PyQt5 import QtCore, QtGui, Qt
from PyQt5 import QtNetwork
from PyQt5 import QtWidgets, uic

from not1mm.lib.multicast import Multicast

os.environ["QT_QPA_PLATFORMTHEME"] = "gnome"

PIXELSPERSTEP = 10
UPDATE_INTERVAL = 2000

loader = pkgutil.get_loader("not1mm")
WORKING_PATH = os.path.dirname(loader.get_filename())

if "XDG_DATA_HOME" in os.environ:
    DATA_PATH = os.environ.get("XDG_DATA_HOME")
else:
    DATA_PATH = str(Path.home() / ".local" / "share")
DATA_PATH += "/not1mm"

if "XDG_CONFIG_HOME" in os.environ:
    CONFIG_PATH = os.environ.get("XDG_CONFIG_HOME")
else:
    CONFIG_PATH = str(Path.home() / ".config")
CONFIG_PATH += "/not1mm"

DARK_STYLESHEET = ""

MULTICAST_PORT = 2239
MULTICAST_GROUP = "239.1.1.1"
INTERFACE_IP = "0.0.0.0"

PREF = {}
if os.path.exists(CONFIG_PATH + "/not1mm.json"):
    with open(CONFIG_PATH + "/not1mm.json", "rt", encoding="utf-8") as file_descriptor:
        PREF = loads(file_descriptor.read())


class Band:
    """the band"""

    bands = {
        "160m": (1.8, 2),
        "80m": (3.5, 4),
        "60m": (5.102, 5.4065),
        "40m": (7.0, 7.3),
        "30m": (10.1, 10.15),
        "20m": (14.0, 14.35),
        "17m": (18.069, 18.168),
        "15m": (21.0, 21.45),
        "12m": (24.89, 25.0),
        "10m": (28.0, 29.7),
        "6m": (50.0, 54.0),
        "4m": (70.0, 71.0),
        "2m": (144.0, 148.0),
    }

    othername = {
        "160m": 1.8,
        "80m": 3.5,
        "60m": 5.1,
        "40m": 7.0,
        "30m": 10.0,
        "20m": 14.0,
        "17m": 18.0,
        "15m": 21.0,
        "12m": 24.0,
        "10m": 28.0,
        "6m": 50.0,
        "4m": 70.0,
        "2m": 144.0,
    }

    def __init__(self, band: str) -> None:
        self.start, self.end = self.bands.get(band, (0.0, 1.0))
        self.name = band
        self.altname = self.othername.get(band, 0.0)


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
        try:
            delete_call = (
                f"delete from spots where callsign = '{spot.get('callsign')}';"
            )
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
        except sqlite3.IntegrityError:
            ...

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

    def get_next_spot(self, current: float, limit: float) -> dict:
        """ "return a list of dict where freq range is defined"""
        self.cursor.execute(
            f"select * from spots where freq > {current} and freq <= {limit} order by freq ASC;"
        )
        return self.cursor.fetchone()

    def get_matching_spot(self, dx: str, start: float, end: float) -> dict:
        """Return the first spot matching supplied dx partial call"""
        self.cursor.execute(
            f"select * from spots where freq >= {start} and freq <= {end} and callsign like '%{dx}%';"
        )
        return self.cursor.fetchone()

    def get_prev_spot(self, current: float, limit: float) -> dict:
        """ "return a list of dict where freq range is defined"""
        self.cursor.execute(
            f"select * from spots where freq < {current} and freq >= {limit} order by freq DESC;"
        )
        return self.cursor.fetchone()

    def delete_spots(self, minutes: int):
        """doc"""
        self.cursor.execute(
            f"delete from spots where ts < datetime('now', '-{minutes} minutes');"
        )


class MainWindow(QtWidgets.QMainWindow):
    """
    The main window
    """

    zoom = 5
    currentBand = Band("20m")
    txMark = []
    rxMark = []
    rx_freq = None
    tx_freq = None
    something = None
    lineitemlist = []
    textItemList = []
    connected = False
    bandwidth = 0
    bandwidth_mark = []
    worked_list = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._udpwatch = None
        data_path = WORKING_PATH + "/data/bandmap.ui"
        uic.loadUi(data_path, self)
        if PREF.get("dark_mode"):
            self.setStyleSheet(DARK_STYLESHEET)
        self.agetime = self.clear_spot_olderSpinBox.value()
        self.clear_spot_olderSpinBox.valueChanged.connect(self.spot_aging_changed)
        self.clearButton.clicked.connect(self.clear_spots)
        self.zoominButton.clicked.connect(self.dec_zoom)
        self.zoomoutButton.clicked.connect(self.inc_zoom)
        self.connectButton.clicked.connect(self.connect)
        self.spots = Database()
        self.bandmap_scene = QtWidgets.QGraphicsScene()
        self.socket = QtNetwork.QTcpSocket()
        self.socket.readyRead.connect(self.receive)
        self.socket.connected.connect(self.maybeconnected)
        self.socket.disconnected.connect(self.disconnected)
        self.socket.errorOccurred.connect(self.socket_error)
        self.bandmap_scene.clear()
        self.bandmap_scene.setFocusOnTouch(False)
        self.bandmap_scene.selectionChanged.connect(self.spot_clicked)
        self.freq = 0.0
        self.keepRXCenter = False
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_station_timer)
        self.update_timer.start(UPDATE_INTERVAL)
        self.update()
        self.udpsocket = QtNetwork.QUdpSocket(self)
        self.udpsocket.bind(
            QtNetwork.QHostAddress.AnyIPv4,
            MULTICAST_PORT,
            QtNetwork.QUdpSocket.ShareAddress,
        )
        self.udpsocket.joinMulticastGroup(QtNetwork.QHostAddress(MULTICAST_GROUP))
        self.udpsocket.readyRead.connect(self.watch_udp)
        self.request_workedlist()

    def connect(self):
        """doc"""
        if self.connected is True:
            self.socket.close()
            self.connected = False
            self.connectButton.setStyleSheet("color: red;")
            self.connectButton.setText("Closed")
            return
        if os.path.exists(CONFIG_PATH + "/not1mm.json"):
            with open(
                CONFIG_PATH + "/not1mm.json", "rt", encoding="utf-8"
            ) as _file_descriptor:
                globals()["PREF"] = loads(_file_descriptor.read())
        server = PREF.get("cluster_server", "dxc.nc7j.com")
        port = PREF.get("cluster_port", 7373)
        logger.debug("%s", f"{server} {port}")
        self.socket.connectToHost(server, port)
        self.connectButton.setStyleSheet("color: white;")
        self.connectButton.setText("Connecting")
        self.connected = True

    def watch_udp(self):
        """doc"""
        while self.udpsocket.hasPendingDatagrams():
            datagram = self.udpsocket.readDatagram(self.udpsocket.pendingDatagramSize())
            bundle, _, _ = datagram
            logger.debug("%s", f"{bundle}")
            try:
                packet = loads(bundle.decode())
            except UnicodeDecodeError as err:
                the_error = f"Not Unicode: {err}\n{bundle}"
                logger.debug(the_error)
                continue
            except JSONDecodeError as err:
                the_error = f"Not JSON: {err}\n{bundle}"
                logger.debug(the_error)
                continue
            if (
                packet.get("cmd", "") == "RADIO_STATE"
                and packet.get("station", "") == platform.node()
            ):
                self.set_band(packet.get("band") + "m", False)
                if self.rx_freq != float(packet.get("vfoa")) / 1000000:
                    self.rx_freq = float(packet.get("vfoa")) / 1000000
                    self.tx_freq = self.rx_freq
                    self.center_on_rxfreq()
                bw_returned = packet.get("bw", "0")
                if not bw_returned.isdigit():
                    bw_returned = "0"
                self.bandwidth = int(bw_returned)
                step, _ = self.determine_step_digits()
                self.drawTXRXMarks(step)
                continue

            if (
                packet.get("cmd", "") == "NEXTSPOT"
                and packet.get("station", "") == platform.node()
                and self.rx_freq
            ):
                spot = self.spots.get_next_spot(
                    self.rx_freq + 0.000001, self.currentBand.end
                )
                if spot:
                    cmd = {}
                    cmd["cmd"] = "TUNE"
                    cmd["station"] = platform.node()
                    cmd["freq"] = spot.get("freq", self.rx_freq)
                    cmd["spot"] = spot.get("callsign", "")
                    packet = bytes(dumps(cmd), encoding="ascii")
                    self.udpsocket.writeDatagram(
                        packet, QtNetwork.QHostAddress(MULTICAST_GROUP), MULTICAST_PORT
                    )
                continue

            if (
                packet.get("cmd", "") == "PREVSPOT"
                and packet.get("station", "") == platform.node()
                and self.rx_freq
            ):
                spot = self.spots.get_prev_spot(
                    self.rx_freq - 0.000001, self.currentBand.start
                )
                if spot:
                    cmd = {}
                    cmd["cmd"] = "TUNE"
                    cmd["station"] = platform.node()
                    cmd["freq"] = spot.get("freq", self.rx_freq)
                    cmd["spot"] = spot.get("callsign", "")
                    packet = bytes(dumps(cmd), encoding="ascii")
                    self.udpsocket.writeDatagram(
                        packet, QtNetwork.QHostAddress(MULTICAST_GROUP), MULTICAST_PORT
                    )
                continue
            if (
                packet.get("cmd", "") == "SPOTDX"
                and packet.get("station", "") == platform.node()
            ):
                dx = packet.get("dx", "")
                freq = packet.get("freq", 0.0)
                spotdx = f"dx {dx} {freq}"
                self.send_command(spotdx)
                continue
            if (
                packet.get("cmd", "") == "FINDDX"
                and packet.get("station", "") == platform.node()
            ):
                dx = packet.get("dx", "")
                spot = self.spots.get_matching_spot(
                    dx, self.currentBand.start, self.currentBand.end
                )
                if spot:
                    cmd = {}
                    cmd["cmd"] = "TUNE"
                    cmd["station"] = platform.node()
                    cmd["freq"] = spot.get("freq", self.rx_freq)
                    cmd["spot"] = spot.get("callsign", "")
                    packet = bytes(dumps(cmd), encoding="ascii")
                    self.udpsocket.writeDatagram(
                        packet, QtNetwork.QHostAddress(MULTICAST_GROUP), MULTICAST_PORT
                    )
                continue
            if (
                packet.get("cmd", "") == "WORKED"
                and packet.get("station", "") == platform.node()
            ):
                self.worked_list = packet.get("worked", {})
                logger.debug("%s", f"{self.worked_list}")

    def spot_clicked(self):
        """dunno"""
        items = self.bandmap_scene.selectedItems()
        for item in items:
            if item:
                cmd = {}
                cmd["cmd"] = "TUNE"
                cmd["station"] = platform.node()
                cmd["freq"] = items[0].property("freq")
                cmd["spot"] = items[0].toPlainText().split()[0]
                packet = bytes(dumps(cmd), encoding="ascii")
                self.udpsocket.writeDatagram(
                    packet, QtNetwork.QHostAddress(MULTICAST_GROUP), MULTICAST_PORT
                )

    def request_workedlist(self):
        """Request worked call list from logger"""
        cmd = {}
        cmd["cmd"] = "GETWORKEDLIST"
        cmd["station"] = platform.node()
        packet = bytes(dumps(cmd), encoding="ascii")
        self.udpsocket.writeDatagram(
            packet, QtNetwork.QHostAddress(MULTICAST_GROUP), MULTICAST_PORT
        )

    def update_station_timer(self):
        """doc"""
        self.update_stations()

    def update(self):
        """doc"""
        self.update_timer.setInterval(UPDATE_INTERVAL)
        self.clear_all_callsign_from_scene()
        self.clear_freq_mark(self.rxMark)
        self.clear_freq_mark(self.txMark)
        self.clear_freq_mark(self.bandwidth_mark)
        self.bandmap_scene.clear()

        step, _digits = self.determine_step_digits()
        steps = int(round((self.currentBand.end - self.currentBand.start) / step))
        self.graphicsView.setFixedSize(330, steps * PIXELSPERSTEP + 30)
        self.graphicsView.setScene(self.bandmap_scene)
        for i in range(steps):  # Draw tickmarks
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
            if i % 5 == 0:  # Add Frequency
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
        self.update_stations()

    def inc_zoom(self):
        """doc"""
        self.zoom += 1
        self.zoom = min(self.zoom, 7)
        self.update()
        self.center_on_rxfreq()

    def dec_zoom(self):
        """doc"""
        self.zoom -= 1
        self.zoom = max(self.zoom, 1)
        self.update()
        self.center_on_rxfreq()

    def drawTXRXMarks(self, step):
        """doc"""
        if self.rx_freq:
            self.clear_freq_mark(self.bandwidth_mark)
            self.clear_freq_mark(self.rxMark)
            self.draw_bandwidth(
                self.rx_freq, step, QtGui.QColor(30, 30, 180, 180), self.bandwidth_mark
            )
            self.drawfreqmark(
                self.rx_freq, step, QtGui.QColor(30, 180, 30, 180), self.rxMark
            )

    def Freq2ScenePos(self, freq: float):
        """doc"""
        if freq < self.currentBand.start or freq > self.currentBand.end:
            return QtCore.QPointF()
        step, _digits = self.determine_step_digits()
        ret = QtCore.QPointF(
            0,
            (
                (Decimal(str(freq)) - Decimal(str(self.currentBand.start)))
                / Decimal(str(step))
            )
            * PIXELSPERSTEP,
        )
        return ret

    def center_on_rxfreq(self):
        """doc"""
        freq_pos = self.Freq2ScenePos(self.rx_freq).y()
        # self.graphicsView.verticalScrollBar().setSliderPosition(
        #     int(freq_pos - (self.height() / 2) + 80)
        # )
        self.scrollArea.verticalScrollBar().setValue(
            int(freq_pos - (self.height() / 2) + 80)
        )
        # This does not work... Have no idea why.
        # anim = QtCore.QPropertyAnimation(
        #     self.scrollArea.verticalScrollBar(), "value".encode()
        # )
        # anim.setDuration(300)
        # anim.setStartValue(self.scrollArea.verticalScrollBar().value())
        # anim.setEndValue(int(freq_pos - (self.height() / 2) + 80))
        # anim.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def drawfreqmark(self, freq, _step, color, currentPolygon):
        """doc"""

        self.clear_freq_mark(currentPolygon)
        # do not show the freq mark if it is outside the bandmap
        if freq < self.currentBand.start or freq > self.currentBand.end:
            return

        Yposition = self.Freq2ScenePos(freq).y()

        poly = QtGui.QPolygonF()

        poly.append(QtCore.QPointF(21, Yposition))
        poly.append(QtCore.QPointF(10, Yposition - 7))
        poly.append(QtCore.QPointF(10, Yposition + 7))
        pen = QtGui.QPen()
        brush = QtGui.QBrush(color)
        currentPolygon.append(self.bandmap_scene.addPolygon(poly, pen, brush))

    def draw_bandwidth(self, freq, _step, color, currentPolygon):
        """bandwidth"""
        logger.debug("%s", f"mark:{currentPolygon} f:{freq} b:{self.bandwidth}")
        self.clear_freq_mark(currentPolygon)
        if freq < self.currentBand.start or freq > self.currentBand.end:
            return
        if freq and self.bandwidth:
            # color = QtGui.QColor(30, 30, 180)
            bw_start = Decimal(str(freq)) - (
                (Decimal(str(self.bandwidth)) / 2) / 1000000
            )
            bw_end = Decimal(str(freq)) + ((Decimal(str(self.bandwidth)) / 2) / 1000000)
            logger.debug("%s", f"s:{bw_start} e:{bw_end}")
            Yposition_neg = self.Freq2ScenePos(bw_start).y()
            Yposition_pos = self.Freq2ScenePos(bw_end).y()
            poly = QtGui.QPolygonF()
            poly.append(QtCore.QPointF(15, Yposition_neg))
            poly.append(QtCore.QPointF(20, Yposition_neg))
            poly.append(QtCore.QPointF(20, Yposition_pos))
            poly.append(QtCore.QPointF(15, Yposition_pos))
            pen = QtGui.QPen()
            brush = QtGui.QBrush(color)
            currentPolygon.append(self.bandmap_scene.addPolygon(poly, pen, brush))

    def update_stations(self):
        """doc"""
        self.update_timer.setInterval(UPDATE_INTERVAL)
        self.clear_all_callsign_from_scene()
        self.spot_aging()
        step, _digits = self.determine_step_digits()

        result = self.spots.getspotsinband(self.currentBand.start, self.currentBand.end)
        entity = ""
        if result:
            min_y = 0.0
            for items in result:
                pen_color = QtGui.QColor(192, 192, 192)
                if items.get("callsign") in self.worked_list:
                    call_bandlist = self.worked_list.get(items.get("callsign"))
                    if self.currentBand.altname in call_bandlist:
                        pen_color = QtGui.QColor(255, 47, 47)
                freq_y = (
                    (items.get("freq") - self.currentBand.start) / step
                ) * PIXELSPERSTEP
                text_y = max(min_y + 5, freq_y)
                self.lineitemlist.append(
                    self.bandmap_scene.addLine(
                        22, freq_y, 55, text_y, QtGui.QPen(pen_color)
                    )
                )
                text = self.bandmap_scene.addText(
                    items.get("callsign")
                    + " @ "
                    + entity
                    + " "
                    + items.get("ts").split()[1][:-3]
                )
                text.document().setDocumentMargin(0)
                text.setPos(60, text_y - (text.boundingRect().height() / 2))
                text.setFlags(
                    QtWidgets.QGraphicsItem.ItemIsFocusable
                    | QtWidgets.QGraphicsItem.ItemIsSelectable
                    | text.flags()
                )
                text.setProperty("freq", items.get("freq"))
                text.setToolTip(items.get("comment"))
                text.setDefaultTextColor(pen_color)
                min_y = text_y + text.boundingRect().height() / 2
                self.textItemList.append(text)

    def determine_step_digits(self):
        """doc"""
        return_zoom = {
            1: (0.0001, 4),
            2: (0.00025, 4),
            3: (0.0005, 4),
            4: (0.001, 3),
            5: (0.0025, 3),
            6: (0.005, 3),
            7: (0.01, 2),
        }
        step, digits = return_zoom.get(self.zoom, (0.0001, 4))

        if self.currentBand.start >= 28.0 and self.currentBand.start < 420.0:
            step = step * 10
            return (step, digits)

        if self.currentBand.start >= 420.0 and self.currentBand.start < 2300.0:
            step = step * 100

        return (step, digits)

    def set_band(self, band: str, savePrevBandZoom: bool):
        """doc"""
        logger.debug("%s", f"{band} {savePrevBandZoom}")
        if band != self.currentBand.name:
            if savePrevBandZoom:
                self.saveCurrentZoom()
            self.currentBand = Band(band)
            # self.zoom = self.savedZoom(band)
            self.update()

    def spot_aging(self):
        """doc"""
        if self.agetime:
            self.spots.delete_spots(self.agetime)

    def clear_all_callsign_from_scene(self):
        """doc"""
        for items in self.textItemList:
            self.bandmap_scene.removeItem(items)
        self.textItemList.clear()
        for items in self.lineitemlist:
            self.bandmap_scene.removeItem(items)
        self.lineitemlist.clear()

    def clear_freq_mark(self, currentPolygon):
        """doc"""
        if currentPolygon:
            for mark in currentPolygon:
                self.bandmap_scene.removeItem(mark)
        currentPolygon.clear()

    def receive(self):
        """doc"""
        data = self.socket.readAll()
        data = str(data, "utf-8").strip()
        if "login:" in data:
            self.send_command(self.callsignField.text())
            self.send_command(PREF.get("cluster_filter", ""))
            self.send_command("set dx extension Name CTY State Section")
            self.send_command("set dx mode " + PREF.get("cluster_mode", "OPEN"))
            return
        if "call:" in data:
            self.send_command(self.callsignField.text())
            self.send_command(PREF.get("cluster_filter", ""))
            self.send_command("set dx extension Name CTY State Section")
            self.send_command("set dx mode " + PREF.get("cluster_mode", "OPEN"))
            return
        if "DX de" in data:
            parts = data.split()
            spotter = parts[2]
            freq = parts[3]
            dx = parts[4]
            _time = parts[-1]
            comment = " ".join(parts[5:-1])
            # spot = DxSpot()
            spot = {}
            spot["ts"] = datetime.utcnow().isoformat(" ")[:19]
            spot["callsign"] = dx
            spot["spotter"] = spotter
            spot["comment"] = comment
            try:
                spot["freq"] = float(freq) / 1000
            except ValueError:
                logger.debug("%s", f"{data}")
            self.spots.addspot(spot)
            return
        if self.callsignField.text().upper() in data:
            self.connectButton.setStyleSheet("color: green;")
            self.connectButton.setText("Connected")
            logger.debug("%s", f"{data}")

    def maybeconnected(self):
        """doc"""
        self.connectButton.setStyleSheet("color: yellow;")
        self.connectButton.setText("Connecting")

    def socket_error(self):
        """doc"""
        print("An Error occurred.")

    def disconnected(self):
        """doc"""
        self.connected = False
        self.connectButton.setStyleSheet("color: red;")
        self.connectButton.setText("Closed")

    def send_command(self, cmd: str):
        """doc"""
        cmd += "\r\n"
        tosend = bytes(cmd, encoding="ascii")
        logger.debug("%s", f"{tosend}")
        if self.socket:
            if self.socket.isOpen():
                self.socket.write(tosend)

    def clear_spots(self):
        """doc"""
        self.spots.delete_spots(0)

    def spot_aging_changed(self):
        """doc"""
        self.agetime = self.clear_spot_olderSpinBox.value()

    def showContextMenu(self):
        """doc"""


def run():
    """doc"""
    sys.exit(app.exec())


logger = logging.getLogger("__main__")
handler = logging.StreamHandler()
formatter = logging.Formatter(
    datefmt="%H:%M:%S",
    fmt="[%(asctime)s] %(levelname)s %(module)s - %(funcName)s Line %(lineno)d:\n%(message)s",
)
handler.setFormatter(formatter)
logger.addHandler(handler)

if Path("./debug").exists():
    logger.setLevel(logging.DEBUG)
    logger.debug("debugging on")
else:
    logger.setLevel(logging.WARNING)
    logger.warning("debugging off")

app = QtWidgets.QApplication(sys.argv)


app.setStyle("Adwaita-Dark")
window = MainWindow()
window.show()
if __name__ == "__main__":
    run()
