"""
K6GTE, CW interface abstraction
Email: michael.bridak@gmail.com
GPL V3
"""

from xmlrpc.client import ServerProxy, Error
import socket
import logging

if __name__ == "__main__":
    print("I'm not the program you are looking for.")


class CW:
    """An interface to cwdaemon and PyWinkeyerSerial"""

    def __init__(self, servertype: int, host: str, port: int) -> None:
        self.servertype = servertype
        self.host = host
        self.port = port

    def sendcw(self, texttosend):
        """sends cw to k1el"""
        logging.info("sendcw: %s", texttosend)
        if self.servertype == 2:
            self._sendcw_xmlrpc(texttosend)
        if self.servertype == 1:
            self._sendcw_udp(texttosend)

    def _sendcw_xmlrpc(self, texttosend):
        """sends cw to xmlrpc"""
        logging.info("xmlrpc: %s", texttosend)
        with ServerProxy(f"http://{self.host}:{self.port}") as proxy:
            try:
                proxy.k1elsendstring(texttosend)
            except Error as exception:
                logging.info(
                    "http://%s:%s, xmlrpc error: %s", self.host, self.port, exception
                )
            except ConnectionRefusedError:
                logging.info(
                    "http://%s:%s, xmlrpc Connection Refused", self.host, self.port
                )

    def _sendcw_udp(self, texttosend):
        """send cw to udp port"""
        logging.info("UDP: %s", texttosend)
        server_address_port = (self.host, self.port)
        # bufferSize          = 1024
        udp_client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        udp_client_socket.sendto(bytes(texttosend, "utf-8"), server_address_port)
