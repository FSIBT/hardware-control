from functools import wraps
import json
import logging
from pathlib import Path
import threading
import time
from typing import Any
from collections.abc import Callable
import datetime

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import zmq

from .Dataset import Dataset
from .Instrument import Instrument
from .ZMQAdapter import ZMQAdapter
from .ZMQRemoteAdapter import ZMQRemoteAdapter
from .hooks import call_hooks
from .alarm_manager import AlarmManager
from .error_handling import handle_file_operation

logger = logging.getLogger(__name__)


def ensure_instrument_exists(f):
    """Error check to make sure that an instrument exists in the app.

    This decorator assumes that the first argument of the decorated function
    is the app class and the second argument is the instrument name.
    """

    @wraps(f)
    def wrapped(*args, **kwargs):
        self = args[0]
        instrument = args[1]

        if instrument not in self._data:
            logger.error(
                f"Cannot find instrument '{instrument}' in {f.__name__} in app"
            )
            return

        return f(*args, **kwargs)

    return wrapped


def ensure_parameter_and_instrument_exists(f):
    """Error check to make sure that a parameter/command exists in the app.

    This decorator assumes that the first argument of the decorated function
    is the app class, the second argument is the instrument name, and the
    third is the parameter name.
    """

    @wraps(f)
    def wrapped(*args, **kwargs):
        self = args[0]
        instrument = args[1]
        parameter = args[2]

        if instrument not in self._data:
            logger.error(
                f"Cannot find instrument '{instrument}'  in {f.__name__} in app"
            )
            return

        if parameter not in self._data[instrument]:
            logger.error(
                f"Cannot find parameter/command '{parameter}' for instrument '{instrument}' in {f.__name__} in app"
            )
            return

        return f(*args, **kwargs)

    return wrapped


class App(QApplication):
    """The main app class.

    This class should be used to create the main Qt app in your
    program. It keeps track of all connected instruments, settings,
    and current data.
    """

    def __init__(self, ipaddress=None, dummy: bool = False) -> None:
        # QApplication can take a list of strings, e.g. from sys.argv
        # we currently don't use this
        super().__init__([])

        self.threads = []
        self.stop_threads_event = threading.Event()
        self._data = {}
        self.zmq_subscribers = {}
        self.birth_time = datetime.datetime.now(datetime.UTC)

        self.alarm_manager = AlarmManager(app=self)

        # publisher that announces commands for instruments
        if ipaddress is None:
            self.ipaddress = "127.0.0.1"
        else:
            self.ipaddress = ipaddress
        self.zmq_publisher_address = f"tcp://{self.ipaddress}"
        self.zmq_context = zmq.Context()
        # to talk to all the instruments
        self.zmq_publisher = self.zmq_context.socket(zmq.PUB)

        port = self.zmq_publisher.bind_to_random_port(self.zmq_publisher_address)
        self.zmq_publisher_address = f"{self.zmq_publisher_address}:{port}"
        # to handle queries from other programs
        self.zmq_info = self.zmq_context.socket(zmq.REP)
        port = self.zmq_info.bind_to_random_port(f"tcp://{self.ipaddress}")
        self.zmq_info_address = f"tcp://{self.ipaddress}:{port}"

        self.dummy = dummy
        self.additional_save_formats = {}

        # keep track of datasets, so that we can autosave, etc.
        self.data_sets = {}

        # keep track of virtual instruments (no hardware connection)
        self.virtual_instruments = set()

        # keep a list of parameters that should be updated periodicaly
        # This is a set of (<instrument name>,<parameters>) combinations
        self.request_updates = set()
        # keep a list of parameters that should be skipped. For example
        # when a parameter it not implemented in an instrument driver,
        # but does exists in a GUI
        self.skip_request_updates = set()
        # keep a list of commands that should be called periodicaly
        # This is a set of (<instrument name>,<commands>,<status>) combinations
        self.continuous_commands = set()

        # a timer to check ZMQ messages
        self.zmq_timer = QTimer(self)
        self.zmq_timer.timeout.connect(self.parse_message_from_instruments)
        self.zmq_timer.timeout.connect(self.handle_request)
        self.zmq_timer.start(100)

        # a timer to requests updates from instruments
        self.update_instrument_timer = QTimer(self)
        self.update_instrument_timer.timeout.connect(self.update_instruments)
        self.update_instrument_timer.timeout.connect(self.call_continuous_commands)
        self.update_instrument_timer.start(1000)

        # default refresh rate used by many GUI elements
        self.globalRefreshRate = 1000

    def stop(self) -> None:
        """Stop all threads and wait until they return."""
        # first set the event which will trigger the while loop in the
        # thread's run function to stop
        self.stop_threads_event.set()

        # wait for all threads to end with timeout
        timeout_seconds = 5.0
        for t in self.threads:
            if hasattr(t, "is_alive"):  # Regular threads (ZMQAdapter)
                t.join(timeout=timeout_seconds)
                if t.is_alive():
                    logger.warning(
                        f"Thread '{t.name}' did not stop within {timeout_seconds}s timeout"
                    )
            else:  # Remote adapters (have join method but not is_alive)
                try:
                    t.join()
                except Exception as e:
                    logger.warning(f"Error stopping remote adapter '{t.name}': {e}")

    def handle_request(self) -> None:
        """Handle requests from other programs.

        This provides an interface for other programs to get
        values. In principle this could also enable remote control in
        the future.

        To make use of this, the other program has to setup a ZMQ REQ
        socket. For example using:

        > import zmq
        > c = zmq.Context()
        > s = c.socket(zmq.REQ)
        >
        > s.connect("tcp://127.0.0.1:1235")
        > s.send_string('get_instrument_parameter(ADAM_6024,CH0_READ_VOLTAGE)')
        >
        > s.recv_string()
        > '1.0'

        We implement the get_instrument_parameter function and perhaps should
        also support similar other function in the future.

        The value will be returned directly as a string.

        """
        while True:
            try:
                msg = self.zmq_info.recv_string(flags=zmq.NOBLOCK)
                logger.debug(f"App got request '{msg}'")

                if msg.startswith("get_instrument_parameter"):
                    msg = msg.replace("get_instrument_parameter", "")
                    msg = msg[1:-1]  # remove ()

                    name, parameter = msg.split(",")
                    name = name.strip().replace("'", "")
                    parameter = parameter.strip().replace("'", "")

                    value = self.get_instrument_parameter(name, parameter)

                self.zmq_info.send_string(str(value))
            except zmq.ZMQError:
                break

    @ensure_instrument_exists
    def register_parameters_and_commands(
        self, instrument: str, read_parameters, set_parameters, commands
    ) -> None:
        """Adds all parameter names to a data dictionary and sets default values."""
        for r in read_parameters:
            p = {
                "read_value": None,
                "set_value": None,
                "post_read_hooks": [],
                "pre_set_hooks": [],
                "widgets": [],
            }
            self._data[instrument][r] = p
        for s in set_parameters:
            p = {
                "read_value": None,
                "set_value": None,
                "post_read_hooks": [],
                "pre_set_hooks": [],
                "widgets": [],
            }
            self._data[instrument][s] = p
        for c in commands:
            p = {
                "pre_call_hooks": [],
                "widgets": [],
            }
            self._data[instrument][c] = p

    def add_dataset(self, dataset: Dataset) -> None:
        """Add a dataset object to the app. See the Dataset base class for more details."""
        name = dataset.name
        if name in self.data_sets:
            logger.error(f"Dataset {name} already exists... not adding dataset to App.")
            return
        self.data_sets[name] = dataset

    def add_virtual_instrument(
        self, instrument_name: str, parameters: list[str]
    ) -> None:
        """Add a virtual instrument with no hardware connection.

        Virtual instruments can be used for data sources that don't have
        physical hardware connections, such as:
        - Web scraping data
        - Calculated values
        - External API data
        - Manual data entry

        Virtual instruments integrate with the rest of the framework:
        - Work with HCLabel and other widgets
        - Can be logged in Datasets
        - Support post_read_hooks (via add_post_hook)
        - Trigger alarms via alarm_manager

        Parameters
        ----------
        instrument_name : str
            Name of the virtual instrument
        parameters : list[str]
            List of parameter names to create
        """
        if instrument_name in self._data:
            logger.error(
                f"Instrument {instrument_name} already exists... cannot add virtual instrument"
            )
            return

        self.virtual_instruments.add(instrument_name)
        self._data[instrument_name] = {}

        for param_name in parameters:
            self._data[instrument_name][param_name] = {
                "read_value": None,
                "widgets": [],
                "post_read_hooks": [],
            }

        logger.info(
            f"Added virtual instrument '{instrument_name}' with parameters: {parameters}"
        )

    def update_virtual_instrument_parameter(
        self, instrument: str, parameter: str, value: Any
    ) -> None:
        """Update a virtual instrument parameter value.

        This will:
        - Apply post_read_hooks
        - Update the stored value
        - Trigger alarm checks
        - Update all registered widgets

        Parameters
        ----------
        instrument : str
            Virtual instrument name
        parameter : str
            Parameter name
        value : Any
            New value (will be converted to string after hooks)
        """
        # Validate it's a virtual instrument
        if instrument not in self.virtual_instruments:
            logger.error(f"{instrument} is not a virtual instrument")
            return

        if parameter not in self._data[instrument]:
            logger.error(
                f"Parameter {parameter} not found in virtual instrument {instrument}"
            )
            return

        # Apply hooks
        post_read_hooks = self._data[instrument][parameter]["post_read_hooks"]
        value = call_hooks(post_read_hooks, str(value))

        if value is not None:
            # Update value
            self._data[instrument][parameter]["read_value"] = value

            # Check alarms
            self.alarm_manager.process_update(instrument, parameter, value)

            # Update widgets
            for widget in self._data[instrument][parameter]["widgets"]:
                widget.hc_update()

    def add_instrument(
        self,
        instrument: Instrument,
        ignore_flag: bool | None = False,
    ) -> None:
        """Add an instrument object to the app. See the Instrument base class for more details."""
        if instrument.name in self._data:
            logger.error(
                f"Instrument {instrument.name} already exists... instruments names need to be unique"
            )
            return

        # Prevent adding hardware instrument if name is used by virtual instrument
        if instrument.name in self.virtual_instruments:
            logger.error(
                f"Cannot add hardware instrument {instrument.name} - name already used by virtual instrument"
            )
            return

        instrument._dummy = self.dummy

        zmq_instrument = ZMQAdapter(
            instrument,
            self.stop_threads_event,
            self.zmq_context,
            publisher=self.zmq_publisher_address,
        )

        # subscribe to the instrument
        # there might be an option to only use one subscriber and
        # subscribe to multiple publisher for now we create multiple subscribers
        subscriber = self.zmq_context.socket(zmq.SUB)
        subscriber.connect(
            f"tcp://{self.ipaddress}:{zmq_instrument.zmq_publisher_port}"
        )
        subscriber.subscribe("")
        self.zmq_subscribers[instrument.name] = subscriber

        # register all possible read/write operations
        if zmq_instrument.instrument.name not in self._data:
            self._data[zmq_instrument.instrument.name] = {}

        reads, sets, commands = zmq_instrument.instrument.list_parameters()
        self.register_parameters_and_commands(
            zmq_instrument.name, reads, sets, commands
        )

        # register an ignore flag for the instrument
        self._data[zmq_instrument.name]["IGNORE"] = ignore_flag

        # some time for ZMQ to set things up
        time.sleep(1)

        # start thread
        self.threads.append(zmq_instrument)
        zmq_instrument.start()

    def add_remote_instrument(self, name: str, address: str) -> None:
        """Connect to a instrument driver on, for example, a different computer.

        This is relatively straightforward since the ZMQ publishers
        that update the data model do not care about which computer
        they are running on. The main task is to create subscribers to
        the already existing publishers (from the app and on the
        remote side). This task is mostly handled by
        :class:`~.base.ZMQRemoteAdapter.ZMQRemoteAdapter`.

        Parameters
        ----------
        name
           The remote instrument name
        address
           The ipaddress:port combination where the remote instrument is running
        """
        if name in self._data:
            logger.error(
                f"Instrument {name} already exists... instruments names need to be unique"
            )
            return

        zmq_instrument = ZMQRemoteAdapter(
            name,
            address,
            self.zmq_context,
            self.zmq_publisher_address,
        )

        subscriber = self.zmq_context.socket(zmq.SUB)
        subscriber.connect(
            f"tcp://{zmq_instrument.instrument_ipaddress}:{zmq_instrument.instrument_port}"
        )
        subscriber.subscribe("")
        self.zmq_subscribers[zmq_instrument.name] = subscriber

        if zmq_instrument.name not in self._data:
            self._data[zmq_instrument.name] = {}
        reads, sets, commands = zmq_instrument.list_parameters()
        self.register_parameters_and_commands(
            zmq_instrument.name, reads, sets, commands
        )

        # save somewhere to be able to call close, this works, since
        # we add a .join() method to the ZMQ remote instrument
        self.threads.append(zmq_instrument)

    def parse_message_from_instruments(self) -> None:
        """Check for messages from the instruments.

        Call any defined hooks and update any widgets.
        Also check alarms.

        """
        for name, sub in self.zmq_subscribers.items():
            # handle all messages in queue
            while True:
                try:
                    msg = sub.recv_string(flags=zmq.NOBLOCK)
                except zmq.ZMQError:
                    break
                logger.debug(f"App got '{msg}' from '{name}'")

                try:
                    inst_name, parameter, value = msg.split()
                except ValueError:
                    logger.error(
                        f"{msg.split()} has too few or too many values (expected 3)."
                    )
                    continue

                if inst_name != name:
                    logger.error(
                        f"Message topic mismatch: expected '{name}', got '{inst_name}'"
                    )
                    continue

                if name not in self._data:
                    logger.error(f"{name} not available in data model")
                    continue

                if parameter not in self._data[name]:
                    logger.error(f"{parameter} not available for instrument {name}")
                    continue

                post_read_hooks = self._data[name][parameter]["post_read_hooks"]
                value = call_hooks(post_read_hooks, value)
                if value is not None:
                    # update value
                    self._data[name][parameter]["read_value"] = value

                    # check alarms
                    self.alarm_manager.process_update(name, parameter, value)

                    # update widgets
                    for w in self._data[name][parameter]["widgets"]:
                        w.hc_update()

    def update_instruments(self) -> None:
        """Update the app's dictionary of instrument parameter values in a desginated set of parameters."""
        for instrument, parameter_or_function in self.request_updates:
            if (instrument, parameter_or_function) in self.skip_request_updates:
                continue
            online = self.get_instrument_parameter(instrument, "ONLINE")
            if online is None or online == "False":
                continue
            if callable(parameter_or_function):
                parameter_or_function()
            else:
                self.update_instrument_parameter(
                    instrument, parameter_or_function, priority=0
                )

    @ensure_instrument_exists
    def add_auto_update_instrument_parameter(
        self, instrument: str, parameter: str
    ) -> None:
        """Add an instrument's parameter to a list for automatic updates.

        The app class provides a mechanism to automaticaly update
        instrument parameters by querying the instrument in a regular
        interval.

        To limit the number of requests and how much data we exchange with an
        instrument driver, not all parameters are automatically
        updated all the time. This function can be used to enable
        automatic updates.
        """
        if not callable(parameter):
            if parameter not in self._data[instrument]:
                logger.error(
                    f"Cannot find parameter/command '{parameter}' for instrument '{instrument}' in app."
                )
                return

        logger.debug(f"register {instrument}->{parameter} for auto updates")
        self.request_updates.add((instrument, parameter))

    def call_continuous_commands(self, priority=0) -> None:
        """Call all commands that are to be called continuously."""
        for instrument, command, status in self.continuous_commands:
            online = self.get_instrument_parameter(instrument, "ONLINE")
            if online is None or online == "False" or status == False:
                return
            self.call_instrument_command(instrument, command, priority)

    @ensure_instrument_exists
    def add_continuous_command(
        self, instrument: str, command: str, status: bool = False
    ) -> None:
        """Add an instrument's parameter to a list of continuously-called commands.

        The app class provides a mechanism to call instrument commands once every
        regular interval. The command will not be called continuously unless the
        status parameter in the self.continuous_commands set is set to True.
        """
        if command not in self._data[instrument]:
            logger.error(
                f"Cannot find parameter/command '{command}' for instrument '{instrument}' in app."
            )
            return

        logger.debug(f"register {instrument}->{command} as a continuous command")
        self.continuous_commands.add((instrument, command, status))

    def add_skip_update_instrument_parameter(
        self, instrument: str, parameter: str
    ) -> None:
        """A method to skip automatic updates for certain parameters.

        This is mostly used for parameters that are defined in a GUI
        but not in an instrument driver. For example, some scopes only
        have highZ inputs and no option to change the input impedance.
        The GUI might define this parameter to be automatically
        updated,vi which would lead to logging errors/warnings. By putting it
        on the skip list, the automated update will just not request an update.
        """
        self.skip_request_updates.add((instrument, parameter))

    @ensure_instrument_exists
    def is_parameter(self, instrument: str, parameter: str) -> bool:
        """Check if the app knows about this instrument parameter."""
        return parameter in self._data[instrument]

    @ensure_parameter_and_instrument_exists
    def set_instrument_parameter(
        self,
        instrument: str,
        parameter: str,
        value: Any,
        priority: int = 1,
        skip_hooks=False,
    ) -> None:
        """Send the value to the instrument thread via ZMQ.

        Any pre_set_hooks will be called and the value will only be
        set if none of them returns None.

        Parameters
        ----------
        instrument
           The name of the instrument
        parameter
           The name of the parameter
        value
           The value to be set (needs to be able to be converted to a string)
        priority
           The priority of the message. See: :func:`.base.zmq_helper.add_ZMQ_message_to_queue`
        skip_hooks
           If True, don't call the available hooks (usefull when
           loading settings from a file for example)
        """
        logger.debug(f"app: updating value '{value}' for '{instrument}-{parameter}'")

        # Don't try to set parameters in dummy mode
        if self.dummy:
            return

        if not skip_hooks:
            if "pre_set_hooks" not in self._data[instrument][parameter]:
                logger.error(
                    f"'{instrument}-{parameter}' seems to be a command instead of a parameter."
                )
                return
            pre_set_hooks = self._data[instrument][parameter]["pre_set_hooks"]
            value = call_hooks(pre_set_hooks, value)
        if value is None:
            logger.info(f"Hook blocked setting of parameter '{instrument}-{parameter}'")
            return
        self._data[instrument][parameter]["set_value"] = value
        self.zmq_publisher.send_string(
            f"{instrument} {priority} set {parameter} {value}"
        )

    @ensure_parameter_and_instrument_exists
    def update_instrument_parameter(
        self, instrument: str, parameter: str, priority: int = 1
    ) -> None:
        """Sends request to the instrument thread via ZMQ to query the parameter value.

        Any post_read_hooks will be called.

        Parameters
        ----------
        instrument
           The name of the instrument
        parameter
           The name of the parameter
        priority
           The priority of the message. See: :func:`.base.zmq_helper.add_ZMQ_message_to_queue`
        """
        self.zmq_publisher.send_string(f"{instrument} {priority} get {parameter}")

    @ensure_parameter_and_instrument_exists
    def call_instrument_command(
        self, instrument: str, command: str, priority: int = 1
    ) -> None:
        """Sends a command to the instrument via ZMQ.

        Any pre_call_hooks will be called, and the command will only
        execute if none of the hooks returns None.

        Parameters
        ----------
        instrument
           The name of the instrument
        command
           The name of the command
        priority
           The priority of the message. See: :func:`.base.zmq_helper.add_ZMQ_message_to_queue`
        """
        try:
            pre_call_hooks = self._data[instrument][command]["pre_call_hooks"]
            value = call_hooks(pre_call_hooks, command)
        except KeyError:
            value = str(command)

        if value:
            self.zmq_publisher.send_string(f"{instrument} {priority} command {command}")

    @ensure_parameter_and_instrument_exists
    def get_instrument_parameter(
        self, instrument: str, parameter: str, return_set_value: bool = False
    ) -> str | None:
        """Return the last value read back for the given instrument parameter.

        This function does not communicate with the instrument.
        """
        # Some parameters are boolean
        if parameter == "IGNORE":
            return self._data[instrument][parameter]

        # Make sure parameter is not a command
        # (Commands don't have "set_value" or "read_value" keys.)
        if (
            "set_value" in self._data[instrument][parameter].keys()
            or "read_value" in self._data[instrument][parameter].keys()
        ):
            if return_set_value:
                return self._data[instrument][parameter]["set_value"]
            return self._data[instrument][parameter]["read_value"]

        # If a command IS being passed write a logger warning
        else:
            logger.warning(
                f"The 'get_instrument_parameter' function was called on the command '{parameter}' in instrument '{instrument}'. Only parameters can be passed to 'get_instrument_parameter'."
            )

    def add_hook(
        self,
        instrument: str,
        parameter: str,
        when: str,
        function: Callable[[Any], Any],
    ) -> None:
        """Add a hook to a parameter or command.

        Every hook function takes a single parameter: the value of the
        parameter to be set (set to None for commands). If a hook requires
        several parameters, one should pass these in when defining the hook
        using lambda functions, e.g.:

        app.add_hook(instrument, parameter, 'pre_set_hooks', lambda x: change_ui(app, x, widget)

        where app and widget are defined in the enironment where add_hook is called.

        Parameters
        ----------
        instrument
           The name of the instrument
        parameter
           The name of the parameter
        when
           At what point the hook should be called. Possible options are: "post_read_hooks", "pre_set_hooks", "pre_call_hooks".
        function
           The hook function to be added.
        """
        if instrument in self._data:
            if parameter in self._data[instrument]:
                if when not in ["post_read_hooks", "pre_set_hooks", "pre_call_hooks"]:
                    logger.error(
                        f"'{instrument}': '{parameter}' has wrong hook type: '{when}'. Needs to be one of 'post_read_hooks', 'pre_set_hooks', 'pre_call_hooks'"
                    )
                    return
                else:
                    self._data[instrument][parameter][when].append(function)
                    return
        logger.info(
            f"Parameter {parameter} does not exist in instrument {instrument}, not adding parameter hook to {when}."
        )

    @ensure_parameter_and_instrument_exists
    def add_widget(self, instrument: str, parameter: str, widget) -> None:
        """Add a widget to a parameter.

        This enables automatic updating if the value changes.
        """
        hc_update = getattr(widget, "hc_update", None)
        if not callable(hc_update):
            logger.error(
                f"Widget '{widget.instrument}:{widget.parameter}' has no update function and cannot be added for automatic updates"
            )

        # don't add a widget twice
        if widget not in self._data[instrument][parameter]["widgets"]:
            self._data[instrument][parameter]["widgets"].append(widget)

    def add_save_format(
        self, format_name: str, save_fxn: Callable[[Dataset, str], None]
    ) -> None:
        """
        Add a save format for a dataset.

        Parameters
        ----------
        format_name
            Name of the new save format
        save_fxn
            The function used for the new save format. This function must
            take a Dataset object and a filename as argument.
        """
        if format_name in Dataset._built_in_save_formats:
            logger.warning(
                f"Cannot add save format '{format_name}'"
                f" because it is already included by default."
            )
            return

        if not callable(save_fxn):
            logger.error(
                f"Cannot add save format '{format_name}' because"
                f" the callback function argument is not callable."
            )

        self.additional_save_formats[format_name] = save_fxn

    @ensure_instrument_exists
    def list_instrument_parameters(self, instrument) -> list[str]:
        """Compile a list of all the parameters for a specified instrument."""
        return [parameter for parameter in self._data[instrument]]

    def list_instruments(self) -> list[str]:
        """Compile a list of all the instruments in the app."""
        if not self._data:
            return []
        return [instrument for instrument in self._data]

    def close(self) -> None:
        """Closes the application.

        Safely closes the application by disconnecting all instruments and saving
        any data specified to save automatically before close.
        """
        self.stop()

        # Close all ZMQ subscribers
        for name, subscriber in self.zmq_subscribers.items():
            try:
                subscriber.close()
                logger.debug(f"Closed ZMQ subscriber for '{name}'")
            except Exception as e:
                logger.warning(f"Error closing ZMQ subscriber for '{name}': {e}")

        # Close main ZMQ sockets
        try:
            self.zmq_publisher.close()
            logger.debug("Closed main ZMQ publisher")
        except Exception as e:
            logger.warning(f"Error closing main ZMQ publisher: {e}")

        try:
            self.zmq_info.close()
            logger.debug("Closed ZMQ info socket")
        except Exception as e:
            logger.warning(f"Error closing ZMQ info socket: {e}")

        # Terminate ZMQ context
        try:
            self.zmq_context.term()
            logger.debug("Terminated ZMQ context")
        except Exception as e:
            logger.warning(f"Error terminating ZMQ context: {e}")

        # Loop through datasets, save all sets to autosave
        for key in self.data_sets:
            if self.data_sets[key].autosave_enabled:
                self.data_sets[key].autosave()

    @handle_file_operation
    def save_settings(self, filename: str | Path) -> None:
        """Save all settings as JSON.

        Parses out all set_value entries from app._data. The
        dictionary is then saved to a JSON file.

        Parameters
        ----------
        filename
            Name of file to save set_value entries to
        """
        app_settings = {}
        for instrument in self._data:
            app_settings[instrument] = {}
            for parameter in self._data[instrument]:
                value = self._data[instrument][parameter]["set_value"]
                if value is not None:
                    app_settings[instrument][parameter] = value

        with open(filename, "w") as file:
            json.dump(app_settings, file)
            logger.info(f"Saved all settings to file '{filename}'")

    @ensure_instrument_exists
    def load_settings_hook(
        self, instrument: str, filename: str | Path, skip_hooks: bool = True
    ) -> None:
        def hook_function(value):
            """Reads a JSON file to overwrite instrument's settings.

            The JSON file must be a dictionary where the keys are parameter names while
            the values are the new settings values. Parameters in the dictionary that
            do not exist in the instrument's settings dictionary are ignored. If the
            file does not specify a parameter held by the instrument's settings dictionary
            then that parameter is unchanged.

            Parameters
            ----------
            filename
                Name of JSON file to read settings from.

            """
            # Read file
            try:
                with open(filename) as file:
                    all_settings = json.load(file)
                    logger.info(
                        f"Settings for instrument '{instrument}' read from file '{filename}'."
                    )
            except (OSError, json.JSONDecodeError) as e:
                logger.error(
                    f"Failed to read settings file '{filename}': {e}", exc_info=True
                )
                return value
            # Try to set instrument settings
            if instrument not in self._data:
                logger.warning(
                    f"{instrument} not found in app. Settings for {instrument} were not set."
                )
                return value
            for parameter in all_settings:
                if parameter not in self._data[instrument]:
                    logger.warning(
                        f"{parameter} not found in {instrument}. Settings for {parameter} were not set."
                    )
                    return value
                set_value = all_settings[parameter]
                self.set_instrument_parameter(
                    instrument, parameter, set_value, skip_hooks=skip_hooks
                )

            return value

        return hook_function

    @ensure_instrument_exists
    def add_load_settings_hook(self, instrument: str, filename: str | Path) -> None:
        """Add a hook that loads a file with a dictionary of instrument settings.

        Parameters
        ----------
        filename
            Name of JSON file to read settings from. See load_settings method
            for details on the formatting of the JSON file.
        """
        self.add_hook(
            instrument,
            "ONLINE",
            "post_read_hooks",
            self.load_settings_hook(instrument, filename, skip_hooks=False),
        )
