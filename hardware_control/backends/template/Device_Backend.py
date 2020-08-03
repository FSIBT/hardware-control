import logging
import random

from ..base import Backend

logger = logging.getLogger(__name__)


class Device_Backend(Backend):
    def __init__(self, connection_addr):

        super().__init__(
            instrument_name="ID of Template Device", connection_addr=connection_addr
        )

        self.num_channels = 8

    # needs to be implemented!
    def update_setting(self, setting: str, value):
        return setting + "=" + value

    # needs to be implemented
    def command(self, cmd: str):
        if self.dummy and cmd == "RND":
            return "RND=" + str(random.random())
        else:
            return "VOLT=20"
