from itertools import cycle
import socket
import sys
import time

from ..base import HC_Control


class DummySocket:
    def __init__(self, parent=None):
        self.parent = parent
        print(f"STM motor: creating dummy connection")
        print(f"   {self.parent.ip} {self.parent.port}")

        self.returnindex = 0
        self.returnvalue = b"\x00\x072345"
        print("debug", self.returnvalue)

    def recvfrom(self, n):
        # print(f' STM_motor ({self.parent.ip}) recvfrom {n}')
        if self.returnindex == len(self.returnvalue):
            self.returnindex = 0
            return b"\r", "dummy"
        else:
            self.returnindex += 1
            return chr(self.returnvalue[self.returnindex - 1]).encode("ascii"), "dummy"

    def send(self, cmd):
        print(f" STM_motor ({self.parent.ip}) write: {cmd}")

    def close(self):
        print(f" STM_motor ({self.parent.ip}) close")


class STM(HC_Control):
    """Control of STM motors, see manual for details

    The motor will remember the port and ipaddress of the first command it gets
    and from then on only allow commands from the same address. To undo this
    you need to power cycle the motors.
    """

    def __init__(self, IPaddress, localPort, dummy=False):
        # save the ipaddress and port, so we can reconnect automatically
        self.port = localPort
        self.ip = IPaddress

        self.online = False
        self.dummy = dummy

        self.position = 0
        self.rotation_per_digit = 200

        self.try_connect()

    def try_connect(self):
        if self.online:
            return
        if not self.dummy:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, 0)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                # create a connection to the motor. We always want to use the same
                # local port, since the motor remembers the IP/port and only accepts
                # the same IP/port combination after the first command it receives
                # (until power cycle)
                sock.bind(("192.168.0.2", self.port))
                sock.connect((self.ip, 7776))  # TCP
                self.sock = sock

                self.online = True
                # set default speed
                self.set_speed(rev_per_sec=0.5)

            except socket.timeout:
                pass
            except OSError:
                print("Motor socket not yet available")
        else:
            self.sock = DummySocket(parent=self)
            self.online = True

    def close(self):
        self.sock.close()

    def read(self):
        """Read the return statement from a motor command

        Receive one byte at a time until we read a \r.
        Form a single string out of it and then remove the leading op-code
        and the trailing \r. Return the result.
        """
        if not self.online:
            return ""

        cont = True
        out = []
        while cont:
            try:
                c, a = self.sock.recvfrom(1)
                if c == b"\r":
                    cont = False
            except socket.timeout:
                cont = False
                c = ""
            out.append(c)
        out = "".join([x.decode("ascii") for x in out[2:-1]])
        if out == "*":
            time.sleep(0.1)
            out = self.read()
        if out.startswith("?"):
            print("ERROR", out[1:])
        return out

    def write(self, cmd):
        # all commands need to have an op-code of 07 in front of the command
        out = f"\0\7{cmd}\r"
        try:
            self.sock.send(out.encode("ascii"))
        except ConnectionResetError:
            self.online = False
            self.try_connect()
            if self.online:
                self.sock.send(out.encode("ascii"))
            else:
                print(f"STM error: command {cmd} failed")

    def query(self, cmd):
        self.write(cmd)
        out = self.read()
        return out

    def set_speed(self, rev_per_sec):
        """Set the speed in revolutions per second"""
        self.query(f"VE{rev_per_sec}")

    def step(self, steps):
        """Take FL 'steps'"""
        self.query(f"FL{steps}")


if __name__ == "__main__":
    # some code to test the instrument
    test = STM(IPaddress="192.168.0.80", localPort=55061)
    test.write("VE")
    print(test.read())
    print("start")
    for k in range(10):
        print("loop", k)
        sys.stdout.flush()

        test.write("CJ")
        out = test.read()
        time.sleep(2)

        test.query("AL")
        time.sleep(0.1)
        test.query("CE")
        time.sleep(0.1)

        # query('EP')
        # time.sleep(0.1)

        test.query("SJ")
        time.sleep(2)

    print("end")
    test.close()
