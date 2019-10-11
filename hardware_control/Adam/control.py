import socket
import numpy as np

from ..base import HC_Control


class Adam(HC_Control):
    """Control of Adam input/output module"""

    def __init__(self, IP, dummy=False):
        self.dummy = dummy
        self.online = False

        self.buf = 200
        self.IP = IP
        self.port = 1025
        self.addr = (self.IP, self.port)

        self.voltage = 0  # used for dummy operation at the moment

        self.try_connect()

    def try_connect(self):
        if self.online:
            return

        if not self.dummy:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.s.connect(self.addr)
            if self.s:
                self.online = True
        else:
            print(f"Adam: creating dummy connection to {self.addr}")
            self.online = True

    def close(self):
        if not self.dummy:
            self.s.close()
        else:
            print("Adam: close dummy connection")

    def read(self):
        """Read values from Adam, correct for voltage offset"""
        if not self.dummy:
            self.s.send("#01\r".encode("ascii"))
            indata = self.s.recv(self.buf)
            data = indata.decode("ascii")[1:-1]
            # the data comes as one string with 7 bytes for each value
            # 1 byte: +- sign
            # 2 digits decimalpoint 3 digits
            # there is no space or separator between data points
            try:
                pressure = float(data[0:7])
                current = float(data[7:14])
                voltage = float(data[14:21])
            except ValueError:
                pressure, current, voltage = 0, 0, 0
                print(
                    f"Adam: Error in read values: p={data[0:7]} I={data[7:14]} V={data[14:21]}"
                )
        else:
            voltage = self.voltage + np.random.normal(0, 100e-3)
            current = self.voltage / 1e3
            pressure = 4 + np.random.uniform(-1, 1)
        return current, voltage, pressure

    def write(self, channel, value):
        """Set Spellman output in kV"""

        # make sure value is valid
        if value < 0 or value > 10:
            return False

        cmd = f"#01{channel:02d}{value:06.3f}\r"

        if not self.dummy:
            self.s.sendto(cmd.encode("ascii"), self.addr)
            indata, inaddr = self.s.recvfrom(self.buf)
            output = indata.decode("ascii")
            if output == "?01\r":
                print("Adam: Last command invalid")
                return False
            if output == ">\r":
                return True
        else:
            print(f"Adam: send {cmd}")
            self.voltage = value
            return True
        return indata
