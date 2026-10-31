"""
TX-slice selection for SO2V over TCI, via AetherSDR's FlexCAT port.
GPL V3

AetherSDR's TCI server cannot move TX without keying: cw_macros validates its
trx index and then sends through CWX on whichever slice already holds TX, and
the active_slice / tx_enable SETs are ignored. Its FlexCAT (SmartSDR CAT)
port can: with the port's VFO A bound to slice A and VFO B to slice B,

    FT1;  ->  slice B becomes the TX slice
    FT0;  ->  TX goes back to slice A

Neither keys the radio. Neither returns a reply on success either, so this
class only writes, draining anything the server does send so the socket
buffer never fills.

The connection is held open for the session: AetherSDR undoes an FT1 when the
CAT client that sent it disconnects, which would hand TX back to slice A behind
not1mm's back.
"""

import logging
import socket

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("flexcat_tx")

CONNECT_TIMEOUT_S = 0.5


class FlexCatTxSelect:
    """Moves the Flex TX slice between trx 0 (VFO A) and trx 1 (VFO B)."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = int(port)
        self.sock: socket.socket | None = None
        self.warned = False

    @staticmethod
    def command_for(trx: int) -> str:
        """FT1 puts TX on VFO B; FT0 returns it to VFO A.

        AetherSDR's FT1 is a no-op while that CAT session already believes it
        has split engaged, so the swap must alternate FT1/FT0 -- never repeat
        FT1 for a second trx-1 selection without an FT0 in between. The SO2V
        swap alternates by construction, and a fresh connection starts with
        split disengaged.
        """
        return "FT1;" if int(trx) == 1 else "FT0;"

    def connect(self) -> bool:
        self.close()
        try:
            self.sock = socket.create_connection(
                (self.host, self.port), timeout=CONNECT_TIMEOUT_S
            )
            self.sock.setblocking(False)
            self.warned = False
            logger.info("FlexCAT TX select connected to %s:%d", self.host, self.port)
            return True
        except OSError as err:
            self.sock = None
            if not self.warned:
                logger.warning(
                    "FlexCAT TX select: cannot reach %s:%d (%s). TX will stay "
                    "on its current slice; enable AetherSDR's FlexCAT port.",
                    self.host,
                    self.port,
                    err,
                )
                self.warned = True
            return False

    def drain(self) -> None:
        if self.sock is None:
            return
        try:
            while True:
                data = self.sock.recv(4096)
                if not data:  # server closed the connection
                    self.close()
                    return
                logger.debug("FlexCAT < %s", data.decode(errors="replace"))
        except BlockingIOError:
            return
        except OSError:
            self.close()

    def select_tx(self, trx: int) -> bool:
        """Put TX on the slice for this trx. True if the command was sent."""
        command = self.command_for(trx).encode()
        for _attempt in (1, 2):  # one reconnect: AetherSDR may have restarted
            if self.sock is None and not self.connect():
                return False
            self.drain()
            if self.sock is None:
                continue
            try:
                self.sock.sendall(command)
                logger.debug("FlexCAT > %s", command.decode())
                return True
            except OSError as err:
                logger.info("FlexCAT TX select send failed (%s), reconnecting", err)
                self.close()
        return False

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
