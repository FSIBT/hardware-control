from collections import defaultdict
import datetime
import json
import logging
from pathlib import Path
import pickle
import time
from typing import Dict, Optional, List

import numpy as np
import pandas as pd

from PyQt5.QtCore import QObject, QTimer

logger = logging.getLogger(__name__)


class Dataset(QObject):
    """Collect values from different instrument parameters over time.

    A Dataset object collects the values of each instrument parameter in a given list
    of parameters once per a given time interval in the Dataset's self.data dictionary. For
    each parameter, self.data has a key (of the format 'instrument:parameter')
    which accesses a list with all returned values for the given parameter. self.data
    also has a key ('time:time') with the times at which the values were returned.

    The values are taken from app._data, meaning that they are not taken
    directly from the instrument; a Dataset therefore does not communicate
    with any actual hardware. It is assumed that the user has set up a
    timer that pulls new values from the hardware into the app._data
    dictionary periodically. This setup can create small discrepancies between the actual
    data in the instrument and what is recorded in the Dataset, but in practice this has
    not been an issue for our experiments.

    A single Dataset can be used to group together certain instrument-parameter combinations
    that are useful to log into a file or display in a single plot.

    The Dataset object can automate saving self.data to disc in different
    formats and enables other widgets to easily display the whole dataset or
    certain columns versus time.

    Since parameters in instruments sometimes have complicated names, the
    class provides an easy way to overwrite names when the data is
    output to, for example, disc, using self.define_alias.
    """

    _built_in_save_formats = ["JSON", "Pickle", "NPY", "TXT"]

    def __init__(self, name: str, app=None) -> None:

        super().__init__()

        self.name = name
        self.app = app

        # The autosave option appends the latest data to the output file
        self.autosave_enabled = False
        self.autosave_interval = 120.0  # in seconds
        self.autosave_format = "JSON"
        self.autosave_filename = Path(f"autosave_{self.name}")
        # for some autosave formats it makes sense to only append new
        # rows, so we keep track of the rows that already have been
        # written to the output file
        self.autosave_next_row = 0

        self.instruments = []
        self.update_interval = 10.0  # in seconds

        # Dictionary of datapoints. Each key follows the <instrument>:<parameter>
        # naming scheme. Every value is a list and all lists need to have the
        # same length
        self.data = defaultdict(list)

        # Dictionary to optionally rename channels. key is 'instrument:parameter'
        # of channel to rename. Value is new name
        self.channel_names = {}

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_data)

    def __repr__(self) -> str:
        return f"Dataset {self.name} @ {hex(id(self))}"

    def __str__(self) -> str:
        return f"Dataset {self.name}"

    def __len__(self) -> int:
        """Returns the number of rows in self.data."""
        if len(self.data.keys()) == 0:
            return 0

        first_key = list(self.data.keys())[0]

        return len(self.data[first_key])

    def clear(self) -> None:
        """Clear the Dataset's contents."""
        self.data = defaultdict(list)
        self.autosave_next_row = 0

    def track_instrument(
        self,
        instrument: str,
        parameter: Optional[str] = None,
        alias: Optional[str] = None,
    ) -> None:
        """Add a parameter from an instrument to the dataset.

        Parameters
        ----------
        instrument
           The instrument name
        parameter
           The parameter that should be tracked. If None, all read parameters
           in the instrument are tracked.
        alias
           Use this as an alias when plotting or saving the dataset
           (only used if a parameter was given)
        """
        if instrument not in self.app._data:
            logger.error(f"{instrument} not found in App.")
            return

        # If a parameter is specified, only track that parameter
        if parameter is not None:
            if parameter not in self.app._data[instrument]:
                logger.error(f"{parameter} not available for {instrument}.")
                return

            self.instruments.append((instrument, parameter))

            # If alias is specified, change parameter name to alias
            if alias is not None:
                self.define_alias(f"{instrument}:{parameter}", alias)
        else:
            for p in self.app.list_instrument_parameters(instrument):
                # Never track the special "IGNORE" parameter
                if p != "IGNORE":
                    # Only track parameters (not commands)
                    # All parameters have a "read_value" key while commands do not
                    if "read_value" in self.app._data[instrument][p].keys():
                        self.instruments.append((instrument, p))

    def define_alias(self, original_name: str, alias: str) -> None:
        """Define an alias for an original parameter name of format <instrument>:<parameter>.

        The alias will be used when saving and plotting.
        """
        instrument, parameter = original_name.split(":")
        if (instrument, parameter) not in self.instruments:
            logger.warning(
                f"'{original_name}' is not available in dataset '{self.name}'."
            )
            return

        self.channel_names[original_name] = alias

    def start_autosave(
        self,
        interval: float = 120,
        file_format: str = "JSON",
        filename: str = "autosave",
    ) -> None:
        """Activates the dataset's autosave feature."""
        self.autosave_enabled = True
        self.autosave_interval = interval
        self.autosave_format = file_format
        self.autosave_filename = Path(filename)

        self.autosave_timer.start(1_000 * self.autosave_interval)

        logger.debug(
            f"Dataset {self.name} activated autosave."
            f" Interval: {self.autosave_interval} s"
        )

    def start_updates(self, interval: float = 10) -> None:
        """Start automaticaly logging data every `interval` seconds."""
        self.update_interval = interval

        self.update_timer.start(1_000 * self.update_interval)

        logger.debug(
            f"Dataset {self.name} started update mode."
            f" Interval: {self.update_interval} s"
        )

    def set_save_interval(self, interval: float) -> None:
        """Set the autosave interval in seconds."""
        self.autosave_interval = interval
        self.autosave_timer.setInterval(1_000 * self.autosave_interval)

    def set_update_interval(self, interval: float) -> None:
        """Set the update interval (when a new row is added) in seconds."""
        self.update_interval = interval
        self.update_timer.setInterval(1e3 * self.update_interval)

    def autosave(self) -> None:
        """Autosave data."""
        logger.debug(
            f"Dataset {self.name} autosaveing to" f" file {self.autosave_filename}"
        )

        if self.autosave_enabled:
            self.save(self.autosave_filename, self.autosave_format)

    def save_txt(self, filename: Path, header: Optional[str] = None) -> None:
        """Save data as a txt file.

        Parameters
        ----------
        filename
            filename to be used. If the file already exists, the data will be
            appended to it.
        header
            None or string to be used as a header. If given, the header should include
            the datetime. Each line of the header must end with \\\\n.
        """
        if filename.suffix != ".txt":
            filename = filename.with_suffix(".txt")

        # Write header if file doesn't exist
        if not filename.is_file():
            if header is None:
                # write default header
                with filename.open("w") as outfile:
                    outfile.write(
                        f"# {datetime.datetime.today().strftime('%Y-%m-%d')}\n"
                        f"# Logfile from hardware_control run\n"
                    )

                    datastructure = self.header_get_instruments()

                    outfile.write(f"{datastructure}\n")

            else:
                with filename.open("w") as outfile:
                    outfile.write(header)

        # Write data to file
        with filename.open("a") as outfile:
            length = len(self)
            while self.autosave_next_row < length:

                # Write line
                line = " ".join(
                    [str(self.data[key][self.autosave_next_row]) for key in self.data]
                )
                outfile.write(line + "\n")

                # Move pointer to next line
                self.autosave_next_row += 1

    def header_get_instruments(self) -> str:
        """Create a string of all values used in the dataset.

        Use the channel alias if available.
        """
        names = []

        for instrument, parameter in self.instruments:
            name = f"{instrument}:{parameter}"
            if name in self.channel_names:
                names.append(self.channel_names[name])
            else:
                names.append(parameter)

        result = "Time[s] "
        result += " ".join(names)
        return result

    def save_json(self, filename: Path) -> None:
        """Save data as a json file."""
        if filename.suffix != ".json":
            filename = filename.with_suffix(".json")

        with filename.open("w", encoding="utf-8") as outfile:
            json.dump(self.data, outfile, ensure_ascii=False, indent=4)

    def save_pickle(self, filename: Path) -> None:
        """Save data as a pickle file."""
        if filename.suffix != ".pickle":
            filename = filename.with_suffix(".pickle")
        with filename.open("wb") as outfile:
            pickle.dump(self.data, outfile)

    def save_npy(self, filename: Path) -> None:
        """Save data as a .npy file."""
        if filename.suffix != ".npy":
            filename = filename.with_suffix(".npy")
        np.save(filename, self.data)

    def save(self, filename: Path, file_format: str) -> None:
        """Saves the Dataset to a file. Format specifies the file format.

        Note: the file_format specifier is not case sensitive.

        File Formats:
           | json
           | pickle
           | npy
           | txt
        """
        file_format = file_format.upper()

        if file_format == "JSON":
            self.save_json(filename)
            logger.debug(f"Saved file {filename} as .json file.")
        elif file_format == "PICKLE":
            self.save_pickle(filename)
            logger.debug(f"Saved file {filename} as .pickle file.")
        elif file_format == "NPY":
            self.save_npy(filename)
            logger.debug(f"Saved file {filename} as .npy file.")
        elif file_format == "TXT":
            self.save_txt(filename)
            logger.debug(f"Saved file {filename} as .txt file.")
        elif self.app is not None and file_format in self.app.additional_save_formats:
            self.app.additional_save_formats[file_format](self, filename)
            logger.debug(f"Saved file {filename} as '{file_format}' file.")
        else:
            logger.warning(f"Unrecognized file format '{file_format}'.")

    def update_data(self) -> None:
        """Log values from the specified instruments in the Dataset.

        This is normally called by the internal timer.
        """
        logger.debug(f"Updating data in Dataset {self.name}.")

        self.data["time:time"].append(str(time.time()))

        for instrument, parameter in self.instruments:
            value = self.app.get_instrument_parameter(instrument, parameter)
            self.data[f"{instrument}:{parameter}"].append(value)

    def get_columns(self, columns: list) -> Dict:
        """Return a subset of columns.

        Parameters
        ----------
        columns
            Keys in self.data that should be returned

        Returns
        -------
        dict
            dictionary of requested columns
        """
        out = {}
        for name in columns:
            if name in self.data:
                out[name] = self.data[name]
            else:
                logger.error(f"{name} does not exist in data set {self.name}.")
        return out

    def to_pandas(
        self,
        columns: Optional[List] = None,
        cleanup: bool = True,
    ) -> pd.DataFrame:
        """Return a subset of columns as a pandas dataframe and optionally clean it up.

        Parameters
        ----------
        columns
            Keys in self.data that should be returned
        cleanup
            Remove all None values
        """
        if columns is None:
            data = self.data
        else:
            data = self.get_columns(columns)

        df = pd.DataFrame.from_dict(data)

        # convert from strings to numeric type
        for key in df.columns:
            df[key] = pd.to_numeric(df[key], errors="coerce")

        if cleanup:
            df = df.dropna()

        if "time:time" in df.columns:
            df.set_index("time:time")

        return df
