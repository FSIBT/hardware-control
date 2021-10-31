from functools import wraps
import json
import logging
from pathlib import Path
import threading
import time
from typing import Union, Optional, Callable, Any, List, Dict

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import zmq

from .Dataset import Dataset
from .Instrument import Instrument
from .ZMQAdapter import ZMQAdapter
from .ZMQRemoteAdapter import ZMQRemoteInstrument
from .hooks import call_hooks

logger = logging.getLogger(__name__)


def ensure_instrument_exists(f):
    """Error check to make sure that instrument is in app._data.

    This decorator assumes that the first argument is the app class
    and then second argument is the instrument name.

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
    """Error check to make sure that parameter/command exists.

    This decorator assumes that the first argument is the app class,
    the second is the instrument name, and the third is the parameter
    name.

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
                f"Cannot find parameter/command '{parameter}' for instrument '{instrument}'  in {f.__name__} in app"
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

        # publisher that announces commands for instruments
        if ipaddress is None:
            self.ipaddress = "127.0.0.1"
        else:
            self.ipaddress = ipaddress
        self.zmq_publisher_address = f"tcp://{self.ipaddress}:1234"
        self.zmq_context = zmq.Context()
        self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
        self.zmq_publisher.bind(self.zmq_publisher_address)

        self.dummy = dummy
        self.additional_save_formats = {}

        # keep track of datasets, so that we can autosave, etc.
        self.data_sets = {}

        # keep a list of parameters that should be updated periodiccaly
        # This is a set of (<instrument name>,<parameters>) combinations
        self.request_updates = set()

        # a timer to check ZMQ messages
        self.zmq_timer = QTimer(self)
        self.zmq_timer.timeout.connect(self.parse_message_from_instruments)
        self.zmq_timer.start(100)

        # a timer to requests updates from instruments
        self.update_instrument_timer = QTimer(self)
        self.update_instrument_timer.timeout.connect(self.update_instruments)
        self.update_instrument_timer.start(1000)

        # default refresh rate used by many GUI elements
        self.globalRefreshRate = 1000

    def stop(self) -> None:
        """Stop all threads and wait until they return"""

        # first set the event which will trigger the while loop in the
        # thread's run function to stop
        self.stop_threads_event.set()
        # wait for all threads to end
        for t in self.threads:
            t.join()

    @ensure_instrument_exists
    def register_parameters_and_commands(
        self, instrument: str, read_parameters, set_parameters, commands
    ) -> None:
        """Adds the parameter names to the data modell and set defaults values."""
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
        name = dataset.name
        if name in self.data_sets:
            logger.error(f"Dataset {name} already exists... not adding dataset to App.")
            return
        self.data_sets[name] = dataset

    def add_instrument(
        self,
        instrument: Instrument,
        ignore_flag: Optional[bool] = False,
    ):

        if instrument.name in self._data:
            logger.error(
                f"Instrument {instrument.name} already exists... instruments names need to be unique"
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
        # subscribe to multiple publisher for now we create multiple
        # subscribers
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
        self._data[zmq_instrument.name]["ignore"] = ignore_flag

        # some time for ZMQ to set things up
        time.sleep(1)

        # start thread
        self.threads.append(zmq_instrument)
        zmq_instrument.start()

    def add_remote_instrument(self, name: str, address: str) -> None:
        """Connect to a instrument driver on, for example, a different computer.

        This is relative straight forward, since the ZMQ publishers
        that update the data modell do not care on which computer they
        are running. The main task is to create subscribers to the
        already existing publishers(from the app and on the remote
        side). This task is mostly handled by `ZMQRemoteInstrument`.

        Parameters
        ----------
        name
           The remote instrument name
        address
           The ipaddress:port combination where the remote instrument is running

        """
        if name in self._data:
            logger.error(
                f"Instrument {instrument.name} already exists... instruments names need to be unique"
            )
            return

        zmq_instrument = ZMQRemoteInstrument(
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
        """Check for message from the instruments.

        Call any defined hooks and update any widgets.
        """

        for name, sub in self.zmq_subscribers.items():
            try:
                msg = sub.recv_string(flags=zmq.NOBLOCK)
            except zmq.ZMQError:
                continue
            logger.debug(f"App got '{msg}' from '{name}'")

            try:
                inst_name, parameter, value = msg.split()
            except ValueError:
                logger.error(
                    f"{msg.split()} has too few or too many values (expected 3)."
                )
                return
            assert inst_name == name

            if name not in self._data:
                logger.error(f"{name} not available in data modell")
                return
            if parameter not in self._data[name]:
                logger.error(f"{parameter} not available for instrument {name}")
                return

            post_read_hooks = self._data[name][parameter]["post_read_hooks"]
            value = call_hooks(post_read_hooks, value)
            if value is not None:
                # update value
                self._data[name][parameter]["read_value"] = value
                # update widgets
                for w in self._data[name][parameter]["widgets"]:
                    w.hc_update()

    def update_instruments(self) -> None:
        for name, parameter_or_function in self.request_updates:
            online = self.get_instrument_parameter(name, "ONLINE")
            if online is None or online == "False":
                return
            if callable(parameter_or_function):
                parameter_or_function()
            else:
                self.update_instrument_parameter(name, parameter_or_function)

    @ensure_instrument_exists
    def add_auto_update_instrument_parameter(
        self, instrument: str, parameter: str
    ) -> None:
        if not callable(parameter):
            if parameter not in self._data[instrument]:
                logger.error(
                    f"Cannot find parameter/command '{parameter}' for instrument '{instrument}'   in app"
                )
                return

        logger.debug(f"register {instrument}->{parameter} for auto updates")
        self.request_updates.add((instrument, parameter))

    @ensure_parameter_and_instrument_exists
    def set_instrument_parameter(
        self, instrument: str, parameter: str, value: Any, skip_hooks=False
    ) -> None:
        """Send the value to the instrument thread via ZMQ.

        Any pre_set_hooks will be called and the value will only be
        set if none of them returns None.

        Parameters
        ----------
        instrument
           The name of the instrument
        paramter
           The name of the parameter
        value
           The value to be set (needs to be able to be converted to a string)
        skip_hooks
           If True, don't call the available hooks (usefull when
           loading settings from a file for example

        """

        logger.debug(f"app: updating value '{value}' for '{instrument}-{parameter}'")
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
        self.zmq_publisher.send_string(f"{instrument} set {parameter} {value}")

    @ensure_parameter_and_instrument_exists
    def update_instrument_parameter(self, instrument: str, parameter: str) -> None:
        """Sends request to the instrument thread via ZMQ to query the parameter value.

        Any pre_set_hooks will be called and the value will only be
        set if none of them returns None.

        Parameters
        ----------
        instrument
           The name of the instrument
        parameter
           The name of the parameter

        """
        self.zmq_publisher.send_string(f"{instrument} get {parameter}")

    @ensure_parameter_and_instrument_exists
    def call_instrument_command(self, instrument: str, command: str) -> None:
        """Sends a command to the instrument via ZMQ.

        Any pre_call_hooks will be called and the command will only
        execute if none of the hooks returns None.

        """
        try:
            pre_call_hooks = self._data[instrument][command]["pre_call_hooks"]
            value = call_hooks(pre_call_hooks, command)
        except KeyError:
            value = str(command)

        if value:
            self.zmq_publisher.send_string(f"{instrument} command {command}")

    @ensure_parameter_and_instrument_exists
    def get_instrument_parameter(
        self, instrument: str, parameter: str, return_set_value: bool = False
    ) -> Optional[str]:
        """Return the last read back value.

        This function does not communicate with the instrument.
        """

        # Some parameters are boolean
        if parameter == "ignore":
            return self._data[instrument][parameter]

        # Make sure parameter is not a command
        # (Commands don't have "set_value" or "read_value" keys.)
        elif (
            "set_value" in self._data[instrument][parameter].keys()
            or "read_value" in self._data[instrument][parameter].keys()
        ):
            if return_set_value:
                return self._data[instrument][parameter]["set_value"]
            return self._data[instrument][parameter]["read_value"]

    @ensure_parameter_and_instrument_exists
    def get_instrument_set_parameter(
        self, instrument: str, parameter: str
    ) -> Optional[str]:
        """Return the last set value.

        This function does not communicate with the instrument.
        """

        return self._data[instrument][parameter]["set_value"]

    @ensure_parameter_and_instrument_exists
    def add_hook(
        self,
        instrument: str,
        parameter: str,
        when: str,
        function: Callable[[Any], Any],
    ) -> None:
        """Adds a hook to a parameter or command.

        Every hook function must take a single parameter: the value of the
        parameter to be set (set to None for commands)

        If a hook requires several parameters, one should pass these in
        when defining the hook using lambda functions, e.g.:

        app.add_hook(instrument, parameter, 'pre_set_hooks', lambda x: change_ui(app, x, widget)

        where app and widget are defined in the enironment where add_hook is called.

        Parameters
        ----------
        instrument
           The name of the instrument
        parameter
           The name of the parameter
        when
           At what time the hook should be called. Possible options are: "post_read_hooks", "pre_set_hooks", "pre_call_hooks".
        function
           The hook function to be added.


        """

        if when not in ["post_read_hooks", "pre_set_hooks", "pre_call_hooks"]:
            logger.error(
                f"'{instrument}': '{parameter}' has wrong hook type: '{when}'. Needs to be one of 'post_read_hook', 'pre_set_hooks', 'pre_call_hooks'"
            )
            return

        self._data[instrument][parameter][when].append(function)

    @ensure_parameter_and_instrument_exists
    def add_widget(self, instrument: str, parameter: str, widget) -> None:
        """Adds a widget to a parameter.

        This enables automatic updating if the value changes
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

        The second argument – the save function – must accept two arguments:
        a Dataset object and a filename.
        """

        if format_name in Dataset.built_in_save_formats:
            logger.warning(
                f"Cannot add save format '{format_name}'"
                f" because it is already included by default."
            )
            return

        if not callable(save_fxn):
            logger.warning(
                f"Cannot add save format '{format_name}' because"
                f" the callback function argument is not callable."
            )

        self.additional_save_formats[format_name] = save_fxn

    @ensure_instrument_exists
    def get_instrument_read_values(self, instrument: str) -> Optional[Dict]:
        """Return a dictionary of an instrument's read_values"""
        instrument_dict_reads = {}
        for parameter in self.list_instrument_parameters(instrument):
            # Ignore boolean parameters
            if type(self._data[instrument][parameter]) is dict:
                # Ignore parameters without read_value functionality
                if "read_value" in self._data[instrument][parameter].keys():
                    if "read_value" in self._data[instrument][parameter].keys():
                        instrument_dict_reads[parameter] = self._data[instrument][
                            parameter
                        ]["read_value"]

        return instrument_dict_reads

    @ensure_instrument_exists
    def get_instrument_set_values(self, instrument: str) -> Optional[Dict]:
        """Return a dictionary of an instrument's set_values"""
        instrument_dict_sets = {}
        for parameter in self.list_instrument_parameters(instrument):
            # Ignore boolean parameters
            if type(self._data[instrument][parameter]) is dict:
                # Ignore parameters without set_value functionality
                if "set_value" in self._data[instrument][parameter].keys():
                    instrument_dict_sets[parameter] = self._data[instrument][parameter][
                        "set_value"
                    ]

        return instrument_dict_sets

    @ensure_instrument_exists
    def list_instrument_parameters(self, instrument) -> List[str]:
        return [parameter for parameter in self._data[instrument]]

    def list_instruments(self) -> List[str]:
        """Compile a list of all the app's instruments."""
        if not self._data:
            return []
        return [instrument for instrument in self._data]

    def close(self) -> None:
        """Closes the application

        Safely closes the application by disconnecting all instruments and saving
        any data specified to save automatically before close.
        """

        self.stop()

        # Loop through datasets, save all set to autosave
        for key in self.data_sets:
            if self.data_sets[key].autosave:
                self.data_sets[key].timer_autosave()

    def save_settings(self, filename: Union[str, Path]) -> None:
        """Save all settings as JSON.

        Parses out all `set_value` entries from app._data. The
        dictionary is then saved to a JSON file.

        Parameters
        ----------
        filename
            Name of file to save _data to

        """

        app_settings = {}
        for instrument in self._data:
            app_settings[instrument] = {}
            for parameter in self._data[instrument]:
                value = self._data[instrument][parameter]["set_value"]
                if value is not None:
                    app_settings[instrument][parameter] = value

        try:
            with open(filename, "w") as file:
                json.dump(app_settings, file)
                logger.info(f"Saved all settigns to file '{filename}'")
        except Exception:
            logger.error(
                f"Failed to write file '{filename}'. State not saved.", exc_info=True
            )

    @ensure_instrument_exists
    def load_settings(self, instrument: str, filename: Union[str, Path]) -> None:
        """Reads a JSON file to overwrite instrument's settings dictionaries.

        Expectss JSON to be a dictionary of dictionaries. The
        first-level key in the instrument name, the value for that key
        is the instrument's settings dictionary. If a parameter in the
        file does not exist in the instrment's settings dictionary it
        is ignored. If the file does not specify a parameter held by
        th instrument's settings dictionary then that parameter is
        unchanged.

        Parameters
        ----------
        filename
            Name of JSON file to read settings from

        """

        # Read file
        try:
            with open(filename) as file:
                all_settings = json.load(file)
                logger.info(f"settings for all instruments read from file '{filename}'")
        except:
            logger.error(f"Failed to read file '{filename}'.", exc_info=True)
            return

        # Try to set instrument settings
        if instrument not in self._data:
            logger.error(f"{instrument} not found in app.")
            return
        for parameter in all_settings:
            value = all_settings[parameter]
            self.set_instrument_parameter(instrument, parameter, value, raw=True)

    @ensure_instrument_exists
    def add_load_settings_hook(
        self, instrument: str, filename: Union[str, Path]
    ) -> None:
        self.add_hook(
            instrument,
            "ONLINE",
            "post_read_hook",
            lambda x: self.load_settings(instrument, filename),
        )
