from collections import defaultdict
import datetime
import hashlib
import json
import logging
import os
import pickle
import time

import numpy as np

from PyQt5.QtCore import QObject, QTimer

from ...utility import convertibleToFloat

logger = logging.getLogger(__name__)


class Dataset(QObject):
    """Represents a complete dataset (ie. a collection of datapoints, which are
    collections of individual measurements)."""

    def __init__(self, name: str, app=None):

        super().__init__()

        self.app = app

        # Name of dataset
        self.name = name

        self.autosave = False  # Whether or not to enable autosave
        self.autosave_interval = 120  # Seconds
        self.autosave_format = "JSON"  # Save format
        self.autosave_filename = f"autosave_{self.name}"
        self.autosave_next_row = 0
        self.built_in_save_formats = ["JSON", "Pickle", "NPY", "TXT"]
        # Next row to save (prev. already saved)

        self.asynchronous_mode = False  # Synchronous vs asynchronous logging
        # list of tuples of instrument and parameters to log. If the parameters
        # list is None, will log all parameters
        self.async_instruments = []
        self.async_log_interval = 10  # Seconds
        self.async_add_timestamp = True  # Option to add timestamp to all values
        self.async_require_float = True  # Whether to requrire async data to be floats

        # Whether or not to require all data to present before allowing data to
        # be logged. If is False, missing values will be saved as None
        self.require_all = False

        # Dictionary of datapoints. Each key follows the <instrument>:<parameter>
        # naming scheme. Every value is a list and all lists need to have the
        # same length
        self.data = defaultdict(list)

        # Dictionary to optionally rename channels. key is 'instrument:parameter'
        # of channel to rename. Value is new name
        self.channel_names = {}

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.exec_autosave)

        self.async_log_timer = QTimer(self)
        self.async_log_timer.timeout.connect(self.log_async)

    def __repr__(self):
        return f"Dataset {self.name} @ {hex(id(self))}"

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.name}"

    def clear(self):
        """ Clears the dataset's contents """

        self.data = defaultdict(list)
        self.autosave_next_row = 0

    def values_are_numeric(self, key: str):
        """ Looks at the value in self.data specified by 'key' and returns if it is numeric

        Parameters
        ----------
        key : str
            Key in self.data specifing a list of data to analyze.

        Returns
        -------
        bool
            True if key in self.data and all values in list specified by 'key' can
            be converted to numeric type.
        """

        def is_number(x):
            try:
                float(x)
            except ValueError:
                return False
            except TypeError:
                return False
            return True

        # Ensure key exists
        if key not in self.data:
            return False

        # Else, for each item in list, check if number
        for val in self.data[key]:
            if not is_number(val):
                return False

        return True

    def values_are_list(self, key: str):
        """ Looks at the value in self.data specified by 'key' and returns if it is a list

        Parameters
        ----------
        key : str
            Key in self.data specifing value to check if is list

        Returns
        -------
        bool
            True if key in self.data and points to a list
        """

        # Ensure key exists
        if key not in self.data:
            return False

        # If not a list, check one number
        if isinstance(self.data[key], list):
            return True

        return False

    def name_channel(self, channel: str, name: str):
        """Channel must be a string listing the instrument and parameter of
        the channel to rename. THe instrument:parameter pair must be
        listed in self.data.

        """

        self.channel_names[channel] = name

    def start_autosave(
        self, interval: float = 120, format: str = "JSON", filename: str = "autosave"
    ):
        """ Activates the dataset's autosave feature. """

        self.autosave = True
        self.autosave_interval = interval
        self.autosave_format = format
        self.autosave_filename = filename

        self.autosave_timer.start(1e3 * self.autosave_interval)

        logger.info(
            f"Dataset {self.name} activated autosave."
            f" Interval: {self.autosave_interval} s"
        )

    def start_asynch(self, interval: float = 10, add_timestamp: bool = True):
        """ Converts the dataset to an asynchronous logging dataset. """

        self.async_log_interval = interval
        self.async_add_timestamp = add_timestamp
        self.asynchronous_mode = True

        self.async_log_timer.start(1e3 * self.async_log_interval)

        logger.info(
            f"Dataset {self.name} activated asynchronous mode."
            f" Interval: {self.async_log_interval} s"
        )

    def set_save_interval(self, interval: float):

        self.autosave_interval = interval

        self.autosave_timer.setInterval(1e3 * self.autosave_interval)

    def set_async_interval(self, interval: float):

        self.async_log_interval = interval

        self.async_log_timer.setInterval(1e3 * self.async_log_interval)

    def len_same(self):
        """Returns the length of all of the values in self.data. If they aren't
        all the same length (they should be), returns -1."""

        # Get maximum and minium length
        val_min = self.len_min()
        val_max = self.len_max()

        # If not same, some values have different lengths
        if val_min != val_max:
            return -1

        # Otherwise return length
        return val_min

    def len_max(self):

        if len(self.data) == 0:
            return 0

        return max([len(self.data[key]) for key in self.data])

    def len_min(self):
        """Returns the length of the shortest list in self.data."""

        if len(self.data) == 0:
            return 0

        return min([len(self.data[key]) for key in self.data])

    def exec_autosave(self):
        """ Called by the autosave timer. Triggers a call to self.save() """

        logger.info(
            f"Dataset {self.name} autosaveing to" f" file {self.autosave_filename}"
        )

        if self.autosave:  # Check if autosave enabled
            self.save(self.autosave_filename, self.autosave_format)

    def save(self, filename: str, format: str):
        """Saves the dataset to a file. format specifies the file format. The
        file format specifier is not case sensitive.

                File Formats:
                    JSON
                    Pickle
                    NPY
                    TXT
                    HDF"""

        ext = os.path.splitext(filename)[-1].lower()

        if format == "JSON":

            # Add extension if not specified
            if ext == "":
                filename = filename + ".json"

            # Write header if file doesn't exist
            with open(filename, "w", encoding="utf-8") as outfile:
                json.dump(self.data, outfile, ensure_ascii=False, indent=4)

        elif format == "Pickle":

            # Add extension if not specified
            if ext == "":
                filename = filename + ".pickle"

            # Write header if file doesn't exist
            with open(filename, "wb") as outfile:
                pickle.dump(self.data, outfile)

        elif format == "NPY":

            # Add extension if not specified
            if ext == "":
                filename = filename + ".npy"

            # Write header if file doesn't exist
            # with open(filename, "w") as outfile:
            np.save(filename, self.data)

        elif format == "TXT":  # TODO: this only appends, not overwrite
            # TODO: Jump to new file if file too big

            # Add extension if not specified
            if ext == "":
                filename = filename + ".txt"

            # Create directory

            # Write header if file doesn't exist
            if not os.path.exists(filename):
                with open(filename, "w") as outfile:

                    outfile.write(
                        f"# {datetime.datetime.today().strftime('%Y-%m-%d')}\n"
                        f"# Logfile from hardware_control run\n"
                    )

                    datastructure = ""
                    if self.async_add_timestamp:
                        datastructure += "Time[s] "
                    datastructure += " ".join(
                        [e[0].get_header(e[1]) for e in self.async_instruments]
                    )

                    myhash = hashlib.sha256()
                    myhash.update(datastructure.encode("utf-8"))
                    version = myhash.hexdigest()

                    outfile.write(f"# Version: {version}\n")
                    outfile.write(f"{datastructure}\n")

            # Write file data
            with open(filename, "a") as outfile:

                length = self.len_min()
                while self.autosave_next_row < length:

                    # Write line
                    line = " ".join(
                        [
                            str(self.data[key][self.autosave_next_row])
                            for key in self.data
                        ]
                    )
                    outfile.write(line + "\n")

                    # Move pointer to next line
                    self.autosave_next_row += 1
        elif self.app is not None and format in self.app.additional_save_formats:
            try:
                self.app.additional_save_formats[format](self, filename)
            except:
                logger.error(
                    f"Invalid save function provided for '{format}'.", exc_info=True
                )
        else:
            logger.warning(f"unrecognized file format '{format}'.")

    def log_async(self):
        """Periodically called by timer, logs values from included instruments
        to the datasets. Logs timestamp if requested.

        """

        # Return immediately if not in async mode
        if not self.asynchronous_mode:
            return

        logger.debug(f"Dataset {self.name} logging asynchronous data")

        # Check that all requested parameters are available. If they
        # aren't, don't log anything. This ensures the dataset's
        # columns are all the same length
        if self.require_all:
            for ai in self.async_instruments:
                name = ai[0].name
                vkeys = ai[0].get_value_keys(ai[1])

                if vkeys is None:
                    logger.info(
                        f"Async log for dataset {self.name} aborted because"
                        f" not all values present"
                    )
                    return

            # If all values must be valid (because require_all is
            # true) and all values must be convertible to float, check
            # that values are valid num
            if self.async_require_float:
                for ai in self.async_instruments:
                    for vk in vkeys:
                        try:
                            float(ai[0].values[vk])
                        except:
                            v = ai[0].values[vk]
                            logger.info(
                                f"Async log for dataset {self.name} aborted"
                                f" because value '{v}' for parameter '{vk}'"
                                f" cannot be converted to a float."
                            )
                            return

        # Add timestamp if requested
        if self.async_add_timestamp:
            self.data["time:time"].append(str(time.time()))

        # Add data from each specified instrument
        for ai in self.async_instruments:
            name = ai[0].name

            vkeys = ai[0].get_value_keys(ai[1], False)
            logger.debug(f"Logging data for instrument: {name}. Keys: {vkeys}")

            # Get each key
            name = ai[0].name
            for vk in vkeys:

                # Check that parameter exists
                if vk not in ai[0].values:
                    self.data[f"{name}:{vk}"].append(None)
                    logger.debug(f"Adding data: data[{name}:{vk}] = None")
                    continue

                # Check that parameter exists
                if self.async_require_float and not convertibleToFloat(
                    ai[0].values[vk]
                ):
                    self.data[f"{name}:{vk}"].append(None)
                    logger.debug(f"Adding data: data[{name}:{vk}] = None")
                    continue

                # Otherwise add raw data
                nd = ai[0].values[vk]
                self.data[f"{name}:{vk}"].append(nd)
                logger.debug(f"Adding data: data[{name}:{vk}]='{nd}'")

    def get_corresponding_arrays(self, set_names: list, convert_to_float=False):
        """Returns lists for each of the parameters specified in set_names (
        indicated as <instrument>:<parameter>). If 'None' appears in
        any of the specified lists, all data points at that index for
        all returned lists are removed. This guarantees all returned
        lists have the same length and that the lists indecies
        correspond with eachother.

        Returns a dictionary, key = parameter name, value = list

        """

        # Initialze return dictionary with the valid values in set_names
        ret_dic = {}
        for sn in set_names:
            if sn in self.data:
                ret_dic[sn] = []

        # Populate ret_dic
        for idx in range(self.len_min()):

            skip_idx = False

            # Check that no elements are 'None' at this index
            for sn in ret_dic:
                # If 'None' present, skip to next index
                if self.data[sn][idx] is None:
                    skip_idx = True
                    break

            if skip_idx:
                continue

            # Add data to ret_dic
            for sn in ret_dic:
                if convert_to_float:
                    ret_dic[sn].append(float(self.data[sn][idx]))
                else:
                    ret_dic[sn].append(self.data[sn][idx])

        return ret_dic

    def add_instrument(self, instr, parameters=None):

        # TODO: Add units to backends

        self.async_instruments.append((instr, parameters))
