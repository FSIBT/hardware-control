import re
from abc import ABC, abstractmethod

import pyvisa


class HC_Backend(ABC):
    """Base"""

    def __init__(self):

        self.ID = "Instrument"
        self.online = False

        self.use_sockets = False

        self.device = None  # This is the physical instrument to write to
        self.debug = False

        self.dummy = False

    def update_setting(self, setting: str, value: str):
        """Overload this function to adjust settings on the device. Must return
        a string (which HC_CommWorker will send back to the main thread)"""
        return value

    def command(self, cmd: str):
        """Overload this function to send commands to the device. Must return
        a string (which HC_CommWorker will send back to the main thread)"""
        return value

    def write(self, msg: str):
        """Passes a command directly from the UI to the instrument"""
        if self.device is not None:
            return self.device.write(msg)

    def query(self, msg: str):
        """Passes a query statement directly from the UI to the instrument"""
        if self.device is not None:
            return self.device.query(msg)

    def command_listdata(self, cmd: str):
        """Overload this function to send commands to the device. Must return
        a tuple with an str, list, and list (which HC_CommWorker will send back
         to the main thread)"""
        return "", [], []

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

        if self.online:  # Has previously connected to the instrument

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

            if not self.use_sockets:  # Use visa
                try:
                    rm = pyvisa.ResourceManager("@py")
                    self.device = rm.open_resource(self.visa_addr)  # Open connection

                    # Verify actually connected (open_resource won't always throw error w/ disconnected USB)
                    self.device.query("*IDN?")
                    if self.debug:
                        print("opened connection")

                except Exception as e:  # Failed to conncet
                    self.online = False
                    if self.debug:
                        print(f"\t{str(e)}")
                        print("OFFLINE")
            else:  # Use sockets
                # This is very specific and probably does not work as it is with other devices
                # First Check current state
                if not self.online:  # If not online, try to connect
                    try:
                        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        self.s.settimeout(2)
                        self.s.connect(self.addr)
                    except:
                        self.online = False
                        return self.online

                    # Independent of the state, try to receive data, if nothing is returned, then the device is offline
                    try:
                        self.s.send("#01\r".encode("ascii"))
                        indata = self.s.recv(self.buf)
                        self.online = True
                        return self.online
                    except:
                        self.online = False
                        return self.online

        else:
            self.online = True

        return self.online


def regex_compare(pattern: str, comp: str):
    """Compares 'comp' to the pattern 'pattern'. periods ('.') act as a wildcard in the regular expression.
    Returns true if 'comp' matches the regex."""
    regex = re.compile(pattern)
    return bool(re.match(regex, comp))


def returnChannelNumber(s: str):
    """Return channel number for a string like 'CH###_TEMP' """
    if s[:2] == "CH":
        number = s[2 : s.find("_")]
        if number.isdigit():
            return number
    else:
        return None


# These functions are helpful for converting numbers to
# specific number formats for strings


def to_NR3(x: float):
    return f" {x:.6E}"


def to_NR1(x: int):
    return f"{x:d}"


def bool_NR1(x: bool):
    if x:
        return "1"
    else:
        return "0"


def str_to_bool(x: str):
    if x == "True":
        return True
    else:
        return False
