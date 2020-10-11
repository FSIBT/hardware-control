import json
import logging
from pathlib import Path
from typing import Union, Callable

from PyQt5.QtWidgets import QApplication

from .Dataset import Dataset
from .Instrument import Instrument

logger = logging.getLogger(__name__)


class App(QApplication):
    """The main app class.

    This class should be used to create the main Qt app in your
    program. It keeps track of all connected instruments, settings,
    and current data.

    """

    def __init__(self, dummy: bool = False) -> None:
        # QApplication can take a list of strings, e.g. from sys.argv
        # we currently don't use this
        super().__init__([])
        self.instruments = []
        self.dummy = dummy
        self.print_close_info = False
        self.comms = {}  # Dictionary of hc.Comm objects
        self.additional_save_formats = {}

        self.data_sets = {}  # Dict of datasets
        untitled_set = Dataset("Untitled")
        self.data_sets["Untitled"] = untitled_set

    def get_instrument_by_name(self, name: str) -> Union[Instrument, None]:
        """Returns the instrument named ``name`` from the ``instruments`` list

        Parameters
        ----------
        name : str
            Name of the instrument to find

        Returns
        -------
        hc.Instrument
            The instrument class or ``None`` if not found
        """

        for inst in self.instruments:
            if name == inst.name:
                return inst

        return None

    def get_instrument_value(
        self, instrument_name: str, value: str
    ) -> Union[str, None]:

        inst = self.get_instrument_by_name(instrument_name)

        if not inst:
            return None

        return inst.values.get(value, None)

    def add_instrument(self, instr: Instrument) -> None:
        """ Adds an hc.Instrument to self.instruments list

        Instruments must have unique names.

        Parameters
        ----------
        instr
            hc.Instrument to add to self.instruments list
        """

        if instr.name in [x.name for x in self.instruments]:
            raise KeyError(f"Intrument name '{instr.name}' is already present")

        self.instruments.append(instr)

    def add_save_format(
        self, name: str, format: Callable[[Dataset, str], None]
    ) -> None:
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

    def save_settings(self, filename: Union[str, Path]) -> None:
        """Save all settings as JSON.

        Copys the settings dictionaries from each instrument into a
        new dictionary with the instrument's name serving as the
        key. The dictionary is then saved to a JSON file.

        Parameters
        ----------
        filename : str or Path
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

    def list_instruments(self) -> None:
        """ Prints a list of all instruments in self.instruments."""

        if not self.instruments:
            print("No known instruments")
            return

        print("Known instruments:")
        for i in self.instruments:
            print(f"  {i}")

    def check_instruments(self) -> None:
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

    def close(self) -> None:
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

    def load_state_from_file(self, filename: Union[str, Path]) -> None:
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

    def save_all_states(self, filename: Union[str, Path], pretty: bool = True) -> str:
        """ Saves the state of every instrument in 'self.instruments' to a file.
        If filename is 'None', does not save a file and instead returns would-be
        file contents as a string.

        Parameters
        ----------
        filename : str or Path
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

    def settings_to_backends(self) -> None:
        """ Sends the front end's state to all backends

        Calls 'send_state' for each instrument in self.instruments, thus sending
        their settings dictionaries to their backends.

        """

        for instr in self.instruments:
            instr.send_state()

    def backends_to_settings(self) -> None:
        """ Overwrites all settings with the current values measured in the physical instrument.

        Calls 'read_state_from_backend' for each instrument, thus updating the
        'settings' dictionary by querying each value from the backend.

        """

        for instr in self.instruments:
            instr.read_state_from_backend()
