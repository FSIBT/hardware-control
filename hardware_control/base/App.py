from functools import wraps
import json
import logging
from pathlib import Path
import threading
from typing import Union, Callable, Any, List

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import zmq

from .Dataset import Dataset
from .Instrument import Instrument
from .ZMQAdapter import ZMQAdapter

logger = logging.getLogger(__name__)


def call_hooks(hooks_list, value):
    """Call a list of function.

    If any of the functions returns None, the final value will be
    ignored and the no further hooks will be called.

    Every hook function must take a single parameter: the value of the
    parameter to be set (set to None for commands)

    If a hook needs several parameter, one should pass these in when
    defining the hook using lambda functions, e.g.:

    app.add_hook(instrument, parameter, 'pre_set_hooks', lambda x: change_ui(app, x, widget)

    where app and widget are defined in the enironment where add_hook
    is called.

    """
    for hook in hooks_list:
        if callable(hook):
            value = hook(value)
            if value is None:
                return None
    return str(value)


def ensure_instrument_exists(f):
    """Error check to make sure that instrument is in app._data."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        self = args[0]
        instrument = args[1]

        if instrument not in self._data:
            logger.error(f"Cannot find instrument '{instrument}' in app")
            return

        return f(*args, **kwargs)

    return wrapped


def ensure_parameter_in_instrument(f):
    """Error check to make sure that paramter/command exists."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        self = args[0]
        instrument = args[1]
        name = args[2]

        if name not in self._data[instrument]:
            logger.error(
                f"Cannot find parameter/command '{name}' for instrument '{instrument}' in app"
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

        self.data_sets = {}  # Dict of datasets

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.parse_message_from_instruments)
        self.update_timer.start(100)

        # default refresh rate used by many GUI elements
        self.globalRefreshRate = 1000

    def stop(self):
        """Stop all threads and wait until they return"""

        # first set the event which will trigger the while loop in the
        # thread's run function to stop
        self.stop_threads_event.set()
        # wait for all threads to end
        for t in self.threads:
            t.join()

    def add_instrument(self, instrument: Instrument):

        if instrument.name in self._data:
            logger.error(
                f"Instrument {instrument.name} already exists... instruments names need to be unique"
            )
            return

        instrument.dummy = self.dummy

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
        read, set, commands = zmq_instrument.instrument.list_parameters()

        if zmq_instrument.instrument.name not in self._data:
            self._data[zmq_instrument.instrument.name] = {}

        for r in read:
            p = {
                "read_value": None,
                "set_value": None,
                "post_read_hooks": [],
                "pre_set_hooks": [],
                "widgets": [],
            }
            self._data[zmq_instrument.name][r] = p
        for c in commands:
            p = {
                "pre_call_hooks": [],
                "widgets": [],
            }
            self._data[zmq_instrument.name][c] = p

        # start thread
        self.threads.append(zmq_instrument)
        zmq_instrument.start()

    def add_remote_instrument(self, name, ipaddress, port):
        if name in self._data:
            logger.error(
                f"Instrument {instrument.name} already exists... instruments names need to be unique"
            )
            return

        zmq_instrument = ZMQRemoteInstrument(
            name, ipaddress, port, self.zmq_context, self.zmq_publisher_port
        )

        subscriber = self.zmq_context.socket(zmq.SUB)
        subscriber.connect(
            f"tcp://{zmq_instrument.instrument_address}:{zmq_instrument.instrument_port}"
        )
        subscriber.subscribe("")
        self.zmq_subscribers[zmq_instrument.name] = subscriber

        read, set, commands = zmq_instrument.list_parameters()

        if zmq_instrument.name not in self._data:
            self._data[zmq_instrument.name] = {}

        # add parameters into _data
        for r in read:
            p = {
                "read_value": None,
                "set_value": None,
                "post_read_hooks": [],
                "pre_set_hooks": [],
                "widgets": [],
            }
            self._data[zmq_instrument.name][r] = p
        for c in commands:
            p = {
                "pre_call_hooks": [],
                "widgets": [],
            }
            self._data[zmq_instrument.name][c] = p

        # save somewhere to be able to call close, this works, since
        # we add a .join() method to the ZMQ remote instrument
        self.threads.append(zmq_instrument)

    def parse_message_from_instruments(self):
        """Check for message from the instruments.

        Call any defined hooks and update any widgets.
        """

        for name, sub in self.zmq_subscribers.items():
            try:
                msg = sub.recv_string(flags=zmq.NOBLOCK)
            except zmq.ZMQError:
                continue
            logger.debug(f"App got '{msg}' from '{name}'")

            # would need error checking here
            inst_name, parameter, value = msg.split()
            assert inst_name == name

            post_read_hooks = self._data[name][parameter]["post_read_hooks"]
            value = call_hooks(post_read_hooks, value)
            if value is not None:
                self._data[name][parameter]["read_value"] = value
                for w in self._data[name][parameter]["widgets"]:
                    w.hc_update()

    @ensure_instrument_exists
    @ensure_parameter_in_instrument
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
        if not skip_hooks:
            pre_set_hooks = self._data[instrument][parameter]["pre_set_hooks"]
            value = call_hooks(pre_set_hooks, value)
        if value is None:
            logger.info(f"Hook blocked setting of parameter '{instrument}-{parameter}'")
            return

        self._data[instrument][parameter]["set_value"] = value
        self.zmq_publisher.send_string(f"{instrument} {parameter} {value}")

    @ensure_instrument_exists
    @ensure_parameter_in_instrument
    def update_instrument_parameter(self, instrument: str, parameter: str) -> None:
        """Sends request to the instrument thread via ZMQ to query the parameter value.

        Any pre_set_hooks will be called and the value will only be
        set if none of them returns None.

        Parameters
        ----------
        instrument
           The name of the instrument
        paramter
           The name of the parameter

        """
        self.zmq_publisher.send_string(f"{instrument} get {parameter}")

    @ensure_instrument_exists
    @ensure_parameter_in_instrument
    def call_instrument_command(self, instrument: str, command: str) -> None:
        """Sends a command to the instrument via ZMQ.

        Any pre_call_hooks will be called and the command will only
        execute if none of the hooks returns None.

        """
        pre_call_hooks = self._data[instrument][command]["pre_call_hooks"]
        value = call_hooks(pre_call_hooks, command)
        if value:
            self.zmq_publisher.send_string(f"{instrument} command {command}")

    @ensure_instrument_exists
    @ensure_parameter_in_instrument
    def get_instrument_parameter(
        self, instrument: str, parameter: str, return_set_value: bool = False
    ) -> Union[str, None]:
        """Return the last read back value.

        This function does not communicate with the instrument.
        """
        if return_set_value:
            return self._data[instrument][parameter]["set_value"]
        return self._data[instrument][parameter]["read_value"]

    @ensure_instrument_exists
    @ensure_parameter_in_instrument
    def get_instrument_set_parameter(
        self, instrument: str, parameter: str
    ) -> Union[str, None]:
        """Return the last set value.

        This function does not communicate with the instrument.
        """

        return self._data[instrument][parameter]["set_value"]

    @ensure_instrument_exists
    @ensure_parameter_in_instrument
    def add_hook(
        self,
        instrument: str,
        name: str,
        when: str,
        function: Callable[[Any], Any],
    ):
        """Adds a hook to a parameter or command.

        Every hook function must take a single parameter: the value of the
        parameter to be set (set to None for commands)

        If a hook needs several parameter, one should pass these in
        when defining the hook using lambda functions, e.g.:

        app.add_hook(instrument, parameter, 'pre_set_hooks', lambda x: change_ui(app, x, widget)

        where app and widget are defined in the enironment where
        add_hook is called.

        """

        if when not in ["post_read_hooks", "pre_set_hooks", "pre_call_hooks"]:
            logger.error(
                'wrong hook type. Needs to be one of "post_read_hook", "pre_set_hooks", "pre_call_hooks"'
            )
            return

        self._data[instrument][name][when].append(function)

    @ensure_instrument_exists
    @ensure_parameter_in_instrument
    def add_widget(self, instrument: str, name: str, widget):
        """Adds a widget to a parameter.

        This enables automatic updating if the value changes
        """
        hc_update = getattr(widget, "hc_update", None)
        if not callable(hc_update):
            logger.error(
                f"Widget '{widget.instrument}:{widget.parameter}' has no update function and cannot be added for automatic updates"
            )

        # don't add a widget twice
        if widget not in self._data[instrument][name]["widgets"]:
            self._data[instrument][name]["widgets"].append(widget)

    def add_save_format(
        self, name: str, format: Callable[[Dataset, str], None]
    ) -> None:
        """
        The callback function must accept two _data:
            1st: Dataset object
            2nd: Filename
        """

        if name in Dataset.built_in_save_formats:
            logger.warning(
                f"Cannot add save format '{name}'"
                f" because it is already included by default."
            )
            return

        if not callable(format):
            logger.warning(
                f"Cannot add save format '{name}' because"
                f" the callback function argument is not callable."
            )

        self.additional_save_formats[name] = format

    def get_instruments(self) -> List[str]:
        return [instrument for instrument in self._data]

    def list_instruments(self) -> None:
        """Prints a list of all instruments."""

        if not self._data:
            print("No known instruments")
            return

        print("Known instruments:")
        for i in self._data:
            print(f"  {i}")

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
        filename : str or Path
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

    def load_settings(self, filename: Union[str, Path]) -> None:
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
        filename : str or Path
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

        # try to set all settings
        for instrument in all_settings:
            if instrument not in self._data:
                logger.error(f"{instrument} not found in app")
                continue
            for parameter in all_settings[instrument]:
                value = all_settings[instrument][parameter]
                self.set_instrument_parameter(instrument, parameter, value, raw=True)
