#
#
# G M Giesbrecht
# 20/08/2019
#

import pyvisa
from typing import List
import numpy as np
import random

from pymodbus.client.sync import ModbusTcpClient as ModbusClient


def converter_ulong_to_IEEE754(x):
    a = (ctypes.c_ulong * 1)(x)
    b = ctypes.cast(a, ctypes.POINTER(ctypes.c_float))
    return b.contents.value


def converter_IEEE754_to_ulong(x):
    a = (ctypes.c_float * 1)(x)
    b = ctypes.cast(a, ctypes.POINTER(ctypes.c_ulong))
    return b.contents.value


class AlicatMSeriesCtrl:
    def __init__(self, ip_addr, dummy: bool = False, print_commands: bool = False):

        self.ID = "AlicatMSeries"

        self.ip_addr = ip_addr
        self.online = False
        self.dummy = dummy
        self.print_commands = print_commands
        self.num_vert_divisions = 8

        self.try_connect()

    #
    # Tries to connect to the oscilloscope. Is called by the timer every second.
    # If already connected, returns immediately.
    #
    def try_connect(self):

        if self.online:
            return True

        if not self.dummy:
            try:
                self.meter = ModbusClient(host=self.ip_addr)
                if self.meter.connect():
                    self.online = True
            except:  # Failed to conncet
                self.online = False

        else:
            print(f"{self.ID}: creating dummy connection to {self.ip_addr}")
            self.online = True

        return self.online

    #
    # Close connection
    #
    def close(self):
        if not self.dummy and self.online:
            self.meter.close()
        else:
            print(f"{self.ID}: closed dummy connection")

    #
    # Receives a state object from the control object.
    #
    def get_state(self, new_state: dict):
        self.state = new_state

        new = set(self.state.items())
        old = set(self.instr_state.items())

        diff = new - old

        for param in diff:
            self.update_parameter(param[0], param[1])
            pass

    def set_rate(self, value: float):
        # """Sets the flowrate"""
        if (not self.dummy) and self.online:
            value = float(self.rate_edit.text())
            i = converter_IEEE754_to_ulong(value)
            a = i >> 16
            b = i & ((1 << 16) - 1)
            r = self.meter.write_registers(address=1009, values=[a, b], unit=0)
            sys.stdout.flush()

    def set_gas(self, value: str):
        # """Sets the gas to flow"""
        if (not self.dummy) and self.online:
            gases = {"Air": 0, "Hydrogen": 6, "Argon": 1, "Helium": 7}
            self.meter.write_registers(
                address=999, values=[1, gases[self.gas_menu.currentText()]], unit=0
            )

    def get_values(self):
        rtn = {}
        if not self.dummy:
            r = self.client.read_input_registers(count=2, address=1202, unit=0)
            a, b = r.registers
            pressure = (a << 16) + b
            pressure = converter_ulong_to_IEEE754(pressure)

            r = self.client.read_input_registers(count=2, address=1208, unit=0)
            a, b = r.registers
            flow = (a << 16) + b
            flow = converter_ulong_to_IEEE754(value)
        else:
            pressure = random.randint(0, 10)
            flow = random.randint(0, 10)

        rtn["pressure"] = pressure
        rtn["flow"] = flow

        return rtn

    def write(self, command: str):
        self.scope.write(command)
        if self.print_commands:
            print(f'\t{self.ID}< "{command}"')

    def query(self, command: str):
        reply = self.scope.query(command)
        if self.print_commands:
            print(f'\t{self.ID}< "{command}" > {reply}')
