import re
from abc import ABC, abstractmethod

import pyvisa
from colorama import Fore, Back, Style


class HC_Backend(ABC):
    """Base"""

    def __init__(self):

        self.ID = "Instrument"
        self.online = False

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
        if (not self.dummy) and self.online and self.device is not None:
            self.device.close()
            self.pDebug(f"{self.ID}: Backend Closed")
            return (
                False
            )  # This can be changed to try to talk to instrument to verify close successful - prob not required
        else:
            self.pDebug(f"{self.ID}: Dummy connection closed")
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
                self.pDebug(
                    f"{self.ID}: creating dummy connection to {self.connection_addr}"
                )
                self.online = True
                return True

        if self.online:  # Has previously connected to the instrument

            try:  # Check if connected by asking for instrument ID
                self.device.query("*IDN?")
                if self.debug:
                    self.pDebug(f"{self.ID}: Connection verified")
            except Exception as e:  # Not connected - reconnect
                if self.debug:
                    self.pDebug("Lost connection to device. Will try to reconnect")
                    self.pDebug(f"\t{str(e)}")
            else:  # Connection stable - return True
                return True

        if self.debug:
            self.pDebug(f"{self.ID}: trying to connect")

        # Try to connect to instrument

        if not self.use_sockets:  # Use visa
            try:
                rm = pyvisa.ResourceManager("@py")
                self.device = rm.open_resource(self.connection_addr)  # Open connection

                # Verify actually connected (open_resource won't always throw error w/ disconnected USB)
                self.device.query("*IDN?")
                if self.debug:
                    self.pDebug("opened connection")
            except Exception as e:
                self.online = False
                if self.debug:
                    self.pDebug(f"\t({self.ID}) ERROR while using visa: /n {str(e)}")
                    self.pDebug(f"{self.ID} is offline")
            else:
                self.online = True
        else:  # Use sockets
            try:
                self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.device.settimeout(2)
                self.device.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
                self.device.connect(self.connection_addr)

                # Verify actually connected (open_resource won't always throw error w/ disconnected USB)
                self.device.query("*IDN?")  # TODO: Test that this works
                if self.debug:
                    self.pDebug("opened connection")
            except Exception as e:
                self.online = False
                if self.debug:
                    self.pDebug(f"\t({self.ID}) ERROR while using sockets: /n {str(e)}")
                    self.pDebug(f"{self.ID} is offline")
            else:
                self.online = True
        return self.online

    def write(self, command: str):

        if not self.online:
            return f"{self.ID}-Offline"

        try:
            if not self.dummy:
                if not self.use_sockets:
                    self.device.write(command)
                else:
                    self.device.sendall(bytes(command + "\n", "utf-8"))
                if self.debug:
                    self.pDebug(f'\t{self.ID} < "{command}"')
            else:
                return command
        except Exception as e:
            self.pDebug(f"ERROR: Query failed.\n\t{e}")

    def query(self, command: str):

        if not self.online:
            return f"{self.ID}-Offline"

        try:
            if not self.dummy:
                if not self.use_sockets:
                    reply = self.device.query(command)
                else:
                    self.device.sendall(bytes(command + "\n", "utf-8"))
                    reply_bytes = recvall(self.device)
                    reply = str(reply_bytes)
                    reply = reply[2 : len(reply) - 3]
                if self.debug:
                    self.pDebug(f'\t{self.ID}< "{command}"')
                return reply
            else:
                return command
        except Exception as e:
            self.pDebug(f"ERROR: Query failed.\n\t{e}")

    def recvall(sock):
        BUFF_SIZE = 4096  # 4 KiB
        data = b""
        while True:
            part = sock.recv(BUFF_SIZE)
            data += part
            t_str = str(part)
            if t_str[len(t_str) - 3 : len(t_str) - 1] == "\\n":
                break
        return data

    def pDebug(self, msg, important=False, blue=False):
        if self.debug:
            if (
                important
                or ("ERR:" in msg)
                or ("ERROR:" in msg)
                or ("EXCEPTION:" in msg)
            ):
                print(Fore.RED, end="")
                print(msg)
                print(Style.RESET_ALL, end="")
            else:
                if blue:
                    print(Fore.BLUE, end="")
                print(msg)
                if blue:
                    print(Style.RESET_ALL, end="")


#
# def regex_compare(pattern: str, comp: str):
#     """Compares 'comp' to the pattern 'pattern'. periods ('.') act as a wildcard in the regular expression.
#     Returns true if 'comp' matches the regex."""
#     regex = re.compile(pattern)
#     return bool(re.match(regex, comp))
#
#
# def returnChannelNumber(s: str):
#     """Return channel number for a string like 'CH###_TEMP' """
#     if s[:2] == "CH":
#         number = s[2 : s.find("_")]
#         if number.isdigit():
#             return number
#     else:
#         return None
#
#
# # These functions are helpful for converting numbers to
# # specific number formats for strings
#
#
# def to_NR3(x: float):
#     return f" {x:.6E}"
#
#
# def to_NR1(x: int):
#     return f"{x:d}"
#
#
# def bool_NR1(x: bool):
#     if x:
#         return "1"
#     else:
#         return "0"
#
#
# def str_to_bool(x: str):
#     if x == "True":
#         return True
#     else:
#         return False
