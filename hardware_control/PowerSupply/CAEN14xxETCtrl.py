import socket
import random
from hardware_control.HC_Backend import HC_Backend, SOCKET, VISA
import logging
from hardware_control.utility import regex_compare, ensure_float

logger = logging.getLogger(__name__)


class CAEN14xxETCtrl(HC_Backend):
    def __init__(
        self, connection_addr,
    ):

        super().__init__()

        self.ID = "CAEN14xxET"

        self.connection_addr = connection_addr
        self.online = False
        self.dummy = False

        self.parse_connection_addr()

        # This specifies the max number of channels the user can request
        self.num_channels = 8

        self.max_V = [None] * self.num_channels
        self.max_I = [None] * self.num_channels

        self.check()

    def check_connection(self):

        if self.connection_type == VISA:

            # Check if connected by asking for instrument ID
            # Verify actually connected (open_resource won't always throw error w/ disconnected USB)
            try:
                self.device.query("$BD:00,CMD:MON,PAR:BDNAME")
            except visa.errors.VisaIOError as e:  # Not connected - reconnect
                logger.warning(
                    "Device connection check failed. Setting online to false.",
                    exc_info=True,
                )
                return False
            else:  # Connection stable - return True
                return True

        elif self.connection_type == SOCKET:

            try:
                self.query("$BD:00,CMD:MON,PAR:BDNAME")
            except Exception as e:
                logger.warning(
                    "Device connection check fail. Setting online to false",
                    exc_info=True,
                )
                return False
            else:
                return True

        else:

            return None

    def update_setting(self, setting: str, value):

        print(setting, value)
        print(f"\tdummy: {self.dummy}, online: {self.online}")

        c = int(setting[2])

        # overwrite channel number for easier comparison
        setting_X = setting[:2] + "X" + setting[3:]

        value = ensure_float(value)
        print(f"val: {value}")

        if setting_X == "CHX_I_max":
            print("\tImax")
            self.max_I[c - 1] = float(value)
            return str(value)
        elif setting_X == "CHX_V_max":
            print("\tImax")
            self.max_V[c - 1] = float(value)
            return str(value)
        else:
            print(f"\tNot a limit: {setting_X}")

        if not self.online:
            return "Offline"

        if self.dummy:
            return value

        if setting_X == "CHX_enable":
            if value == "True":
                self.query(f"$BD:00,CMD:SET,CH:{c},PAR:ON")
            else:
                self.query(f"$BD:00,CMD:SET,CH:{c},PAR:OFF")
            status = self.read_status(c)

            if status is None:
                return "None"
            return str(bool(status["on_off"]))

        elif setting_X == "CHX_I_set":
            if self.max_I[c] is not None:
                value = min(value, self.max_I[c - 1])

            self.query(f"$BD:00,CMD:SET,CH:{c},PAR:ISET,VAL:{value}")
            result = self.query(f"$BD:00,CMD:MON,CH:{c},PAR:ISET")

            if result is None:
                return "None"
            return result[-7:]
        elif setting_X == "CHX_V_set":
            if self.max_V[c] is not None:
                value = min(value, self.max_V[c - 1])

            self.query(f"$BD:00,CMD:SET,CH:{c},PAR:VSET,VAL:{value}")
            result = self.query(f"$BD:00,CMD:MON,CH:{c},PAR:VSET")

            if result is None:
                return "None"
            return result[-6:]

    def command(self, cmd: str):

        print("************************************")
        for idx, mv in enumerate(self.max_V):
            print(f"Vmax[{idx}] = {mv}")
        for idx, mi in enumerate(self.max_I):
            print(f"Imax[{idx}] = {mi}")

        try:

            if regex_compare("CH._I_max?", cmd):  # Get CHx I max
                cmd = cmd[:-1]
                c = cmd[2]

                try:
                    rval = self.max_I[c - 1]
                except:
                    rval = "Error"

                return f"{cmd}={rval}"

            elif regex_compare("CH._V_max?", cmd):  # Get CHx V max
                cmd = cmd[:-1]
                c = cmd[2]

                try:
                    rval = self.max_V[c - 1]
                except:
                    rval = "Error"

                return f"{cmd}={rval}"

            if not self.online:
                return "Offline"

            if self.dummy:
                num = random.random() * 10
                return f"{cmd.strip('?')}={num}"

            if regex_compare("CH._V_out?", cmd):  # Get CHx V out
                cmd = cmd[:-1]
                c = cmd[2]
                result = self.query(f"$BD:00,CMD:MON,CH:{c},PAR:VMON")

                if result is None:
                    return "None"
                rval = result[-6:]

                return f"{cmd}={rval}"

            elif regex_compare("CH._I_out?", cmd):  # Get CHx I out
                cmd = cmd[:-1]
                c = cmd[2]
                result = self.query(f"$BD:00,CMD:MON,CH:{c},PAR:IMON")

                if result is None:
                    return "None"
                rval = result[-7:]

                return f"{cmd}={rval}"

            elif regex_compare("CH._I_set?", cmd):  # Get CHx I setpoint
                cmd = cmd[:-1]
                c = cmd[2]
                result = self.query(f"$BD:00,CMD:MON,CH:{c},PAR:ISET")

                if result is None:
                    return "None"
                rval = result[-6:]

                return f"{cmd}={rval}"

            elif regex_compare("CH._V_set?", cmd):  # Get CHx V setpoint
                cmd = cmd[:-1]
                c = cmd[2]
                result = self.query(f"$BD:00,CMD:MON,CH:{c},PAR:VSET")

                if result is None:
                    return "None"
                rval = result[-6:]

                return f"{cmd}={rval}"

        except Exception as e:
            logger.error(
                "An error occured in CAEN14xxETCtrl.py when sending SCPI commands to the instrument.",
                exc_info=True,
            )

    def read_status(self, channel):
        """See table on page 24 of manual"""
        if self.dummy:
            outputs = [1 + 128 + 1024, 128, 1, 1024]
            value = random.choice(outputs)
        else:
            result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:STAT")
            if result is None:
                return None
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
