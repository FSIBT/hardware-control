import socket

import numpy as np
from hardware_control.HC_Backend import HC_Backend, VISA, SOCKET
from hardware_control.utility import regex_compare, to_NR3, to_NR1, bool_NR1

import pyvisa
import logging

logger = logging.getLogger(__name__)


class NI_DAQ:
    def __init__(
        self, connection_addr,
    ):

        self.ID = "KEY4000X"

        self.connection_addr = connection_addr
        self.online = False
        self.dummy = dummy
        self.num_vert_divisions = 8

        self.parse_connection_addr()

        self.try_connect()

    #
    # Tries to connect to the oscilloscope. Is called by the timer every second.
    # If already connected, returns immediately.
    #
    def try_connect(self):

        if self.online:
            return

        if not self.dummy:

            try:
                if self.connection_type == VISA:
                    rm = pyvisa.ResourceManager()
                    self.scope = rm.open_resource(
                        self.connection_addr
                    )  # Open connection
                    # self.configure_read_waveform();
                elif self.connection_type == SOCKET:
                    self.scope = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.scope.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
                    self.scope.connect((self.ip_addr, self.port_no))
            except Exception as e:  # Failed to conncet);
                logger.error("Failed to connect to instrument", exc_info=True)
                self.online = False
            else:
                self.online = True

        else:
            logger.debug(
                f"KEY4000X: creating dummy connection to {self.connection_addr}"
            )
            self.online = True

    #
    # Close connection
    #
    def close(self):
        if not self.dummy and self.online:
            self.scope.close()
        else:
            logger.debug("KEY4000X: closed dummy connection")

    #
    # Receives a state object from the control object.
    #
    def get_state(new_state: dict):
        self.state = new_state

        new = set(self.state.items())
        old = set(self.instr_state.items())

        diff = new - old

        for param in diff:
            update_parameter(param[0], param[1])
            pass

    def set_timebase(self, value: float):
        """Sets the time per division"""
        if not self.dummy:
            self.write(":TIM:SCAL " + to_NR3(value))

    def set_time_offset(self, value: float):
        """Sets the time offset"""
        if not self.dummy:
            self.write(f":TIM:POS {to_NR3(value)}")

    def set_volts_div(self, channel: int, value: float):
        """Sets the volts for division for specified channel"""
        if not self.dummy:
            self.write(":CHAN" + to_NR1(channel) + ":SCAL " + to_NR3(value))

    def set_offset(self, channel: int, value: float):
        """Sets the voltage offset for specified channel"""
        if not self.dummy:
            self.write(":CHAN" + to_NR1(channel) + ":OFFS " + to_NR3(-1.0 * value))

    def set_BW_lim(self, channel: int, value: bool):
        """Sets the bandwidth limit for specified channel"""
        if not self.dummy:
            self.write(":CHAN" + to_NR1(channel) + ":BWL " + bool_NR1(value))

    def set_channel_active(self, channel: int, value: bool):
        """Sets if specified channel is on"""
        if not self.dummy:
            self.write(":CHAN" + to_NR1(channel) + ":DISP " + bool_NR1(value))

    #
    # Value options: 50, 1e6 (Defaults to 1e6 if other value given)
    #
    # @pyqtSlot()
    def set_channel_impedance(self, channel: int, value: float = 1e6):
        """Sets the impedance for specified channel"""
        if not self.dummy:
            if value == 50:
                self.write(":CHAN" + to_NR1(channel) + ":IMP FIFT")
            else:
                self.write(":CHAN" + to_NR1(channel) + ":IMP ONEM")

    def set_channel_label(self, channel: int, value: str):
        """Sets the label for specified channel"""
        if not self.dummy:

            # Length is capped at 32 characters
            if len(value) > 32:
                value = value[0:32]

            self.write(":CHAN" + to_NR1(channel) + ':LAB "' + value + '"')

    def set_labels_enabled(self, value: bool):
        """Enables/disables all channel labels"""
        self.write(":DISP:LAB " + bool_NR1(value))

    def set_channel_invert(self, channel: int, value: bool):
        """Sets the inversion for specified channel"""
        if not self.dummy:
            self.write(":CHAN" + to_NR1(channel) + ":INV " + bool_NR1(value))

    #
    # ie. 10 gives x10 or 10:1 probe
    #
    def set_probe_atten(self, channel: int, value: float):
        """Sets the attenutation of the probe for specified channel"""
        if not self.dummy:
            self.write(":CHAN" + to_NR1(channel) + ":PROB " + to_NR3(value))

    #
    # Value options: AC or DC (Defaults to DC if neither option given)
    #
    def set_channel_coupling(self, channel: int, value: str = "DC"):
        """Sets the channel coupling"""
        if not self.dummy:
            if value == "AC":
                self.write(":CHAN" + to_NR1(channel) + ":COUP AC")
            else:
                self.write(":CHAN" + to_NR1(channel) + ":COUP DC")

    #
    # For edge trigger only
    #
    def set_trigger_level(self, value: float):
        """Set channel, level, slope, mode, etc"""
        if not self.dummy:
            self.write(":TRIG:EDGE:LEV " + to_NR3(value))

    #
    # Value options: AC, DC, LFReject (Defualt DC)
    #
    def set_trigger_coupling(self, value: str):
        """Set trigger coupling mode """
        if not self.dummy:
            if value == "AC":
                self.write(":TRIG:COUP AC")
            elif value == "LFReject":
                self.write(":TRIG:COUP LFReject")
            else:
                self.write(":TRIG:COUP DC")

    #
    # Value options: POS, NEG, EITH, ALT (defualt positive)
    #
    def set_trigger_edge(self, value: str):
        """Set trigger edge """
        if not self.dummy:
            if value == "BOTH":
                self.write(":TRIG:EDGE BOTH")
            elif value == "NEG":
                self.write(":TRIG:EDGE NEG")
            elif value == "ALT":
                self.write(":TRIG:EDGE ALT")
            else:
                self.write(":TRIG:EDGE POS")

    def set_trigger_channel(self, chan: int):
        """SEt trigger source"""
        if not self.dummy:
            self.write(f":TRIG:SOUR CHAN{to_NR1(chan)}")

    def set_trigger_ext(self):
        """SEt trigger source"""
        if not self.dummy:
            self.write(":TRIG:SOUR EXT")

    def halt(self):
        """Stops aquisition"""
        if not self.dummy:
            self.write(":STOP")
        pass

    def digitize(self):
        """Similar to single trigger. Aquires waveform according to :ACQ command
        subsystem. Stops instrument when aquisition is complete. Acquires
        channels currently displayed (can change this with arguments to do more
        or less). """
        if not self.dummy:
            self.write(":DIG")

    def read_all_waveforms(self, ch1, ch2, ch3, ch4):

        wave = {}

        if not self.dummy:
            if ch1:
                wave["CH1"] = self.read_waveform(1)
            if ch2:
                wave["CH2"] = self.read_waveform(2)
            if ch3:
                wave["CH3"] = self.read_waveform(3)
            if ch4:
                wave["CH4"] = self.read_waveform(4)

        return wave

    def single_trigger(self):
        """Tells oscilloscope to run with trigger mode set to single trigger"""
        if not self.dummy:
            self.write(":SING")

    def norm_trigger(self):
        """Tell oscilloscope to run with trigger mode set to normal"""
        if not self.dummy:
            self.write(":RUN")

    def auto_trigger(self):
        """Tells oscilloscope to run with trigger mode set to auto"""
        pass

    def set_measurement(self, parameter: str, avg: str):
        """Tells oscilloscope to enable a given measurement (eg. freq, Vpp_avg)"""
        pass

    def read_measurement(self, parameter: str, avg: str):
        """Reads measurement value from oscilloscope (if measurement first set
        by 'set_measurement()')"""
        pass

    #
    #
    # Returns (V, t) as float[]
    def read_waveform(self, channel: int):
        """Reads a waveform from the oscilloscope."""

        if self.dummy or not self.online:
            return ([], [])

        # Read data from oscilloscope
        try:
            self.write(f":WAV:SOUR CHAN{channel}")
            # Set the source channel
            raw_data = self.query(":WAV:DATA?")
            # Read waveform data
        except:
            self.digitize()
            self.configure_read_waveform()
            raw_data = self.query(":WAV:DATA?")
            # Read waveform data

        x_orig = self.query(":WAV:XOR?")
        # Read X Origin
        x_ref = self.query(":WAV:XREF?")
        # Read X Reference
        x_incr = self.query(":WAV:XINC?")
        # Read X Increment

        try:
            # x_orig = float(x_orig[0:len(x_orig)-1]); #Convert X Origin
            x_orig = float(x_orig[0 : len(x_orig)])
            # Convert X Origin
        except Exception as e:
            logger.error("ERROR: Received bad origin from scope.", exc_info=True)
            return ([], [])
        try:
            # x_ref = float(x_ref[0:len(x_ref)-1]); #Convert X Reference
            x_ref = float(x_ref[0 : len(x_ref)])
            # Convert X Reference
        except Exception as e:
            logger.error("ERROR: Received bad reference from scope.", exc_info=True)
            return ([], [])
        try:
            # x_incr = float(x_incr[0:len(x_incr)-1]); #Convert X Increment
            x_incr = float(x_incr[0 : len(x_incr)])
            # Convert X Increment
        except Exception as e:
            logger.error("ERROR: Received bad increment from scope.", exc_info=True)
            return ([], [])

        try:
            # Format and convert data into float[]
            block_header = raw_data[0:10]
            raw_data = raw_data[
                11 : len(raw_data) - 1
            ]  # Trim block header from packet & remove newline character from end
            fmt = [float(x.strip()) for x in raw_data.split(",")]
            # Break at commas, strip whitespace, convert to float, add to array

            t = (
                (np.linspace(0, len(fmt), len(fmt), False) - x_ref) * x_incr + x_orig
            ).tolist()
            # Calculate time values
        except Exception as e:
            logger.error("ERROR: Failed to calculate V & t.", exc_info=True)
            return ([], [])

        return (fmt, t)

    def configure_read_waveform(self):
        """Sets the data transfer mode of the oscilloscope. Call this function
        once before reading waveform data with 'read_waveform()'. """

        self.write(":WAV:FORM ASC")
        # Sets data format to ASCII text
        self.write(":WAV:POIN 1000")
        # Set the number of points to read to 1000 (OPtions: 1000, 500, 250, 100, MAX (~4M))
        self.write(":WAV:POIN:MODE NORM")
        # Set data record to transfer to 'measurement record'
        self.write(":ACQ:TYPE NORM")
        # Set aquisition mode to normal

    def write(self, command: str):
        if self.online and not self.dummy:
            if self.connection_type == VISA:
                self.scope.write(command)
            elif self.connection_type == SOCKET:
                self.scope.sendall(bytes(command + "\n", "utf-8"))
            logger.debug(f'\tKEY4000X< "{command}"')

    def query(self, command: str):
        if self.online and not self.dummy:
            if self.connection_type == VISA:
                reply = self.scope.query(command)
            elif self.connection_type == SOCKET:
                self.scope.sendall(bytes(command + "\n", "utf-8"))
                reply_bytes = recvall(self.scope)
                logger.debug(f"reply size: {len(reply_bytes)}")
                reply = str(reply_bytes)
                if len(reply) < 100:
                    logger.debug("\t\t" + reply)
                reply = reply[2 : len(reply) - 3]
            logger.debug(f'\t{self.ID}< "{command}"')
            return reply
        else:
            return ""


def recvall(sock):
    BUFF_SIZE = 4096  # 4 KiB
    data = b""
    while True:
        part = sock.recv(BUFF_SIZE)
        data += part
        t_str = str(part)
        if t_str[len(t_str) - 3 : len(t_str) - 1] == "\\n":
            break
    return data


# 71-209
