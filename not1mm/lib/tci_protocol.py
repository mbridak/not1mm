"""
TCI protocol helpers: frame parsing, command building, mode translation.
Email: michael.bridak@gmail.com
GPL V3

Pure functions only -- no sockets, no Qt, no not1mm state. The fiddly string
handling lives here so it stays testable without a running SDR.
"""

import logging

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("tci_protocol")

# TCI modulation names are lowercase and do not match not1mm's conventions.
# Radio.cw_list / Radio.rtty_list (not1mm/radio.py:36-42) match the output of
# get_mode_list() by exact string, so everything is normalized to not1mm's
# uppercase names on the way in.
# Verified against a live AetherSDR handshake on 2026-08-01; see
# docs/superpowers/specs/2026-08-01-tci-handshake.md. AetherSDR reports:
#   modulations_list:usb,lsb,cw,cwr,am,sam,fm,nfm,digu,digl,rtty;
TCI_TO_NOT1MM_MODE = {
    "usb": "USB",
    "lsb": "LSB",
    "cw": "CW",  # in Radio.cw_list
    "cwr": "CWR",  # in Radio.cw_list
    "am": "AM",
    "sam": "SAM",
    "fm": "FM",
    # AetherSDR offers fm AND nfm. Folding nfm into FM would collide, and the
    # reverse map would then lose fm entirely.
    "nfm": "NFM",
    "digu": "DIGI-U",
    "digl": "DIGI-L",  # in Radio.rtty_list
    "rtty": "RTTY",  # in Radio.rtty_list -- native, never remapped to digl
    # Not offered by AetherSDR; harmless, and correct for other TCI servers.
    "dsb": "DSB",
    "wfm": "WFM",
    "drm": "DRM",
}

# Plain inversion, no special cases: AetherSDR has a native rtty mode, so
# not1mm's RTTY maps straight through.
NOT1MM_TO_TCI_MODE = {v: k for k, v in TCI_TO_NOT1MM_MODE.items()}


def parse_frame(frame: str) -> tuple[str, list[str]] | None:
    """Split one TCI frame into (command, args).

    "vfo:0,0,14030000;" -> ("vfo", ["0", "0", "14030000"])
    "ready;"            -> ("ready", [])

    Returns None for anything malformed. TCI servers emit plenty of commands
    not1mm does not care about, so callers drop None quietly rather than
    treating it as an error.
    """
    frame = frame.strip()
    if not frame.endswith(";"):
        return None
    body = frame[:-1].strip()
    if not body:
        return None
    if ":" not in body:
        return body.lower(), []
    name, _, argstr = body.partition(":")
    name = name.strip().lower()
    if not name:
        return None
    args = [a.strip() for a in argstr.split(",")] if argstr.strip() else []
    return name, args


def split_frames(payload: str) -> list[str]:
    """Split a websocket text payload into individual ';'-terminated frames.

    One payload may carry several commands, which is normal during the connect
    handshake.
    """
    return [chunk + ";" for chunk in payload.split(";") if chunk.strip()]


def build_command(name: str, *args) -> str:
    """Build a TCI command frame.

    build_command("vfo", 0, 0, 14030000) -> "vfo:0,0,14030000;"
    build_command("stop")                -> "stop;"
    """
    if not args:
        return f"{name};"
    return f"{name}:{','.join(str(a) for a in args)};"


def tci_mode_to_not1mm(mode: str) -> str:
    """Normalize a TCI modulation name to not1mm's convention."""
    cleaned = mode.strip()
    return TCI_TO_NOT1MM_MODE.get(cleaned.lower(), cleaned.upper())


def not1mm_mode_to_tci(mode: str) -> str:
    """Translate a not1mm mode name to TCI's convention."""
    cleaned = mode.strip()
    return NOT1MM_TO_TCI_MODE.get(cleaned.upper(), cleaned.lower())


def bandwidth_from_filter_band(low: str, high: str) -> str:
    """Derive filter width in Hz from an rx_filter_band edge pair.

    Returns "" when unparseable, which the caller treats as "no update".
    """
    try:
        return str(abs(int(high) - int(low)))
    except (TypeError, ValueError):
        return ""
