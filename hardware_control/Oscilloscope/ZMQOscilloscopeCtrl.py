"""This backend communicates with a remote computer via ZMQ.

 This backend acts as a client to the remote computer's ZMQ
server. The server is connected to a PicoScope oscilloscope via USB
and relays commands from this client to the PicoScope. The reason for
adding the extra step of the ZMQ client is to connect to an instrument
that 1.)  does not have network access 2.) can not be physically
accessed by the computer on which this backend runs.

"""

import json
import zmq

from hardware_control.HC_Backend import HC_Backend, VISA
from hardware_control.utility import regex_compare
import logging

logger = logging.getLogger(__name__)


class ZMQOscilloscopeCtrl(HC_Backend):
    def __init__(
        self, connection_addr: str,
    ):

        super().__init__()
        self.ID = "ZMQ-Oscilloscope"

        # Create context and socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)

        self.zmq_address = connection_addr
        self.connection_addr = connection_addr  # So widget can read address
        self.online = False
        self.dummy = False
        self.num_vert_divisions = 8  # Todo: remove this from all files

        self.parse_connection_addr()

        self.settings = self.default_settings()
        self.check()

    def update_setting(self, setting: str, value):
        def get_chan_str():
            chan_str = ""
            if chan != 1:
                chan = setting[2]
                chan_str = f" {chan}"
            return chan_str

        if not self.online:
            return "Offline"

        try:
            if self.dummy:
                return value
            else:
                if regex_compare("CH._volts_div", setting):
                    chan_str = get_chan_str()
                    self.settings[f"Voltage range{chan_str}"] = float(value)
                    self.send_json_settings()
                    return f"{setting}:{value}"
                elif setting == "timebase":
                    self.settings[f"Timebase"] = float(value)
                    self.send_json_settings()
                    return f"{setting}:{value}"
                elif setting == "time_offset":
                    try:
                        val = float(value) / float(self.settings["Timebase"]) * 100
                    except:
                        val = 50
                        logger.error(
                            f"{self.ID} - Failed to calculate valid time_offset value",
                            exc_info=True,
                        )
                    self.settings[f"Ref Position (%)"] = val
                    self.send_json_settings()
                    return f"{setting}:{value}"
                elif regex_compare("CH._offset", setting):
                    chan_str = get_chan_str()
                    self.settings[f"Voltage offset{chan_str}"] = float(value)
                    self.send_json_settings()
                    return f"{setting}:{value}"
                elif regex_compare("CH._BW_lim", setting):
                    chan_str = get_chan_str()
                    if bool(value):
                        self.settings[f"bandwidth filter{chan_str}"] = "20MHz"
                        # Todo: @Giesbrecht Verify this is the correct code
                    else:
                        self.settings[f"bandwidth filter{chan_str}"] = "Full"
                    self.send_json_settings()
                    return f"{setting}:{value}"
                elif regex_compare("CH._active", setting):
                    chan_str = get_chan_str()
                    self.settings[f"Ch enable{chan_str}"] = bool(value)
                    self.send_json_settings()
                    return f"{setting}:{value}"
                elif regex_compare("CH._impedance", setting):
                    return f"Warning: Setting 'impedance' not available"
                elif regex_compare("CH._label", setting):
                    return f"Warning: Setting 'label' not available"
                elif setting == "labels_enabled":
                    return f"Warning: Setting 'label' not available"
                elif regex_compare("CH._invert", setting):
                    return f"Warning: Setting 'label' not available"
                elif regex_compare("CH._probe_atten", setting):
                    chan_str = get_chan_str()
                    self.settings[f"External Gain/Attenuator{chan_str}"] = f"x{value}"
                    # Todo: double check this is formatted correctly @Giesbrecht
                    self.send_json_settings()
                    return f"{setting}:{value}"
                elif regex_compare("CH._coupling", setting):

                    # Make sure valid value provided
                    if value != "AC" and value != "DC":
                        value = "DC"

                    chan_str = get_chan_str()
                    self.settings[f"AC/DC{chan_str}"] = value
                    self.send_json_settings()
                    return f"{setting}:{value}"

                elif setting == "trigger_level":
                    chan_str = get_chan_str()
                    self.settings[f"Trigger level"] = float(value)
                    self.send_json_settings()
                    return f"{setting}:{value}"
                elif setting == "trigger_coupling":
                    chan_str = get_chan_str()
                    self.settings[f"Ch enable{chan_str}"] = value
                    self.send_json_settings()
                    return f"{setting}:{value}"
                elif setting == "trigger_edge":
                    chan_str = get_chan_str()
                    if value == "POS":
                        value = "Rising"  # ToDo: cheeck that this is valid @Giesbrecht
                    elif value == "NEG":
                        value = "Falling"
                    else:
                        value = "Rising"
                    # Todo: @Giesbrecht check that there aren't any other valid options
                    self.settings[f"Ch enable{chan_str}"] = value
                    self.send_json_settings()
                    return f"{setting}:{value}"
                elif setting == "trigger_channel":
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
                    self.settings[f"Trigger channel"] = value
                    self.send_json_settings()
                    return f"{setting}:{value}"
        except Exception as e:

            logger.error(
                f"An error occured with {self.ID} when sending commands to the instrument.",
                exc_info=True,
            )

    def command(self, cmd: str):
        if not self.online:
            return "Offline"

        # Todo: things probably need to go here

    def try_connect(self):

        # TODO: Make a common ZMQ backend for ZMQCOnnectionTool and ZMQ scope

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
            # Todo: check that this will reconnect automatically, if not fix
            return True

        # Try to connect - restart socket
        if self.socket is not None:
            self.socket.close()
        self.socket = self.context.socket(zmq.REP)
        self.socket.connect(self.zmq_address)

        self.online = True

        return True

    # def restart_port(self):
    #
    #     # Close out old socket
    #     self.socket.close()
    #
    #     # Open new socket
    #     self.socket = self.context.socket(zmq.REP)
    #     self.socket.bind(self.settings["port"])
    #
    #     pstr = self.settings["port"]
    #     self.port_label.setText(f"Port: {pstr}")

    def default_settings(self):
        dflt = {
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
        self.socket.send_string(
            "set scope settings"
        )  # This tells the Pi to get ready for the settings dict
        self.socket.send_string(json.dumps(self.settings))
