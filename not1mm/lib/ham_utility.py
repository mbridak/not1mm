"""A sad collection of maybe useful things."""

import logging
import socket
import re
from datetime import datetime
from math import asin, atan2, cos, pi, radians, sin, sqrt

logger = logging.getLogger("__main__")


def calculate_wpx_prefix(the_call: str) -> str:
    """Calculate a WPX Prefix"""
    if not the_call:
        return ""
    if the_call in ["OPON", "CW", "SSB", "RTTY"]:
        return ""
    suffix_to_ignore = ["M", "MM", "P", "QRP", "A", "LH", "NLD"]
    result = None
    working_call = the_call.split("/")
    if len(working_call) > 1:
        result = min(working_call, key=len)
        if not result.isnumeric():
            if result not in suffix_to_ignore:
                if any(chr.isdigit() for chr in result):
                    return result
                return result + "0"

    working_call = max(working_call, key=len)
    last_digit = re.match(".+([0-9])[^0-9]*$", working_call)
    position = last_digit.start(1)
    prefix = working_call[: position + 1]
    if not result:
        return prefix
    return prefix[:-1] + result


def gridtolatlon(maiden):
    """
    Converts a maidenhead gridsquare to a latitude longitude pair.
    """
    try:
        maiden = str(maiden).strip().upper()

        chars_in_grid_square = len(maiden)
        if not 8 >= chars_in_grid_square >= 2 and chars_in_grid_square % 2 == 0:
            return 0, 0

        lon = (ord(maiden[0]) - 65) * 20 - 180
        lat = (ord(maiden[1]) - 65) * 10 - 90

        if chars_in_grid_square >= 4:
            lon += (ord(maiden[2]) - 48) * 2
            lat += ord(maiden[3]) - 48

        if chars_in_grid_square >= 6:
            lon += (ord(maiden[4]) - 65) / 12 + 1 / 24
            lat += (ord(maiden[5]) - 65) / 24 + 1 / 48

        if chars_in_grid_square >= 8:
            lon += (ord(maiden[6])) * 5.0 / 600
            lat += (ord(maiden[7])) * 2.5 / 600

        logger.debug("lat:%d lon:%d", lat, lon)
        return round(lat, 4), round(lon, 4)
    except IndexError:
        return 0, 0


def getband(freq: str) -> str:
    """
    Convert a (string) frequency into a (string) band.
    Returns a (string) band.
    Returns a "0" if frequency is out of band.
    """
    # logger.info("getband: %s %s", type(freq), freq)
    if freq.isnumeric():
        frequency = int(float(freq))
        if 2000000 > frequency > 1800000:
            return "160"
        if 4000000 > frequency > 3500000:
            return "80"
        if 5406000 > frequency > 5330000:
            return "60"
        if 7300000 > frequency > 7000000:
            return "40"
        if 10150000 > frequency > 10100000:
            return "30"
        if 14350000 > frequency > 14000000:
            return "20"
        if 18168000 > frequency > 18068000:
            return "17"
        if 21450000 > frequency > 21000000:
            return "15"
        if 24990000 > frequency > 24890000:
            return "12"
        if 29700000 > frequency > 28000000:
            return "10"
        if 54000000 > frequency > 50000000:
            return "6"
        if 148000000 > frequency > 144000000:
            return "2"
        if 225000000 > frequency > 222000000:
            return "222"
        if 450000000 > frequency > 420000000:
            return "432"
    return "0"


def get_logged_band(freq: str) -> str:
    """
    Convert a (string) frequency into a (string) band.
    Returns a (string) band.
    Returns a "0" if frequency is out of band.
    """

    if freq.isnumeric():
        frequency = int(float(freq))
        if 2000000 > frequency > 1800000:
            return "1.8"
        if 4000000 > frequency > 3500000:
            return "3.5"
        if 5406000 > frequency > 5330000:
            return "5"
        if 7300000 > frequency > 7000000:
            return "7"
        if 10150000 > frequency > 10100000:
            return "10"
        if 14350000 > frequency > 14000000:
            return "14"
        if 18168000 > frequency > 18068000:
            return "18"
        if 21450000 > frequency > 21000000:
            return "21"
        if 24990000 > frequency > 24890000:
            return "24"
        if 29700000 > frequency > 28000000:
            return "28"
        if 54000000 > frequency > 50000000:
            return "50"
        if 148000000 > frequency > 144000000:
            return "144"
        if 225000000 > frequency > 222000000:
            return "222"
        if 450000000 > frequency > 420000000:
            return "430"
    return "0"


def fakefreq(band, mode):
    """
    If unable to obtain a frequency from the rig,
    This will return a sane value for a frequency mainly for the cabrillo and adif log.
    Takes a band and mode as input and returns freq in khz.
    """
    # logger.info("fakefreq: band:%s mode:%s", band, mode)
    modes = {"CW": 0, "DG": 1, "PH": 2, "FT8": 1, "SSB": 2}
    fakefreqs = {
        "160": ["1830", "1805", "1840"],
        "80": ["3530", "3559", "3970"],
        "60": ["5332", "5373", "5405"],
        "40": ["7030", "7040", "7250"],
        "30": ["10130", "10130", "0000"],
        "20": ["14030", "14070", "14250"],
        "17": ["18080", "18100", "18150"],
        "15": ["21065", "21070", "21200"],
        "12": ["24911", "24920", "24970"],
        "10": ["28065", "28070", "28400"],
        "6": ["50030", "50300", "50125"],
        "2": ["144030", "144144", "144250"],
        "222": ["222100", "222070", "222100"],
        "432": ["432070", "432200", "432100"],
        "SAT": ["144144", "144144", "144144"],
    }
    freqtoreturn = fakefreqs[band][modes[mode]]
    # logger.info("fakefreq: returning:%s", freqtoreturn)
    return freqtoreturn


def has_internet():
    """
    Connect to a main DNS server to check connectivity.
    """
    try:
        socket.create_connection(("1.1.1.1", 53))
        return True
    except OSError:
        pass
    return False


def update_time() -> None:
    """
    Update local and UTC time on screen.
    """
    _now = datetime.now().isoformat(" ")[5:19].replace("-", "/")
    _utcnow = datetime.utcnow().isoformat(" ")[1:19]
    # self.localtime.setText(now)
    # self.utctime.setText(utcnow)
    return _utcnow


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    # convert degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    aye = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    cee = 2 * asin(sqrt(aye))
    arrgh = 6372.8  # Radius of earth in kilometers.
    return cee * arrgh


def bearing(grid1: str, grid2: str) -> float:
    """
    Calculate bearing to contact
    Takes Yourgrid, Theirgrid, returns a float
    """
    lat1, lon1 = gridtolatlon(grid1)
    lat2, lon2 = gridtolatlon(grid2)
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)
    londelta = lon2 - lon1
    why = sin(londelta) * cos(lat2)
    exs = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(londelta)
    brng = atan2(why, exs)
    brng *= 180 / pi

    if brng < 0:
        brng += 360

    return round(brng)


def reciprocol(heading):
    """return back of the beam heading"""
    heading += 180
    if heading > 360:
        heading -= 360
    return heading


def bearing_with_latlon(grid1: str, lat2: float, lon2: float) -> float:
    """
    Calculate bearing to contact
    Takes Yourgrid, Theirgrid, returns a float
    """
    lat1, lon1 = gridtolatlon(grid1)
    logger.debug("lat1:%d lon1:%d lat2:%d lon2:%d", lat1, lon1, lat2, lon2)
    # lat2, lon2 = gridtolatlon(grid2)
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)
    londelta = lon2 - lon1
    why = sin(londelta) * cos(lat2)
    exs = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(londelta)
    brng = atan2(why, exs)
    brng *= 180 / pi

    if brng < 0:
        brng += 360

    return round(brng)


def distance(grid1: str, grid2: str) -> float:
    """
    Takes two maidenhead gridsquares and returns the distance between the two in kilometers.
    """
    lat1, lon1 = gridtolatlon(grid1)
    lat2, lon2 = gridtolatlon(grid2)
    return round(haversine(lon1, lat1, lon2, lat2))


def distance_with_latlon(grid1: str, lat2: float, lon2: float) -> float:
    """
    Takes two maidenhead gridsquares and returns the distance between the two in kilometers.
    """
    lat1, lon1 = gridtolatlon(grid1)
    logger.debug("lat1:%d lon1:%d lat2:%d lon2:%d", lat1, lon1, lat2, lon2)
    # lat2, lon2 = gridtolatlon(grid2)
    return round(haversine(lon1, lat1, lon2, lat2))
