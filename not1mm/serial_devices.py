"""Serial device discovery."""

import logging
import argparse
from typing import Iterable

import serial
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo

logger: logging.Logger = logging.getLogger(__name__)

VFOKNOB_BAUD_RATE = 115200

PICO_VID = 0x2E8A
PICO_PID = 0x0005

COLUMNS_WIDTH = (40, 6, 6, 20, 20, 10)


# -------------------------
# USB discovery
# -------------------------
def probe(port: ListPortInfo) -> bool:
    """Return True if this port is a vfoknob device."""
    try:
        with serial.Serial(port.device, VFOKNOB_BAUD_RATE, timeout=1.0) as ser:
            ser.write(b"whatareyou\r")
            response = ser.readline()
            vfoknob_found = b"vfoknob" in response
            logger.debug(
                "Probing port '%s': response: '%s', found: %s",
                port.device,
                response,
                vfoknob_found,
            )
            return vfoknob_found
    except serial.SerialException as e:
        logger.debug("Probing port '%s': exception: '%s'", port.device, e)
        return False


def serial_device_candidate_ports() -> Iterable[ListPortInfo]:
    """
    Yield (generator for) likely candidate USB serial  ports.
    - Search for known VID/PID
    - Fallback probe on likely USB serial devices
    Yield for each serial device candidate.
    """
    for port in list_ports.comports():

        # Prefer exact VID/PID match
        if port.vid == PICO_VID and port.pid == PICO_PID:
            yield port
            continue

        # Fallback heuristic
        name = port.device.lower()
        if any(s in name for s in ("usb", "acm", "modem")):
            yield port


def get_serial_device_ports() -> Iterable[ListPortInfo]:
    """
    Return a tuple of serial devices.
    """
    return (device for device in serial_device_candidate_ports())


def find_vfoknob() -> ListPortInfo | None:
    """
    Discover the vfoknob USB device and if it probes correctly, return it.
    If no vfoknob is found, return None.
    """
    for port in serial_device_candidate_ports():
        if probe(port):
            return port

    return None


# -------------------------
# Printing helpers
# -------------------------
def _fmt(value: str, width: int) -> str:
    """Return a column formatted string"""
    return f"{value:{width}s}" if value else f"{'None':{width}s}"


def _fmt_hex(value: int, width: int) -> str:
    """Return a column formatted integer value as hex"""
    hex_width = width - len("0x")
    return f"0x{value:0{hex_width}X}" if value else f"{'None':{width}s}"


def print_serial_device_header() -> None:
    """Print the device header for a table"""
    headers = ("Device", "VID", "PID", "Manufacturer", "Product", "Location")

    print(*(f"{h:{w}s}" for h, w in zip(headers, COLUMNS_WIDTH)))
    print(*(("=" * w) for w in COLUMNS_WIDTH))


def print_serial_device(device: ListPortInfo) -> None:
    """Print a Serial device row element"""
    print(
        f"{device.device:{COLUMNS_WIDTH[0]}s}",
        _fmt_hex(device.vid, COLUMNS_WIDTH[1]),
        _fmt_hex(device.pid, COLUMNS_WIDTH[2]),
        _fmt(device.manufacturer, COLUMNS_WIDTH[3]),
        _fmt(device.product, COLUMNS_WIDTH[4]),
        _fmt(device.location, COLUMNS_WIDTH[5]),
    )


def discover_and_print_serial_devices() -> None:
    """Discover and print serial devices"""
    print_serial_device_header()
    for port in list_ports.comports():
        print_serial_device(port)


def main() -> None:
    """CLI for playing with serial devices"""
    parser = argparse.ArgumentParser(description="USB device utilities")

    parser.add_argument(
        "-d", "--discover", action="store_true", help="List all serial devices"
    )

    parser.add_argument(
        "-v", "--vfoknob", action="store_true", help="Discover vfoknob device"
    )

    args = parser.parse_args()

    if args.discover:
        discover_and_print_serial_devices()

    if args.vfoknob:
        device = find_vfoknob()

        if device is None:
            print("No vfoknob device found")
        else:
            print_serial_device_header()
            print_serial_device(device)


if __name__ == "__main__":
    main()
