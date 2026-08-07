"""A sad collection of maybe useful things."""

import logging
import re
import socket
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from math import asin, atan2, cos, pi, radians, sin, sqrt

logger = logging.getLogger("ham_utility")


def calculate_wpx_prefix(the_call: str) -> str:
    """Calculate a WPX Prefix"""
    if not the_call:
        return ""
    if the_call in ["OPON", "CW", "SSB", "RTTY"]:
        return ""
    suffix_to_ignore = [
        "M",
        "MM",
        "P",
        "QRP",
        "A",
        "J",
        "LH",
        "LGT",
        "LS",
        "NLD",
        "T",
        "R",
        "TR",
    ]
    for suffix in suffix_to_ignore:
        the_call = re.sub("/" + suffix + "$", "", the_call)
    result = None
    working_call = the_call.split("/")
    if len(working_call) > 1:
        result = min(working_call, key=len)
        if not result.isnumeric():
            if any(chr.isdigit() for chr in result):
                return result
            return result + "0"

    working_call = max(working_call, key=len)
    last_digit = re.match(".+([0-9])[^0-9]*$", working_call)
    if last_digit is None:
        return working_call[0:2] + "0"
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


@dataclass(frozen=True)
class BandDef:
    """A radio amateur band.

    band_mhz is the canonical DXLOG.Band value (independent of band edges).
    """

    start: float  # kHz
    end: float  # kHz
    name: str  # "40m", "13cm"
    band_mhz: float
    cw_khz: int
    digi_khz: int
    ssb_khz: int


BANDS: tuple[BandDef, ...] = (
    #       start (kHz)     end (kHz)      name      band_mhz  cw_khz     digi_khz   ssb_khz
    #       -------------  --------------  --------  --------  ---------  ---------  ---------
    BandDef(        135.7,          137.8,  "2190m",     0.137,         0,         0,         0),
    BandDef(        472.0,          479.0,   "630m",     0.472,         0,         0,         0),
    BandDef(        501.0,          504.0,   "560m",     0.502,         0,         0,         0),
    BandDef(      1_800.0,        2_000.0,   "160m",       1.8,      1830,      1805,      1840),
    BandDef(      3_500.0,        4_000.0,    "80m",       3.5,      3530,      3559,      3970),
    BandDef(      5_060.0,        5_450.0,    "60m",       5.0,      5332,      5373,      5405),
    BandDef(      7_000.0,        7_300.0,    "40m",       7.0,      7030,      7040,      7250),
    BandDef(     10_100.0,       10_150.0,    "30m",      10.0,    10_130,    10_130,    10_130),
    BandDef(     14_000.0,       14_350.0,    "20m",      14.0,    14_030,    14_070,    14_250),
    BandDef(     18_068.0,       18_168.0,    "17m",      18.0,    18_080,    18_100,    18_150),
    BandDef(     21_000.0,       21_450.0,    "15m",      21.0,    21_065,    21_070,    21_200),
    BandDef(     24_890.0,       24_990.0,    "12m",      24.0,    24_911,    24_920,    24_970),
    BandDef(     28_000.0,       29_700.0,    "10m",      28.0,    28_065,    28_070,    28_400),
    BandDef(     40_000.0,       45_000.0,     "8m",      40.0,         0,         0,         0),
    BandDef(     50_000.0,       54_000.0,     "6m",      50.0,    50_030,    50_300,    50_125),
    BandDef(     54_000.0,       69_900.0,     "5m",      54.0,         0,         0,         0),
    BandDef(     70_000.0,       71_000.0,     "4m",      70.0,    70_030,    70_300,    70_125),
    BandDef(    144_000.0,      148_000.0,     "2m",     144.0,   144_030,   144_144,   144_250),
    BandDef(    222_000.0,      225_000.0,  "1.25m",     222.0,   222_100,   222_070,   222_100),
    BandDef(    420_000.0,      450_000.0,   "70cm",     432.0,   432_070,   432_200,   432_100),
    BandDef(    902_000.0,      928_000.0,   "33cm",     902.0,   902_100,   902_100,   902_100),
    BandDef(  1_240_000.0,    1_300_000.0,   "23cm",    1296.0, 1_296_100, 1_296_100, 1_296_100),
    BandDef(  2_300_000.0,    2_450_000.0,   "13cm",    2300.0,         0,         0,         0),
    BandDef(  3_300_000.0,    3_500_000.0,    "9cm",    3300.0,         0,         0,         0),
    BandDef(  5_650_000.0,    5_925_000.0,    "6cm",    5650.0,         0,         0,         0),
    BandDef( 10_000_000.0,   10_500_000.0,    "3cm",  10_000.0,         0,         0,         0),
    BandDef( 24_000_000.0,   24_250_000.0, "1.25cm",  24_000.0,         0,         0,         0),
    BandDef( 47_000_000.0,   47_200_000.0,    "6mm",  47_000.0,         0,         0,         0),
    BandDef( 75_500_000.0,   81_000_000.0,    "4mm",  75_500.0,         0,         0,         0),
    BandDef(119_980_000.0,  123_000_000.0,  "2.5mm", 119_980.0,         0,         0,         0),
    BandDef(134_000_000.0,  149_000_000.0,    "2mm", 134_000.0,         0,         0,         0),
    BandDef(241_000_000.0,  250_000_000.0,    "1mm", 241_000.0,         0,         0,         0),
    BandDef(300_000_000.0, 7500_000_000.0,  "submm", 300_000.0,         0,         0,         0),
)  # fmt: skip

_UNKNOWN_BAND = BandDef(0.0, 1.0, "unknown", 0.0, 0, 0, 0)
_BY_BAND_NAME: dict[str, BandDef] = {b.name: b for b in BANDS}
_BY_BAND_MHZ: dict[float, BandDef] = {b.band_mhz: b for b in BANDS}


def khz2banddef(freq_khz: Decimal, unknown_band=False) -> BandDef | None:
    """Convert a frequency in kHz into a BandDef.

    Returns None if the frequency is out of band unless unknown_band is True,
    then returns _UNKNOWN_BAND (a 1 kHz window at 0 Hz).
    """
    for b in BANDS:
        if b.start <= freq_khz < b.end:
            return b
    if unknown_band:
        return _UNKNOWN_BAND
    return None


def band2banddef(band_name: str, unknown_band=False) -> BandDef | None:
    """Look up band data for a given band name."""
    if band := _BY_BAND_NAME.get(band_name):
        return band
    if unknown_band:
        return _UNKNOWN_BAND
    return None


def getband(freq_hz: str) -> str:
    """Convert a (string) frequency in Hz into a band name.

    Returns "" if the frequency is out of band.
    """
    band = khz2banddef(Decimal(freq_hz) / 1000)
    if band:
        return band.name
    return ""


def get_logged_band(freq_hz: str) -> str:
    """Convert a (string) frequency in Hz into a band_mhz (canonical DXLOG value).

    Returns "0.0" if the frequency is out of band.
    """
    band = khz2banddef(Decimal(freq_hz) / 1000)
    if band:
        return str(band.band_mhz)
    return "0.0"


def get_adif_band(freq_mhz: Decimal) -> str:
    """Convert a frequency in MHz into a band name.

    Returns "" if the frequency is out of band.
    """
    band = khz2banddef(freq_mhz * 1000)
    if band:
        return band.name
    return ""


def get_not1mm_band(band: str) -> float:
    """Convert band name into band_mhz (canonical DXLOG value).

    Returns 0.0 if the band is unknown.
    """
    b = _BY_BAND_NAME.get(band)
    return b.band_mhz if b else 0.0


def fakefreq(band_name: str, mode: str) -> str:
    """Return a sensible kHz-as-string frequency for cabrillo/ADIF when the rig is offline.

    Looks up by ADIF band name (e.g., "20m"). Returns "" if band name is unknown
    or the band has no fakefreq (cw_khz == 0). Unknown modes default to CW.
    """
    b = _BY_BAND_NAME.get(band_name)
    if b is None or b.cw_khz == 0:
        return ""
    mode_idx = {"CW": 0, "RTTY": 1, "DG": 1, "PH": 2, "FT8": 1, "SSB": 2}.get(mode, 0)
    return [str(b.cw_khz), str(b.digi_khz), str(b.ssb_khz)][mode_idx]


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
    Returns UTC time '2026-07-29 18:30:53'
    """
    # _now = datetime.now(tz=datetime.UTC).isoformat(" ")[5:19].replace("-", "/")
    _utcnow = datetime.now(datetime.UTC).isoformat(" ")[0:19]
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


def reciprocal(heading):
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


def parse_udc(filename: str) -> dict:
    """
    simply parses a n1mm style udc file and returns a dict with key value pairs.
    """

    udc_contest = {}
    the_good_stuff = False

    try:
        with open(filename, "r", encoding="utf-8") as file_descriptor:
            for line in file_descriptor:
                if "[CONTEST]" in line.upper():
                    the_good_stuff = True
                    continue
                if "=" in line and the_good_stuff is True:
                    try:
                        key, value = line.split("=")
                        udc_contest[key.strip()] = value.strip()
                    except ValueError:
                        ...
    except FileNotFoundError:
        logger.debug("UDC file not found.")
        return {}
    return udc_contest
