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
        if device is not None:
            return self.device.write(msg)

    def query(self, msg: str):
        """Passes a query statement directly from the UI to the instrument"""
        if device is not None:
            return self.device.query(msg)
