"""A backend for a dummy instrument that can be used for debugging and development.

The QT instrument frontend for this virtual instrument can be found in hardware_control/debug/demoA.py



"""


import logging

from ..base import Backend, ensure_online
from ..utility import get_channel_from_command

logger = logging.getLogger(__name__)


class DemoA(Backend):
    def __init__(self, connection_addr: str):
        super().__init__(
            instrument_name="DemoA", connection_addr=connection_addr, default_port=7123
        )
        self.encoding = "ascii"

    @ensure_online
    def update_setting(self, setting: str, value):

        channel, setting_X = get_channel_from_command(setting)

        if setting_X == "CHX_ENABLE":
            self.write(f"CH{channel}:{value}")
            rval = self.query(f"CH{channel}?")
            return f"{setting}={rval}"

    @ensure_online
    def command(self, cmd: str):
        channel, cmd_X = get_channel_from_command(cmd)
        print(cmd_X, channel)

        if cmd_X == "CHX_ENABLE?":
            rval = self.query(f"CH{channel}?")
            return f"{cmd}={rval}"
