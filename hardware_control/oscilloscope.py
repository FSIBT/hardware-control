"""Create an abstract base class for instruments

This defines the interface that should be present for new instruments.

Functions that _have_to_ be implemented are decorated and functions
that _can_ be implemented raise a NotImplementedError.


Note: the real implementation can have different amount of arguments,
e.g. write could be write(channel, value).

"""

from ..Instrument import Instrument

class Oscilloscope(Instrument):

    @abstractmethod
    def set_time_per_div(self, value:float):
        """Sets the time per division"""
        pass;

    @abstractmethod
    def set_volts_per_div(self, channel:int, value:float):
        """Sets the volts for division for specified channel"""
        pass;

    @abstractmethod
    def set_channel_active(self, channel:int, active:bool):
        """Sets if the specified channel is on or off"""
        pass;

    @abstractmethod
    def set_trigger_param(self, kwargs):
        """Set channel, level, slope, mode, etc"""
        pass;

    @abstractmethod
    def halt(self):
        """Stops aquisition"""
        pass;

    @abstractmethod
    def single_trigger(self):
        """Tells oscilloscope to run with trigger mode set to single trigger"""
        pass;

    @abstractmethod
    def norm_trigger(self):
        """Tell oscilloscope to run with trigger mode set to normal"""
        pass;

    @abstractmethod
    def auto_trigger(self):
        """Tells oscilloscope to run with trigger mode set to auto"""
        pass;

    @abstractmethod
    def set_measurement(self, kwargs):
        """Tells oscilloscope to enable a given measurement (eg. freq, Vpp_avg)"""
        pass;

    @abstractmethod
    def read_measurement(self, kwargs):
        """Reads measurement value from oscilloscope (if measurement first set
        by 'set_measurement()')"""
        pass;
