#!/usr/bin/env python3
"""Inject UDP test packet"""
# pylint: disable=line-too-long
import socket

BYTES_TO_SEND      = b'\xad\xbc\xcb\xda\x00\x00\x00\x02\x00\x00\x00\x0c\x00\x00\x00\x06WSJT-X\x00\x00\x01l\n<adif_ver:5>3.1.0\n<programid:6>WSJT-X\n<EOH>\n<call:5>KE0OG <gridsquare:6>DM10AT <mode:3>FT8 <rst_sent:0> <rst_rcvd:0> <qso_date:8>20210329 <time_on:6>183213 <qso_date_off:8>20210329 <time_off:6>183213 <band:3>20m <freq:9>14.074754 <station_callsign:5>K6GTE <my_gridsquare:6>DM13AT <contest_id:14>ARRL-FIELD-DAY <SRX_STRING:5>1D UT <class:2>1D <arrl_sect:2>UT <EOR>'
serverAddressPort   = ("127.0.0.1", 2237)
#bufferSize          = 1024

# Create a UDP socket at client side
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Send to server using created UDP socket
UDPClientSocket.sendto(BYTES_TO_SEND, serverAddressPort)
