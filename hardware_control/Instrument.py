"""Create an abstract base class for instruments

This defines the interface that should be present for new instruments.

Functions that _have_to_ be implemented are decorated and functions
that _can_ be implemented raise a NotImplementedError.


Note: the real implementation can have different amount of arguments,
e.g. write could be write(channel, value).

"""

from abc import ABC, abstractmethod


class Instrument(ABC):
    @abstractmethod
    def read(self):
        """Read values from instrument.

        If the instrument has multiple values to set, this should
        function should take a channel arguments or something similar.
        """

        pass

    @abstractmethod
    def write(self, value):
        """Write values to instrument.

        This function should take a value or channel/value argument.
        """

        pass

    @abstractmethod
    def try_connect(self):
        """Try to connect to instrument.

        This function should check if we are already connected and in
        that case do nothing. We should be able to call this function
        as often as we want without much overhead.
        """

        pass

    @abstractmethod
    def close(self):
        """Closes any connection that got opened by try_connect"""

        pass

    def is_on(self):
        """Return True/False, if the instrument is on

        This is an optional functions. It is listed here just to give
        the recommended name for this function.
        """

        raise NotImplementedError
