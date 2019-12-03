import sys

import numpy as np
import pyvisa

# from hardware_control.base import HC_Control


rm = pyvisa.ResourceManager()


class GP390Ctrl:
    # control of Micro-Ion ATM Ion Gauge

    def __init__(self, port, address, dummy=False, parent=None, pressure_limit=None):
        self.dummy = dummy
        self.online = False

        self.buf = 760
        self.port = port
        self.addr = address
        self.data = ""

        self.pressure = 0  # for dummy operation only

        self.connect()

    def connect(self):
        if self.online:
            return
        # connect to visa resource for micro-ion atm, GP390; COM4
        if not self.dummy:
            self.s = rm.open_resource(self.port)
            self.s.read_termination = "\r"
            self.s.write_termination = "\r"
            self.s.baud_rate = 19200
            self.s.timeout = 5000
            if self.s:
                self.online = True
            print("QATM online")

        else:
            print(f"Ion Gauge: creating dummy connection to {self.addr}")

    def close(self):
        if not self.dummy:
            self.s.close()
        else:
            print("Micro-Ion ATM: close dummy connection")

    def read(self):
        """Read Pressure from Ion Gauge
        """

        if not self.dummy:
            indata = self.s.query("#02RD")
            #            print("read was called (IonGauge)", indata[3:])
            # Need to determine if .encode necessary otherwise use address #02 send read command (RD)
            # indata = self.s.read(self.buf)
            # not sure if above is needed
            data = indata
            print(type(data))
            pressure = float(data[3:])

        #            try:
        #                pressure = float(data[4:])

        #            except ValueError:
        #                pressure = 0
        #                print(f"Ion Gauge: Error in read values: p={data[0:4]}")

        else:
            pressure = round(self.pressure + np.random.normal(0, 9.99e09), 3)

        return pressure

    #    def read2(self):
    #
    #        if not self.dummy:
    #            self.s.recv
    #
    def write(self, commandstr):

        cmd = f"#{self.addr:02d}{commandstr}"
        if not self.dummy:
            self.data = self.s.query(cmd)
            #            self.indata = self.s.recv()
            print(f"{cmd} {self.data}")
            sys.stdout.flush()
            #            self.data = self.indata.decode("ascii")
            return self.data[2:]
        else:
            print(f"IonGauge: sending command {cmd}")

            sys.stdout.flush()


#        if value < 0 or value >= 9.99e09:
#            return False
#
#        cmd = "#02RD"
#
#        if not self.dummy:
#
#            self.s.sendto(cmd.encode("ascii"), self.addr)
#            indata, inaddr = self.s.recvfrom(self.buf)
#            output = indata.decode("ascii")
#
#            if output == "9.99E+09":  # this may be in ascii '
#                print("ATM: Module cannot indicate a valid pressure value")
#                return False
#            else:
#                print(f"ATM: send {cmd}")
#                self.pressure = value
#                return True
#            return indata
