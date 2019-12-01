import pyvisa
from typing import List
import numpy as np
import socket
from hardware_control.HC_Backend import HC_Backend

import pyvisa


def to_NR3(x: float):
    return f" {x:.6E}"


def to_NR1(x: int):
    return f"{x:d}"


def bool_NR1(x: bool):
    if x:
        return "1"
    else:
        return "0"


class SRSDG535Ctrl(HC_Backend):
    def __init__(
        self,
        visa_addr,
        dummy: bool = False,
        print_commands: bool = False,
        use_pyvisapy: bool = False,
    ):

        super().__init__()

        self.use_pyvisapy = use_pyvisapy

        self.ID = "SRS-DG535"

        self.visa_addr = visa_addr
        self.online = False
        self.dummy = dummy
        self.print_commands = print_commands
        self.num_vert_divisions = 8

        self.command_str = ""

        self.use_sockets = (
            False
        )  # This tells the default try_connect() function to use visa

    def update_setting(self, setting: str, value):
        try:
            if self.dummy:
                return value
            else:
                if setting == "command":
                    self.command_str = value
                    return value
        except Exception as e:
            print("An exception occured in update_setting() of SRSDG535Ctrl.py.")
            print(str(e))

    def command(self, cmd: str):
        if cmd == "TRIGGER":
            """Tells DG535 to trigger"""
            self.write(self.command_str)
        return cmd

    def write(self, cmd: str):
        if self.online and not self.dummy:
            if not self.use_sockets:
                self.instr.write(cmd)
            if self.print_commands:
                print(f'\tSRSDG535< "{cmd}"')

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

            # Todo: impliment new way of verifying is online

            # try:  # Check if connected by asking for instrument ID
            #     self.device.query("*IDN?")
            #     if self.debug:
            #         print(f"{self.ID}: Connection verified")
            # except visa.errors.VisaIOError as e:  # Not connected - reconnect
            #     if self.debug:
            #         print("Lost connection to device. Will try to reconnect")
            #         print(f"\t{str(e)}")
            # else:  # Connection stable - return True
            return True

        if self.debug:
            print(f"{self.ID}: trying to connect")

        # Try to connect to instrument
        try:
            if not self.use_sockets:  # Use visa
                if self.use_pyvisapy:
                    rm = pyvisa.ResourceManager(
                        "@py"
                    )  # linux-gpib is required for pyvisapy to support GPIB. Use VISA if on windows
                else:
                    if self.debug:
                        print("Connecting with NI-VISA backend")
                    rm = pyvisa.ResourceManager()
                self.device = rm.open_resource(self.visa_addr)  # Open connection

                # TODO: Find a different way to verify connection. This instrument does not recognize *IDN?

                # # Verify actually connected (open_resource won't always throw error w/ disconnected USB)
                # self.device.query("*IDN?")
                # if self.debug:
                #     print("opened connection")

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
