from collections import OrderedDict
import json
import logging
import abc
import sip

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QGroupBox

from .Comm import Comm

logger = logging.getLogger(__name__)

ipy_logger = logging.getLogger("ipykernel")
ipy_logger.setLevel("ERROR")


class CombinedMetaclass(sip.wrappertype, abc.ABCMeta):
    """
    This class inherits from the metaclasses used in both QGroupBox and ABC. This
    enables hc.Instrument to subclass both QGroupBox and ABC.
    """

    pass


class Instrument(QGroupBox, abc.ABC, metaclass=CombinedMetaclass):

    # ramp_mode options
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    OFF = "off"

    def __init__(self, app, name: str, backend=None, lock_until_sync=False):
        super().__init__(name)
        self.settings = OrderedDict()
        self.values = OrderedDict()
        self.values_unit = OrderedDict()
        self.app = app  # The main hc.app
        self.name = name
        self.backend = backend
        self.manufacturer = None
        self.company = None
        self.online = False
        self.comm = None
        self.address = None

        self.update_settings_hooks = []
        self.update_values_hooks = []

        if self.backend:
            self.backend.dummy = self.app.dummy
            self.address = self.backend.connection_addr

        # Dictates if instrument should be ignored by widgets listing online
        # status (such as the connection widget)
        self.ignore = False

        # Dictates if instrument should be ignored by widgets or lists collecting
        # all instruments with settings to adjust. For example, the scan_widget
        # will not list instruments with ignore_control=True because the scan
        # widget is offering a list of controllable intruments.
        self.ignore_control = False

        self.address = ""  # This is used mostly for displaying the instrument's
        # address to the user

        self.online_callback = None

        if backend is not None:
            if backend.connection_addr in self.app.comms:
                self.comm = self.app.comms[backend.connection_addr]
                self.comm.addWidget(self)
            else:
                self.app.comms[backend.connection_addr] = Comm(
                    backend, self, lock_until_sync=lock_until_sync
                )
                self.comm = self.app.comms[backend.connection_addr]

        self.us_hooks = []  # Run every time update settings is called
        self.ramp_hooks = []  # Run every time update_ramp is called
        self.ramp_mode = Instrument.OFF
        self.ramp_val = OrderedDict()
        self.ramp_target = OrderedDict()
        self.default_ramp_speed = 100  # Units/sec
        self.ramp_speed = {}  # Override default_ramp_speed for specific parameters here
        self.ramp_update_period = 1e3  # time between ramp steps in ms

        # Global Constants
        self.globalRefreshRate = 1000  # ms refresh
        # this is a global reference for limiting the scaling the widgets
        self.globalLineHeight = 50  # Lineheight of athe average  spinbox
        self.globalLineWidth = 300  # Linewidth of athe average  spinbox
        self.online_color = (
            "Green"  # Color of online light for status tool. Can be Green or Blue
        )

        # ConnectionTool and ScanWidget widgets

        self.app.add_instrument(self)

        self.ramp_timer = QTimer(self)
        self.ramp_timer.timeout.connect(self.update_ramp)

    def __repr__(self):
        return (
            f"Instrument {self.name} {self.manufacturer} @ {self.address}"
            f" online:{self.online}"
        )

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.name}"

    def backend_return_listdata(self, descr: str, data1: list, data2: list):
        """Is called by self.comm when the backend returns from command_listdata,
        which returns a string and two lists. The author of the UI can overwrite
        this function to process the return data."""
        pass

    def init_values(self):
        """Initializes the values dictionary.

        The values dictionary should consist of empty strings at the
        beginning of the program whereas the default_state should
        contain strings of the default values.

        The values loaded into the values dict by this function will
        also be used by the read_state_from_backend() function to
        initialize the settings dictionary and/or UI.

        """

        self.values = {key: "" for key in self.default_state()}

    @abc.abstractmethod
    def default_state(self):
        """Sets the default values for all known settings of the instrument.

        Needs to be defined in each Instrument.
        """
        pass

    @abc.abstractmethod
    def settings_to_UI(self):
        """ Overwrites the values in the UI with the values in self.settings """

        pass

    def set_online_callback(self, callback_function):
        """
        This function allows the user to specify a callback function which will
        be called when the backend reports 'online' the next time.
        """

        if not callable(callback_function):
            logger.warning(
                f"Specified a non-callable object ({callback_function}) for"
                f" a callback function. "
            )
            return

        self.online_callback = callback_function

    def update_ramp(self):

        # List of parameters to remove from ramp_target after for loop. Note that
        # removing items from dict while iterating over dict is not well-defined,
        # hence why 'pop_list' is neccesary
        pop_list = []

        if self.ramp_mode == Instrument.MANUAL:

            # For each parameter being ramped
            for key in self.ramp_target:

                # Get current value. Set to 0 if not specified
                curr = 0
                if key in self.ramp_val:
                    curr = self.ramp_val[key]
                elif key in self.values:
                    curr = self.values[key]
                try:
                    curr = float(curr)
                except:
                    logger.warning("Invalid value for 'curr'. Ramping from 0.")
                    curr = 0

                # Run all hooks
                for rhook in self.ramp_hooks:

                    if callable(rhook):
                        try:
                            curr = rhook(self, key, curr, self.ramp_target[key])
                        except:
                            logger.warning(
                                f"Call to hook '{rhook}' failed. skipping. ",
                                exc_info=True,
                            )

                # If curr is None, that indicates ramp is
                # complete. Delete value from targets
                if curr is None:
                    pop_list.append(key)
                else:
                    self.ramp_val[key] = curr
                    self.comm.update_setting(key, str(curr))

            for pkey in pop_list:
                self.ramp_target.pop(pkey, None)

        if self.ramp_mode == Instrument.AUTOMATIC:

            logger.debug("Callback Automatic ramp")

            # For each parameter being ramped
            for key in self.ramp_target:

                logger.debug(f"Handling ramp for parameter {key}")

                # Get current value. Set to 0 if not specified
                curr = 0
                if key in self.ramp_val:
                    curr = self.ramp_val[key]
                elif key in self.values:
                    curr = self.values[key]
                try:
                    curr = float(curr)
                except:
                    logger.warning("Invalid value for 'curr'. Ramping from 0.")
                    curr = 0

                logger.debug(f"Value at start for parameter {key} was {curr}")

                # Get increment
                if key in self.ramp_speed:
                    dVal = self.ramp_speed[key]
                else:
                    dVal = self.default_ramp_speed
                try:
                    dVal = float(dVal)
                except:
                    logger.error(
                        "Ramp speeds must be floats. Cannot ramp."
                        " Changing ramp_mode to OFF."
                    )
                    self.ramp_mode = Instrument.OFF
                    self.ramp_timer.stop()
                    return

                logger.debug(f"Increment for parameter {key} will be {dVal}")

                # Update value
                if self.ramp_target[key] > curr:
                    curr = min(curr + dVal, self.ramp_target[key])
                else:
                    curr = max(curr - dVal, self.ramp_target[key])

                logger.debug(f"New value for parameter {key} will be {curr}")

                # If curr is None, that indicates ramp is
                # complete. Delete value from targets
                if curr == self.ramp_target[key]:
                    pop_list.append(key)

                self.ramp_val[key] = curr
                self.comm.update_setting(key, str(curr))

            for pkey in pop_list:
                self.ramp_target.pop(pkey, None)

        # IF all ramps complete, stop timer
        if len(self.ramp_target) < 1:
            logger.debug("Killing ramp timer")
            self.ramp_timer.stop()

    def remote_update_setting(self, setting: str, value: str):
        """ Calls update_setting to update backend, then uses setting_to_UI.

        A function to be called from outside the widget which both updates the
        widget and backend.

        Parameters
        ----------
        setting : str
            Setting to update
        calue : str
            New value for setting

        Returns
        -------
        None
        """

        self.update_setting(setting, value)
        self.settings_to_UI()

    def update_setting(self, setting: str, value: str):
        """Update a setting in settings dictionary and send it to the backend.

        The user has the option to set hooks that can modify the
        values. The hooks get called before the value is set and send
        to the backend. The hook needs to return the value or None if
        the value should **not** be set.

        """

        if setting not in self.settings:
            logger.error(
                f"Key '{setting}' does not exist for instrument '{self.name}'"
                f" in settings dictionary.",
                exc_info=True,
            )
            return

        for hook in self.update_settings_hooks:
            if callable(hook):
                value = hook(setting, value)
                if value is None:
                    return

        self.settings[setting] = value

        if self.comm is not None:
            # If ramp mode is on, set the target value and activate the timer
            if self.ramp_mode in [Instrument.AUTOMATIC, Instrument.MANUAL]:
                try:
                    self.ramp_target[setting] = float(value)
                except:
                    logger.warning(
                        f"Cannot set received value '{value}' as ramp target"
                        f" value because it cannot be converted to a float."
                        f" Setting '{setting}' directly to '{value}'."
                    )
                    self.comm.update_setting(setting, value)
                    return
                if not self.ramp_timer.isActive():
                    self.ramp_timer.start(self.ramp_update_period)
                return

            self.comm.update_setting(setting, value)

    def command(self, cmd_str: str):
        """Update a setting in settings and values dictionary for the instrument"""

        if self.comm is not None:
            self.comm.command(cmd_str)

    def command_listdata(self, cmd_str: str):
        """Send a command to the instrument and get a string and two lists back"""

        if self.comm is not None:
            self.comm.command_listdata(cmd_str)

    def set_setting(self, parameter: str, value: str):
        """Adjusts a parameter in 'self.settings' and updates any GUI elements to reflect the change."""

        # Find instrument, get current setting for parameter
        try:
            current_val = self.settings[parameter]
        except KeyError:
            logger.error(
                "Key '{parameter}' does not exist for instrument '{self.name}'.",
                exc_info=True,
            )

        if isinstance(current_val, str):
            try:
                self.settings[parameter] = value
            except:
                logger.error(
                    f"Failed to convert {type(value)} '{value}' to string.",
                    exc_info=True,
                )
                return False
        elif isinstance(current_val, (int, float)):
            try:
                self.settings[parameter] = float(value)
            except:
                logger.error(
                    f"Failed to convert {type(value)} '{value}' to float. Exiting scan.",
                    exc_info=True,
                )
                return False

        else:
            logger.error(
                f"Settings must have string, float, or int datatype.\n"
                f"\tInstrument '{self.name}' setting {parameter} has"
                f" type: {type(current_val)}"
            )
            return False

        return True

    def load_state(self, filename: str):
        """Reads the settings dictionary from file"""

        # Get default state - this identifies all required fields
        dflt = self.default_state()

        # Read a settings from file
        try:
            with open(filename) as file:
                self.settings = json.load(file)
                logger.info(f"settings for {self.name} read from file '{filename}'")
        except:
            logger.error(
                f"Failed to read file '{filename}'. Using defualt case.", exc_info=True
            )
            self.settings = self.default_state()

        # Ensure all fields in default_state are present in the loaded state
        for key in dflt:
            if not (key in self.settings):
                self.settings[key] = dflt[key]

    def save_state(self, filename: str):
        """Saves the instrument state to a JSON file"""
        try:
            with open(filename, "w") as file:
                json.dump(self.settings, file)
                logger.info(f"settings for {self.name} saved to file '{filename}'")
        except Exception:
            logger.error(
                f"Failed to write file '{filename}'. settings not saved.", exc_info=True
            )

    def send_state(self):
        """Writes the entire state/settings dicitonary to the oscilloscope"""
        for key in self.settings:
            if self.comm is not None:
                self.comm.update_setting(key, str(self.settings[key]))

    def read_state_from_backend(self):

        if self.comm is None:
            logger.warning("Failed to read state from backend. 'Comm' is None.")
            return

        # Send a query to the backend for every possible value
        for v in self.values:
            self.comm.command(f"{v}?")

        # Send a 'sync' command to the backend. It will be returned
        # immediately and used by the backend as an indicator for when all
        # of the previous commands have been processed

        self.comm.command("SYNC_BACKEND")

    def close(self):
        if self.comm is not None:
            self.comm.close()

    def read_values(self, prefix: str):
        """Looks for an entry in self.values with the key 'prefix'. If found, the
        key's value is returned, else it returns None."""

        return self.values.get(prefix, None)

    def sync_backend_called(self):
        """
        This function is called when 'SYNC_BACKEND' is received from hc.Comm. It
        is used in read_state_from_backend to indicate when the backend has sent
        all queried values back to the front end.
        """

        # Transfer 'values' to 'settings'
        for v in self.values:
            if v in self.settings:
                self.settings[v] = self.values[v]

        # Transfer 'settings' to UI
        self.settings_to_UI()

    def backend_return(self, retval: str):
        """This function is called by self.comm when the backend returns a value.

        The return string is converted here into a dictionary's
        key/value pair and added to self.values.  An equals sign ('=')
        is used to separate the key and value, with key coming
        first.

        The user can add hooks that will receive the key and value. If
        the hook returns True, the other hooks will not be called.

        Parameters
        ----------
        retval : str
             most of the times this will be of the form "<setting_name>=<value>"

        """

        if retval == "SYNC_BACKEND":
            self.sync_backend_called()

        sep_idx = retval.find("=")
        if sep_idx != -1:  # Separator was found...
            key = retval[0:sep_idx]
            value = retval[sep_idx + 1 :]
        else:  # If no separator, put under 'Misc'
            key = "Misc"
            value = retval

        self.values[key] = value

        for hook in self.update_values_hooks:
            if callable(hook):
                ret = hook(key, value)
                if ret:
                    return

    def backend_return_online(self, connected: bool):
        """Is called by self.comm when the backend returns an online status."""

        self.online = connected

        if self.online_callback is None:
            return

        if not callable(self.online_callback):
            self.online_callback = None
            return

        self.online_callback(self)
        self.online_callback = None

    def backend_return_log(self, retval: str, point_data):
        """Performs the logging action before backend_return() updates the UI.

        When hc.Comm's command_log() returns, backend_return_log() is called
        prior to backend_return(). backend_return_log() stores the value in
        self.values, or whatever else it may be configured to do.
        """

        found = False
        for ds in self.app.data_sets:
            if point_data.dataset_name == ds.name:

                sep_idx = retval.find("=")
                if sep_idx == -1:
                    logger.error(
                        "Failed to find '=' in return string after call to command_log()",
                        exc_info=True,
                    )
                    return False

                key_param = retval[0:sep_idx]
                val = retval[sep_idx + 1 :]

                key_name = point_data.instrument_name + ":" + key_param
                ds.data[key_name].append(val)
                found = True

        if not found:
            return False

        return True

        # TODO: Record 'id' for each measurement
        # TODO: Erase measurements with corresponding ID if one fails

    def get_header(self, parameters=None):
        """ Returns a header to describe what is returned by get_values(). It
        must be overwritten by the instrument if the instrument is to be
        compatible with asynchronous logging datasets.

            Example 1:
                return ' '.join([ch.get_header() for ch in self.channels])

            Example 2:
                return 'HV-Voltage[V] HV-Current[A] Pressure[mTorr]' """

        # Make sure parameters is list or None
        if parameters is not None and not isinstance(parameter, list):
            return None

        #
        header = ""
        for v in self.values:

            # If parameters is a list (not None) and 'v' is not listed, skip
            if v is not None and v not in parameters:
                continue

            header = header + v
            if v in self.values_unit:
                unit = self.values_unit[v]
                header = header + f"[{unit}] "
            else:
                self.values_unit[v] = "?"
                header = header + " "
        return header

    def get_value_keys(self, parameters=None, require_all: bool = True):
        """ Returns the keys of the values tracked by the instrument. This
        function is called by datasets during asynchronous logging. If an
        instrument is to work with asynchronous logging, it must overwrite this
        function to return the parameters it wants to track. These parameters
        must match what is listed in get_header().

        If require_all is true and not all requested parameters are present the
        function returns None.

        Example:
            return ['voltage', 'current', 'pressure'] """

        # If nothing specified, return all values
        if parameters is None:
            return [str(v) for v in self.values]

        # Otherwise make sure is list
        if not isinstance(parameters, list):
            logger.info(
                f"get_value_keys() received bad 'parameters' argument."
                f" type must be list or None but was '{type(parameters)}'."
            )
            return None

        rval = []
        for p in parameters:

            if not require_all:
                rval.append(p)
                continue

            if p in self.values:
                rval.append(p)
            else:
                logger.warning(
                    f"get_value_keys() skipped parameter '{p}' because it"
                    f" was not listed in values ({self.values})"
                )
                return None
        return rval
