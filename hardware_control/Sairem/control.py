import numpy as np
import sys
from pymodbus.client.sync import ModbusSerialClient as ModbusClient

from ..Instrument import Instrument


class DummyReadReturn:
    def __init__(self):
        self.registers = [int(123 + np.random.uniform(-10, 10))]

    def isError(self):
        return False


class DummyConnection:
    def __init__(self):
        print("Sairem: Creating dummy connection")

    def write_register(self, unit, address, value):
        print(f"Sairem: dummy write: unit={unit} address={address} value={value}")

    def read_holding_registers(self, unit, address, count):
        print(f"Sairem: dummy read: unit={unit} address={address} count={count}")
        return DummyReadReturn()

    def close(self):
        print("Sairem: close instrument")


class Sairem(Instrument):
    """Control the microwave power supply"""

    def __init__(self, dummy=False):
        """Talk to the microwave power supply using Modbus over serial"""

        self.dummy = dummy
        self.online = False

        self.nr_errors = 0

        self.inst = None
        self.try_connect()

    def try_connect(self):
        if self.online:
            return

        if not self.dummy:
            if not self.inst:
                client = ModbusClient(method="rtu", port="COM3", baudrate=115200)
                if client.connect():
                    self.online = True
                    self.inst = client
                    self.set_timeout(600)
        else:
            self.inst = DummyConnection()
            self.online = True

    def close(self):
        if self.inst:
            self.inst.close()

    def read(self, address):
        """Reads the holding register of inst at address with a count of 1"""
        if self.inst:
            ret = self.inst.read_holding_registers(unit=1, address=address, count=1)
        else:
            self.nr_errors += 1
            if self.nr_errors > 3:
                self.online = False
            return -1

        if ret.isError():
            if self.online:
                print(
                    f"Sairem: read: Got error {self.nr_errors} at address {address} {ret}"
                )
                if hasattr(ret, "function_code"):
                    print(f"    fcode: {ret.function_code}")
                    print(f"    check: {ret.check}")
                    print(f"    reg:   {ret.registers}")
                self.nr_errors += 1

            sys.stdout.flush()
            if self.nr_errors > 3:
                self.online = False
            return -1
        self.online = True
        self.nr_errors = 0
        return ret.registers[0]

    def write(self, unit, address, value):
        if self.inst:
            self.inst.write_register(unit=unit, address=address, value=value)

    def set_frequency(self, freq):
        if not (freq >= 2400 and freq <= 2500):
            print(f"Sairem: set_frequency: out of range, got {freq}")
            return
        # convert to value needed for communication
        freq = int(freq * 10)
        self.write(unit=1, address=9, value=freq)

    def set_power(self, power):
        power = int(power)
        if not (power >= 0 and power <= 200):
            print("Sairem: set_power: out of range, got {power}")
            return
        self.write(unit=1, address=0, value=power)

    def set_reflected_power(self, power):
        if not (power >= 0 and power <= 200):
            print(f"Sairem: set_reflected power: out of range, got {power}")
            return
        self.write(unit=1, address=1, value=power)

    def set_timeout(self, t):
        """t in seconds"""
        # got to multiples of 100 ms
        t = t * 10
        if not (t >= 15 and t <= 6000):
            print(f"Sairem: set_timeout: out of range, got {t}")
            return
        self.write(unit=1, address=98, value=t)

    def read_power(self):
        return self.read(0)

    def read_frequency(self):
        # read out in multiples of 100kHz
        return self.read(112) / 10

    def read_forward_power(self):
        return self.read(102)

    def read_reflected_power(self):
        return self.read(103)

    def read_fault_status(self):
        return (self.read(105) & 8) == 8

    def is_local_mode(self):
        return (self.read(104) & 4) == 4

    def is_on(self):
        return (self.read(2) & 64) == 64

    def on(self):
        status = self.read(2)
        self.write(unit=1, address=2, value=status | 64)

    def off(self):
        status = self.read(2)
        self.write(unit=1, address=2, value=(status & 0b10111111))

    def is_autotuning(self):
        return (self.read(2) & 2) == 2

    def autotuning_on(self):
        status = self.read(2)
        self.write(unit=1, address=2, value=status | 2)

    def autotuning_off(self):
        status = self.read(2)
        self.write(unit=1, address=2, value=(status & 0b11111101))

    def reset_faults(self):
        status = self.read(2)
        self.write(unit=1, address=2, value=status | 128)

    def set_timeout(self, value):
        """Set timeouts in seconds"""
        # in units of 100 ms
        value = int(value * 10)
        if not (value >= 15 and value <= 6000):
            print(f"Sairem: set_timeout: out of range, got raw {value}")
            return
        self.write(unit=1, address=98, value=value)


if __name__ == "__main__":
    import time

    A = Sairem()
    if A.online:
        A.reset_faults()
        A.set_frequency(2468.1)
        A.set_power(35)
        print("local?", A.is_local_mode())
        A.on()
        for i in range(10):
            time.sleep(1)
            print("FP", A.read_forward_power())
        print("on?", A.is_on())
        print("FP", A.read_forward_power())
        print("RP", A.read_reflected_power())
        print("Freq", A.read_frequency())
        A.off()
    A.close()
