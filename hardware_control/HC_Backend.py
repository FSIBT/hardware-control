import pyvisa


class HC_Backend:
    """Base"""

    def __init__(self):
        super().__init__()

        self.device = None  # This is the actual, physical, instrument to write to

    def update_setting(self, setting: str, value: str):
        """User must overload this function. Must return a string"""
        return command

    def command(self, command: str):
        """User must overload this function. Must return a string"""
        return command

    def write(self, msg: str):
        """Passes a command directly from the UI to the instrument"""
        if self.device is not None:
            return self.device.write(msg)

    def query(self, msg: str):
        """Passes a query statement directly from the UI to the instrument"""
        if self.device is not None:
            return self.device.query(msg)

    def close(self):
        """Close connection to instrument"""
        if not self.dummy and self.online:
            self.device.close()
        else:
            print("Dummy connection closed");

    #
    # Tries to connect to the oscilloscope. Is called by the timer every second.
    # If already connected, returns immediately.
    #
    def try_connect(self):
        """Checks if the backend is in communication with the object, if it is
        not, it tries to re-establish communication."""

        print("try connect called")

        # Handle dummy case
        if self.dummy:
            print("dummy - leaving")
            if self.online:
                return True
            else:
                print(f"KEY4000X: creating dummy connection to {self.visa_addr}")
                self.online = True
                return True

        if self.online:  # Has previously connected to the isntrument

            try:  # Check if connected by asking for instrument ID
                self.device.query("*IDN?")
                print("Connection verified")
            except pyvisa.errors.VisaIOError as e:  # Not connected - reconnect
                print("Lost connection to device. Will try to reconnect")
                print(str(e))
            else:  # Connection stable - return True
                return True

        print("trying to connect")

        # Try to connect to scope
        try:
            if not self.use_sockets:  # Use Pyvisa
                rm = pyvisa.ResourceManager()
                self.device = rm.open_resource(self.visa_addr)  # Open connection
            else:  # Use sockets
                self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.device.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
                self.device.connect((self.ip_addr, self.port_no))
        except Exception as e:  # Failed to conncet
            print(e)
            self.online = False
        else:
            self.online = True

        return self.online
