import visa

# from PyTektronixScope import PyTektronixScope
import socket
import numpy as np
import pandas
from struct import unpack
import sys
from matplotlib import *
import datetime

rm = visa.ResourceManager()


class Scope:
    def __init__(
        self,
        port,
        dummy=False,
        parent=None,
    ):
        self.dummy = dummy
        self.online = False
        self.buf = 760
        self.port = port
        self.data = ""
        #        self.ch1 = channel_1
        #        self.ch2 = channel_2
        #        self.ch3 = channel_3
        #        self.ch4 = channel_4
        self.time = datetime.datetime.now()

        self.connect()

    def connect(self):
        if self.online:
            return

        if not self.dummy:
            self.s = rm.open_resource(self.port)
            self.s.read_termination = "\n"
            self.s.write_termination = "\n"
            self.s.write("RS232:TRAN:TERM LF;:RS232:HARDF ON;")
            self.s.write(":HEADER OFF;*ESE 60;*SRE 32;*CLS;")
            self.s.baud_rate = 9600  # baud_rate for the oscilloscope
            self.s.timeout = 10000
            self.s.flow_control = 2
            self.s.parity = None
            self.s.stop_bits = 1.0
            self.s.data_bits = 8
            self.s.write(":HEADER OFF;*ESE 60;*SRE 32;*CLS;")

            #            self.ch1 = self.s.write('DATA:SOU CH1')
            #            self.ch2 = self.s.write('DATA:SOU CH2')
            #            self.ch3 = self.s.write('DATA:SOU CH3')
            #            self.ch4 = self.s.write('DATA:SOU CH4')
            # set range per channel
            # self.ch1_range =
            if self.s:
                self.online = True

        else:
            print(f"Scope: creating dummy connection to {self.port}")

    def close(self):
        if not self.dummy:
            self.s.close()
        else:
            print("Scope: close dummy connection")

    def trigger(self, channel):
        self.trigger_channel = channel

    def cmd(self, channel, command):
        # send commands and Read outputs from Oscilloscope
        cmd_string = ":DATA:SOURCE " + str(channel) + "; " + str(command)
        if not self.dummy:

            data = self.s.write(cmd_string)
            print(f"cmd was called for {channel}, {command}")
            return data

        else:
            print("Scope: sending command " + cmd_string)

    def read(self, channel):
        if self.online:
            # dont know exactly how to read outputs yet putting different options below to try out
            self.s.write(f"DAT:SOU {channel};:DAT:ENC ASCII;:DAT:STOP 1000")
            #            self.s.write('ACQUIRE:STOPAFTER SEQUENCE')
            #            self.s.write('ACQUIRE:STATE ON')
            #            self.s.write('*OPC?')
            indata = self.s.query("CURVE?")
            #            print(indata)
            spliit = indata.split(",")
            raw = list(map(float, spliit))
            data = np.array(raw)
            # retrieve y offset, multiply, and zero
            yoffs = self.s.query(f"WFMP:{channel}:YOF?")
            ymult = self.s.query(f"WFMP:{channel}:YMU?")
            yzero = self.s.query(f"WFMP:{channel}:YZE?")
            print(
                type(data), type(yoffs), yoffs, type(ymult), ymult, type(yzero), yzero
            )
            volts = ((data - float(yoffs)) * float(ymult)) + float(yzero)

            # retrieve X zero, Increment and number of data points
            xzero = self.s.query("WFMP:XZE?")
            xincr = self.s.query("WFMP:XIN?")
            point_count = self.s.query(f"WFMP:{channel}:NR_P?")
            times = np.arange(float(point_count)) * float(xincr) + float(xzero)

            data = [(times[i], volts[i]) for i in range(0, len(times))]
            print(type(data))

            #            data = self.cmd(channel, "CURV?")
            #            self.values_read.emit(data)
            #            sys.stdout.flush()
            #            print(f"{channel} is being read")
            print(f"{channel} is being read")
            return times, volts
        else:
            print("ERROR NO CHANNEL READ")

    def get_values(self, channel):
        """Read back the voltage in volts

        TODO: this is very slow, not sure how to fix this.
        """
        if self.dummy:
            voltage_noise = np.random.normal(0, 0.1, size=3)
            voltage = [x + n for x, n in zip([2, 5, -5], voltage_noise)]
            values = [voltage, self.time]
            print("generating random voltages")
        #            current_noise = np.random.normal(0, 0.1, size=3)
        #            current = [x+n for x, n in zip([1.4, 0.06, 0.06], voltage_noise)]
        elif self.online:
            values = self.read(f"{channel}")

        return values


#        return CH1, CH2, CH3, CH4
