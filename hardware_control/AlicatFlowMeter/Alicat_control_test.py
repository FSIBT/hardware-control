#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pyvisa
import socket
import numpy as np
import sys

rm = pyvisa.ResourceManager()


class Alicat:
    # control of the Alicat Flow meter
    def __init__(self, port, address, dummy=False, parent=None, mass_flow_limit=None):
        self.dummy = dummy
        self.online = False
        self.port = port
        self.addr = address
        self.data = ""

        self.massflow = 0  # for dummy only and in %

        self.connect()

    def connect(self):
        if self.online:
            return
        # connect to visa resource for Alicat Flowmeter
        if not self.dummy:
            self.s = rm.open_resource(self.port, send_end=True)
            self.s.read_termination = "\r"
            self.s.write_termination = "\r\r"
            self.baud_rate = 19200
            # here we have baud rate for ATM check alicat manual or labview code to see if Alicat has a similar quality

            self.s.timeout = 5500
            if self.s:
                self.online = True

        else:
            print(f"Alicat: creating dummy connection to {self.addr}")

    def close(self):
        if not self.dummy:
            self.s.close()

        else:
            print("Alicat: close dummy connection")

    def read(self):
        # read mass flow from Alicat

        if not self.dummy:
            indata = self.s.query(
                "A$$R"
            )  # need to find command that returns mass flow % from Alicat manual

            print("read was called (Alicat)", indata)

            try:
                massflow = float(indata)
            except ValueError:
                massflow = 0
                print(f"Alicat: Error in read values: mf={indata}")

        else:
            self.massflow = self.massflow + np.random.normal(0, 100)

        return self.massflow

    def write(self, commandstr):

        cmd = f"#{self.addr}{commandstr}"
        if not self.dummy:
            self.data = self.s.query(cmd)
            print(f"{cmd}{self.data}")
            sys.stdout.flush()

            return self.data
        else:
            print(f"Alicat: sending command{cmd}")

            sys.stdout.flush()
