import pyvisa
from abc import ABC, abstractmethod

class HC_Backend(ABC):
    """Base"""

    def __init__(self):

        self.ID = "Instrument"
        self.online = False

        self.device = None  # This is the physical instrument to write to
        self.debug = False

    @abstractmethod
    def update_setting(self, setting: str, value: str):
        """User must overload this function. Must return a string"""

    @abstractmethod
    def command(self, cmd: str):
        """User must overload this function. Must return a string"""

    def write(self, msg: str):
        """Passes a command directly from the UI to the instrument"""
        if self.device is not None:
            return self.device.write(msg)

    def query(self, msg: str):
        """Passes a query statement directly from the UI to the instrument"""
        if self.device is not None:
            return self.device.query(msg)

    def close(self):
        """Close connection to instrument"""
        if (not self.dummy) and self.online:
            self.device.close()
            print(f"{self.ID}: Backend Closed")
            return (
                False
            )  # This can be changed to try to talk to instrument to verify close successful - prob not required
        else:
            print(f"{self.ID}: Dummy connection closed")
            return False

    #
    # Tries to connect to the oscilloscope. Is called by the timer every second.
    # If already connected, returns immediately.
    #
    def try_connect(self):
        """Checks if the backend is in communication with the object, if it is
        not, it tries to re-establish communication."""

        # Handle dummy case
        if self.dummy:
            if self.online:
                return True
            else:
                print(f"{self.ID}: creating dummy connection to {self.visa_addr}")
                self.online = True
                return True

        if self.online:  # Has previously connected to the isntrument

            try:  # Check if connected by asking for instrument ID
                self.device.query("*IDN?")
                if self.debug:
                    print(f"{self.ID}: Connection verified")
            except visa.errors.VisaIOError as e:  # Not connected - reconnect
                if self.debug:
                    print("Lost connection to device. Will try to reconnect")
                    print(f"\t{str(e)}")
            else:  # Connection stable - return True
                return True

        if self.debug:
            print(f"{self.ID}: trying to connect")

        # Try to connect to instrument
        try:
            if not self.use_sockets:  # Use visa
                rm = pyvisa.ResourceManager("@py")
                self.device = rm.open_resource(self.visa_addr)  # Open connection

                # Verify actually connected (open_resource won't always throw error w/ disconnected USB)
                self.device.query("*IDN?")
                if self.debug:
                    print("opened connection")

            else:  # Use sockets
                self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.device.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
                self.device.connect((self.ip_addr, self.port_no))
        except Exception as e:  # Failed to conncet

            self.online = False
            if self.debug:
                print(f"\t{str(e)}")
                print("OFFLINE")
        else:
            self.online = True

        return self.online
