


import pyvisa
from typing import List
import numpy as np
import socket
from hardware_control.HC_Backend import HC_Backend
import re
import random


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

        self.ID = "ID of Template Device"

        self.visa_addr = visa_addr
        self.online = False
        self.dummy = dummy
        self.print_commands = print_commands

        #example
        self.use_sockets = use_sockets
        self.port_no = port_no
        self.ip_addr = ip_addr

        self.num_channels = 8


    #needs to be implemented!
    def update_setting(self, setting: str, value):
       return setting +"="+ value

    #needs to be implemented
    def command(self, cmd: str):
        if self.dummy and cmd=="RND":
            return "RND="+str(random.random())
        else:
            return "VOLT=20"
