


import visa
from typing import List
import numpy as np
import socket
from hardware_control.HC_Backend import HC_Backend
import re


class DeviceBackend(HC_Backend):
    def __init__(
        self,
        visa_addr,
        dummy: bool = False,
        print_commands: bool = False,
        use_sockets: bool = False,
        ip_addr: str = "",
        port_no=5025,
    ):

        super().__init__()

        self.ID = "this is a Backend ID"

        self.visa_addr = visa_addr
        self.online = False
        self.dummy = dummy
        self.print_commands = print_commands

        self.use_sockets = use_sockets
        self.port_no = port_no
        self.ip_addr = ip_addr

        self.num_channels = 8

      
    #needs to be implemented!
    def update_setting(self, setting: str, value):
        pass

    #needs to be implemented
    def command(self, cmd: str):
        pass