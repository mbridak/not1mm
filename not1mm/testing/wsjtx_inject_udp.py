#!/usr/bin/env python3
"""Inject UDP test packet"""
# pylint: disable=line-too-long
import socket
import random
import time
import datetime


BYTES_TO_SEND = b"\xad\xbc\xcb\xda\x00\x00\x00\x02\x00\x00\x00\x0c\x00\x00\x00\x06WSJT-X\x00\x00\x01l\n<adif_ver:5>3.1.0\n<programid:6>WSJT-X\n<EOH>\n<call:5>KE0OG <gridsquare:6>DM10AT <mode:3>FT8 <rst_sent:0> <rst_rcvd:0> <qso_date:8>20210329 <time_on:6>183213 <qso_date_off:8>20210329 <time_off:6>183213 <band:3>20m <freq:9>14.074754 <station_callsign:5>K6GTE <my_gridsquare:6>DM13AT <contest_id:14>ARRL-FIELD-DAY <SRX_STRING:5>1D UT <class:2>1D <arrl_sect:2>UT <EOR>"
serverAddressPort = ("127.0.0.1", 2237)
# bufferSize          = 1024

# Create a UDP socket at client side
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Send to server using created UDP socket
# UDPClientSocket.sendto(BYTES_TO_SEND, serverAddressPort)


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
    print(f"{call=}")
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


def main():
    serverAddressPort = ("127.0.0.1", 2237)
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    while True:
        dt = datetime.datetime.now(datetime.timezone.utc).isoformat(" ")
        yrmoda = dt[0:10].replace("-", "")
        tm = dt[11:19].replace(":", "")
        # '2024-07-27 01:21:38.959693+00:00'
        # <qso_date_off:8>20210329 <time_off:6>183213
        the_call = generate_callsign()
        the_class = generate_class()
        the_section = generate_section(the_call)
        header = b"\xad\xbc\xcb\xda\x00\x00\x00\x02\x00\x00\x00\x0c\x00\x00\x00\x06WSJT-X\x00\x00\x01l\n"
        payload = f"<adif_ver:5>3.1.0\n<programid:6>WSJT-X\n<EOH>\n<call:{len(the_call)}>{the_call} <gridsquare:6>DM10AT <mode:3>FT8 <rst_sent:0> <rst_rcvd:0> <qso_date:{len(yrmoda)}>{yrmoda} <time_on:{len(tm)}>{tm} <qso_date_off:{len(yrmoda)}>{yrmoda} <time_off:{len(tm)}>{tm} <band:3>20m <freq:9>14.074754 <station_callsign:5>K6GTE <my_gridsquare:6>DM13AT <contest_id:14>ARRL-FIELD-DAY <SRX_STRING:5>1D UT <class:{len(the_class)}>{the_class} <arrl_sect:{len(the_section)}>{the_section} <EOR>"
        BYTES_TO_SEND = header + payload.encode()
        print(f"{BYTES_TO_SEND=}")
        UDPClientSocket.sendto(BYTES_TO_SEND, serverAddressPort)
        time.sleep(15)


if __name__ == "__main__":
    main()
