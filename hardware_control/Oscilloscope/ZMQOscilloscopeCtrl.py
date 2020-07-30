import json
import logging

import numpy as np
import zmq

from hardware_control.base.HC_Backend import HC_Backend, ensure_online
from hardware_control.utility import get_channel_from_command

logger = logging.getLogger(__name__)


class ZMQOscilloscopeCtrl(HC_Backend):
    """This backend communicates with a remote computer via ZMQ.

    This backend acts as a client to the remote computer's ZMQ
    server. The server is connected to a PicoScope oscilloscope via USB
    and relays commands from this client to the PicoScope. The reason for
    adding the extra step of the ZMQ client is to connect to an instrument
    that 1.)  does not have network access 2.) can not be physically
    accessed by the computer on which this backend runs.

    """

    def __init__(
        self, connection_addr: str,
    ):
        super().__init__(
            instrument_name="ZMQ-Oscilloscope", connection_addr=connection_addr
        )

        # Create context and socket
        self.context = zmq.Context()
        self.socket = None
        self.timeout_time_ms = 500
        self.zmq_address = connection_addr
        self.num_vert_divisions = 8  # Todo: remove this from all files
        self.settings = self.default_settings()

    def check_connection(self):
        if not self.online:
            return False

        self.socket.send_string("ping")
        try:
            if self.socket.recv_string() == "alive":
                return True
        except zmq.error.Again:
            return False  # Receive timed out
        return False

    @ensure_online
    def update_setting(self, setting: str, value):

        if self.dummy:
            return value
        try:
            channel, setting_X = get_channel_from_command(setting)
            if setting_X == "CHX_volts_div":
                self.settings[f"Voltage range{channel}"] = float(value)
                self.send_json_settings()
                return f"{setting}:{value}"
            if setting == "timebase":
                self.settings["Timebase"] = float(value)
                self.send_json_settings()
                return f"{setting}:{value}"
            if setting == "time_offset":
                try:
                    val = float(value) / float(self.settings["Timebase"]) * 100
                except:
                    val = 50
                    logger.error(
                        f"{self.ID} - Failed to calculate valid time_offset value",
                        exc_info=True,
                    )
                self.settings["Ref Position (%)"] = val
                self.send_json_settings()
                return f"{setting}:{value}"
            if setting_X == "CHX_offset":
                self.settings[f"Voltage offset{channel}"] = float(value)
                self.send_json_settings()
                return f"{setting}:{value}"
            if setting_X == "CHX_BW_lim":
                if bool(value):
                    self.settings[f"bandwidth filter{channel}"] = "20MHz"
                else:
                    self.settings[f"bandwidth filter{channel}"] = "Full"
                self.send_json_settings()
                return f"{setting}:{value}"
            if setting_X == "CHX_active":
                chan_str = get_chan_str()
                self.settings[f"Ch enable{chan_str}"] = bool(value)
                self.send_json_settings()
                return f"{setting}:{value}"
            if setting_X == "CHX_impedance":
                return "Warning: Setting 'impedance' not available"
            if setting_X == "CHX_label":
                return "Warning: Setting 'label' not available"
            if setting == "labels_enabled":
                return "Warning: Setting 'label' not available"
            if setting_X == "CHX_invert":
                return "Warning: Setting 'label' not available"
            if setting_X == "CHX_probe_atten":
                self.settings[f"External Gain/Attenuator{channel}"] = f"x{value}"
                self.send_json_settings()
                return f"{setting}:{value}"
            if setting_X == "CHX_coupling":
                # Make sure valid value provided
                if value not in ["AC", "DC"]:
                    value = "DC"

                self.settings[f"AC/DC{channel}"] = value
                self.send_json_settings()
                return f"{setting}:{value}"
            if setting == "trigger_level":
                self.settings["Trigger level"] = float(value)
                self.send_json_settings()
                return f"{setting}:{value}"
            if setting == "trigger_coupling":
                self.settings[f"Ch enable{channel}"] = value
                self.send_json_settings()
                return f"{setting}:{value}"
            if setting == "trigger_edge":
                if value == "POS":
                    value = "Rising"
                elif value == "NEG":
                    value = "Falling"
                else:
                    value = "Rising"
                self.settings[f"Ch enable{channel}"] = value
                self.send_json_settings()
                return f"{setting}:{value}"
            if setting == "trigger_channel":
                if value == "1":
                    value = "A"
                elif value == "2":
                    value = "B"
                elif value == "3":
                    value = "C"
                elif value == "4":
                    value = "D"
                else:
                    value = "A"
                self.settings["Trigger channel"] = value
                self.send_json_settings()
                return f"{setting}:{value}"
        except Exception:
            logger.error(
                f"An error occured with {self.ID} when sending commands {setting} = {value} to the instrument.",
                exc_info=True,
            )

    @ensure_online
    def command(self, cmd: str):
        pass

    @ensure_online
    def command_listdata(self, cmd: str):
        """ Executes an action specified by 'cmd', returns a tuple with a string and two lists

        Parameters
        ----------
        cmd
            Name of command to execute

        Notes
        -----
        Available commands (<X> indicates a number):

        * CH<X>_WVFM?: Reads the waveform for channel 'X'
        * CH<X>_CLEAR: Clears the waveform for channel 'X' and returns two empty lists
        * RUN: Set the instrument to continuously trigger
        * CONFIG_READ_WAVE: Configure oscilloscope settings to prepare for reading waveforms
        * STOP: Prevent the instrument from triggering
        """

        if not self.online:
            return "", [], []

        channel, cmd_X = get_channel_from_command(cmd)

        if cmd_X == "CHX_WVFM?":
            # Returns a tuple (str, list, list)
            return self.read_waveform(channel)
        if cmd_X == "CHX_CLEAR":
            return f"CH{channel}_WVFM", [], []
        else:
            return "", [], []

    @ensure_online
    def read_waveform(self, channel: int):

        if self.socket is None:
            return "", [], []

        self.socket.send_string("get graph")

        try:
            message = self.socket.recv_string()
            message = json.loads(message)
        except zmq.error.Again:
            self.online = False
            return "", [], []
        # NOTE: Returned dictionary comes back in format:
        #
        # j = [{'t(0)': T0,
        #   'delta t': dt,
        #   'data': A},
        #  {'t(0)': T0,
        #   'delta t': dt,
        #   'data': B},
        #  {'t(0)': T0,
        #   'delta t': dt,
        #   'data': C},
        #  {'t(0)': T0,
        #   'delta t': dt,
        #   'data': D}]

        T0 = message[0]["t(0)"]
        delta_t = message[0]["delta t"]
        try:
            data = message[channel - 1]["data"]
        except:
            logger.error(
                "Failed to read channel {channel}. Channel number out of bounds."
            )
            return
        num_pts = len(data)

        time = np.linspace(T0, T0 + delta_t * (num_pts - 1), num_pts)

        return f"CH{channel}_WVFM", time.tolist(), data

    def try_connect(self):

        if self.dummy:
            if self.online:
                return True
            else:
                logger.debug(
                    f"{self.ID}: creating dummy connection to {self.zmq_address}"
                )
                self.online = True
                return True

        if self.online:
            return True

        # Try to connect - restart socket
        if self.socket is not None:
            self.socket.close()
        logger.debug(f"{self.ID}: Trying to connect to {self.zmq_address}")
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.RCVTIMEO, self.timeout_time_ms)
        self.socket.connect(self.zmq_address)

        self.online = True

        check_passed = self.check_connection()
        if check_passed is not None:
            self.online = check_passed

        return self.online

    def default_settings(self):
        return {
            "Timebase": 0.001,
            "Record Length": 1000.0,
            "Bit resolution": "12",
            "Ref Position (%)": 10.0,
            "Voltage range": 0.1,
            "Voltage offset": 0.0,
            "AC/DC": "DC",
            "bandwidth filter": "Full",
            "External Gain/Attenuator": "x1",
            "Calibration factor": 1.0,
            "Voltage range 2": 15.0,
            "Voltage offset 2": 0.0,
            "AC/DC 2": "DC",
            "bandwidth filter 2": "Full",
            "External Gain/Attenuator 2": "x1",
            "Calibration factor 2": 1.0,
            "Voltage range 3": 15.0,
            "Voltage offset 3": 0.0,
            "AC/DC 3": "DC",
            "bandwidth filter 3": "Full",
            "Calibration factor 3": 1.0,
            "Voltage range 4": 15.0,
            "Voltage offset 4": 0.0,
            "AC/DC 4": "DC",
            "bandwidth filter 4": "Full",
            "External Gain/Attenuator 3": "x1",
            "Calibration factor 4": 1.0,
            "Trigger channel": "B",
            "Trigger edge": "Falling",
            "Trigger level": -5.0,
            "Ch enable": True,
            "Ch enable 2": True,
            "Ch enable 3": True,
            "Ch enable 4": True,
        }

    def send_json_settings(self):
        """Sends the settings dictionary to the Raspberry Pi"""
        # This tells the Pi to get ready for the settings dict
        self.socket.send_string("set scope settings")

        try:
            message = self.socket.recv_string()
        except zmq.error.Again:
            self.online = False

        if message != "JSON?":
            logger.debug(f"{self.ID} wrong response to send json settings")

        self.socket.send_string(json.dumps(self.settings))

        try:
            message = self.socket.recv_string()
        except zmq.error.Again:
            self.online = False

        if message != "ok":
            logger.debug(f"{self.ID} wrong response to send json settings")
