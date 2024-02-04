"""
K6GTE, multicast broadcast interface
Email: michael.bridak@gmail.com
GPL V3
"""

# pylint: disable=unused-import, c-extension-no-member
import logging
from json import JSONDecodeError, dumps, loads

from dicttoxml import dicttoxml

from PyQt5 import QtNetwork

logger = logging.getLogger("__main__")

if __name__ == "__main__":
    print("I'm not the program you are looking for.")


class Multicast:
    """Sets up multicast connection"""

    def __init__(self, multicast_group: str, multicast_port: int, interface_ip: str):
        self.multicast_group = multicast_group
        self.multicast_port = int(multicast_port)
        self.interface_ip = interface_ip
        self.server_udp = QtNetwork.QUdpSocket()
        self.server_udp.bind(
            QtNetwork.QHostAddress.AnyIPv4,
            int(self.multicast_port),
            QtNetwork.QUdpSocket.ShareAddress,
        )
        self.server_udp.joinMulticastGroup(QtNetwork.QHostAddress(self.multicast_group))

    def has_pending_datagrams(self) -> bool:
        """Check if there is a pending datagram"""
        return self.server_udp.hasPendingDatagrams()

    def read_datagram(self) -> bytes:
        """Read datagram"""
        datagram, _, _ = self.server_udp.readDatagram(
            self.server_udp.pendingDatagramSize()
        )
        logger.debug("%s", f"datagram {datagram}")
        return datagram

    def read_datagram_as_json(self) -> dict:
        """Read datagram as json"""
        datagram = self.read_datagram()

        json_dict = {}

        if datagram:
            try:
                json_dict = loads(datagram.decode())
            except UnicodeDecodeError as err:
                the_error = f"Not Unicode: {err}\n{datagram}"
                logger.debug(the_error)
            except JSONDecodeError as err:
                the_error = f"Not JSON: {err}\n{datagram}"
                logger.debug(the_error)

        return json_dict

    def ready_read_connect(self, watcher) -> None:
        """pass in function to watch traffic"""
        self.server_udp.readyRead.connect(watcher)

    def send_as_json(self, dict_object: dict) -> None:
        """Send dict as json encoded packet"""
        packet = bytes(dumps(dict_object), encoding="ascii")
        logger.debug("%s", f"{dict_object}")
        self.server_udp.writeDatagram(
            packet, QtNetwork.QHostAddress(self.multicast_group), self.multicast_port
        )

    def send_as_xml(self, dict_object: dict, package_name: str) -> None:
        """Send dict as XML encoded packet"""
        packet = dicttoxml(dict_object, custom_root=package_name, attr_type=False)
        self.server_udp.writeDatagram(
            packet, QtNetwork.QHostAddress(self.multicast_group), self.multicast_port
        )

    def getpacket(self):
        """return a packet"""
        packet = (
            self.server_udp.receiveDatagram(self.server_udp.pendingDatagramSize())
            .data()
            .data()
        )
        return packet
