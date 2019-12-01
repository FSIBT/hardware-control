# -*- coding: utf-8 -*-
import pyvisa
import socket
import numpy as np
from struct import unpack
import sys
from matplotlib import *
import datetime

rm = pyvisa.ResourceManager()


class DelayGenerator:
    def __init__(self, port, parent=None, dummy=False):
        self.dummy = dummy
        self.online = False
        self.bud = 760
        self.port = port
        self.data = ""
        self.connect()

    def connect(self):
        if self.online:
            return
        # connect to visa resource for 4-Ch Delay Generator
        if not self.dummy:
            self.s = rm.open_resource(self.port, send_end=True)
            self.s.read_termination = "\r\n"
            self.s.write_termination = "\r\n"
            self.s.baud_rate = 19200

            self.s.timeout = 5000
            if self.s:
                self.online = True

        else:
            print(f"Delay Generator: creating dummy connection to {self.port}")

    def close(self):
        if not self.dummy:
            self.s.close()
            print("close connection to Delay Generator")
        else:
            print("Delay Generator: close dummy connection")

    #    def read(self):
    #        #read settings from Delay Generator
    #
    #        if not self.dummy:
    #            indata = self.s.query('find command for reading settings off delay generator')
    #            print('read was called (Delay Generator)', indata)
    #
    #            data = indata
    #
    #            return data

    def write(self, commandstr):
        # cmd = f'#{self.addr}{commandstr}'
        if not self.dummy:
            self.s.write(commandstr)
            print(f"DelayGenerator: sending command {commandstr}")

        else:
            print(f"DelayGenerator: sending command {commandstr}")
