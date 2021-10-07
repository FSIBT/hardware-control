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
    """Collect values from different instruments over time.

    This data structure an be used to track values over time. It
    requires a list of instruments, parameter names, a time interval
    in order to add a row with the current time stamp and the values
    for each parameter to an internal data table every N seconds.

    The object also automates saving this table to disc in different
    formats and enables other widgets to easily display the whole
    dataset or certain columns vs time.

    The idea is that a single datasets can group together certain
    instrument-parameter combinations that are useful to log into a
    file or display in a single plot.

    The length of a Dataset is the number of rows in self.data.

    Since parameters in instruments can have complicated names, the
    class provides an easy way to overwrite names when the data is
    output to, for example, disk.

    The internal data is saved as a defaultdict of lists where the keys
    have the form 'instrument:parameter' and the list has the
    instrument value for each time stamp.

    The time is stored in a special column called 'time:time'.

    The data is taken from hc.Instruments, meaning that it is not taken
    directly from the backends; a Dataset therefore does not communicate
    with any actual hardware. It is assumed that the user has set up a
    timer that pulls new data from the hardware into the Instrument.values
    dictionary periodically.

    """

    built_in_save_formats = ["JSON", "Pickle", "NPY", "TXT"]

    def __init__(self, name: str, app=None) -> None:

        super().__init__()

        self.name = name
        self.app = app

        self.autosave = False
        self.autosave_interval = 120  # in seconds
        self.autosave_format = "JSON"
        self.autosave_filename = Path(f"autosave_{self.name}")
        # for some autosave formats it makes sense to only append new
        # rows, so we keep track of the rows that already have been
        # written to the output file
        self.autosave_next_row = 0

        self.instruments = []
        self.update_interval = 10  # in seconds

        # Dictionary of datapoints. Each key follows the <instrument>:<parameter>
        # naming scheme. Every value is a list and all lists need to have the
        # same length
        self.data = defaultdict(list)

        # Dictionary to optionally rename channels. key is 'instrument:parameter'
        # of channel to rename. Value is new name
        self.channel_names = {}

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.timer_autosave)

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
        """Clears the dataset's contents"""

        self.data = defaultdict(list)
        self.autosave_next_row = 0

    def track_instrument(
        self,
        instrument: str,
        parameter: Optional[str] = None,
        alias: Optional[str] = None,
        channels: Optional[List] = None,
    ) -> None:
        """Add a parameter from an instrument to the dataset.

        If parameter is `None`, all parameters that can be read
        are included. If a list of channels is specified, only
        the parameters of those channels are included.

        If a parameter is specified, one can provide an alias
        for the parameter.

        """

        # If a parameter is specified, only track that parameter
        if parameter is not None:
            self.instruments.append((instrument, parameter))
            # If alias is specified, change parameter name to alias
            if alias is not None:
                self.define_alias(instrument + ":" + parameter, alias)
        else:
            for p in self.app.list_instrument_parameters(instrument):
                # If a list of channels is specified, track all parameters of those channels
                if channels is not None:
                    for ch in channels:
                        ch = "CH" + str(ch)
                        if ch in p:
                            self.instruments.append((instrument, p))
                # If neither parameter nor channel is specified, track all the instrument's parameters
                else:
                    self.instruments.append((instrument, p))

    def define_alias(self, channel: str, alias: str) -> None:
        """Channel must be a key in self.data and name is the replacement string."""

        instrument, parameter = channel.split(":")
        if (instrument, parameter) not in self.instruments:
            logger.warning(f"'{channel}' is not available in dataset '{self.name}'.")
            return

        self.channel_names[channel] = alias

    def start_autosave(
        self, interval: float = 120, format: str = "JSON", filename: str = "autosave"
    ):
        """Activates the dataset's autosave feature."""

        self.autosave = True
        self.autosave_interval = interval
        self.autosave_format = format
        self.autosave_filename = Path(filename)

        self.autosave_timer.start(1e3 * self.autosave_interval)

        logger.debug(
            f"Dataset {self.name} activated autosave."
            f" Interval: {self.autosave_interval} s"
        )

    def start_updates(self, interval: float = 10):
        """Start automaticaly logging data every `interval` seconds."""

        self.update_interval = interval

        self.update_timer.start(1e3 * self.update_interval)

        logger.debug(
            f"Dataset {self.name} activated asynchronous mode."
            f" Interval: {self.update_interval} s"
        )

    def set_save_interval(self, interval: float):
        self.autosave_interval = interval
        self.autosave_timer.setInterval(1e3 * self.autosave_interval)

    def set_update_interval(self, interval: float):
        self.update_interval = interval
        self.update_timer.setInterval(1e3 * self.update_interval)

    def timer_autosave(self):
        logger.debug(
            f"Dataset {self.name} autosaveing to" f" file {self.autosave_filename}"
        )

        if self.autosave:
            self.save(self.autosave_filename, self.autosave_format)

    def save_txt(self, filename: Path, header: Optional[str] = None) -> None:
        r"""Appends data if the file already exists.

        Parameters
        ----------
        filename
            filename to be used
        header
            None or string to be used as a header. If given the header needs to include
            and end on a \n.

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

                    datastructure = "Time[s] "
                    datastructure += " ".join(
                        [
                            instrument_param_tuple[1]
                            for instrument_param_tuple in self.instruments
                        ]
                    )

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

    def save_json(self, filename: Path):
        if filename.suffix != ".json":
            filename = filename.with_suffix(".json")

        with filename.open("w", encoding="utf-8") as outfile:
            json.dump(self.data, outfile, ensure_ascii=False, indent=4)

    def save_pickle(self, filename: Path):
        if filename.suffix != ".pickle":
            filename = filename.with_suffix(".pickle")
        with filename.open("wb") as outfile:
            pickle.dump(self.data, outfile)

    def save_npy(self, filename: Path):
        if filename.suffix != ".npy":
            filename = filename.with_suffix(".npy")
        np.save(filename, self.data)

    def save(self, filename: Path, format: str):
        """Saves the dataset to a file. Format specifies the file format.

        The file format specifier is not case sensitive.

        File Formats:
           JSON
           Pickle
           NPY
           TXT

        """

        format = format.upper()

        if format == "JSON":
            self.save_json(filename)
        elif format == "PICKLE":
            self.save_pickle(filename)
        elif format == "NPY":
            self.save_npy(filename)
        elif format == "TXT":
            self.save_txt(filename)
        elif self.app is not None and format in self.app.additional_save_formats:
            self.app.additional_save_formats[format](self, filename)
        else:
            logger.warning(f"Unrecognized file format '{format}'.")

    def update_data(self) -> None:
        """Logs values from the specified instruments to the datasets.

        Normally called by the internal timer.

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
            dictionay of requested columns

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
