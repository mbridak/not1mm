#!/usr/bin/env python3
"""
not1mm Contest logger
Email: michael.bridak@gmail.com
GPL V3
Class: BandMapWindow
Purpose: Onscreen widget to show realtime spots from an AR cluster.
"""

# pylint: disable=unused-import, c-extension-no-member, no-member, invalid-name, too-many-lines
# pylint: disable=logging-fstring-interpolation, line-too-long, no-name-in-module

import logging
import os
import platform
import re
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from json import loads

from PyQt6 import QtCore, QtGui, QtWidgets, uic, QtNetwork
from PyQt6.QtGui import QColorConstants, QFont, QColor
from PyQt6.QtWidgets import QDockWidget, QStyle
from PyQt6.QtCore import Qt, pyqtSignal

import not1mm.fsutils as fsutils

# from not1mm.lib.multicast import Multicast

logger = logging.getLogger(__name__)

PIXELSPERSTEP = 10
UPDATE_INTERVAL = 2000
CLEAR_FREQ = 0.1  # 100 Hz


class Band:
    """the band"""

    bands = {
        "160m":     (1800,     2000,    1.8),
        "80m":      (3500,     4000,    3.5),
        "60m":      (5102,     5407,    5.1),
        "40m":      (7000,     7300,    7.0),
        "30m":     (10100,    10150,   10.0),
        "20m":     (14000,    14350,   14.0),
        "17m":     (18068,    18168,   18.0),
        "15m":     (21000,    21450,   21.0),
        "12m":     (24890,    24990,   24.0),
        "10m":     (28000,    29700,   28.0),
        "6m":      (50000,    54000,   50.0),
        "4m":      (70000,    71000,   70.0),
        "2m":    (144_000,  148_000,  144.0),
        "70cm":  (420_000,  450_000,  432.0),
        "33cm":  (902_000,  928_000,  932.0),
        "23cm": (1240_000, 1300_000, 1232.0),
    } # fmt: skip

    def __init__(self, band: str) -> None:
        self.start, self.end, self.altname = self.bands.get(band, (0.0, 1.0, 0.0))
        self.name = band

    def new_from_freq(freq: float) -> (float, float):
        """Find band matching a frequency."""

        for band, edges in Band.bands.items():
            if edges[0] <= freq <= edges[1]:
                return Band(band)
        return Band("unknown")


class Database:
    """
    An in memory Database class to hold spots.
    """

    def __init__(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = self.row_factory
        self.cursor = self.db.cursor()
        sql_command = (
            "create table spots ("
            "callsign VARCHAR(15) NOT NULL, "
            "ts DATETIME NOT NULL, "
            "freq DOUBLE NOT NULL, "  # in kHz
            "mode VARCHAR(6), "
            "spotter VARCHAR(15) NOT NULL, "
            "comment VARCHAR(45));"
        )
        self.cursor.execute(sql_command)

        self.cursor.execute("CREATE INDEX spot_call_index ON spots (callsign);")
        self.cursor.execute("CREATE INDEX spot_freq_index ON spots (freq);")
        self.cursor.execute("CREATE INDEX spot_ts_index ON spots (ts);")

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

    def get_like_calls(self, call: str) -> dict:
        """
        Returns spots where the spotted callsigns contain the supplied string.

        Parameters
        ----------
        call : str
        The callsign to search for.

        Returns
        -------
        a dict like:

        {'K5TUX': [14.0, 21.0], 'N2CQR': [14.0], 'NE4RD': [14.0]}
        """
        try:
            self.cursor.execute(
                f"select distinct callsign from spots where callsign like '%{call}%' ORDER by callsign ASC;"
            )
            result = self.cursor.fetchall()
            return result
        except sqlite3.OperationalError as exception:
            logger.debug("%s", exception)
            return {}

    def addspot(self, spot: dict, clear_freq=False) -> None:
        """
        Add spot to database, replacing any previous spots with the same call
        on the same band.

        Parameters
        ----------
        spot: Dict
        A dict of the form: {'ts': datetime, 'callsign': str, 'freq': float,
        'band': str,'mode': str,'spotter': str, 'comment': str}

        clear_freq: bool
        If True, delete any previous spots around this frequency.

        Returns
        -------
        Nothing.
        """
        if "band" in spot:
            band = Band(spot.get("band"))
        else:
            band = Band.new_from_freq(spot.get("freq"))

        try:
            delete_call_q = (
                "delete from spots where callsign = ? and freq between ? and ?"
            )
            if "MARKED" not in spot.get("comment", ""):
                # new spot is not MARKED, don't overwrite any MARKED spot
                delete_call_q += " and comment not like '%MARKED%'"
            self.cursor.execute(
                delete_call_q, (spot.get("callsign"), band.start, band.end)
            )

            if clear_freq:
                clear_freq_q = "delete from spots where freq between ? and ?;"
                self.cursor.execute(
                    clear_freq_q,
                    (spot.get("freq") - CLEAR_FREQ, spot.get("freq") + CLEAR_FREQ),
                )

            self.cursor.execute(
                "INSERT INTO spots(callsign, ts, freq, mode, spotter, comment) VALUES(?, ?, ?, ?, ?, ?)",
                (
                    spot["callsign"],
                    spot.get("ts", datetime.now(timezone.utc).replace(second=0, microsecond=0, tzinfo=None)),
                    spot["freq"],
                    spot.get("mode", None),
                    spot.get("spotter", platform.node()),
                    spot.get("comment", ""),
                ),
            )
            self.db.commit()
        except sqlite3.IntegrityError:
            ...

    def getspots(self) -> list:
        """
        Return a list of spots, sorted by the ascending frequency of the spot.

        Parameters
        ----------
        None

        Returns
        -------
        a list of dicts.
        """
        try:
            self.cursor.execute("select * from spots order by freq ASC;")
            return self.cursor.fetchall()
        except sqlite3.OperationalError:
            return ()

    def getspotsinband(self, start: float, end: float) -> list:
        """
        Returns spots in a list of dicts where the spotted frequency
        is in the range defined, in ascending order.

        Parameters
        ----------
        start : float
        The start frequency.
        end : float
        The end frequency.

        Returns
        -------
        A list of dicts.
        """
        self.cursor.execute(
            "select * from spots where freq >= ? and freq <= ? order by freq ASC;",
            (start, end),
        )
        return self.cursor.fetchall()

    def get_next_spot(self, current: float, limit: float) -> dict:
        """
        Return a list of dict where freq range is defined by current and limit.
        The list is sorted by the ascending frequency of the spot.

        Parameters
        ----------
        current : float
        The current frequency.
        limit : float
        The limit frequency.

        Returns
        -------
        A dict of the spot.
        """
        self.cursor.execute(
            "select * from spots where freq > ? and freq <= ? order by freq ASC;",
            (current, limit),
        )
        return self.cursor.fetchone()

    def get_matching_spot(self, dx: str, start: float, end: float) -> dict:
        """
        Return the first spot matching supplied dx partial callsign.

        Parameters
        ----------
        dx : str
        The dx partial callsign.
        start : float
        The start frequency.
        end : float
        The end frequency.

        Returns
        -------
        A dict of the spot.
        """

        self.cursor.execute(
            "select * from spots where freq >= ? and freq <= ? and callsign like ?;",
            (start, end, f"%{dx}%"),
        )
        return self.cursor.fetchone()

    def get_prev_spot(self, current: float, limit: float) -> dict:
        """
        Return a list of dict where freq range is defined in descending order.

        Parameters
        ----------
        current : float
        The current frequency.
        limit : float
        The limit frequency.

        Returns
        -------
        A list of dicts.
        """
        self.cursor.execute(
            "select * from spots where freq < ? and freq >= ? order by freq DESC;",
            (current, limit),
        )
        return self.cursor.fetchone()

    def delete_spot(self, call: str, freq: float) -> None:
        """
        Delete a spot identified by call and frequency.
        """
        self.cursor.execute(
            "delete from spots where callsign = ? and freq = ?",
            (call, freq))
        self.db.commit()

    def delete_spots(self, minutes: int) -> None:
        """
        Delete spots older than the specified number of minutes.

        Parameters
        ----------
        minutes : int
        The number of minutes to delete.

        Returns
        -------
        None
        """
        self.cursor.execute(
            "delete from spots where ts < datetime('now', ?);",
            (f"-{minutes} minutes",),
        )

    def delete_marks(self) -> None:
        """Delete marked spots."""
        self.cursor.execute("delete from spots where ts > datetime('now');")


class BandMapScene(QtWidgets.QGraphicsScene):
    """
    QGraphicsScene class with custom context menu hook.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def contextMenuEvent(self, event):
        item = self.itemAt(event.scenePos(), QtGui.QTransform())
        if item:
            callsign = item.property("callsign")
            freq = item.property("freq")
            comment = item.toolTip()

            menu = QtWidgets.QMenu()
            menu.addAction("Confirm", lambda: self.parent.spots.addspot({
                "callsign": callsign,
                "freq": freq,
                "comment": comment,
            }, True))
            if "MARKED" in comment:
                menu.addAction("Unmark", lambda: self.parent.spots.addspot({
                    "callsign": callsign,
                    "freq": freq,
                    "comment": comment.replace("MARKED", ""),
                }, True))
            else:
                menu.addAction("Mark", lambda: self.parent.spots.addspot({
                    "callsign": callsign,
                    "freq": freq,
                    "comment": comment + " MARKED",
                }, True))
            menu.addAction("Delete", lambda: self.parent.spots.delete_spot(callsign, freq))
            menu.exec(event.screenPos())
        else:
            super().contextMenuEvent(event)


class BandMapWindow(QDockWidget):
    """The BandMapWindow class."""

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
    multicast_interface = None
    text_color = QColor(45, 45, 45)
    worked_color = QColor(128, 128, 128)
    cluster_expire = pyqtSignal(str)
    message = pyqtSignal(dict)
    date_pattern = r"^\d{2}-[A-Za-z]{3}-\d{4}$"
    wwv_pattern = (
        r"(\d{2}-\w{3}-\d{4})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(.*?)\s+<(\w+)>"
    )
    bandmapwindow_closed = pyqtSignal()

    def __init__(self, action):
        super().__init__()
        self.action = action
        self.active = False
        self._udpwatch = None

        uic.loadUi(fsutils.APP_DATA_PATH / "bandmap.ui", self)
        # self.thefont = QFont()
        # self.thefont.setFamily("JetBrains Mono")
        self.thefont = QFont("JetBrains Mono", 10)
        self.settings = self.get_settings()
        self.clear_spot_olderSpinBox.setValue(
            int(self.settings.get("cluster_expire", 1))
        )
        self.agetime = self.clear_spot_olderSpinBox.value()
        self.clear_spot_olderSpinBox.valueChanged.connect(self.spot_aging_changed)
        self.clearButton.clicked.connect(self.clear_spots)
        pixmapi = QStyle.StandardPixmap.SP_TrashIcon
        icon = self.style().standardIcon(pixmapi)
        self.clearButton.setIcon(icon)
        self.clearmarkedButton.clicked.connect(self.clear_marked)
        self.clearmarkedButton.setIcon(icon)
        self.zoominButton.clicked.connect(self.dec_zoom)
        self.zoomoutButton.clicked.connect(self.inc_zoom)
        self.connectButton.clicked.connect(self.connect)
        self.spots = Database()
        # self.font = QFont("JetBrains Mono ExtraLight", 10)
        self.socket = QtNetwork.QTcpSocket()
        self.socket.readyRead.connect(self.receive)
        self.socket.connected.connect(self.maybeconnected)
        self.socket.disconnected.connect(self.disconnected)
        self.socket.errorOccurred.connect(self.socket_error)
        self.bandmap_scene = BandMapScene(self)
        self.bandmap_scene.setFont(self.thefont)
        self.bandmap_scene.clear()
        self.bandmap_scene.setFocusOnTouch(False)
        self.bandmap_scene.selectionChanged.connect(self.spot_clicked)
        self.freq = 0.0
        self.keepRXCenter = False
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_station_timer)
        self.update_timer.start(UPDATE_INTERVAL)
        self.setDarkMode()
        self.update()
        self.request_workedlist()
        self.request_contest()

    def setActive(self, mode: bool):
        self.active = bool(mode)
        self.request_workedlist()

    def get_settings(self) -> dict:
        """Get the settings."""
        if os.path.exists(fsutils.CONFIG_FILE):
            with open(fsutils.CONFIG_FILE, "rt", encoding="utf-8") as file_descriptor:
                return loads(file_descriptor.read())

    def msg_from_main(self, packet):
        """"""
        if self.active is False or not self.isVisible():
            return
        if packet.get("cmd", "") == "RADIO_STATE":
            target_band_name = packet.get("band", "")
            if len(target_band_name):
                if target_band_name[-1:] == "m":
                    self.set_band(target_band_name, False)
                else:
                    self.set_band(packet.get("band") + "m", False)
            try:
                if self.rx_freq != float(packet.get("vfoa")) / 1000:
                    self.rx_freq = float(packet.get("vfoa")) / 1000
                    self.tx_freq = self.rx_freq
                    self.center_on_rxfreq()
            except ValueError:
                print(f"vfo value error {packet.get('vfoa')}")
                logger.debug(f"vfo value error {packet.get('vfoa')}")
                return
            bw_returned = packet.get("bw", "0")
            if not bw_returned.isdigit():
                bw_returned = "0"
            self.bandwidth = int(bw_returned)
            step, _ = self.determine_step_digits()
            self.drawTXRXMarks(step)
            return
        if packet.get("cmd", "") == "NEXTSPOT" and self.rx_freq:
            spot = self.spots.get_next_spot(self.rx_freq + 0.001, self.currentBand.end)
            if spot:
                cmd = {}
                cmd["cmd"] = "TUNE"
                cmd["freq"] = spot.get("freq", self.rx_freq)
                cmd["spot"] = spot.get("callsign", "")
                self.message.emit(cmd)
            return
        if packet.get("cmd", "") == "PREVSPOT" and self.rx_freq:
            spot = self.spots.get_prev_spot(
                self.rx_freq - 0.001, self.currentBand.start
            )
            if spot:
                cmd = {}
                cmd["cmd"] = "TUNE"
                cmd["freq"] = spot.get("freq", self.rx_freq)
                cmd["spot"] = spot.get("callsign", "")
                self.message.emit(cmd)
            return
        if packet.get("cmd", "") == "SPOTDX":
            dx = packet.get("dx", "")
            freq = packet.get("freq", 0.0)
            spotdx = f"dx {dx} {freq}"
            self.send_command(spotdx)
            return
        if packet.get("cmd", "") == "MARKDX":
            dx = packet.get("dx", "")
            freq = packet.get("freq", 0.0)
            the_UTC_time = datetime.now(timezone.utc).isoformat(" ")[:19].split()[1]
            comment = packet.get("comment", "")
            spot = {
                "ts": "2099-01-01 " + the_UTC_time,
                "callsign": dx,
                "freq": freq,
                "band": self.currentBand.name,
                "mode": "DX",
                "spotter": platform.node(),
                "comment": comment,
            }
            self.spots.addspot(spot, clear_freq=True)
            self.update_stations()
            return

        if packet.get("cmd", "") == "FINDDX":
            dx = packet.get("dx", "")
            spot = self.spots.get_matching_spot(
                dx, self.currentBand.start, self.currentBand.end
            )
            if spot:
                cmd = {}
                cmd["cmd"] = "TUNE"
                cmd["freq"] = spot.get("freq", self.rx_freq)
                cmd["spot"] = spot.get("callsign", "")
                self.message.emit(cmd)
            return
        if packet.get("cmd", "") == "WORKED":
            self.worked_list = packet.get("worked", {})
            logger.debug("%s", f"{self.worked_list}")
            self.update_stations()
            return
        if packet.get("cmd", "") == "CALLCHANGED":
            call = packet.get("call", "")
            if call:
                result = self.spots.get_like_calls(call)
                if result:
                    cmd = {}
                    cmd["cmd"] = "CHECKSPOTS"
                    cmd["spots"] = result
                    self.message.emit(cmd)
                    return
            cmd = {}
            cmd["cmd"] = "CHECKSPOTS"
            cmd["spots"] = []
            self.message.emit(cmd)
            return
        if packet.get("cmd", "") == "CONTESTSTATUS":
            if not self.callsignField.text():
                self.callsignField.setText(packet.get("operator", "").upper())
            return
        if packet.get("cmd", "") == "DARKMODE":
            self.setDarkMode()

    def is_it_dark(self) -> bool:
        """Returns if the DE has a dark theme active."""
        hints = QtGui.QGuiApplication.styleHints()
        scheme = hints.colorScheme()
        return scheme == Qt.ColorScheme.Dark

    def setDarkMode(self):
        """Set dark mode"""

        setdarkmode = self.is_it_dark()
        if setdarkmode is True:
            self.text_color = QColorConstants.White
            self.worked_color = QColor(108, 108, 108)
            self.update()
        else:
            self.text_color = QColorConstants.Black
            self.worked_color = QColor(178, 178, 178)
            self.update()

    def connect(self):
        """Connect to the cluster."""
        if not self.callsignField.text():
            self.callsignField.setFocus()
            return
        if self.connected is True:
            self.close_cluster()
            return
        self.settings = self.get_settings()
        server = self.settings.get("cluster_server", "dxc.nc7j.com")
        port = self.settings.get("cluster_port", 7373)
        logger.info(f"connecting to dx cluster {server} {port}")
        self.socket.connectToHost(server, port)
        self.connectButton.setText("Connecting")
        self.connected = True

    def spot_clicked(self):
        """dunno"""
        items = self.bandmap_scene.selectedItems()
        for item in items:
            if item:
                cmd = {}
                cmd["cmd"] = "TUNE"
                cmd["freq"] = items[0].property("freq")
                cmd["spot"] = items[0].toPlainText().split()[0]
                self.message.emit(cmd)

    def request_workedlist(self):
        """Request worked call list from logger"""
        cmd = {}
        cmd["cmd"] = "GETWORKEDLIST"
        self.message.emit(cmd)

    def request_contest(self):
        """Request active contest from logger"""
        cmd = {}
        cmd["cmd"] = "GETCONTESTSTATUS"
        self.message.emit(cmd)

    def update_station_timer(self):
        """doc"""
        self.update_stations()

    def update(self):
        """doc"""
        try:
            self.update_timer.setInterval(UPDATE_INTERVAL)
        except AttributeError:
            ...
        # if self.active is False:
        #     return
        self.clear_all_callsign_from_scene()
        self.clear_freq_mark(self.rxMark)
        self.clear_freq_mark(self.txMark)
        self.clear_freq_mark(self.bandwidth_mark)
        self.bandmap_scene.clear()
        # self.bandmap_scene.setFont(self.font)
        self.bandmap_scene.setFont(self.thefont)
        step, _digits = self.determine_step_digits()
        steps = int(round((self.currentBand.end - self.currentBand.start) / step)) + 1
        self.graphicsView.setFixedSize(330, steps * PIXELSPERSTEP + 30)
        self.graphicsView.setScene(self.bandmap_scene)
        # self.graphicsView.setFont(self.font)
        self.graphicsView.setFont(self.thefont)
        for i in range(steps):  # Draw tickmarks
            length = 10
            if i % 5 == 0:
                length = 15
            self.bandmap_scene.addLine(
                10,
                i * PIXELSPERSTEP,
                length + 10,
                i * PIXELSPERSTEP,
                QtGui.QPen(self.text_color),
            )
            if i % 5 == 0:  # Add Frequency
                freq = self.currentBand.start + step * i
                # text = f"{freq:.3f}"
                text = "{1:.{0}f}".format(_digits, freq)
                self.something = self.bandmap_scene.addText(text)
                self.something.setFont(self.thefont)
                self.something.setDefaultTextColor(self.text_color)
                self.something.setPos(
                    -(self.something.boundingRect().width()) + 10,
                    i * PIXELSPERSTEP - (self.something.boundingRect().height() / 2),
                )

        freq = self.currentBand.end + step * steps
        endFreqDigits = f"{freq:.1f}"
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
        self.zoom = max(self.zoom, 0)
        self.update()
        self.center_on_rxfreq()

    def drawTXRXMarks(self, step):
        """doc"""
        if self.rx_freq:
            self.clear_freq_mark(self.bandwidth_mark)
            self.clear_freq_mark(self.rxMark)
            self.draw_bandwidth(
                self.rx_freq, step, QColor(30, 30, 180, 180), self.bandwidth_mark
            )
            self.drawfreqmark(self.rx_freq, step, QColor(30, 180, 30, 180), self.rxMark)

    def Freq2ScenePos(self, freq: float):
        """doc"""
        if not freq or freq < self.currentBand.start or freq > self.currentBand.end:
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
        self.scrollArea.verticalScrollBar().setValue(
            int(freq_pos - (self.height() / 2) + 80)
        )

    def drawfreqmark(self, freq, _step, color, currentPolygon) -> None:
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

    def draw_bandwidth(self, freq, _step, color, currentPolygon) -> None:
        """bandwidth"""
        logger.debug("%s", f"mark:{currentPolygon} f:{freq} b:{self.bandwidth}")
        self.clear_freq_mark(currentPolygon)
        if freq < self.currentBand.start or freq > self.currentBand.end:
            return
        if freq and self.bandwidth:
            # color = QColor(30, 30, 180)
            bw_start = Decimal(str(freq)) - ((Decimal(str(self.bandwidth)) / 2) / 1000)
            bw_end = Decimal(str(freq)) + ((Decimal(str(self.bandwidth)) / 2) / 1000)
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
        if self.active is False or not self.isVisible():
            return
        self.clear_all_callsign_from_scene()
        self.spot_aging()
        step, _digits = self.determine_step_digits()

        result = self.spots.getspotsinband(self.currentBand.start, self.currentBand.end)
        logger.debug(
            f"{len(result)} spots in range {self.currentBand.start} - {self.currentBand.end}"
        )

        entity = ""
        if result:
            # ⌾ ⦿ 🗼 ⛯ ⊕ ⊞ ⁙ ⁘ ⁕ ⌖ Ⓟ ✦ 🄿 🄿 Ⓢ 🅂 🏔
            min_y = 0.0
            for items in result:
                flag = " @"
                if "CW" in items.get("comment"):
                    flag = " ○"
                if "NCDXF B" in items.get("comment"):
                    flag = " 🗼"
                if "BCN " in items.get("comment"):
                    flag = " 🗼"
                if "FT8" in items.get("comment"):
                    flag = " ⦿"
                if "FT4" in items.get("comment"):
                    flag = " ⦿"
                if "RTTY" in items.get("comment"):
                    flag = " ⌾"
                if "POTA" in items.get("comment"):
                    flag += "[P]"
                if "SOTA" in items.get("comment"):
                    flag += "[S]"
                
                pen_color = self.text_color
                if "MARKED" in items.get("comment"):
                    setdarkmode = self.is_it_dark()
                    if setdarkmode is True:
                        pen_color = QColor(254, 194, 17)
                    else:
                        pen_color = QColor(0, 160, 0)
                if items.get("callsign") in self.worked_list:
                    call_bandlist = self.worked_list.get(items.get("callsign"))
                    if self.currentBand.altname in call_bandlist:
                        pen_color = self.worked_color
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
                    + flag
                    + entity
                    + " "
                    + items.get("ts").split()[1][:-3]
                )
                text.setFont(self.thefont)
                text.document().setDocumentMargin(0)
                text.setPos(60, text_y - (text.boundingRect().height() / 2))
                text.setFlags(
                    QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
                    | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                    | text.flags()
                )
                text.setProperty("callsign", items.get("callsign"))
                text.setProperty("freq", items.get("freq"))
                text.setToolTip(items.get("comment"))
                text.setDefaultTextColor(pen_color)
                min_y = text_y + text.boundingRect().height() / 2
                self.textItemList.append(text)

    def determine_step_digits(self):
        """doc"""
        return_zoom = {
            0: (0.04, 1),
            1: (0.1, 1),
            2: (0.2, 0),
            3: (0.4, 0),
            4: (1, 0),
            5: (2, 0),
            6: (4, 0),
            7: (10, 0),
        }
        step, digits = return_zoom.get(self.zoom, (0.1, 1))

        if self.currentBand.start >= 28.0 and self.currentBand.start < 420.0:
            step = step * 10
            return (step, digits)

        if self.currentBand.start >= 420.0 and self.currentBand.start < 2300.0:
            step = step * 100

        return (step, digits)

    def set_band(self, band: str, savePrevBandZoom: bool) -> None:
        """Change band being shown."""
        logger.debug("%s", f"{band} {savePrevBandZoom}")
        if band != self.currentBand.name:
            if savePrevBandZoom:
                self.saveCurrentZoom()
            self.currentBand = Band(band)
            self.update()

    def spot_aging(self) -> None:
        """Delete spots older than age time."""
        if self.agetime:
            self.spots.delete_spots(self.agetime)

    def clear_all_callsign_from_scene(self) -> None:
        """Remove callsigns from the scene."""
        for items in self.textItemList:
            self.bandmap_scene.removeItem(items)
        self.textItemList.clear()
        for items in self.lineitemlist:
            self.bandmap_scene.removeItem(items)
        self.lineitemlist.clear()

    def clear_freq_mark(self, currentPolygon) -> None:
        """Remove frequency marks from the scene."""
        if currentPolygon:
            for mark in currentPolygon:
                self.bandmap_scene.removeItem(mark)
        currentPolygon.clear()

    def receive(self) -> None:
        """Process waiting bytes"""
        while self.socket.bytesAvailable():
            data = self.socket.readLine(1000)

            try:
                data = str(data, "utf-8").strip()
            except UnicodeDecodeError:
                continue

            if os.environ.get("SEND_CLUSTER", False) is not False:
                print(f"{data}")

            if (
                "login:" in data.lower()
                or "call:" in data.lower()
                or "callsign:" in data.lower()
            ):
                self.send_command(self.callsignField.text())
                return

            if "password:" in data.lower():
                self.send_command(self.settings.get("cluster_password", ""))
                return

            if "BEACON" in data:
                return

            if "DX de" in data:
                parts = data.split()
                spotter = parts[2]
                freq = parts[3]
                dx = parts[4]
                _time = parts[-1]
                comment = " ".join(parts[5:-1])
                spot = {}
                spot["ts"] = datetime.now(timezone.utc).isoformat(" ")[:19]
                spot["callsign"] = dx
                spot["spotter"] = spotter
                spot["comment"] = comment
                logger.debug(f"{spot}")
                try:
                    spot["freq"] = float(freq)
                    self.spots.addspot(spot)
                except ValueError:
                    logger.debug(f"couldn't parse freq from datablock {data}")
                return

            if "HELLO" in data.upper():
                self.connectButton.setText("Connected")
                self.send_command(self.settings.get("cluster_filter", ""))
                self.send_command("set dx extension Section")
                self.send_command(
                    "set dx mode " + self.settings.get("cluster_mode", "OPEN")
                )
                self.send_command("sh wwv 1")
                logger.debug(f"callsign login acknowledged {data}")

            match = re.search(self.wwv_pattern, data)

            if match:
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

    def maybeconnected(self) -> None:
        """Update visual state of the connect button."""
        self.connectButton.setText("Connecting")

    def socket_error(self) -> None:
        """Oopsie"""
        logger.warning("An Error occurred.")

    def disconnected(self) -> None:
        """Called when socket is disconnected."""
        self.connected = False
        self.connectButton.setText("Closed")

    def send_command(self, cmd: str) -> None:
        """Send a command to the cluster."""
        cmd += "\r\n"
        if os.environ.get("SEND_CLUSTER", False) is not False:
            print(f"{cmd}")
        tosend = bytes(cmd, encoding="ascii")
        logger.debug("Command sent to the cluster")
        if self.socket:
            if self.socket.isOpen():
                self.socket.write(tosend)

    def clear_spots(self) -> None:
        """Delete all spots from the database."""
        self.spots.delete_spots(0)

    def clear_marked(self) -> None:
        """Delete all marked spots."""
        self.spots.delete_marks()

    def spot_aging_changed(self) -> None:
        """Called when spot aging spinbox is changed."""
        self.agetime = self.clear_spot_olderSpinBox.value()
        self.cluster_expire.emit(str(self.agetime))

    def showContextMenu(self) -> None:
        """doc string for the linter"""

    def close_cluster(self) -> None:
        """Close socket connection"""
        if self.socket and self.socket.isOpen():
            logger.info("Closing dx cluster connection")
            self.socket.close()
            self.connected = False
            self.connectButton.setText("Closed")

    def closeEvent(self, _event: QtGui.QCloseEvent) -> None:
        """Triggered when instance closes."""
        self.close_cluster()
        self.action.setChecked(False)
        self.bandmapwindow_closed.emit()
        _event.accept()
