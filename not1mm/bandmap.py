#!/usr/bin/env python3
"""
not1mm Contest logger
Email: michael.bridak@gmail.com
GPL V3
Class: BandMapWindow
Purpose: Onscreen widget to show realtime spots from an AR cluster.
"""

import logging
import platform
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QDockWidget, QStyle

from not1mm import fsutils
from not1mm.lib.ham_utility import band2banddef, khz2banddef
from not1mm.lib.i18n import load_ui
from not1mm.lib.preferences import Preferences

# from not1mm.lib.multicast import Multicast

logger = logging.getLogger(__name__)

PIXELSPERSTEP = 10
UPDATE_INTERVAL = 2000
CLEAR_FREQ = 0.1  # 100 Hz


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
            band = band2banddef(spot.get("band", ""), unknown_band=True)
        else:
            band = khz2banddef(spot.get("freq"), unknown_band=True)

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
                clear_freq_q = "delete from spots where freq between ? and ?"
                if "MARKED" not in spot.get("comment", ""):
                    clear_freq_q += " and comment not like '%MARKED%'"
                clear_freq_q += ";"
                self.cursor.execute(
                    clear_freq_q,
                    (spot.get("freq") - CLEAR_FREQ, spot.get("freq") + CLEAR_FREQ),
                )

            self.cursor.execute(
                "INSERT INTO spots(callsign, ts, freq, mode, spotter, comment) VALUES(?, ?, ?, ?, ?, ?)",
                (
                    spot["callsign"],
                    spot.get(
                        "ts",
                        datetime.now(UTC).replace(second=0, microsecond=0, tzinfo=None),
                    ),
                    spot["freq"],
                    spot.get("mode", None),
                    spot.get("spotter", platform.node()),
                    spot.get("comment", ""),
                ),
            )
            self.db.commit()
        except sqlite3.IntegrityError:
            ...

    def markspot(self, spot: dict, clear_freq=False) -> None:
        "..."
        print(f"{spot=}")
        the_UTC_time = datetime.now(UTC).isoformat(" ")[:19].split()[1]
        ts = "2099-01-01 " + the_UTC_time
        try:
            self.cursor.execute(
                f"update spots set ts='{ts}', comment='{spot.get('comment', '')}' where freq='{spot.get('freq', '')}' and callsign='{spot.get('callsign', '')}';"
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
            "delete from spots where callsign = ? and freq = ?", (call, freq)
        )
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
            "delete from spots where ts < datetime('now', ?) and comment not like '%MARKED%';",
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
            menu.addAction(
                "Confirm",
                lambda: self.parent.spots.addspot(
                    {
                        "callsign": callsign,
                        "freq": freq,
                        "comment": comment,
                    },
                    True,
                ),
            )
            if "MARKED" in comment:
                menu.addAction(
                    "Unmark",
                    lambda: self.parent.spots.addspot(
                        {
                            "callsign": callsign,
                            "freq": freq,
                            "comment": comment.replace("MARKED", ""),
                        },
                        True,
                    ),
                )
            else:
                menu.addAction(
                    "Mark",
                    lambda: self.parent.spots.markspot(
                        {
                            "callsign": callsign,
                            "freq": freq,
                            "comment": comment + " MARKED",
                        },
                        True,
                    ),
                )
            menu.addAction(
                "Delete", lambda: self.parent.spots.delete_spot(callsign, freq)
            )
            menu.exec(event.screenPos())
        else:
            super().contextMenuEvent(event)


class BandMapWindow(QDockWidget):
    """The BandMapWindow class."""

    default_zoom = 5
    zoom_levels = [  # kHz per tick, decimal digits  # noqa: RUF012
        (0.04, 1),
        (0.1, 1),
        (0.2, 0),
        (0.4, 0),
        (1, 0),
        (2, 0),  # default level (index 5)
        (4, 0),
        (10, 0),
    ]
    currentBand = band2banddef("20m")
    txMark = []  # noqa: RUF012
    rxMark = []  # noqa: RUF012
    rx_freq = None
    something = None
    lineitemlist = []  # noqa: RUF012
    textItemList = []  # noqa: RUF012
    connected = False
    test_for_data = None
    bandwidth = 0
    bandwidth_mark = []  # noqa: RUF012
    worked_list = {}  # noqa: RUF012
    multicast_interface = None
    text_color = QColor(45, 45, 45)
    worked_color = QColor(128, 128, 128)

    dark_text_color = QColor(205, 214, 244)  # Catppuccin Mocha Text
    dark_worked_color = QColor(108, 112, 134)  # Catppuccin Mocha Overlay0
    dark_marked_color = QColor(249, 226, 175)  # Catppuccin Mocha Yellow

    light_text_color = QColor(76, 79, 105)  # Catppuccin Latte Text
    light_worked_color = QColor(156, 160, 176)  # Catppuccin Latte Overlay0
    light_marked_color = QColor(223, 142, 29)  # Catppuccin Latte Yellow
    cluster_expire = pyqtSignal(str)
    message = pyqtSignal(dict)
    bandmapwindow_closed = pyqtSignal()

    def __init__(self, action):
        super().__init__()
        self.action = action
        self.active = False
        self._udpwatch = None

        load_ui(self, fsutils.APP_DATA_PATH / "bandmap.ui")
        # self.thefont = QFont("JetBrains Mono", 10, QFont.Weight.Thin)
        self.thefont = QFont("JetBrains Mono", 10)
        self.settings = Preferences.data()
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
        self.zoominButton.clicked.connect(self.zoom_in)
        self.zoomoutButton.clicked.connect(self.zoom_out)
        self.spots = Database()
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

    def setActive(self, mode: bool):
        self.active = bool(mode)
        self.request_workedlist()

    def msg_from_main(self, packet):
        """Process messages from the main screen."""
        if self.active is False or not self.isVisible():
            return
        if packet.get("cmd", "") == "RADIO_STATE":
            self.set_band(packet.get("band", ""))
            try:
                if self.rx_freq != float(packet.get("vfoa")) / 1000:
                    self.rx_freq = float(packet.get("vfoa")) / 1000
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

        if packet.get("cmd", "") == "DX":
            spot = packet
            spot["callsign"] = packet.get("dx", "")  # rename field
            self.spots.addspot(spot, clear_freq=True)
            self.update_stations()
            return
        if packet.get("cmd", "") == "MARKDX":
            dx = packet.get("dx", "")
            freq = packet.get("freq", 0.0)
            the_UTC_time = datetime.now(UTC).isoformat(" ")[:19].split()[1]
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
            self.text_color = self.dark_text_color
            self.worked_color = self.dark_worked_color
            self.update()
        else:
            self.text_color = self.light_text_color
            self.worked_color = self.light_worked_color
            self.update()

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
        self.setWindowTitle(f"BandMap: {self.currentBand.name}")
        self.clear_all_callsign_from_scene()
        self.clear_freq_mark(self.rxMark)
        self.clear_freq_mark(self.txMark)
        self.clear_freq_mark(self.bandwidth_mark)
        self.bandmap_scene.clear()
        # self.bandmap_scene.setFont(self.font)
        self.bandmap_scene.setFont(self.thefont)
        step, _digits = self.determine_step_digits()
        steps = round((self.currentBand.end - self.currentBand.start) / step) + 1
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

    def zoom_out(self):
        """The zoom out button was clicked"""
        zoom = self.settings.get("bandmap_zoom", self.default_zoom) + 1
        zoom = min(zoom, len(self.zoom_levels) - 1)  # clamp to valid values
        self.settings["bandmap_zoom"] = zoom
        self.update()
        self.center_on_rxfreq()

    def zoom_in(self):
        """The zoom in button was clicked"""
        zoom = self.settings.get("bandmap_zoom", self.default_zoom) - 1
        zoom = max(zoom, 0)  # clamp to valid values
        self.settings["bandmap_zoom"] = zoom
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
                        pen_color = self.dark_marked_color
                    else:
                        pen_color = self.light_marked_color
                if items.get("callsign") in self.worked_list:
                    call_bandlist = self.worked_list.get(items.get("callsign"))
                    if self.currentBand.band_mhz in call_bandlist:
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
        zoom = self.settings.get("bandmap_zoom", self.default_zoom)
        zoom = max(0, min(zoom, len(self.zoom_levels) - 1))
        step, digits = self.zoom_levels[zoom]

        if self.currentBand.start >= 50_000.0 and self.currentBand.start < 420_000.0:
            step = step * 10
            digits = 0
        elif (
            self.currentBand.start >= 420_000.0 and self.currentBand.start < 2300_000.0
        ):
            step = step * 100
            digits = 0

        return (step, digits)

    def set_band(self, band: str) -> None:
        """Change band being shown."""
        if band and band != self.currentBand.name:
            self.currentBand = band2banddef(band, unknown_band=True)
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

    def closeEvent(self, _event: QtGui.QCloseEvent) -> None:
        """Triggered when instance closes."""
        self.action.setChecked(False)
        self.bandmapwindow_closed.emit()
        _event.accept()
