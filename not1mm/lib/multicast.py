"""
K6GTE, multicast broadcast interface
Email: michael.bridak@gmail.com
GPL V3
"""
# pylint: disable=unused-import
import logging
import socket
from json import JSONDecodeError, dumps, loads

from dicttoxml import dicttoxml

logger = logging.getLogger("__main__")

if __name__ == "__main__":
    print("I'm not the program you are looking for.")


class Multicast:
    """Sets up multicast connection"""

    def __init__(self, multicast_group: str, multicast_port: int, interface_ip: str):
        self.multicast_group = multicast_group
        self.multicast_port = multicast_port
        self.interface_ip = interface_ip
        self.server_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_udp.bind(("", int(self.multicast_port)))
        mreq = socket.inet_aton(self.multicast_group) + socket.inet_aton(
            self.interface_ip
        )
        self.server_udp.setsockopt(
            socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, bytes(mreq)
        )
        self.server_udp.settimeout(0.01)

    def send_as_json(self, dict_object: dict):
        """Send dict as json encoded packet"""
        bytes_to_send = bytes(dumps(dict_object), encoding="ascii")
        logger.debug("%s", f"{dict_object}")
        try:
            self.server_udp.sendto(
                bytes_to_send,
                (self.multicast_group, int(self.multicast_port)),
            )
        except OSError as err:
            logger.warning("%s", err)

    def send_as_xml(self, dict_object: dict, package_name: str):
        """Send dict as XML encoded packet"""
        bytes_to_send = dicttoxml(
            dict_object, custom_root=package_name, attr_type=False
        )
        try:
            self.server_udp.sendto(
                bytes_to_send,
                (self.multicast_group, int(self.multicast_port)),
            )
        except OSError as err:
            logger.warning("%s", err)
