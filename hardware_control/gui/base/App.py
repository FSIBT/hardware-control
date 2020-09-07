import json
import logging
from typing import Callable

from PyQt5.QtWidgets import QApplication

from .MeasurementDirector import MeasurementDirector
from .MeasurementRequest import MeasurementRequest
from .Dataset import Dataset

logger = logging.getLogger(__name__)


class App(QApplication):
    """The main app class.

    This class should be used to create the main Qt app in your
    program. It keeps track of all connected instruments, settings,
    and current data.

    """

    def __init__(self, dummy=False):
        # QApplication can take a list of strings, e.g. from sys.argv
        # we currently don't use this
        super().__init__([])
        self.instruments = []
        self.macros = {}  # Dict of hc-commands (used for scans + trigger buttons)
        self.function_handles = {}  # Dict of function handles for macros to call
        # self.saved_data = {}
        # Dict of data saved directly with query commmands
        self.dummy = dummy
        self.print_close_info = False
        self.comms = {}  # Dictionary of hc.Comm objects
        self.additional_save_formats = {}

        self.data_sets = {}  # Dict of datasets
        untitled_set = Dataset("Untitled")
        self.data_sets["Untitled"] = untitled_set

        self.director = MeasurementDirector(self)

    def get_instrument_by_name(self, name: str):
        """Returns the instrument named 'name' in 'instruments' list

        Parameters
        ----------
        name : str
            Name of the instrument to find

        Returns
        -------
        hc.Instrument
            The instrument class or `None` if not found
        """

        for inst in self.instruments:
            if name == inst.name:
                return inst

        return None

    def get_instrument_value(self, instrument_name: str, value: str):

        inst = self.get_instrument_by_name(instrument_name)

        if not inst:
            return None

        return inst.values.get(value, None)

    def add_instrument(self, widget):
        """ Adds an hc.Instrument to self.instruments list

        Instruments must have unique names.

        Parameters
        ----------
        widget
            hc.Instrument to add to self.instruments list
        """

        if widget.name in [x.name for x in self.instruments]:
            raise KeyError(f"Intrument name '{widget.name}' is already present")

        self.instruments.append(widget)

    def add_save_format(self, name: str, format):
        """
        The callback function must accept two parameters:
            1st: Dataset object
            2nd: Filename
        """

        dummy_set = Dataset("Dummy")

        if name in dummy_set.built_in_save_formats:
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

    def save_settings(self, filename: str):
        """Save all settings as JSON.

        Copys the settings dictionaries from each instrument into a
        new dictionary with the instrument's name serving as the
        key. The dictionary is then saved to a JSON file.

        Parameters
        ----------
        filename : str
            Name of file to save parameters to

        """

        app_settings = {instr.name: instr.settings for instr in self.instruments}

        # Write JSON file
        try:
            with open(filename, "w") as file:
                json.dump(app_settings, file)
                logger.info(
                    f"settings for {self.comm.instr.ID} saved to file '{filename}'"
                )
        except Exception:
            logger.error(
                f"Failed to write file '{filename}'. State not saved.", exc_info=True
            )

    def list_instruments(self):
        """ Prints a list of all instruments in self.instruments."""

        if not self.instruments:
            print("No known instruments")
            return

        print("Known instruments:")
        for i in self.instruments:
            print(f"  {i}")

    def check_instruments(self):
        """ Ensures all instruments conform to specifications"""
        for i in self.instruments:
            try:
                i.name
            except AttributeError:
                logger.error(f"Instrument  {i} needs a .name")
            if i.manufacturer is None:
                logger.error(f"Instrument  {i} needs a .manufacturer")
            if i.model is None:
                logger.error(f"Instrument  {i} needs a .model")

    def close(self):
        """ Closes the application

        Safely closes the application by disconnecting all instruments and saving
        any data specified to save automatically before close.
        """

        # Loop through instruments, close each one...
        for instr in self.instruments:
            instr.close()

        # Loop through datasets, save all set to autosave
        for ds_key in self.data_sets:
            if self.data_sets[ds_key].autosave:
                self.data_sets[ds_key].exec_autosave()

    def add_macro(self, name: str, commands: list):
        """Adds a macro to the app's macro list. Overwrites if macro already exists"""
        self.macros[name] = commands

    def add_macro_file(self, name: str, filename: str):
        """Adds a macro to the app's macro list. Overwrites if macro already exists"""

        commands = []

        # Read file line by line
        with open(filename) as infile:
            for line in infile:
                commands.append(line.rstrip("\n"))

        if len(commands) > 0:
            self.add_macro(name, commands)
            return True
        else:
            return False

    def process_external_command(self, command: str):
        """Accepts a text command, and executes it on the app"""

        tokens = command.split(":")  # Split the command up into tokens
        uptokens = command.upper().split(":")  # Upper case tokens...

        # Check if too few commands are given
        if len(tokens) < 1:
            logger.warning(
                f"Invalid HC-Command received. No tokens. Command: '{command}'"
            )
            return "ERROR: Invalid command"

        # Find out the 'mode' of the command
        if uptokens[0] == "SET" or uptokens[0] == "SET_UI":

            # Make sure the correct number of arguments are given
            if len(tokens) < 4:  # Requires: MODE:INSTRUMENT:PARAMETER:VALUE
                logger.warning(
                    f"Invalid HC-Command received. Wrong number of tokens."
                    f" Command: '{command}'"
                )
                return "ERROR: Invalid command"

            tokens = command.split(":", 3)
            instr_str = tokens[1]
            setting_str = tokens[2]
            value_str = tokens[3]

            inst = self.get_instrument_by_name(instr_str)
            if inst is None:
                logger.warning(f"Instrument '{instr_str}' not found.")
                return "ERROR: Instrument not found"

            inst.update_setting(setting_str, value_str)
            if uptokens[0] == "SET_UI":
                inst.settings_to_UI()

            logger.debug(
                f"Executed Setting Update:\n\tInstrument: {instr_str}\n"
                f"\tSetting: {setting_str}\n\tValue: {value_str}"
            )

        elif uptokens[0] == "CMD":

            # Recalculate tokens, with max of 2 splits. This allows colons to appear in the command
            tokens = command.split(":", 2)

            # Make sure the correct number of arguments are given
            if len(tokens) != 3:  # Requires: MODE:INSTRUMENT:PARAMETER:VALUE
                logger.warning(
                    f"Invalid HC-Command received. Wrong number of tokens."
                    f" Command'{command}'"
                )
                return "ERROR: Invalid command"

            instr_str = tokens[1]
            command_str = tokens[2]

            inst = self.get_instrument_by_name(instr_str)
            if inst is None:
                logger.warning(
                    f"Invalid HC-Command received. Wrong number of tokens."
                    f" Command: '{command}'"
                )
                return "ERROR: Invalid command"

            inst.command(command_str)
            logger.debug(
                f"Executed Command:\n\tInstrument: {instr_str}\n"
                f"\tCommand: {command_str}"
            )

        elif uptokens[0] == "MEAS":
            if uptokens[1] == "REQ":
                # Recalculate tokens, with max of 2 splits. This
                # allows colons to appear in the command
                tokens = command.split(":", 9)

                # Format: CMDLG:group:instrument:parameter:cmd_str:steady_num:dt:tol:iterations

                # Make sure the correct number of arguments are given
                if len(tokens) != 10:  # Requires: MODE:INSTRUMENT:PARAMETER:VALUE
                    logger.warning(
                        f"Invalid HC-Command received. Wrong number of tokens."
                        f" Command'{command}'"
                    )
                    return "False"

                try:
                    meas_req = MeasurementRequest(
                        tokens[2],
                        tokens[3],
                        tokens[4],
                        tokens[5],
                        int(tokens[6]),
                        float(tokens[7]),
                        float(tokens[8]),
                        int(tokens[9]),
                    )
                except Exception:
                    logger.warning(
                        "Invalid HC-Command received. Failed to create "
                        "MeasurementRequest from given arguments.",
                    )
                    return "False"

                if not self.director.measure(meas_req):
                    logger.warning("Failed to add MeasurementRequest to director'")
                    return "False"

                logger.debug(
                    f"Executed Command:\n\tInstrument: {instr_str}\n"
                    f"\tCommand: {command_str}"
                )

            elif uptokens[1] == "START":
                self.director.start()
                return "Started"

            elif uptokens[1] == "PSTATE":
                print(self.director.state)
                if self.director.state == "Error":
                    print(f"\tError message: {self.director.err_str}")

            elif uptokens[1] == "GETSTATE":
                return self.director.state

        elif uptokens[0] == "FUNC":
            # 'FUNC' indicates that the command is calling an internal function

            # Ensure more tokens exist
            if len(tokens) < 2:
                logger.warning("Invalid HC-Command received. FUNC requires arguments.",)
                return "False"

            # Make sure handle exists
            if tokens[1] in self.function_handles:

                if not callable(self.function_handles[tokens[1]]):
                    func_name = tokens[1]
                    logger.warning(
                        f"Non-callable object provided as function handle '{func_name}'"
                    )
                    return "False"

                # Run function - note: this can become recursive and get stuck in
                # an infinite loop if the user runs a function that calls itself
                if len(tokens) > 2:
                    tokens = command.split(":", 2)
                    return self.function_handles[tokens[1]](tokens[2])
                else:
                    return self.function_handles[tokens[1]]()

            else:
                logger.warning("Requested function does not exist.")
                return "False"

        else:
            logger.warning(
                f"Invalid HC-Command received. Unrecognized mode token. Command: '{command}'"
            )
            return "WARNING: Couldn't process command"

        return "True"

    def run_macro(self, m_commands):
        """ Accepts a list of hc-commands (from a macro) and runs all, blocking
        the GUI until they are complete """

        for cmd in m_commands:
            self.process_external_command(cmd)

    def load_state_from_file(self, filename: str):
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
        filename : str
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

        # For each instrument...
        for instr in self.instruments:

            # Proceed if instrument's settings are in master file...
            # (else skip to next instrument)
            if instr.name not in all_settings:
                continue

            # Get instrument's new settings from file
            instr_settings = all_settings[instr.name]

            # For each parameters specified in new settings...
            for param in instr_settings:

                # If paraeter is valid in instrument settings...
                # (else skip to next parameter)
                if param not in instr.settings:
                    continue

                # Write new setting to instrument's dictionary
                instr.settings[param] = instr_settings[param]

    def save_all_states(self, filename: str, pretty: bool = True):
        """ Saves the state of every instrument in 'self.instruments' to a file.
        If filename is 'None', does not save a file and instead returns would-be
        file contents as a string.

        Parameters
        ----------
        filename : str
            Name of the JSON file to save the instrument states to
        pretty : bool
            Determines if indentation and sorting should be used

        Returns
        -------
        str
            Returns an empty string if saved to file. If filename is None, returns
            a string with the contents of what would have been saved to the file.
        """

        all_states = {}

        # Combine all widgets into one state object
        for inst in self.instruments:
            all_states[inst.name] = inst.settings

        if filename is None:
            if pretty:
                return json.dumps(all_states, sort_keys=True, indent=4)
            else:
                return json.dumps(all_states)

        # Save to file
        try:
            with open(filename, "w") as file:
                if pretty:
                    json.dump(all_states, file, sort_keys=True, indent=4)
                else:
                    json.dump(all_states, file)
                logger.info(f"Settings for all instruments saved to file '{filename}'")
        except Exception:
            logger.error(
                f"Failed to write file '{filename}'. settings not saved.",
                exc_info=True,
            )

        return ""

    def settings_to_backends(self):
        """ Sends the front end's state to all backends

        Calls 'send_state' for each instrument in self.instruments, thus sending
        their settings dictionaries to their backends.

        """

        for instr in self.instruments:
            instr.send_state()

    def backends_to_settings(self):
        """ Overwrites all settings with the current values measured in the physical instrument.

        Calls 'read_state_from_backend' for each instrument, thus updating the
        'settings' dictionary by querying each value from the backend.

        """

        for instr in self.instruments:
            instr.read_state_from_backend()
