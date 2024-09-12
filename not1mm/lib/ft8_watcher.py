#!/usr/bin/env python3
"""
WSJT-x UDP Packet Watcher
Email: michael.bridak@gmail.com
https://github.com/mbridak/not1mm
GPL V3
"""

import logging

from PyQt6 import QtNetwork

import struct

logger = logging.getLogger(__name__)


class FT8Watcher:
    """Main Window"""

    datadict = {}

    def __init__(self, *args, **kwargs):
        """Initialize"""
        super().__init__(*args, **kwargs)
        self.multicast_group = "224.0.0.1"
        self.multicast_port = 2237
        self.interface_ip = "0.0.0.0"
        self.udp_socket = QtNetwork.QUdpSocket()
        b_result = self.udp_socket.bind(
            QtNetwork.QHostAddress.SpecialAddress.AnyIPv4,
            int(self.multicast_port),
            QtNetwork.QAbstractSocket.BindFlag.ReuseAddressHint,
        )
        logger.info(f"multicast bind {b_result}")
        join_result = self.udp_socket.joinMulticastGroup(
            QtNetwork.QHostAddress(self.multicast_group)
        )
        logger.info(f"joinMulticastGroup result {join_result}")

        self.callback = None
        self.udp_socket.readyRead.connect(self.on_udp_socket_ready_read)

    def set_callback(self, callback):
        """Set callback"""
        self.callback = callback

    @staticmethod
    def getint(bytestring):
        """
        Returns an int from a bigendian signed 4 byte string
        """
        return int.from_bytes(bytestring, byteorder="big", signed=True)

    @staticmethod
    def getuint(bytestring):
        """
        Returns an int from a bigendian unsigned 4 byte string
        """
        return int.from_bytes(bytestring, byteorder="big", signed=False)

    @staticmethod
    def getbool(bytestring):
        """
        Returns a bool from a 1 byte string
        """
        return bool.from_bytes(bytestring, byteorder="big", signed=False)

    def getvalue(self, item):
        """I don't remember what this does."""
        if item in self.datadict:
            return self.datadict[item]
        return "NOT_FOUND"

    def on_udp_socket_ready_read(self):
        """
        This will process incomming UDP log packets from WSJT-X.
        I Hope...
        """
        self.datadict = {}
        datagram, sender_host, sender_port_number = self.udp_socket.readDatagram(
            self.udp_socket.pendingDatagramSize()
        )
        logger.debug(f"{datagram=}")

        if datagram[0:4] != b"\xad\xbc\xcb\xda":
            return  # bail if no wsjt-x magic number
        version = self.getuint(datagram[4:8])
        packettype = self.getuint(datagram[8:12])
        uniquesize = self.getint(datagram[12:16])
        unique = datagram[16 : 16 + uniquesize].decode()
        payload = datagram[16 + uniquesize :]

        if packettype == 0:  # Heartbeat
            hbmaxschema = self.getuint(payload[0:4])
            hbversion_len = self.getint(payload[4:8])
            hbversion = payload[8 : 8 + hbversion_len].decode()
            print(
                f"heartbeat: sv:{version} p:{packettype} "
                f"u:{unique}: ms:{hbmaxschema} av:{hbversion}"
            )
            return

        if packettype == 1:  # Status
            ...
            [dialfreq] = struct.unpack(">Q", payload[0:8])
            modelen = self.getint(payload[8:12])
            mode = payload[12 : 12 + modelen].decode()
            payload = payload[12 + modelen :]
            dxcalllen = self.getint(payload[0:4])
            dxcall = payload[4 : 4 + dxcalllen].decode()
            print(
                f"Status: sv:{version} p:{packettype} u:{unique} df:{dialfreq} m:{mode} dxc:{dxcall}"
            )

            # if f"{dxcall}{self.band}{self.mode}" in self.dupdict:
            #     self.ft8dupe = f"{dxcall} {self.band}M {self.mode} FT8 Dupe!"
            return

        if packettype == 2:  # Decode commented out because we really don't care
            return

        if packettype != 12:
            return  # bail if not logged ADIF
        # if log packet it will contain this nugget.
        gotcall = datagram.find(b"<call:")
        if gotcall != -1:
            datagram = datagram[gotcall:]  # strip everything else
        else:
            return  # Otherwise we don't want to bother with this packet

        data = datagram.decode()
        splitdata = data.upper().split("<")

        for data in splitdata:
            if data:
                tag = data.split(":")
                if tag == ["EOR>"]:
                    break
                self.datadict[tag[0]] = tag[1].split(">")[1].strip()
        # print(f"\n{self.datadict}\n")
        if self.callback:
            self.callback(self.datadict)
