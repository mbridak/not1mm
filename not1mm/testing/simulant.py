#!/usr/bin/env python3
"""Simulated Field Day club participant"""

# pylint: disable=global-statement, raise-missing-from

import random
import socket
import uuid
import time
import threading
import queue
import argparse
from random import randint
from datetime import datetime
from json import dumps, loads, JSONDecodeError


parser = argparse.ArgumentParser(description="Simulate a Field Day participant.")
parser.add_argument("-c", "--call", type=str, help="Your Callsign")
parser.add_argument("-b", "--band", type=str, help="Your Band")
parser.add_argument("-m", "--mode", type=str, help="Your Mode")
parser.add_argument("-p", "--power", type=str, help="Your Power")

args = parser.parse_args()

MULTICAST_PORT = 2239
MULTICAST_GROUP = "239.1.1.1"
INTERFACE_IP = "0.0.0.0"
GROUP_CALL = None

eightymeterstalk = (
    "What are the @stats?",
    "That K6GTE guy is a jerk!",
    "I worked your mama on 80 meters.",
    "I have nothing interesting to add, I'm just running my keys.",
    "Who's here that has gout?",
    "Jim, go to 40",
    "I gotta pee again, someone cover the GOTA station.",
    "Who made that 'Chili'... Gawd aweful!",
    ".. -..  - .- .--.  - .... .- -",
    "Why's no one covering 160?",
    "That FT8, It's so enjoyable!",
    "Yes Jim, you have to DISCONNECT the dummy load.",
)

bands = ("160", "80", "40", "20", "15", "10", "6", "2")
if args.band:
    if args.band in bands:
        BAND = args.band
    else:
        print('Allowed bands: "160", "80", "40", "20", "15", "10", "6", "2"')
        raise SystemExit(1)
else:
    BAND = bands[random.randint(0, len(bands) - 1)]

modes = ("CW", "PH", "DI")
if args.mode:
    if args.mode.upper() in modes:
        MODE = args.mode.upper()
    else:
        print('Allowed modes: "CW", "PH", "DI"')
        raise SystemExit(1)
else:
    MODE = modes[random.randint(0, len(modes) - 1)]

if args.power:
    try:
        POWER = int(args.power)
        if POWER < 1 or POWER > 100:
            raise ValueError
    except ValueError:
        print("Power is a number between 1 and 100")
        raise SystemExit(1)
else:
    POWER = 5

udp_fifo = queue.Queue()
server_commands = []


def generate_class():
    """Generates a valid Field Day class"""
    suffix = ["A", "B", "C", "D", "E", "F"][random.randint(0, 5)]
    if "C" in suffix:
        return "1C"
    if "D" in suffix:
        return "1D"
    if "E" in suffix:
        return "1E"
    if "B" in suffix:
        return str(random.randint(1, 2)) + suffix
    if "A" in suffix:
        return str(random.randint(3, 20)) + suffix

    return str(random.randint(1, 20)) + suffix


def generate_callsign():
    """Generates a US callsign, Need to add the land of maple syrup."""
    prefix = ["A", "K", "N", "W"]
    letters = [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
        "Z",
    ]
    callsign = prefix[random.randint(0, 3)]

    add_second_prefix_letter = random.randint(0, 2) == 0
    if "A" in callsign:  # We have no choice. Must add second prefix.
        callsign += letters[random.randint(0, 11)]
        add_second_prefix_letter = False

    if add_second_prefix_letter:
        callsign += letters[random.randint(0, 25)]

    callsign += str(random.randint(0, 9))
    if "A" in callsign[0]:
        suffix_length = random.randint(1, 2)
    else:
        length = [
            1,
            2,
            2,
            3,
            3,
            3,
        ]  # Stupid way to get a weighted result. But I'm stupid so it's normal.
        suffix_length = length[random.randint(0, 5)]

    for unused_variable in range(suffix_length):
        callsign += letters[random.randint(0, 25)]

    return callsign


def generate_section(call):
    """Generate section based on call region"""
    call_areas = {
        "0": "CO MO IA ND KS NE MN SD",
        "1": "CT RI EMA VT ME WMA NH",
        "2": "ENY NNY NLI SNJ NNJ WNY",
        "3": "DE MDC EPA WPA",
        "4": "AL SC GA SFL KY TN NC VA NFL VI PR WCF",
        "5": "AR NTX LA OK MS STX NM WTX",
        "6": "EBA SCV LAX SDG ORG SF PAC SJV SB SV",
        "7": "AK NV AZ OR EWA UT ID WWA MT WY",
        "8": "MI WV OH",
        "9": "IL WI IN",
    }
    if call[1].isdigit():
        area = call[1]
    else:
        area = call[2]
    sections = call_areas[area].split()
    return sections[random.randint(0, len(sections) - 1)]


def fakefreq(band, mode):
    """
    If unable to obtain a frequency from the rig,
    This will return a sane value for a frequency mainly for the cabrillo and adif log.
    Takes a band and mode as input and returns freq in khz.
    """
    _modes = {"CW": 0, "DI": 1, "PH": 2, "FT8": 1, "SSB": 2}
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
        "6": ["50.030", "50300", "50125"],
        "2": ["144030", "144144", "144250"],
        "222": ["222100", "222070", "222100"],
        "432": ["432070", "432200", "432100"],
        "SAT": ["144144", "144144", "144144"],
    }
    freqtoreturn = fakefreqs[band][_modes[mode]]
    return freqtoreturn


def log_contact():
    """Send a contgact to the server."""
    unique_id = uuid.uuid4().hex
    callsign = generate_callsign()
    contact = {
        "cmd": "POST",
        "hiscall": callsign,
        "class": generate_class(),
        "section": generate_section(callsign),
        "mode": MODE,
        "band": BAND,
        "frequency": int(float(fakefreq(BAND, MODE)) * 1000),
        "date_and_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "power": POWER,
        "grid": "DM13at",
        "opname": "John Doe",
        "station": STATION_CALL,
        "unique_id": unique_id,
    }
    server_commands.append(contact)
    bytes_to_send = bytes(dumps(contact), encoding="ascii")
    try:
        s.sendto(bytes_to_send, (MULTICAST_GROUP, int(MULTICAST_PORT)))
    except OSError as err:
        print(f"Error: {err}")
        # logging.warning("%s", err)


def remove_confirmed_commands(data):
    """Removed confirmed commands from the sent commands list."""
    for index, item in enumerate(server_commands):
        if item.get("unique_id") == data.get("unique_id") and item.get(
            "cmd"
        ) == data.get("subject"):
            server_commands.pop(index)
            print(f"Confirmed {data.get('subject')}")


def watch_udp():
    """Puts UDP datagrams in a FIFO queue"""
    while True:
        try:
            datagram = s.recv(1500)
        except socket.timeout:
            time.sleep(1)
            continue
        if datagram:
            udp_fifo.put(datagram)


def check_udp_queue():
    """checks the UDP datagram queue."""
    global GROUP_CALL
    while not udp_fifo.empty():
        datagram = udp_fifo.get()
        try:
            json_data = loads(datagram.decode())
        except UnicodeDecodeError as err:
            the_error = f"Not Unicode: {err}\n{datagram}"
            print(the_error)
            continue
        except JSONDecodeError as err:
            the_error = f"Not JSON: {err}\n{datagram}"
            print(the_error)
            continue
        # logging.info("%s", json_data)
        if json_data.get("cmd") == "PING":
            pass
            # print(f"[{strftime('%H:%M:%S', gmtime())}] {json_data}")
        if json_data.get("cmd") == "RESPONSE":
            if json_data.get("recipient") == STATION_CALL:
                if json_data.get("subject") == "HOSTINFO":
                    GROUP_CALL = str(json_data.get("groupcall"))
                    return
                if json_data.get("subject") == "LOG":
                    print("Server Generated Log.")

                remove_confirmed_commands(json_data)

        if json_data.get("cmd") == "CONFLICT":
            band, mode = json_data.get("bandmode").split()
            if (
                band == BAND
                and mode == MODE
                and json_data.get("recipient") == STATION_CALL
            ):
                print(f"CONFLICT ON {json_data.get('bandmode')}")
        if json_data.get("cmd") == "GROUPQUERY":
            if GROUP_CALL:
                send_status_udp()


def send_chat():
    """Sends UDP chat packet with text entered in chat_entry field."""
    message = eightymeterstalk[randint(0, len(eightymeterstalk) - 1)]
    packet = {"cmd": "CHAT"}
    packet["sender"] = STATION_CALL
    packet["message"] = message
    bytes_to_send = bytes(dumps(packet), encoding="ascii")
    try:
        s.sendto(bytes_to_send, (MULTICAST_GROUP, int(MULTICAST_PORT)))
    except OSError as err:
        print(f"{err}")


def query_group():
    """Sends request to server asking for group call/class/section."""
    update = {
        "cmd": "GROUPQUERY",
        "station": STATION_CALL,
    }
    bytes_to_send = bytes(dumps(update), encoding="ascii")
    try:
        s.sendto(bytes_to_send, (MULTICAST_GROUP, int(MULTICAST_PORT)))
    except OSError as err:
        print(f"{err}")


def send_status_udp():
    """Send status update to server informing of our band and mode"""

    if GROUP_CALL is None:
        query_group()
        # return

    update = {
        "cmd": "PING",
        "mode": MODE,
        "band": BAND,
        "station": STATION_CALL,
    }
    bytes_to_send = bytes(dumps(update), encoding="ascii")
    try:
        s.sendto(bytes_to_send, (MULTICAST_GROUP, int(MULTICAST_PORT)))
    except OSError as err:
        print(f"Error: {err}")


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("", MULTICAST_PORT))
mreq = socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton(INTERFACE_IP)
s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, bytes(mreq))
s.settimeout(0.01)

if args.call:
    STATION_CALL = args.call.upper()
else:
    STATION_CALL = generate_callsign()


def main():
    """The main loop"""
    _udpwatch = threading.Thread(
        target=watch_udp,
        daemon=True,
    )
    _udpwatch.start()
    print(f"Station: {STATION_CALL} on {BAND}M {MODE}")
    send_status_udp()
    count = 0
    while True:
        count += 1
        if count % 30 == 0:
            log_contact()
        if count % 15 == 0:
            send_status_udp()
        if count % 45 == 0:
            send_chat()
        check_udp_queue()

        time.sleep(1)


if __name__ == "__main__":
    main()
