import random

from hardware_control.HC_Backend import HC_Backend


class DeviceBackend(HC_Backend):
    def __init__(
        self,
        connection_addr,
        dummy: bool = False,
        debug: bool = False,
        use_sockets: bool = False,
        ip_addr: str = "",
        port_no=5025,
    ):

        super().__init__()

        self.ID = "ID of Template Device"

        self.connection_addr = connection_addr
        self.online = False
        self.dummy = dummy
        self.debug = debug

        # example
        self.use_sockets = use_sockets
        self.port_no = port_no
        self.ip_addr = ip_addr

        self.num_channels = 8

    # Implementation might be needed - depends on device
    # def try_connect(self):
    #     if not dummy:
    #         #try to connect
    #         #return True/False
    #     else
    #         return True

    # needs to be implemented!
    def update_setting(self, setting: str, value):
        return setting + "=" + value

    # needs to be implemented
    def command(self, cmd: str):
        if self.dummy and cmd == "RND":
            return "RND=" + str(random.random())
        else:
            return "VOLT=20"
