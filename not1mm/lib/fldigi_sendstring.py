import xmlrpc.client


class FlDigi_Comm:
    """Send strings to fldigi for RTTY"""

    def __init__(self):
        self.target = "http://127.0.0.1:7362"

    def send_string(
        self, message: str = None, nlbefore: bool = True, rxafter: bool = True
    ):
        """send string"""
        try:
            server = xmlrpc.client.ServerProxy(self.target)
            server.main.tx()
            if nlbefore:
                message = f"\n{message}"
            if rxafter:
                message = f"{message}^r"
            server.text.add_tx(message)
        except OSError:
            ...
