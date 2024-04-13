"""
Instrument driver for TPI from Trinity Power

.. image:: /images/TPI.jpg
  :height: 200

"""

from dataclasses import dataclass
import logging
import time

import numpy as np

from ...base import Instrument, StopBits
from ...base.hooks import call_hooks

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Command:
    command: bytes
    parameter_length: int = 0
    parameter_type: np.dtype = int
    respond_length: int = 0


def validate_frequency(value: int):
    """Value is in kHz."""
    if value < 35_000:
        return False
    if value > 4_400_000:
        return False
    return True


class TPI(Instrument):
    """TPI Signal Generator

    .. image:: /images/TPI.jpg
      :height: 200

    TPI-1001, TPI-1002, & TPI-1005.

    Implements its own binary driver.

    """

    def __init__(self, instrument_name: str, connection_addr: str):
        super().__init__(instrument_name, connection_addr)

        self.manufacturer = "Trinity Power"
        self.model = "TDI Signal Generator"

        self.add_parameter(
            "FREQUENCY",
            read_command=Command(b"\x07\x09", 4, np.dtype("<i4")),
            set_command=Command(b"\x08\x09", 4, np.dtype("<i4")),
            post_hooks=[lambda x: str(int(x))],
        )
        self.add_parameter(
            "OUTPUT_LEVEL",
            read_command=Command(b"\x07\x0A", 1, np.dtype("i1")),
            set_command=Command(b"\x08\x0A", 1, np.dtype("i1")),
            post_hooks=[lambda x: str(int(x))],
        )

        self.add_parameter(
            "OUTPUT_ON_OFF",
            read_command=Command(b"\x07\x0B", 1, np.dtype(bool)),
            set_command=Command(b"\x08\x0B", 1, np.dtype(bool)),
            post_hooks=[lambda x: str(bool(x))],
        )

        READ_ONLY_COMMANDS = {
            "USER_CONTROL_STATUS": Command(b"\x07\x01", 1, np.dtype(bool)),
            "READ_MODEL_NUMBER": Command(b"\x07\x02", 16, np.dtype("a16")),
            "READ_SERIAL_NUMBER": Command(b"\x07\x03", 16, np.dtype("a16")),
            "READ_HARDWARE_VERSION": Command(b"\x07\x04", 16, np.dtype("a16")),
            "READ_FIRMWARE_VERSION": Command(b"\x07\x05", 16, np.dtype("a16")),
            "READ_TPI_LINK_VERSION": Command(b"\x07\x06", 8, np.dtype("<i2")),
            "READ_SUPPLY_VOLTAGE": Command(b"\x07\x07", 24, np.dtype("<f4")),
            "READ_CURRENT_STATE": Command(b"\x07\x08", 2, np.dtype("u1")),
        }
        for k, v in READ_ONLY_COMMANDS.items():
            self.add_parameter(k, v)

        COMMANDS = {
            "USER_CONTROL": Command(b"\x08\x01"),
            "SCAN_STOP": Command(b"\x08\x08\x04\x00"),
            "SCAN_START": Command(b"\x08\x08\x04\x01"),
            "SCAN_PAUSE": Command(b"\x08\x08\x04\x02"),
            "SCRIPT_STOP": Command(b"\x08\x08\x05\x00"),
            "SCRIPT_START": Command(b"\x08\x08\x05\x01"),
            "SCRIPT_CONTINUE": Command(b"\x08\x08\x05\x02"),
        }
        for k, v in COMMANDS.items():
            self.add_command(k, v)

        self.add_command("OUTPUT_ON", self.output_on)
        self.add_command("OUTPUT_OFF", self.output_off)

    def output_on(self):
        self["OUTPUT_ON_OFF"] = 1

    def output_off(self):
        self["OUTPUT_ON_OFF"] = 0

    def config(self):
        """Needs to be called when coming online."""
        self.config_serial(
            baud_rate=3_000_000,
            stop_bits=StopBits.one,
            data_bits=8,
            parity=None,
        )
        self.device.write_termination = None
        self.device.read_termination = None
        self.device.end_input = False
        self.device.end_output = False
        self.delay = 0.01

    def try_connect(self) -> bool:
        """Overwrite try_connect to always call config when getting online."""

        ret = super().try_connect()
        if self._online and not self._dummy:
            self.config()
            self.command("USER_CONTROL")

        return ret

    def read_package(self):
        """Read a full package from the instrument.

        Reads a package and checks the checksum.
        A package consists of:

        0xAA, 0x55, L1, L2, body bytes, checksum

        with:
           L1 the high order bytes of a 16 bit integer
           L2 the low order bytes of a 16 bit integer
              that is L = 256*L1 + L2
           body bytes are L bytes
           checksum is 0xFF - sum(all bytes ignoreing the first two)

        """
        header = self.device.read_bytes(2)
        if header[0] != 0xAA:
            print("Error")
        if header[1] != 0x55:
            print("Error")

        length = self.device.read_bytes(2)
        L = length[0] * 256 + length[1]

        body = self.device.read_bytes(L)
        checksum = self.device.read_bytes(1)

        # calculate package checksum
        tmp = 0xFF - (sum(length + body) % 256)

        if checksum != tmp.to_bytes(1, byteorder="little"):
            print(
                f"Error in checksum: got {checksum}, expected {tmp}. bytes: {length+body}."
            )

        return body

    def write_package(self, command: bytes):
        """Low level write binary data to the instrument.

        Builds a package and sends it. A package consists of:
        0xAA, 0x55, L1, L2, body bytes, checksum

        with:
           L1 the high order bytes of a 16 bit integer
           L2 the low order bytes of a 16 bit integer
              that is L = 256*L1 + L2
           body bytes are L bytes
           checksum is 0xFF - sum(all bytes ignoreing the first two)
        """

        L = len(command)
        L1 = L // 256
        L2 = L % 256

        out = (
            L1.to_bytes(1, byteorder="little")
            + L2.to_bytes(1, byteorder="little")
            + command
        )

        checksum = 0xFF - (sum(out) % 256)

        package = (
            0xAA.to_bytes(1, byteorder="little")
            + 0x55.to_bytes(1, byteorder="little")
            + out
            + checksum.to_bytes(1, byteorder="little")
        )

        self.device.write_raw(package)

    def query_serial(self, command, delay):
        self.write_package(command.command)
        time.sleep(delay)
        reply = self.read_package()
        reply = reply[2:]
        reply = np.frombuffer(reply, dtype=command.parameter_type)[0]

        return reply

    def write(self, command):
        self.write_package(command.command)
        self.read_package()

    def set_value(self, parameter: str, value) -> None:
        if parameter in self.set_commands:
            if parameter in self.pre_hooks:
                hooks = self.pre_hooks[parameter]
                value = call_hooks(hooks, value)
            if value is None:
                return

            # if we get strings for values and expect bool, we need to convert manually
            if (
                self.set_commands[parameter].parameter_type == np.dtype(bool)
                and type(value) == str
            ):
                value = value == "True"

            value = np.array(value, dtype=self.set_commands[parameter].parameter_type)
            msg = self.set_commands[parameter].command + value.tobytes()
            self.write_package(msg)
            reply = self.read_package()

            return
        logger.error(
            f"When calling 'Instrumentset_value': '{parameter}' not available in instrument '{self.name}'"
        )
