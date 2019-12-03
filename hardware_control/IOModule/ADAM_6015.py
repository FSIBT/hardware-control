"""
This is a device for reading Temperatures
It receives a string "CH#_TEMP?"
There are no settings to be set
"""

import random
import re
import socket

from hardware_control.HC_Backend import HC_Backend  # regex_compare #ToDo


class Adam_6015(HC_Backend):
    """Control of Adam input/output module"""
    def __init__(self, IP="192.168.1.25", dummy=False):
        self.dummy = dummy
        self.online = False
        self.ID="Advantac_ADAM-6015"
        self.buf = 200
        self.IP = IP
        self.port = 1025
        self.addr = (self.IP, self.port)
        self.try_connect()

    #ToDo check if it works with sockets instead
    def try_connect(self):
        """this is a override - sockets are used"""
        if not self.dummy:
            #First Check current state
            if not self.online: # If not online, try to connect
                try:
                    self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self.s.settimeout(2)
                    self.s.connect(self.addr)
                except:
                    self.online=False
                    return self.online

            # Independent of the state, try to receive data, if nothing is returned, then the device is offline
            try:
                self.s.send("#01\r".encode("ascii"))
                indata = self.s.recv(self.buf)
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

    def close(self):
        """this is a override - sockets are used"""
        if not self.dummy:
            self.s.close()
        else:
            print("Adam: close dummy connection")

    def write(self,msg: str):
        """this is a override - sockets are used"""
        if not self.dummy:
            msg = msg+"\r"
            self.s.send(msg.encode("ascii"))
            indata = self.s.recv(self.buf)
            data = indata.decode("ascii")[1:-1]
            return data

    def read(self):
        """Read values from Adam"""
        """this is a override - sockets are used"""
        if not self.dummy:
            self.s.send("#01\r".encode("ascii"))
            indata = self.s.recv(self.buf)
            data = indata.decode("ascii")
        else:
            #Just a random answer it once received
            data =">+0025.9237+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000-0050.0000"
        return data

    def command(self, cmd: str):
        """Use Convention "CH#_TEMP?"  the answer is like >+0025.9237+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000-0050.0000 """
        if self.dummy:
            d=cmd[:-1]+"="+str(random.randint(0,10000)/1000)
            return d
        if regex_compare("CH._TEMP?",cmd) and int(cmd[2]) in range(1,9):
            #cmd[2] equals the channel#
            out="#01\r" #simply asks for all channels
            self.s.send(out.encode("ascii"))
            indata = self.s.recv(self.buf)
            data = indata.decode("ascii")[1:]  # cut off ">"
            n = int(cmd[2])-1
            data = data[n*10:n*10+10]
            return "CH"+cmd[2]+"_TEMP="+data
        else:
            return "Unexpected Command"

    def update_setting(self, setting: str, value: str):
        """Device has no Settings"""
        pass

#ToDo remove later
def regex_compare(pattern: str, comp: str):
    """ . as a wildcard"""
    regex = re.compile(pattern)
    return bool(re.match(regex, comp))