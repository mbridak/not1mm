import socket
import logging

if __name__ == "__main__":
    print("I'm not the program you are looking for.")

logger = logging.getLogger("rot_interface")


class RotatorInterface:
    """
    A class to interface with a rotator control program (like rotctld).
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 4533):
        self.host: str = host
        self.port: int = port
        self.socket: socket.socket | None = None
        self.connected: bool = False
        self.connect()

    def set_host_port(self, host: str, port: int) -> None:
        """Set the host and port of the rotator control program."""
        self.host = host
        self.port = port
        self.disconnect()
        self.connect()

    def connect(self) -> None:
        """Connect to the rotator control program."""
        try:
            self.socket = socket.create_connection((self.host, self.port), timeout=1)
            self.connected = True
            logger.info(f"Connected to rotator at {self.host}:{self.port}")
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            self.connected = False
            logger.warning(
                f"Failed to connect to rotator at {self.host}:{self.port}: {e}"
            )
            self.socket = None

    def disconnect(self) -> None:
        """Disconnect from the rotator control program."""
        if isinstance(self.socket, socket.socket):
            try:
                self.socket.close()
                logger.info("Disconnected from rotator")
            except OSError as e:
                logger.warning(f"Error closing rotator socket: {e}")
            self.socket = None
            self.connected = False

    def send_command(self, command) -> str | None:
        """Send a command to the rotator control program and return the response."""
        if self.connected is False or self.socket is None:
            self.connect()
            if self.connected is False or self.socket is None:
                logger.warning("Not connected to rotator. Command not sent.")
                return None

        try:
            self.socket.sendall((command + "\n").encode())
            response = self.socket.recv(1024).decode().strip()
            logger.debug(f"Sent: {command}, Received: {response}")
            return response
        except OSError as e:
            logger.warning(f"Error sending command to rotator: {e}")
            self.disconnect()
            return None

    def get_position(self) -> tuple[float, float] | None:
        """Get the current azimuth and elevation from the rotator."""
        response = self.send_command("p")
        logger.debug(f"get_position response: {response}")
        if response is not None:
            if response == "RPRT -1":
                return None, None
            try:
                azimuth, elevation = map(float, response.split("\n"))
                return azimuth, elevation
            except ValueError:
                logger.warning(f"Invalid response from rotator: {response}")
        return None, None

    def set_position(self, azimuth, elevation=0.0) -> bool:
        """Set the azimuth and elevation on the rotator."""
        response = self.send_command(f"P {azimuth} {elevation}")
        return response is not None

    def park_rotator(self) -> bool:
        """Park the rotator."""
        response = self.send_command("K")
        return response is not None

    def reset_rotator(self) -> bool:
        """Reset the rotator."""
        response = self.send_command("R")
        return response is not None

    def move_rotator(self, direction, speed) -> bool:
        """Move the rotator in the specified direction at the specified speed."""
        response = self.send_command(f"M {direction} {speed}")
        return response is not None

    def stop_rotator(self) -> bool:
        """Stop the rotator."""
        response = self.send_command("S")
        return response is not None
