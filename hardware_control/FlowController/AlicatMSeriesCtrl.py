#
#
# G M Giesbrecht
# 20/08/2019
#

import visa
from typing import List
import numpy as np
import random
from PyQt5.QtCore import QObject

from pymodbus.client.sync import ModbusTcpClient as ModbusClient


def converter_ulong_to_IEEE754(x):
    a = (ctypes.c_ulong * 1)(x)
    b = ctypes.cast(a, ctypes.POINTER(ctypes.c_float))
    return b.contents.value


def converter_IEEE754_to_ulong(x):
    a = (ctypes.c_float * 1)(x)
    b = ctypes.cast(a, ctypes.POINTER(ctypes.c_ulong))
    return b.contents.value


class AlicatMSeriesCtrl(QObject):
    def __init__(self, ip_addr, dummy: bool = False, print_commands: bool = False):

        super().__init__()

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

    def update_setting(self, setting: str, value):

        if not self.online:
            return f"{self.ID}-Offline"

        try:
            if self.dummy:
                return value
            else:

                # Note: We ignore channel number because there is only
                # one channel on this model of PSU
                if setting == "rate":
                    value = float(self.rate_edit.text())
                    i = converter_IEEE754_to_ulong(value)
                    a = i >> 16
                    b = i & ((1 << 16) - 1)
                    r = self.meter.write_registers(address=1009, values=[a, b], unit=0)
                    sys.stdout.flush()

                    return value
                elif settting == "flow":
                    value = float(self.rate_edit.text())
                    i = converter_IEEE754_to_ulong(value)
                    a = i >> 16
                    b = i & ((1 << 16) - 1)
                    r = self.meter.write_registers(address=1009, values=[a, b], unit=0)
                    sys.stdout.flush()

                    return value
        except Exception as e:
            print(
                "An error occured in CAEN14xxETCtrl.py when sending SCPI commands to the instrument."
            )
            print(f"\t{str(e)}")
            print(f"\t{setting}, {value}")

    def command(self, cmd: str):

        if not self.online:
            return f"{self.ID}-Offline"

        try:
            # Note: usually a self.dummy check would be here, but it is taken
            # care of in get_values() for the AlicanMSeriesFlowMeter

            # Note: We ignore channel number because there is only
            # one channel on this model of PSU
            if cmd == "rate?":
                vals = self.get_values()
                rval = str(vals["flow"])
                return f"rate={rval}"
            elif cmd == "pressure?":
                vals = self.get_values()
                rval = str(vals["pressure"])
                return f"pressure={rval}"
        except Exception as e:
            print(
                f"An error occured in {self.ID} when sending SCPI commands to the instrument."
            )
            print(str(e))

    def get_values(self):
        rtn = {}

        if not self.online:
            rtn["pressure"] = -1
            rtn["flow"] = -1
            return rtn

        if not self.dummy:
            r = self.meter.read_input_registers(count=2, address=1202, unit=0)
            a, b = r.registers
            pressure = (a << 16) + b
            pressure = converter_ulong_to_IEEE754(pressure)

            r = self.meter.read_input_registers(count=2, address=1208, unit=0)
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
