"""R14xxET CAEN Power Supply

.. image:: /images/CAENR14xxET.jpg
  :height: 200

.. image:: /images/CAENR803x.jpg
  :height: 200


See class definition for details.

"""

import logging
import random

from ..base import Backend
from ..utility import ensure_float, get_channel_from_command


logger = logging.getLogger(__name__)


class Caen_14xxET(Backend):
    """CAEN high voltage power supplies.

    This backend provides controls for CAEN power supplies.
    Tested instruments include: R14xxET and R803x.

    """

    def __init__(
        self, connection_addr,
    ):

        super().__init__(instrument_name="CAEN14xxET", connection_addr=connection_addr)

        # This specifies the max number of channels the user can request
        self.num_channels = 8

        self.max_V = [None] * self.num_channels
        self.max_I = [None] * self.num_channels

    def update_setting(self, setting: str, value):

        channel, setting_X = get_channel_from_command(setting)
        value_original = value
        value = ensure_float(value)

        logger.info(
            f"CAEN u_s received {setting}, {value} and interpreted chan={channel}, setting_X={setting_X}, value={value}"
        )

        # These settings return valid values even in dummy mode or while offline.
        # That's why we check for self.online after these if-statements
        if setting_X == "CHX_I_MAX":
            self.max_I[channel - 1] = float(value)
            return f"{setting}={value}"

        if setting_X == "CHX_V_MAX":
            self.max_V[channel - 1] = float(value)
            return f"{setting}={value}"

        if not self.online:
            logger.info("CAEN")
            return f"{self.ID}-Offline"

        if self.dummy:
            return f"{setting}={value}"

        if setting_X == "CHX_ENABLE":
            if value_original == "True":
                self.query(f"$BD:00,CMD:SET,CH:{channel},PAR:ON")
            else:
                self.query(f"$BD:00,CMD:SET,CH:{channel},PAR:OFF")
            status = self.read_status(channel)

            if status is None:
                return "None"
            rval = bool(status["ON_OFF"])
            return f"{setting}={rval}"

        if setting_X == "CHX_I_SET":
            logger.debug(f"Iset called with value {value}")

            if self.max_I[channel - 1] is not None:
                value = min(value, self.max_I[channel - 1])
                logger.debug(f"Iset value changed to {value} because it exceeded limit")

            # the CAEN uses values in uA
            value = float(value) * 1e6
            self.query(f"$BD:00,CMD:SET,CH:{channel},PAR:ISET,VAL:{value}")
            result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:ISET")

            if result is None:
                return "None"
            rval = result[-7:]
            return f"{setting}={rval}"

        if setting_X == "CHX_V_SET":
            logger.debug(f"Vset called with value {value}")

            if self.max_V[channel - 1] is not None:
                value = min(value, self.max_V[channel - 1])
                logger.debug(f"Vset value changed to {value} because it exceeded limit")

            self.query(f"$BD:00,CMD:SET,CH:{channel},PAR:VSET,VAL:{value}")
            result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:VSET")

            if result is None:
                return "None"
            rval = result[-6:]
            return f"{setting}={value}"

    def command(self, cmd: str):
        channel, command_X = get_channel_from_command(cmd)

        if command_X == "CHX_I_MAX?":
            rval = self.max_I[channel - 1]
            return f"{cmd[:-1]}={rval}"

        if command_X == "CHX_V_MAX?":
            rval = self.max_V[channel - 1]
            return f"{cmd[:-1]}={rval}"

        if not self.online:
            return f"{self.ID}-Offline"

        if self.dummy:
            num = random.random() * 10
            return f"{cmd.strip('?')}={num}"

        if command_X == "CHX_V_OUT?":
            command = "VMON"
        elif command_X == "CHX_I_OUT?":
            command = "IMON"
        elif command_X == "CHX_I_SET?":
            command = "ISET"
        elif command_X == "CHX_V_SET?":
            command = "VSET"
        elif command_X == "CHX_ENABLE?":
            result = self.read_status(channel)

            if result is None:
                return "False"

            if result["ON_OFF"]:
                rval = "True"
            else:
                rval = "False"
            return f"{cmd[:-1]}={rval}"
        else:
            logging.debug(f"Unknown CAEN command {cmd}")

        result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:{command}")
        if result is None:
            return "None"

        rval = result[result.find("VAL:") + 4 :]
        rval = rval.strip("\\nr")

        if command_X in ["CHX_I_OUT?", "CHX_I_SET?"]:
            # Current is read in uA
            rval = float(rval) * 1e-6

        return f"{cmd[:-1]}={rval}"

    def read_status(self, channel):
        """See table on page 24 of manual"""
        if self.dummy:
            outputs = [1 + 128 + 1024, 128, 1, 1024]
            value = random.choice(outputs)
        else:
            result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:STAT")
            if result is None:
                return None
            result = result.strip(r"\r")
            print(result, flush=True)
            if result.endswith("CMD:OK"):
                return None
            value = int(result[result.find("VAL:") + 4 :])

        status = {
            "ON_OFF": value & 1,
            "RAMPING_UP": value & 2,
            "RAMPING_DOWN": value & 4,
            "OVER_CURRENT": value & 8,
            "OVER_VOLTAGE": value & 16,
            "UNDER_VOLTAGE": value & 32,
            "MAX_VOLTAGE": value & 64,
            "TRIPPED": value & 128,
            "OVER_POWER": value & 256,
            "OVER_TEMPERATURE": value & 512,
            "DISABLED": value & 1024,
            "KILL": value & 2048,
            "INTERLOCKED": value & 4096,
            "CALIBRATION_ERROR": value & 8192,
        }
        return status
