import visa
import numpy as np


class DummyConnection:
    def __init__(self):
        print("Created dummy Keysight instrument")

    def write(self, command):
        print(f"Keysight: write command {command}")

    def read(self):
        print("Keysight: call read")

    def query(self, command):
        print(f"Keysight: query command {command}")

    def close(self):
        print("Keysight: close connection")


class E36313A:
    """Control the low voltage power supply"""

    def __init__(self, ResourceManager, dummy=False):
        """The resource manager needs to be created by visa"""

        self.rm = ResourceManager
        self.dummy = dummy
        self.online = False
        self.inst = None

        self.nr_errors = 0

        if not dummy:
            self.try_connect()
        else:
            self.inst = DummyConnection()
            self.online = True

    def try_connect(self):
        if not self.online:
            try:
                if self.rm:
                    self.inst = self.rm.open_resource(
                        "TCPIP::192.168.0.3::5025::SOCKET", open_timeout=30
                    )
                    self.inst.read_termination = "\n"
                    self.online = True
            except visa.VisaIOError:
                pass

    def write(self, command):
        if self.inst:
            self.inst.write(command)

    def query(self, command):
        if self.inst:
            try:
                ret = self.inst.query(command)
                self.nr_errors = 0
            except visa.VisaIOError:
                print(f"Error: Keysight got visa io error on cmd={command}")
                self.nr_errors += 1
                if self.nr_errors > 3:
                    self.online = False
            else:
                return ret
        else:
            return "not connected"

    def setup_preamp(self, init=True):
        """make sure we are in the right mode

        set up all the voltage ranges and overvolt protections
        """
        # this is the only mode that enables ch3 to be negative output
        self.write("SYST:PERS:MOD E3631A")
        # set maximum outputs
        if init:
            self.write("SOURCE:CURR 0.01, (@1); VOLT 3.5, (@1)")
        else:
            self.write("SOURCE:VOLT 3.5, (@1)")
        self.write("SOURCE:CURR 0.2, (@2); VOLT 5, (@2)")
        self.write("SOURCE:CURR 0.2, (@3); VOLT -5, (@3)")

        self.write("SOURCE:VOlTAGE:PROTECTION 6, (@2)")
        self.write("SOURCE:VOlTAGE:PROTECTION -6, (@3)")

    def on(self):
        self.write("OUTPUT ON")

    def off(self):
        self.write("OUTPUT OFF")

    def is_on(self):
        out = self.query("output:state?")
        return out

    def set_heater(self, current):
        if current < 0 or current > 1.8:
            return
        self.write(f"SOURCE:CURR {current}, (@1)")

    def get_version(self):
        return self.query("SYST:VERS?")

    def get_values(self):
        """Read back the current in amps and the voltage in volts

        TODO: this is very slow, not sure how to fix this.
        """
        if self.dummy:
            voltage_noise = np.random.normal(0, 0.1, size=3)
            voltage = [x + n for x, n in zip([2, 5, -5], voltage_noise)]
            current_noise = np.random.normal(0, 0.1, size=3)
            current = [x + n for x, n in zip([1.4, 0.06, 0.06], voltage_noise)]
        elif self.online:
            values = self.query("MEAS:CURR? (@1,2,3); VOLT? (@1,2,3)")
            current, voltage = values.split(";")
            current = [float(x) for x in current.split(",")]
            voltage = [float(x) for x in voltage.split(",")]
        else:
            current = 3 * [-1]
            voltage = 3 * [-1]

        return current, voltage

    def error(self):
        """print a list of errors"""
        out = self.query("system:error?")
        print(out)

    def clear_errors(self):
        """clear the internal error list on the instrument"""
        self.write("*CLS")

    def status(self):
        print("not implemented yet: print status")

    def close(self):
        if self.inst:
            self.inst.close()


if __name__ == "__main__":
    rm = visa.ResourceManager()
    A = E36313A(rm)
