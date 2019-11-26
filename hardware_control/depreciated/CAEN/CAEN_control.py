import random
import sys
import pyvisa

from ..base import HC_Control


class DummyConnection:
    def __init__(self):
        print("Created dummy CAEN instrument")

    def write(self, command):
        print(f"CAEN: write command {command}")

    def read(self):
        print("CAEN: call read")

    def query(self, command):
        print(f"CAEN: query command {command}")

    def close(self):
        print("CAEN: close connection")


class CAEN_control(HC_Control):
    def __init__(self, ResourceManager, IP_address, IP_port, dummy=False):
        self.dummy = dummy
        self.online = False
        self.rm = ResourceManager

        self.IP = IP_address
        self.port = IP_port

        self.nr_errors = 0

        self.voltage = 200  # for dummy mode
        self.try_connect()

    def try_connect(self):
        if self.online:
            return

        if not self.dummy:
            try:
                self.inst = self.rm.open_resource(
                    f"TCPIP::{self.IP}::{self.port}::SOCKET"
                )
                self.inst.read_termination = "\r\n"
                self.inst.write_termination = "\r\n"
                self.online = True
            except visa.VisaIOError as err:
                print(
                    f"CAEN: error while trying to connect, complete error message below:"
                )
                print(f"      {err}")
                sys.stdout.flush()
        else:
            self.inst = DummyConnection()
            self.online = True

    def close(self):
        self.inst.close()

    def read(self, cmd):
        """dummies, since we use query for this instrument"""
        pass

    def write(self, cmd):
        """dummies, since we use query for this instrument"""
        pass

    def query(self, cmd):
        try:
            result = self.inst.query(cmd)
            self.nr_errors = 0
        except visa.VisaIOError as err:
            print(f'CAEN: read error, channel, CMD: {cmd}, complete error below"')
            print(f"      {err}")
            self.nr_errors += 1
            if self.nr_errors > 3:
                self.online = False
            sys.stdout.flush()
            result = "           -1"
        return result

    def read_vset(self, channel):
        if self.dummy:
            return 1500.0
        result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:VSET")
        return float(result[-6:])

    def read_voltage(self, channel):
        if self.dummy:
            self.voltage = float(self.voltage) + random.uniform(-100, 100)
            self.voltage = max(0, self.voltage)
            return self.voltage
        result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:VMON")
        self.voltage = float(result[-6:])
        return float(result[-6:])

    def read_current(self, channel):
        if self.dummy:
            return 100e-6
        result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:IMON")
        return float(result[-7:])

    def read_status(self, channel):
        """See table on page 24 of manual"""
        if self.dummy:
            outputs = [1 + 128 + 1024, 128, 1, 1024]
            value = random.choice(outputs)
        else:
            result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:STAT")
            value = int(result[-5:])

        status = {
            "on_off": value & 1,
            "ramping_up": value & 2,
            "ramping_down": value & 4,
            "over_current": value & 8,
            "over_voltage": value & 16,
            "under_voltage": value & 32,
            "max_voltage": value & 64,
            "tripped": value & 128,
            "over_power": value & 256,
            "over_temperature": value & 512,
            "disabled": value & 1024,
            "kill": value & 2048,
            "interlocked": value & 4096,
            "calibration_error": value & 8192,
        }
        return status

    def read_iset(self, channel):
        if self.dummy:
            return 100e-6
        result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:ISET")
        return float(result[-7:])

    def read_maxV(self, channel):
        if self.dummy:
            return 2000
        result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:MAXV")
        return float(result[-4:])

    def read_rampup(self, channel):
        if self.dummy:
            return 21
        result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:RUP")
        return float(result[-3:])

    def read_rampdown(self, channel):
        if self.dummy:
            return 25
        result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:RDW")
        return float(result[-3:])

    def read_polarity(self, channel):
        if self.dummy:
            return "+"
        result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:POL")
        return result[-3:]

    def clear_alarm(self):
        self.query(f"$BD:00,CMD:SET,PAR:BDCLR")

    def set_voltage(self, channel, voltage):
        self.query(f"$BD:00,CMD:SET,CH:{channel},PAR:VSET,VAL:{voltage}")

    def set_current(self, channel, current):
        self.query(f"$BD:00,CMD:SET,CH:{channel},PAR:ISET,VAL:{current}")

    def set_maxV(self, channel, maxV):
        self.query(f"$BD:00,CMD:SET,CH:{channel},PAR:MAXV,VAL:{maxV}")

    def set_rampup(self, channel, rUP):
        self.query(f"$BD:00,CMD:SET,CH:{channel},PAR:RUP,VAL:{rUP}")

    def set_rampdown(self, channel, rDW):
        self.query(f"$BD:00,CMD:SET,CH:{channel},PAR:RDW,VAL:{rDW}")

    def enable_channel(self, channel):
        self.query(f"$BD:00,CMD:SET,CH:{channel},PAR:ON")

    def disable_channel(self, channel):
        self.query(f"$BD:00,CMD:SET,CH:{channel},PAR:OFF")


# USB connection
"""
import usb.util

dev = usb.core.find(idVendor=0x21e1, idProduct=0x0003)
dev.reset()
if dev is None:
    raise ValueError('Device not found. Make sure the GECO2020 is connected via USB.')
dev.reset()
dev.set_configuration()
cfg = dev.get_active_configuration()
intf = cfg[(1, 0)]
ep_out = usb.util.find_descriptor(intf,
                              custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)

ep_in = usb.util.find_descriptor(intf,
                              custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
#print('\n'*20)
#print('Enabling channel.\n')
"""
