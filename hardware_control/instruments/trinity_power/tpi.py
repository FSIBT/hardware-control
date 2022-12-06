"""
Instrument driver fro TPI from Trinity Power

TOOD: refactor query and set_value, so that many checks are still done in Instruemnt
and only the actual write is overwritten here

Move all COMMANDS2 into add_parameter, add_commnad

"""

from dataclasses import dataclass
from typing import Any

import numpy as np

from ...base import Instrument
from .hooks import call_hooks


@dataclass(frozen=True)
class Command:
    command: bytes
    parameter_length: int = 0
    parameter_type: np.dtype = int
    respond_length: int = 0


COMMANDS2 = {
    "USER_CONTROL": Command(b"\x08\x01"),
    "USER_CONTROL_STATUS": Command(b"\x07\x01", 1, np.dtype(bool)),
    "READ_MODEL_NUMBER": Command(b"\x07\x02", 16, np.dtype("a16")),
    "READ_SERIAL_NUMBER": Command(b"\x07\x03", 16, np.dtype("a16")),
    "READ_HARDWARE_VERSION": Command(b"\x07\x04", 16, np.dtype("a16")),
    "READ_FIRMWARE_VERSION": Command(b"\x07\x05", 16, np.dtype("a16")),
    "READ_TPI_LINK_VERSION": Command(b"\x07\x06", 8, np.dtype("<i2")),
    "READ_SUPPLY_VOLTAGE": Command(b"\x07\x07", 24, np.dtype("<f4")),
    "READ_CURRENT_STATE": Command(b"\x07\x08", 2, np.dtype("u1")),
    "READ_OUTPUT_LEVEL": Command(b"\x07\x0A", 1, np.dtype("i1")),
    "SET_OUTPUT_LEVEL": Command(b"\x08\x0A", 1, np.dtype("i1")),
    "READ_OUTPUT_STATUS": Command(b"\x07\x0B", 1, np.dtype(bool)),
    "SET_OUTPUT_STATUS": Command(b"\x08\x0B", 1, np.dtype(bool)),
}

COMMANDS = {
    "SCAN_STOP": Command(b"\x08\x08\x04\x00"),
    "SCAN_START": Command(b"\x08\x08\x04\x01"),
    "SCAN_PAUSE": Command(b"\x08\x08\x04\x02"),
    "SCRIPT_STOP": Command(b"\x08\x08\x05\x00"),
    "SCRIPT_START": Command(b"\x08\x08\x05\x01"),
    "SCRIPT_CONTINUE": Command(b"\x08\x08\x05\x02"),
}


def validate_frequency(value: int):
    """Value is in kHz."""
    if value < 35_000:
        return False
    if value > 4_400_000:
        return False
    return True


class TPI(Instrument):
    """TPI Signal Generator

    TPI-1001, TPI-1002, & TPI-1005

    """

    def __init__(self, instrument_name: str, connection_addr: str):
        super().__init__(instrument_name, connection_addr)

        self.manufacturer = "Trinity Power"
        self.model = "TDI Signal Generator"

        self.add_parameter(
            "FREQUENCY",
            Command(b"\x07\x09", 4, np.dtype("<i4")),
            Command(b"\x08\x09", 4, np.dtype("<i4")),
        )

        for k, v in COMMANDS.items():
            self.add_command(k, v)

    def config(self):
        """Needs to be called when coming online."""
        self.config_serial(baud_rate=3_000_000, stop_bits=1, data_bits=8, parity=None)
        self.device.write_termination = None
        self.device.read_termination = None
        self.device.end_input = False
        self.device.end_output = False

    def try_connect(self) -> bool:
        """Overwrite try_connect to always call config when getting online."""
        ret = super().try_connect()
        if self._online:
            self.config()
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

        if checksum != tmp:
            print("Error in checksum")

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

        out = L1.to_bytes() + L2.to_bytes() + command

        checksum = 0xFF - (sum(out) % 256)

        package = 0xAA.to_bytes() + 0x55.to_bytes() + out + checksum.to_bytes()

        self.device.write_raw(package)

    def query(self, command):
        if self._dummy:
            logger.debug(f"'{self.name}' sending query command '{command}'")
            return
        try:
            logger.debug(f"'{self.name}' sending query command '{command}'")
            if self.connection_type == Instrument.VISA:
                if self.delay is not None:
                    inst_delay = self.delay
                else:
                    inst_delay = 0.0

                if delay is not None:
                    inst_delay = delay

                self.write_package(command.command)

                time.sleep(inst_delay)

                reply = self.read_package()

                if reply[:2] != command.command:
                    print("ERROR: wrong return")

                values = reply[2 : 2 + command.parameter_length]
                values = np.frombuffer(values, dtype=command.parameter_type)
                return values
        except Exception:
            logger.error(f"Query {command} failed in {self.name}", exc_info=True)
            self._online = False
            return None

    def set_value(self, parameter: str, value) -> None:
        if parameter in self.set_commands:
            if parameter in self.pre_hooks:
                hooks = self.pre_hooks[parameter]
                value = call_hooks(hooks, value)
            if value is None:
                return

            self.write_package(self.set_commands[parameter].format(value))
            reply = self.read_package()

            return
        logger.error(
            f"When calling 'Instrumentset_value': '{parameter}' not available in instrument '{self.name}'"
        )
