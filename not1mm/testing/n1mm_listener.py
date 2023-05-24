#!/usr/bin/env python3
"""Test multicasting"""
# pylint: disable=invalid-name
import socket
import time
import threading
import queue
import xmltodict

multicast_port = 12061
multicast_group = "127.0.0.1"
interface_ip = "0.0.0.0"

fifo = queue.Queue()

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", multicast_port))
# mreq = socket.inet_aton(multicast_group) + socket.inet_aton(interface_ip)
# s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, bytes(mreq))
s.settimeout(0.1)


def watch_udp():
    """watch udp"""
    while True:
        try:
            datagram = s.recv(1500)
        except socket.timeout:
            time.sleep(1)
            continue
        if datagram:
            fifo.put(datagram)


_udpwatch = threading.Thread(
    target=watch_udp,
    daemon=True,
)
_udpwatch.start()

while 1:
    # print("Waiting...")
    while not fifo.empty():
        timestamp = time.strftime("%H:%M:%S", time.gmtime())
        print(f"[{timestamp}] {xmltodict.parse(fifo.get())}\n")
    time.sleep(1)
