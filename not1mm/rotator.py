from PyQt6.QtWidgets import (
    QDockWidget,
    QGraphicsScene,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
)

from PyQt6.QtGui import (
    QImage,
    QColor,
    QPixmap,
    QPen,
    QBrush,
    QPainterPath,
    QShowEvent,
    QResizeEvent,
    QMouseEvent,
)

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6 import uic

from not1mm.lib.rot_interface import RotatorInterface
import not1mm.fsutils as fsutils
import math
import logging
import os

logger = logging.getLogger(__name__)


class RotatorWindow(QDockWidget):
    message: pyqtSignal = pyqtSignal(dict)
    pref: dict = {}
    MAP_RESOLUTION: int = 600
    GLOBE_RADIUS: float = 100.0
    requestedAzimuthNeedle: QGraphicsPathItem | None = None
    antennaNeedle: QGraphicsPathItem | None = None

    def __init__(self, host: str = "127.0.0.1", port: int = 4533):
        super().__init__()
        self.host = host
        self.port = port
        self.active: bool = False
        self.compassScene: QGraphicsScene | None = None
        self.mygrid: str = "DM13at"
        self.requestedAzimuth: float | None = None
        self.antennaAzimuth: float | None = None
        uic.loadUi(fsutils.APP_DATA_PATH / "rotator.ui", self)
        self.north_button.clicked.connect(self.set_north_azimuth)
        self.south_button.clicked.connect(self.set_south_azimuth)
        self.east_button.clicked.connect(self.set_east_azimuth)
        self.west_button.clicked.connect(self.set_west_azimuth)
        self.move_button.clicked.connect(self.the_eye_of_sauron)
        self.stop_button.clicked.connect(lambda x: self.rotator.send_command("S"))
        self.park_button.clicked.connect(lambda x: self.rotator.send_command("K"))
        self.redrawMap()
        self.rotator: RotatorInterface = RotatorInterface(self.host, self.port)
        self.antennaAzimuth, _ = self.rotator.get_position()
        self.set_antenna_azimuth(self.antennaAzimuth)
        self.watch_timer: QTimer = QTimer()
        self.watch_timer.timeout.connect(self.check_rotator)
        self.watch_timer.start(1000)

    def set_host_port(self, host: str, port: int) -> None:
        """"""
        self.host = host
        self.port = port
        self.rotator.set_host_port(self.host, self.port)
        self.redrawMap()

    def msg_from_main(self, msg: dict) -> None:
        """"""
        if self.active is True and isinstance(msg, dict):
            if msg.get("cmd", "") in ("UPDATELOG", "CONTACTCHANGED", "DELETED"):
                ...
            if msg.get("cmd", "") == "NEWDB":
                ...

    def set_mygrid(self, mygrid: str) -> None:
        """"""
        if isinstance(mygrid, str):
            self.mygrid = mygrid
            self.redrawMap()

    def setActive(self, active: bool) -> None:
        """"""
        if isinstance(active, bool):
            self.active = active

    def set_requested_azimuth(self, azimuth: float) -> None:
        if isinstance(azimuth, float):
            self.requestedAzimuth = azimuth
            self.requestedAzimuthNeedle.setRotation(self.requestedAzimuth)
            self.requestedAzimuthNeedle.show()
        else:
            self.requestedAzimuthNeedle.hide()

    def set_antenna_azimuth(self, azimuth: float) -> None:
        if isinstance(azimuth, float):
            self.antennaAzimuth = azimuth
            self.antennaNeedle.setRotation(self.antennaAzimuth)
            self.antennaNeedle.show()
        else:
            self.antennaNeedle.hide()

    def set_north_azimuth(self) -> None:
        """Point the antenna North."""
        if self.rotator.connected:
            self.rotator.set_position(0.0)

    def set_south_azimuth(self) -> None:
        """Point the antenna South."""
        if self.rotator.connected:
            self.rotator.set_position(180.0)

    def set_east_azimuth(self) -> None:
        """Point the antenna East."""
        if self.rotator.connected:
            self.rotator.set_position(90.0)

    def set_west_azimuth(self) -> None:
        """Point the antenna West."""
        if self.rotator.connected:
            self.rotator.set_position(270.0)

    def the_eye_of_sauron(self) -> None:
        """Move the antennas azimuth to match the contacts."""
        if self.rotator.connected:
            self.rotator.set_position(self.requestedAzimuth)

    def redrawMap(self) -> None:
        """"""
        self.compassScene: QGraphicsScene = QGraphicsScene()
        self.compassView.setScene(self.compassScene)
        self.compassView.setStyleSheet("background-color: transparent;")
        file = fsutils.APP_DATA_PATH / "map3.png"
        source: QImage = QImage()
        source.load(str(file))
        the_map: QImage = QImage(
            self.MAP_RESOLUTION, self.MAP_RESOLUTION, QImage.Format.Format_ARGB32
        )
        the_map.fill(QColor(0, 0, 0, 0))
        lat, lon = self.gridtolatlon(self.mygrid)

        if os.path.exists(f"{fsutils.USER_DATA_PATH}/{self.mygrid}v2.png"):
            the_map.load(f"{fsutils.USER_DATA_PATH}/{self.mygrid}v2.png")
        else:
            the_map = self.equirectangular_to_azimuthal_equidistant(
                source, lat, lon, output_size=self.MAP_RESOLUTION
            )

        pixMapItem: QGraphicsPixmapItem | None = self.compassScene.addPixmap(
            QPixmap.fromImage(the_map)
        )
        if pixMapItem is None:
            logging.error("Unable to add pixmap to scene")
        else:
            pixMapItem.moveBy(-self.MAP_RESOLUTION / 2, -self.MAP_RESOLUTION / 2)
            pixMapItem.setTransformOriginPoint(
                self.MAP_RESOLUTION / 2, self.MAP_RESOLUTION / 2
            )
            pixMapItem.setScale(self.GLOBE_RADIUS * 2 / self.MAP_RESOLUTION)
        self.compassScene.addEllipse(
            -100,
            -100,
            self.GLOBE_RADIUS * 2,
            self.GLOBE_RADIUS * 2,
            QPen(QColor(100, 100, 100)),
            QBrush(QColor(0, 0, 0), Qt.BrushStyle.NoBrush),
        )
        self.compassScene.addEllipse(
            -1,
            -1,
            2,
            2,
            QPen(Qt.PenStyle.NoPen),
            QBrush(QColor(0, 0, 0), Qt.BrushStyle.SolidPattern),
        )
        path: QPainterPath = QPainterPath()
        path.lineTo(-4, 0)
        path.lineTo(0, -90)
        path.lineTo(4, 0)
        path.closeSubpath()

        # path2: QPainterPath = QPainterPath()
        # path2.lineTo(-1, 0)
        # path2.lineTo(0, -90)
        # path2.lineTo(1, 0)
        # path2.closeSubpath()

        self.requestedAzimuthNeedle: QGraphicsPathItem | None = (
            self.compassScene.addPath(
                path,
                QPen(QColor(0, 0, 0, 150)),
                QBrush(QColor(0, 0, 255), Qt.BrushStyle.SolidPattern),
            )
        )

        if (
            isinstance(self.requestedAzimuth, float)
            and self.requestedAzimuthNeedle is not None
        ):
            self.requestedAzimuthNeedle.setRotation(self.requestedAzimuth)
            self.requestedAzimuthNeedle.show()
        else:
            self.requestedAzimuthNeedle.hide()

        self.antennaNeedle: QGraphicsPathItem | None = self.compassScene.addPath(
            path,
            QPen(QColor(0, 0, 0, 150)),
            QBrush(QColor(255, 191, 0), Qt.BrushStyle.SolidPattern),
        )
        if isinstance(self.antennaAzimuth, float) and self.antennaNeedle is not None:
            self.antennaNeedle.setRotation(self.antennaAzimuth)
            self.antennaNeedle.show()
        else:
            self.antennaNeedle.hide()

    def gridtolatlon(self, maiden: str) -> tuple[float, float]:
        """
        Converts a maidenhead gridsquare to a latitude longitude pair.
        """
        try:
            maiden: str = str(maiden).strip().upper()

            chars_in_grid_square: int = len(maiden)
            if not 8 >= chars_in_grid_square >= 2 and chars_in_grid_square % 2 == 0:
                return 0.0, 0.0
            lon = (ord(maiden[0]) - 65) * 20 - 180
            lat = (ord(maiden[1]) - 65) * 10 - 90
            if chars_in_grid_square >= 4:
                lon += (ord(maiden[2]) - 48) * 2
                lat += (ord(maiden[3]) - 48) * 1
                if chars_in_grid_square >= 6:
                    lon += (ord(maiden[4]) - 65) * (5.0 / 60.0)
                    lat += (ord(maiden[5]) - 65) * (2.5 / 60.0)
                    if chars_in_grid_square >= 8:
                        lon += (ord(maiden[6]) - 48) * (30.0 / 3600.0)
                        lat += (ord(maiden[7]) - 48) * (15.0 / 3600.0)
                        lon += 15.0 / 3600.0
                        lat += 7.5 / 3600.0
                    else:
                        lon += 2.5 / 60.0
                        lat += 1.25 / 60.0
                else:
                    lon += 1
                    lat += 0.5
            else:
                lon += 10
                lat += 5

            return float(lat), float(lon)
        except IndexError:
            return 0.0, 0.0

    def equirectangular_to_azimuthal_equidistant(
        self,
        source_img: QImage,
        center_lat_deg: float,
        center_lon_deg: float,
        output_size: int = 600,
    ) -> QImage:
        """This does some super magic"""

        width, height = source_img.width(), source_img.height()
        dest_img: QImage = QImage(output_size, output_size, QImage.Format.Format_ARGB32)

        # Convert center point to radians
        lat0: float = math.radians(center_lat_deg)
        lon0: float = math.radians(center_lon_deg)

        sin_lat: float = math.sin(lat0)
        cos_lat: float = math.cos(lat0)

        R: float = output_size / 2
        for y in range(output_size):
            for x in range(output_size):
                # Convert pixel coordinate to normalized cartesian coordinate in range [-1, 1]
                dx = (x - R) / R
                dy = (R - y) / R  # Invert Y axis to have +Y upwards

                rho = math.sqrt(dx * dx + dy * dy)
                if rho > 1.0:
                    # Outside the projection circle
                    dest_img.setPixelColor(x, y, QColor(0, 0, 0, 0))
                    continue

                c = (
                    rho * math.pi
                )  # scale rho to angular distance (c = great-circle distance)

                if rho == 0:
                    lat = lat0
                    lon = lon0
                else:
                    sin_c = math.sin(c)
                    cos_c = math.cos(c)

                    lat = math.asin(cos_c * sin_lat + (dy * sin_c * cos_lat / rho))

                    lon = lon0 + math.atan2(
                        dx * sin_c,
                        rho * cos_lat * cos_c - dy * sin_lat * sin_c,
                    )

                # Map lat/lon to source image pixel coordinates (equirectangular)
                lon_deg = math.degrees(lon)
                lat_deg = math.degrees(lat)

                # Wrap longitude to [-180, 180]
                if lon_deg < -180:
                    lon_deg += 360
                elif lon_deg > 180:
                    lon_deg -= 360

                # Map to source image coordinates
                src_x = int(((lon_deg + 180.0) / 360.0) * width)
                src_y = int(((90 - lat_deg) / 180.0) * height)

                # Clamp coordinates
                src_x = max(0, min(width - 1, src_x))
                src_y = max(0, min(height - 1, src_y))

                color = source_img.pixelColor(src_x, src_y)
                dest_img.setPixelColor(x, y, color)

        dest_img.save(f"{fsutils.USER_DATA_PATH}/{self.mygrid}v2.png", "PNG")
        return dest_img

    def showEvent(self, event: QShowEvent) -> None:
        """Make the globe fit in the widget when widget is shown."""
        self.compassView.fitInView(
            self.compassScene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Make globe fit in widget when widget is resized."""
        self.compassView.fitInView(
            self.compassScene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Catch mouse clicks in the widget"""
        if event.button() == Qt.MouseButton.LeftButton:
            clickPos = self.compassView.mapToScene(
                self.compassView.mapFromGlobal(event.globalPosition().toPoint())
            )
            dx: float = clickPos.x()
            dy: float = -1 * clickPos.y()
            if math.sqrt(math.pow(dx, 2) + math.pow(dy, 2)) <= self.GLOBE_RADIUS:

                angle: float = math.degrees(math.atan2(dx, dy))

                if angle < 0:
                    angle += 360

                self.rotator.set_position(angle)

    def check_rotator(self) -> None:
        """Check the rotator"""
        if self.rotator.connected:
            self.antennaAzimuth, _ = self.rotator.get_position()
            self.set_antenna_azimuth(self.antennaAzimuth)
        else:
            self.rotator.connect()
