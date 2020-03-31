from abc import ABC

import pyvisa
import socket
from pymodbus.client.sync import ModbusTcpClient as ModbusClient

from colorama import Fore, Style
import logging
logger = logging.getLogger(__name__)

VISA = "visa"
SOCKET = "socket"
MODBUS = "modbus"


class HC_Backend(ABC):
    """Base class for all instruments"""

    def __init__(self):

        self.ID = None  # this should be a string with instrument name
        self.online = False  # does a connection to the instrument exist?

        self.device = None  # This is the physical instrument to write to
        self.debug = False
        self.dummy = False
        self.connection_type = None

    def check(self):
        """Some error checking

        to be called at the end of __init__ in the instrument

        """
        if self.connection_type not in [VISA, SOCKET, MODBUS]:
            print(
                f"Error: the connection type {self.connection_type}"
                + " is not supported"
            )
        if self.ID is None:
            print(f"Error: Need to set the instrument ID")

    def update_setting(self, setting: str, value: str):
        """Overload this function to adjust settings on the device. Must return
        a string (which HC_CommWorker will send back to the main thread)"""
        return value

    def command(self, cmd: str):
        """Overload this function to send commands to the device. Must return
        a string (which HC_CommWorker will send back to the main thread)"""
        return cmd

    def command_listdata(self, cmd: str):
        """Overload this function to send commands to the device. Must return
        a tuple with an str, list, and list (which HC_CommWorker will send back
         to the main thread)"""
        return "", [], []

    def close(self):
        """Close connection to instrument"""

        if self.dummy:
            self.pDebug(f"{self.ID}: Dummy connection closed")
            return False

        if self.device is None:
            self.pDebug(f"{self.ID}: Called close with not device dfined")
            return False

        if self.online:
            self.device.close()
            self.pDebug(f"{self.ID}: Backend Closed")
            return False
        else:
            self.pDebug(f"{self.ID}: device not online, no need to close")
            return False

    def try_connect(self):
        """Checks if the backend is in communication with the object, if it is
        not, it tries to re-establish communication."""

        if self.dummy:
            if self.online:
                return True
            else:
                self.pDebug(
                    f"{self.ID}: creating dummy connection"
                    + f" to {self.connection_addr}"
                )
                self.online = True
                return True

        if self.online:
            return True

        self.pDebug(f"{self.ID}: trying to connect")

        # Try to connect to instrument
        if self.connection_type == VISA:
            try:
                rm = pyvisa.ResourceManager("@py")
                self.device = rm.open_resource(self.connection_addr)

                # Verify actually connected (open_resource won't
                # always throw error w/ disconnected USB)
                self.device.query("*IDN?")
                self.pDebug("opened connection")
            except Exception as e:
                self.online = False
                self.pDebug(f"\t({self.ID}) ERROR while using visa: /n {str(e)}")
                self.pDebug(f"{self.ID} is offline")
            else:
                self.online = True
        elif self.connection_type == SOCKET:
            try:
                self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.device.settimeout(2)
                self.device.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
                self.device.connect(self.connection_addr)

                # Verify actually connected (open_resource won't
                # always throw error w/ disconnected USB)
                self.device.query("*IDN?")  # TODO: Test that this works
                self.pDebug("opened connection")
            except Exception as e:
                self.online = False
                self.pDebug(f"\t({self.ID}) ERROR while using sockets: /n {str(e)}")
                self.pDebug(f"{self.ID} is offline")
            else:
                self.online = True
        elif self.connection_type == MODBUS:
            try:
                self.device = ModbusClient(host=self.connection_addr)
                if self.device.connect(self.connection_addr):
                    self.online = True
                    self.pDebug("opened connection")
            except Exception as e:
                self.online = False
                self.pDebug(f"\t({self.ID}) ERROR while using modbus: /n {str(e)}")
                self.pDebug(f"{self.ID} is offline")

        return self.online

    def write(self, command: str):

        if not self.online:
            return f"{self.ID}-Offline"

        if self.dummy:
            return command

        try:
            self.pDebug(f'\t{self.ID} < "{command}"')
            if self.connection_type == VISA:
                self.device.write(command)
            elif self.connection_type == SOCKET:
                self.device.sendall(bytes(command + "\n", "utf-8"))
        except Exception as e:
            self.pDebug(f"ERROR: Query failed.\n\t{e}")

    @staticmethod
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

    def query(self, command: str):

        if not self.online:
            return f"{self.ID}-Offline"

        if self.dummy:
            return command

        try:
            if self.connection_type == VISA:
                reply = self.device.query(command)
            elif self.connection_type == SOCKET:
                self.device.sendall(bytes(command + "\n", "utf-8"))
                reply_bytes = HC_Backend.recvall(self.device)
                reply = str(reply_bytes)
                reply = reply[2 : len(reply) - 3]
                self.pDebug(f'\t{self.ID}< "{command}"')
            return reply
        except Exception as e:
            self.pDebug(f"ERROR: Query failed.\n\t{e}")

    def pDebug(self, msg, important=False, blue=False):
        if self.debug:
            if (
                important
                or ("ERR:" in msg)
                or ("ERROR:" in msg)
                or ("EXCEPTION:" in msg)
            ):
                print(f"{Fore.RED}{msg}{Style.RESET_ALL}")
            else:
                if blue:
                    print(f"{Fore.BLUE}{msg}{Style.RESET_ALL}")
