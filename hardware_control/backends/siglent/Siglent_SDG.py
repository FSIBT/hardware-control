""" Siglent SDG Series.

.. image:: /images/SDG1000X.png
  :height: 200

See class definition for details.

"""

import logging

from ..base import Backend, ensure_online
from ..utility import regex_compare, get_channel_from_command


logger = logging.getLogger(__name__)


class Siglent_SDG(Backend):
    """A driver for the Siglent SDG Series.

    Instrument home page: https://www.siglent.eu/waveform-generators

    """

    def __init__(self, connection_addr: str):
        super().__init__(instrument_name="SIGLENT-SDG", connection_addr=connection_addr)

    @ensure_online
    def update_setting(self, setting: str, value):

        channel, setting_X = get_channel_from_command(setting)

        if self.dummy:
            return f"{setting}={value}"

        # only one channel on this model of AWG
        if setting_X == "CHX_ENABLED":
            if value == "True":
                self.write(f"C{channel}:OUTP ON")
            else:
                self.write(f"C{channel}:OUTP OFF")
            rval = self.query("C1:OUTP?")
            rval = rval[8:10] == "ON"
            return f"{setting}={rval}"

        if setting_X == "CHX_WAVEFORM":
            wvfm = "SIN"
            if value in ["SINE", "SQUARE", "RAMP", "PULSE", "PRBS", "NOISE", "DC"]:
                wvfm = value
            elif value == "TRIANGLE":
                wvfm = "RAMP"
            elif value == "ARBITRARY":
                wvfm = "ARB"

            self.write(f"C{channel}:BSWV WVTP,{wvfm}")
            rval = self.query(f":C{channel}:BSWV?")
            rval = rval[:-1]  # Trim newline character
            return f"{setting}={rval}"

        if setting_X == "CHX_FREQUENCY":
            self.write(f"C{channel}:BSWV FRQ,{float(value):.6E}")
            rval = self.query(f"C{channel}:BSWV?")
            rval = rval[:-1]
            return f"{setting}={rval}"

        if setting_X == "CHX_AMPLITUDE":
            self.write(f"C{channel}:BSWV AMP,{float(value):.6E}")
            rval = self.query(f"C{channel}:BSWV?")
            rval = rval[:-1]
            return f"{setting}={rval}"

        if setting_X == "CHX_OFFSET":
            self.write(f"C{channel}:BSWV OFST,{float(value):.6E}")
            rval = self.query(f"C{channel}:BSWV?")
            rval = rval[:-1]
            return f"{setting}={rval}"

        if setting_X == "CHX_IMPEDANCE":
            if value == "50":
                self.write(f"C{channel}:OUTP LOAD,50")
            else:
                self.write(f"C{channel}:OUTP LOAD,HZ")
            rval = self.query(f"C{channel}:OUTP?")
            rval = rval[:-1]
            return f"{setting}={rval}"

    @ensure_online
    def command(self, cmd: str):
        pass
