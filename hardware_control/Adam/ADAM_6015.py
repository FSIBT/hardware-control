import re

from hardware_control.HC_Backend import HC_Backend  # regex_compare #ToDo


class Adam_6015(HC_Backend):
    """Control of Adam input/output module"""

    def __init__(self, address, dummy=False):
        """Initialize connection to the instrument

        Parameters
        ----------
        address : str
            either ip_address:port or only ip_address. In the latter case the default port of 1025 will be used.

        """
        self.dummy = dummy
        self.online = False
        self.ID = "123"
        self.buf = 200
        tmp = address.split(":")
        if len(tmp) == 1:
            self.IP = tmp[0]
            self.port = 1025
        elif len(tmp) == 2:
            self.IP = tmp[0]
            self.port = tmp[1]
        else:
            print("[Error] Can't parse address")
        self.addr = (self.IP, self.port)

        self.try_connect()

    def try_connect(self):
        """this is a override - sockets are used"""
        if not self.dummy:
            # First Check current state
            if not self.online:  # If not online, try to connect
                try:
                    self.device = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self.device.settimeout(2)
                    self.device.connect(self.addr)
                except:
                    self.online = False
                    return self.online

            # Independent of the state, try to receive data, if nothing is returned, then the device is offline
            try:
                self.device.send("#01\r".encode("ascii"))
                indata = self.device.recv(self.buf)
                self.online = True
                return self.online
            except:
                self.online = False
                return self.online
        else:
            if not self.online:
                print(f"Adam: creating dummy connection to {self.addr}")
            self.online = True
            return self.online

    def write(self, msg: str):
        """this is a override - sockets are used"""
        if not self.dummy:
            msg = msg + "\r"
            self.device.send(msg.encode("ascii"))
            indata = self.device.recv(self.buf)
            data = indata.decode("ascii")[1:-1]
            return data

    def read(self):
        """Read values from Adam"""
        if not self.dummy:
            self.device.send("#01\r".encode("ascii"))
            indata = self.device.recv(self.buf)
            data = indata.decode("ascii")
        else:
            # Just a random answer it once received
            data = ">+0025.9237+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000-0050.0000"
        return data

    def command(self, cmd: str):
        if self.dummy:
            return cmd[:-1] + "=123"  # Jsut return the same string with temp 123
        """Use Convention "CH#_TEMP?"  the answer is like >+0025.9237+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000-0050.0000 """
        if regex_compare("CH._TEMP?", cmd) and int(cmd[2]) in range(1, 9):
            # cmd[2] equals the channel#
            out = "#01\r"  # simply asks for all channels
            self.device.send(out.encode("ascii"))
            indata = self.device.recv(self.buf)
            data = indata.decode("ascii")[1:]  # cut off ">"
            # print(data)
            n = int(cmd[2]) - 1
            data = data[n * 10 : n * 10 + 10]
            return "CH" + cmd[2] + "_TEMP=" + data
        else:
            return "Unexpected Command"

    def update_setting(self, setting: str, value: str):
        """Device has no Settings"""
        pass


# ToDo remove later
def regex_compare(pattern: str, comp: str):
    """ . as a wildcard"""
    regex = re.compile(pattern)
    return bool(re.match(regex, comp))
