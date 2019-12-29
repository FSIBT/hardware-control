# -*- coding: utf-8 -*-
import datetime
import hashlib
import pathlib
import sys
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from colorama import Fore, Style
import json

from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QObject, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QAction,
    QGroupBox,
    QInputDialog,
)


class HC_Comm(QObject):
    """This object is used to automate creating threads and communication objects.
    By calling this object's functions, data can be safely transfered between the
    main thread and communication threads."""

    sigUpdateSettings = pyqtSignal(str, str, float)
    sigCommand = pyqtSignal(str, float)
    sigWrite = pyqtSignal(str, float)
    sigQuery = pyqtSignal(str, float)
    sigTryConnect = pyqtSignal(float)
    sigCommandList = pyqtSignal(str, float)
    sigClose = pyqtSignal()

    # TODO: @TImo Bauer Add 'try_connect' frequency
    def __init__(self, backend, instrument, try_connect_period=1000):
        super().__init__()
        self.backend = backend
        self.instrument = instrument  # Calling instrument UI (eg. HC_scope)
        self.backend_model = backend.ID
        self.try_connect_period = try_connect_period

        self.expire_time = 40
        self.list_expire_time = 5

        self.worker = HC_CommWorker(self.backend)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        # Connect Comm's signals for CommWorker's slots
        self.sigUpdateSettings.connect(self.worker.update_setting)
        self.sigCommand.connect(self.worker.command)
        self.sigWrite.connect(self.worker.write)
        self.sigQuery.connect(self.worker.query)
        self.sigTryConnect.connect(self.worker.try_connect)
        self.sigCommandList.connect(self.worker.command_listdata)
        self.sigClose.connect(self.worker.close)

        # Connect CommWorker's signals to Comm's slots
        self.worker.sigReturnValues.connect(self.backend_return)
        self.worker.sigReturnOnline.connect(self.backend_return_online)
        self.worker.sigReturnList.connect(self.backend_return_listdata)

        # Connect timer
        self.try_connect_timer = QTimer(self)
        self.try_connect_timer.timeout.connect(self.try_connect)
        self.try_connect_timer.start(self.try_connect_period)

    def close(self):
        self.instrument.pDebug(
            f"\tInstrument: '{self.instrument.name}' closing Comm with backend of type '{self.backend_model}'."
        )
        self.try_connect_timer.stop()  # Stop
        self.sigClose.emit()
        self.worker_thread.quit()  # Kill thread
        if self.instrument.window.app.print_close_info:
            print(
                Fore.BLUE
                + f"\t'{self.instrument.name}': Closing...\t\t\t--:-- sec"
                + Style.RESET_ALL,
                end="",
                flush=True,
            )
            start_time = time.time()
        self.worker_thread.wait()  # Wait for thread to join (otherwise, if main thread exists first, stdout will be closed while the worker_thread may still be running and try to write to stdout, causing an error to arise)
        if self.instrument.window.app.print_close_info:
            print(
                f"\r\t'{self.instrument.name}': Closed    \t\t\t"
                + "{:.2f}".format(time.time() - start_time)
                + " sec    "
            )

    def update_setting(self, setting: str, value: str):
        """Transfers the setting and value information to the worker thread"""
        self.instrument.pDebug(
            f"Instrument: {self.instrument.name} called 'update_setting()' for setting '{setting}' and sent message '{value}'."
        )
        self.sigUpdateSettings.emit(setting, value, time.time() + self.expire_time)
        self.instrument.window.app.add_log(
            self.instrument.name, self.backend_model, "SET", setting, value
        )

    def command(self, cmd: str):
        """Sends a command to the worker in the worker thread"""
        self.instrument.pDebug(
            f"Instrument: {self.instrument.name} called 'command()' and sent command: '{cmd}'."
        )
        self.sigCommand.emit(cmd, time.time() + self.expire_time)
        self.instrument.window.app.add_log(
            self.instrument.name, self.backend_model, "CMD", cmd
        )

    def write(self, msg: str):
        """Sends a command to be sent to the instrument by the worker in the worker thead"""
        self.instrument.pDebug(
            f"Instrument: {self.instrument.name} called 'write()' and sent message: '{msg}'."
        )
        self.sigWrite.emit(msg, time.time() + self.expire_time)
        self.instrument.window.app.add_log(
            self.instrument.name, self.backend_model, "WRT", setting
        )

    def query(self, msg: str):
        """Sends a query statement to be sent to the instrument by the worker in the worker thead"""
        self.instrument.pDebug(
            f"Instrument: {self.instrument.name} called 'query()' and sent message: '{msg}'."
        )
        self.sigQuery.emit(msg, time.time() + self.expire_time)
        self.instrument.window.app.add_log(
            self.instrument.name, self.backend_model, "QRY", setting
        )

    def try_connect(self):
        """Tells the worker to tell the backend to try to connect to the instrument"""
        self.sigTryConnect.emit(time.time() + self.expire_time)

    def command_listdata(self, cmd: str):
        """Sends a command to the worker in the worker thread just like command(),
        but returns two lists instead of a string."""
        self.instrument.pDebug(
            f"Instrument: {self.instrument.name} called 'command_listdata()' and sent command: '{cmd}'."
        )
        self.sigCommandList.emit(cmd, time.time() + self.list_expire_time)
        self.instrument.window.app.add_log(
            self.instrument.name, self.backend_model, "CMDLD", cmd
        )

    @pyqtSlot(str)
    def backend_return(self, retval: str):
        """Receives a return value from the CommWorker and sends it to the instrument's
        backend_return function, which adds it to the instrument's values dictionary or
        , if overwritten, may process the return string immediately for example by
        updating the UI."""
        self.instrument.pDebug(
            f"Instrument: {self.instrument.name} received return from backend '{self.backend_model}'. Return message: {retval}"
        )
        self.instrument.backend_return(retval)

    @pyqtSlot(bool)
    def backend_return_online(self, connected: bool):
        """ Gets called by the worker after the worker hears from the instrument if it successfully connected.
        Updates the state of the instrument - ie. if it is or is not online"""
        self.instrument.backend_return_online(connected)

    @pyqtSlot(str, list, list)
    def backend_return_listdata(self, desc: str, data1: list, data2: list):
        """Receives a return value from the CommWorker and sends it to the instrument's
        backend_return_listdata function, which can be overwritten by the UI's author
        to process the data."""
        self.instrument.backend_return_listdata(desc, data1, data2)


class HC_CommWorker(QObject):
    """Uses signals + slots to receive data from HC_Comm and relays the information
    to the backend object. Then sends the return value back to HC_Comm via signals +
    slots, when HC_Comm then pushes onto the back of the isntrument's values dict"""

    sigReturnValues = pyqtSignal(str)
    sigReturnOnline = pyqtSignal(bool)
    sigReturnList = pyqtSignal(str, list, list)

    def __init__(self, backend):
        super().__init__()

        self.backend = backend

    @pyqtSlot(str, str, float)
    def update_setting(self, setting: str, value: str, expire_time: float):
        """Transfers a setting and value to the backend"""

        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=SET: "{setting}" "{value}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.update_setting(setting, value)
        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(str, float)
    def command(self, cmd: str, expire_time: float):
        """Transfers a command to the backend"""
        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=CMD:"{cmd}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.command(cmd)
        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(str, float)
    def write(self, msg: str, expire_time: float):
        """Transfers a command to be sent directly to the instrument to the backend"""
        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=WRT:"{msg}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.write(msg)
        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(str, float)
    def query(self, msg: str, expire_time: float):
        """Transfers a query statement to be sent directly to the instrument to the backend"""
        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=QRY:"{msg}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.query(msg)
        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(float)
    def try_connect(self, expire_time: float):
        """Is called by HC_Comm on a timer. Tells backend to check if is
        connected, else connect."""
        if time.time() > expire_time:  # Skip command if too old
            pass
        else:
            online = self.backend.try_connect()
            self.sigReturnOnline.emit(online)

    @pyqtSlot(str, float)
    def command_listdata(self, cmd: str, expire_time: float):
        """Transfers a command to the backend"""
        if time.time() > expire_time:  # Skip command if too old
            ret_val = (
                f'EXPIRED=CMD:"{cmd}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]',
                [],
                [],
            )
        else:
            ret_val = self.backend.command_listdata(cmd)
        self.sigReturnList.emit(ret_val[0], ret_val[1], ret_val[2])

    @pyqtSlot()
    def close(self):
        """"Tells backend to close the connection. Then reports if instrument is
        offline."""
        online = self.backend.close()
        self.sigReturnOnline.emit(online)


class LoggingGroup:
    """Describes a list of values in an HC_Instrument that should be logged
    when get_header() or get_values() is called."""

    def __init__(self, group_name: str):

        # These are the keys of <HC_Insturment>.values to log. This is a list
        # of strings.
        self.values_keys = []

        # These are the names for each of the logged values. These titles/names
        # are what will be passed when get_header() is called.
        self.values_titles = []

        # These are optional desciptions for each of the logged parameters.
        self.values_descriptions = []

        # This is the name of the logging group
        self.group_name = group_name

    def setDescriptions(self, descrs: list):
        """Add descriptions for the logging values"""
        self.values_descriptions = descrs


class HC_Instrument(QGroupBox):
    def __init__(self, window, name: str):
        super().__init__(name)
        # ToDo Why ordered dict??
        self.settings = OrderedDict()
        self.values = OrderedDict()
        self.values_unit = []
        self.logging_groups = []
        self.name = name
        self.manufacturer = None
        self.company = None
        self.online = False
        self.comm = None
        self.ignore = False  # Dictates if instrument should be ignored by

        # Global Constants
        self.globalRefreshRate = 500  # ms refresh
        # this is a global reference for limiting the scaling the widgets
        self.globalLineHeight = 50  # Lineheight of athe average  spinbox
        self.globalLineWidth = 300  # Linewidth of athe average  spinbox

        # ConnectionTool and ScanTool widgets

        # self.inbox = {}  # Receives strings from the HC_comm object

        self.window = window  # parent needs to have a field called 'app' which
        # is an instance of 'HC_App'

        window.app.add_instrument(self)

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.name}"

    def add_logging_group(
        self, group_name: str, value_keys: list, header_strs: list = []
    ):
        """Adds a group of values to log. When calling get_values() or
        get_header()"""

        # Make sure arrays match dimensions
        if len(value_keys != header_strs):
            return False

        # Only keep keys actually present in self.values
        vks = []
        hss = []
        for idx, vk in enumerate(value_keys):
            if vk in self.values:
                vks.append(vk)
                hss.append(header_strs[idx])

        # Create new group
        new_group = LoggingGroup(group_name, vks, hss)

        # Append new group to list
        self.logging_groups.append(new_group)

        return True

    def get_logging_group(self, group_name: str):
        """Finds the logging group with name 'group_name' and returns it. If
        no such group is found, returns None."""

        for g in self.logging_groups:
            if g.name == group_name:
                return g

        return None

    def get_header(self, group_name=""):
        """Returns the header for the specified logging group. If the group
        requested does not exist, returns None"""
        if group_name == "":
            return get_default_header()
        else:

            for lg in self.logging_groups:
                if lg.group_name == group_name:
                    return ".".join(lg.values_titles)  # TODO: Better way to join/label?

    def get_values(self, group_name=""):
        """Returns the values for the specified logging group. If the group
        requested does not exist, returns None"""
        if group_name == "":
            return get_default_header()
        else:

            vals = []
            for lg in self.logging_groups:
                if lg.group_name == group_name:
                    for k in lg.value_keys:
                        vals.append(self.values[k])
                return vals
            return None

    def get_default_header(self):
        """Supply a header for a log file"""
        header = f"{self.manufacturer}-{self.model}-"
        header += "-".join(
            [
                f"{vname}[{vunit}]"
                for vname, vunit in zip(self.values.keys(), self.values_unit)
            ]
        )
        return header

    def get_default_values(self):
        """Return current list of values for logging"""
        return self.values.values()

    def enableDisableWidgets(self, setting: str, value: str):
        """User can overwrite this to enable/disable widgets when conditions/settings
        are changed"""
        pass

    def update_setting(self, setting: str, value: str):
        """Update a setting in settings and values dictionary for the instrument"""

        self.enableDisableWidgets(setting, value)

        try:
            self.settings[setting] = value
        except KeyError:
            self.pDebug(
                "ERROR: Key '{parameter}' does not exist for instrument '{self.name}' in settings dictionary."
            )

        if self.comm is not None:
            try:
                self.values[setting] = self.comm.update_setting(setting, value)
            except KeyError:
                self.pDebug(
                    "ERROR: Key '{parameter}' does not exist for instrument '{self.name}' in values dictionary."
                )

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
            self.pDebug(
                "ERROR: Key '{parameter}' does not exist for instrument '{self.name}'."
            )

        if type(current_val) == str:
            try:
                self.settings[parameter] = value
            except:
                self.pDebug(
                    f"ERROR: Failed to convert {type(value)} '{value}' to string."
                )
                self.pDebug("Exiting scan")
                return False
        elif type(current_val) == int or type(current_val) == float:
            try:
                self.settings[parameter] = float(value)
            except:
                self.pDebug(
                    f"ERROR: Failed to convert {type(value)} '{value}' to float."
                )
                self.pDebug("Exiting scan")
                return False

        else:
            self.pDebug("ERROR: Settings must have string, float, or int datatype.")
            self.pDebug(
                f"\tInstrument '{self.name}' setting {parameter} has type: {type(current_val)}"
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
                self.pDebug(f"settings for {self.name} read from file '{filename}'")
        except:
            self.pDebug(f"ERROR: Failed to read file '{filename}'. Using defualt case.")
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
                self.pDebug(f"settings for {self.name} saved to file '{filename}'")
        except Exception as e:
            self.pDebug(
                f"ERROR: Failed to write file '{filename}'. settings not saved."
            )
            self.pDebug(f"\t{e}")

    def send_state(self):
        """Writes the entire state/settings dicitonary to the oscilloscope"""
        for key in self.settings:
            if self.comm is not None:
                self.comm.update_setting(key, str(self.settings[key]))

    def close(self):
        if self.comm is not None:
            self.comm.close()

    def log_note(self, note: str):
        """Adds a 'Note' type log entry to the HC_App's log list"""
        if self.comm is not None:
            self.window.app.add_log(self.name, self.comm.backend_model, "NOTE", note)
        else:
            self.window.app.add_log(self.name, "N/A", "NOTE", note)

    def read_message(self, prefix: str):
        """Looks for an entry in self.values with the key 'prefix'. If found, the
        key's value is returned, else it returns None."""

        if prefix in self.values:  # If prefix exists as key, return vale
            rval = self.values[prefix]
        else:  # Else return None
            rval = None

        return rval

    def backend_return(self, retval: str):
        """Is called by self.comm when the backend returns a value. The return string
        is converted here into a dictionary's key/value pair and added to self.values.
        An equals sign ('=') is used to separate the key and value, with key coming
        first."""

        sep_idx = retval.find("=")
        if sep_idx != -1:  # Separator was found...

            # Check for asterisk at end of key, ie. right before '='. This indicates
            # that this command unlocks HC_App's Macro runner and that the parameter
            # needs to be logged in HC_App.saved_data immediately by appending the
            # received value to the back of the list in HC_App.saved_data with the
            # key specified by the returned value.
            if sep_idx > 0 and retval[sep_idx - 1] == "*":

                self.pDebug("Received RCD", False, True)

                self.window.app.macro_locked = False
                # Unlock macro

                sep_idx -= 1
                # Remove asterisk from key
                key = retval[0:sep_idx]  # Get key
                val = retval[sep_idx + 2 :]  # Get value

                try:  # Append data
                    self.window.app.saved_data[key].append(val)
                except:  # Does not exist, create list and key
                    self.window.app.saved_data[key] = [val]

            else:
                key = retval[0:sep_idx]
                val = retval[sep_idx + 1 :]

            self.values[key] = val

        else:  # If no separator, put under 'Misc'

            self.values["Misc"] = retval

    def backend_return_online(self, connected: bool):
        """Is called by self.comm when the backend returns an online status."""

        self.online = connected

    def backend_return_listdata(self, descr: str, data1: list, data2: list):
        """Is called by self.comm when the backend returns from command_listdata,
        which returns a string and two lists. The author of the UI can overwrite
        this function to procses the return data."""
        pass

    def pDebug(self, msg, important=False, blue=False):
        self.window.app.pDebug(msg, important)


class HC_App(QApplication):
    """Subclass of QApplication that is aware of what hardware is connected to it and can log data"""

    def __init__(self, debug: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instruments = (
            []
        )  # TODO: Verify this is actually a dict and change declaration here
        self.log = []  # List of strings for debugging/logging purposes
        self.macros = {}  # Dict of hc-commands (used for scans + trigger buttons)
        self.variables = {}  # Dict of app variables
        self.saved_data = {}
        # Dict of data saved directly with query commmands
        self.dummy = False
        self.print_close_info = False
        self.debug = debug

        # Dictates if hc_commands are allowed to execute raw python code via calls to the
        # via teh 'exec' function
        self.exec_enabled = True

        self.macro_locked = False
        self.macro_lock_end_time = None
        self.curr_macro = []
        self.curr_cmd_idx = 0

        # Start a timer to resume timer after any pauses
        self.macro_timer = QTimer(self)
        self.macro_timer.timeout.connect(self.resume_macro)
        # Don't start timer yet...

    def add_instrument(self, widget):
        # check if name is already present
        if widget.name in [x.name for x in self.instruments]:
            raise KeyError(f"Intrument name '{widget.name}' is already present")

        self.instruments.append(widget)

    def save_settings(self, filename: str):
        """ Copys the settings dictionaries from each instrument into a new dictionary
        with the instrument's name serving as the key. The dictionary is then saved
        to a JSON file. """

        app_settings = {instr.name: instr.settings for instr in self.instruments}

        # Write JSON file
        try:
            with open(filename, "w") as file:
                json.dump(app_settings, file)
                self.pDebug(
                    f"settings for {self.comm.instr.ID} saved to file '{filename}'"
                )
        except Exception as e:
            self.pDebug(f"ERROR: Failed to write file '{filename}'. State not saved.")
            self.pDebug(f"\t{e}")

    def list_instruments(self):
        if self.instruments:
            self.pDebug("Known instruments:")
        else:
            self.pDebug("No instruments known")
        for i in self.instruments:
            self.pDebug(f"  {i}")

    def check_instruments(self):
        """Make sure all instruments conform to specifications"""
        for i in self.instruments:
            try:
                i.name
            except AttributeError:
                self.pDebug(f"Error: Instrument  {i} needs a .name")
            if i.manufacturer is None:
                self.pDebug(f"Error: Instrument  {i} needs a .manufacturer")
            if i.model is None:
                self.pDebug(f"Error: Instrument  {i} needs a .model")

    def close(self):
        """Closes all instruments"""
        for instr in self.instruments:
            try:  # User may not have initialized comm correctly as HC_Comm - error check here
                instr.comm.close()  # Send close signal to backend - stop connect timer
            except Exception as e:
                self.pDebug(f"Failed to close instrument '{instr.name}'.")
                self.pDebug(str(e))

    def add_log(
        self,
        instr_name: str,
        backend_model: str,
        log_type: str,
        arg1: str,
        arg2: str = "",
    ):

        datestr = datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")
        if log_type == "SET":
            self.log.append(
                f'{instr_name}: \tSET "{arg1}" "{arg2}" \t[{datestr}] \t[{backend_model}]'
            )
        elif (
            log_type == "CMD"
            or log_type == "WRT"
            or log_type == "QRY"
            or log_type == "NOTE"
            or log_type == "WARNING"
            or log_type == "CMDLD"
        ):
            self.log.append(
                f'{instr_name}: \t{log_type} "{arg1}" \t[{datestr}] \t[{backend_model}]'
            )
        else:
            self.pDebug(f"Invalid log type code '{log_type}' received")

    def close(self):

        for instr in self.instruments:
            self.pDebug(f"HC_App called 'close()' for instrument: '{instr.name}'.")
            instr.close()

    def add_macro(self, name: str, commands: list):
        """Adds a macro to the app's macro list. Overwrites if macro already exists"""
        self.macros[name] = commands

    def add_macro_file(self, name: str, filename: str):
        """Adds a macro to the app's macro list. Overwrites if macro already exists"""

        commands = []

        #Read file line by line
        with open(filename, "r") as infile:
            for line in infile:
                commands.append(line.rstrip('\n'))

        if len(commands) > 0:
            self.add_macro(name, commands)
            return True
        else:
            return False



    def add_variable(self, name: str, value: str):
        """Adds an application variable. Overwrites if variable already exists"""
        self.variables[name] = value

    def process_hc_command(self, command: str):
        """Accepts a text command, and executes it on the app"""

        tokens = command.split(":")  # Split the command up into tokens

        # Check if too few commands are given
        if len(tokens) < 1:
            self.add_log(
                "HC-Command Processor",
                "N/A",
                "WARNING",
                f"Invalid HC-Command received. No tokens. Command: '{command}'",
            )
            return False

        # Find out the 'mode' of the command
        if (
            tokens[0] == "SET"
        ):  # THis indicates that the command provides arguments for an instrument's update_settings() function

            # Make sure the correct number of arguments are given
            if len(tokens) != 4:  # Requires: MODE:INSTRUMENT:PARAMETER:VALUE
                self.add_log(
                    "HC-Command Processor",
                    "N/A",
                    "WARNING",
                    f"Invalid HC-Command received. Wrong number of tokens. Command: '{command}'",
                )
                return False

            instr_str = tokens[1]
            setting_str = tokens[2]
            value_str = tokens[3]

            # If instrument exists...
            if instr_str in [x.name for x in self.instruments]:

                # Find instrument....
                for inst in self.instruments:
                    if instr_str == inst.name:
                        inst.update_setting(setting_str, value_str)
            else:
                self.add_log(
                    "HC-Command Processor",
                    "N/A",
                    "WARNING",
                    f"Instrument '{instr_str}' not found.",
                )
                return False

            self.pDebug(
                f"Executed Setting Update:\n\tInstrument: {instr_str}\n\tSetting: {setting_str}\n\tValue: {value_str}"
            )

        elif (
            tokens[0] == "CMD"
        ):  # This indicates the command provides arguments for an instrument's command() function

            # Recalculate tokens, with max of 2 splits. This allows colons to appear in the command
            tokens = command.split(":", 2)

            # Make sure the correct number of arguments are given
            if len(tokens) != 3:  # Requires: MODE:INSTRUMENT:PARAMETER:VALUE
                self.add_log(
                    "HC-Command Processor",
                    "N/A",
                    "WARNING",
                    f"Invalid HC-Command received. Wrong number of tokens. Command'{command}'",
                )
                return False

            instr_str = tokens[1]
            command_str = tokens[2]

            # Find instrument....
            instr_idx = -1
            for idx, inst in enumerate(self.instruments):
                if instr_str == inst.name:
                    instr_idx = idx

            if instr_idx != -1:
                self.instruments[instr_idx].command(command_str)
            else:
                self.add_log(
                    "HC-Command Processor",
                    "N/A",
                    "WARNING",
                    f"Invalid HC-Command received. Wrong number of tokens. Command: '{command}'",
                )
                return False

            self.pDebug(
                f"Executed Command:\n\tInstrument: {instr_str}\n\tCommand: {command_str}"
            )

        elif tokens[0] == "RCD":

            # Lock macros - backend_retun will unlock when it sees a key with an asterisk
            self.macro_locked = True

            # Recalculate tokens, with max of 2 splits
            tokens = command.split(":", 2)

            # Make sure the correct number of arguments are given
            if len(tokens) != 3:  # Requires: MODE:INSTRUMENT:QUERY_SETTING
                self.add_log(
                    "HC-Command Processor",
                    "N/A",
                    "WARNING",
                    f"Invalid HC-Command received. Wrong number of tokens. Command'{command}'",
                )
                return False

            instr_str = tokens[1]
            command_str = tokens[2] + "*"

            # Find instrument....
            instr_idx = -1
            for idx, inst in enumerate(self.instruments):
                if instr_str == inst.name:
                    instr_idx = idx

            if instr_idx != -1:
                self.instruments[instr_idx].command(command_str)
            else:
                self.add_log(
                    "HC-Command Processor",
                    "N/A",
                    "WARNING",
                    f"Invalid HC-Command received. Wrong number of tokens. Command: '{command}'",
                )
                return False

            self.pDebug(
                f"Executed Command:\n\tInstrument: {instr_str}\n\tCommand: {command_str}"
            )

        elif tokens[0] == "EXEC":

            # Recalculate tokens, with max of 2 splits. This allows colons to appear in the command
            tokens = command.split(":", 1)

            if self.exec_enabled:
                try:
                    exec(tokens[1])
                except Exception as e:
                    ec = tokens[1]
                    print(f"ERROR: Failed to execute command '{ec}'.\n\t{e}")
            else:
                print("Executing python code has been disabled")

        elif (
            tokens[0] == "FUNC"
        ):  # This indicates that the command is calling an internal function

            # Ensure more tokens exist
            if len(tokens) < 2:
                self.add_log(
                    "HC-Command Processor",
                    "N/A",
                    "WARNING",
                    f"Invalid HC-Command received. FUNC requires arguments.",
                )
                return False

            if tokens[1] == "debug":  # Turn debug mode on or off

                # Ensure more tokens exist
                if len(tokens) < 3:
                    self.add_log(
                        "HC-Command Processor",
                        "N/A",
                        "WARNING",
                        f"Invalid HC-Command received. FUNC:debug requires arguments.",
                    )
                    return False

                # Change value
                if tokens[2].upper() == "ON" or tokens[2].upper() == "TRUE":
                    self.debug = True
                else:
                    self.debug = False

            elif tokens[1] == "run":  # Run a macro

                # Ensure more tokens exist
                if len(tokens) < 3:
                    self.add_log(
                        "HC-Command Processor",
                        "N/A",
                        "WARNING",
                        f"Invalid HC-Command received. FUNC:run requires arguments.",
                    )
                    return False

                # Make sure macro exists
                if tokens[2] in self.macros:

                    # Run macro - note: this can become recursive and get stuck in
                    # an infinite loop if the user runs a macro that calls itself
                    return self.run_macro(self.macros[tokens[2]])

                else:
                    self.add_log(
                        "HC-Command Processor",
                        "N/A",
                        "WARNING",
                        f"Requested macro to run does not exist.",
                    )
                    return False

            elif tokens[1] == "var":  # Change or create variable

                # Ensure more tokens exist
                if len(tokens) < 4:
                    self.add_log(
                        "HC-Command Processor",
                        "N/A",
                        "WARNING",
                        f"Invalid HC-Command received. FUNC:var requires arguments.",
                    )
                    return False

                # Update/create variable
                self.variables[tokens[2]] = tokens[3]

            elif tokens[1] == "disp":  # Display data

                # Ensure more tokens exist
                if len(tokens) < 3:
                    self.add_log(
                        "HC-Command Processor",
                        "N/A",
                        "WARNING",
                        f"Invalid HC-Command received. FUNC:disp requires arguments.",
                    )
                    return False

                if tokens[2] == "var":  # Show all variables

                    print("Application Variables:")
                    for v in self.variables:
                        val = self.variables[v]
                        print(f"\t{v} = {val}")

                elif tokens[2] == "macro":  # Show all macros

                    print("Application Macros:")
                    for m in self.macros:
                        cmds = self.macros[m]
                        print(f"\t{m}: {cmds}")

                elif tokens[2] == "str":  # Show a string...

                    # Recalculate tokens w/ all after string counting as 1 token
                    tokens = command.split(":", 3)

                    if len(tokens) < 4:  # Blank line
                        print("")
                    else:  # Display remaining text
                        print(tokens[3])

                else:
                    self.add_log(
                        "HC-Command Processor",
                        "N/A",
                        "WARNING",
                        f"Invalid HC-Command received.",
                    )
                    return False

            elif tokens[1] == "time":

                if len(tokens) < 4:
                    self.add_log(
                        "HC-Command Processor",
                        "N/A",
                        "WARNING",
                        f"Invalid HC-Command received. FUNC:time requires arguments.",
                    )

                if tokens[2] == "sleep":

                    if self.macro_locked:
                        if time.time() >= self.macro_lock_end_time:
                            self.macro_locked = False
                    else:  # Lock for 'x' seconds
                        try:
                            self.macro_lock_end_time = time.time() + float(tokens[3])
                            self.macro_locked = True
                        except Exception:
                            self.pDebug(
                                f"Failed to convert hc-command argument to float"
                            )
        elif tokens[0] == "DEV":

            # Ensure more tokens exist
            if len(tokens) < 2:
                self.add_log(
                    "HC-Command Processor",
                    "N/A",
                    "WARNING",
                    f"Invalid HC-Command received. DEV requires arguments.",
                )
                return False

            if tokens[1] == "maclock":  # Turn macro lock on or off

                # Ensure more tokens exist
                if len(tokens) < 3:
                    self.add_log(
                        "HC-Command Processor",
                        "N/A",
                        "WARNING",
                        f"Invalid HC-Command received. DEV:maclock requires arguments.",
                    )
                    return False

                # Change value
                if tokens[2].upper() == "ON" or tokens[2].upper() == "TRUE":
                    self.macro_locked = True
                else:
                    self.macro_locked = False
        else:
            self.add_log(
                "HC-Command Processor",
                "N/A",
                "WARNING",
                f"Invalid HC-Command received. Unrecognized mode token. Command: '{command}'",
            )
            return "WARNING: Couldn't process command"

        return True

    def run_macro(self, m_commands):

        # Start timer, check every 300 ms
        self.macro_timer.start(300)

        # Load macro and pointer into object memory
        self.curr_macro = m_commands
        self.curr_cmd_idx = 0

    def resume_macro(self):

        # If out of bounds, end timer, kill macro
        if self.curr_cmd_idx > len(self.curr_macro):
            self.macro_timer = False

        self.process_hc_command(self.curr_macro[self.curr_cmd_idx])

        # If macro isn't locked, advance to next command
        if not self.macro_locked:
            self.curr_cmd_idx += 1

    def pDebug(self, msg, important=False, blue=False):
        if self.debug:
            if important:
                print(Fore.RED, end="")
                print(msg)
                print(Style.RESET_ALL, end="")
            else:
                if blue:
                    print(Fore.BLUE, end="")
                print(msg)
                if blue:
                    print(Style.RESET_ALL, end="")


class HC_MainWindow(QMainWindow):
    def __init__(self, app):

        super().__init__()

        self.app = app

        self.add_menu()

    def add_menu(self):

        self.bar = self.menuBar()  # self.menuBar() is a function in QMainWindow

        ###### File menu
        #
        self.file_menu = self.bar.addMenu("File")
        self.file_menu.triggered[QAction].connect(self.process_file_menu)
        #
        self.save_state_act = QAction("Save Instrument States", self)
        self.save_state_act.setShortcut("Ctrl+Shift+S")
        self.file_menu.addAction(self.save_state_act)
        #
        self.save_data_act = QAction("Save Data", self)
        self.save_data_act.setShortcut("Ctrl+S")
        self.file_menu.addAction(self.save_data_act)
        #
        self.file_menu.addSeparator()
        #
        self.close_act = QAction("Close Window", self)
        self.close_act.setShortcut("Ctrl+W")
        self.file_menu.addAction(self.close_act)

        ####### Instrument Menu
        #
        self.instr_menu = self.bar.addMenu("Instrument")
        self.instr_menu.triggered[QAction].connect(self.process_instr_menu)
        #
        self.sync_from_ui_act = QAction("Sync from UI", self)
        self.instr_menu.addAction(self.sync_from_ui_act)
        #
        self.sync_from_instr_act = QAction("Sync from Instrument", self)
        self.instr_menu.addAction(self.sync_from_instr_act)
        #
        self.sync_from_file_act = QAction("Sync from File", self)
        self.instr_menu.addAction(self.sync_from_file_act)
        #
        self.instr_menu.addSeparator()
        #
        self.print_addresses_act = QAction("Print Addresses", self)
        self.instr_menu.addAction(self.print_addresses_act)

        ####### Scripting Menu
        #
        self.scripting_menu = self.bar.addMenu("Scripting")
        self.scripting_menu.triggered[QAction].connect(self.process_scripting_menu)
        #
        self.run_command_act = QAction("Run Command", self)
        self.run_command_act.setShortcut("Ctrl+R")
        self.scripting_menu.addAction(self.run_command_act)
        #
        self.run_script_act = QAction("Run Macro")
        self.scripting_menu.addAction(self.run_script_act)
        #
        self.scripting_menu.addSeparator()
        #
        self.add_macro_act = QAction("Add Macro")
        self.scripting_menu.addAction(self.add_macro_act)
        #
        self.add_variable_act = QAction("Add Variable")
        self.scripting_menu.addAction(self.add_variable_act)
        #
        self.scripting_menu.addSeparator()
        #
        self.show_variables_act = QAction("Show Variables")
        self.scripting_menu.addAction(self.show_variables_act)

    def process_file_menu(self, q):

        if q.text() == "Save Instrument States":  # TODO: impliment
            print("This is where I save a state")
        elif q.text() == "Save Data":  # TODO: Impliment actual save + options

            print(json.dumps(self.app.saved_data))

        elif q.text() == "Close Window":
            self.close()
            sys.exit(0)
        else:
            print("Error: function not supported")

    def process_instr_menu(self, q):

        if q.text() == "Sync from Instrument":  # TODO: impliment
            print("Not implimented")
            # Todo: impliment sync from instr
        elif q.text() == "Sync from UI":  # TODO: impliment
            print("Not implimented")
            # Todo: impliment sync from ui
        elif q.text() == "Sync from File":  # TODO: impliment
            print("Not implimented")
            # Todo: impliment sync from file
        else:
            print("Error: function not supported")

    def process_scripting_menu(self, q):
        if q.text() == "Run Command":  # TODO: impliment

            dlg = QInputDialog(self)
            dlg.setInputMode(QInputDialog.TextInput)
            dlg.setLabelText("Command:")
            dlg.resize(500, 100)
            okPressed = dlg.exec_()
            text = dlg.textValue()

            # text, okPressed = QInputDialog.getText(self, "Where am I??", "Command", QLineEdit.Normal)
            if okPressed and text != "":
                self.app.process_hc_command(text)

        elif q.text() == "Run Macro":  # TODO: impliment
            print("Not implimented")
        elif q.text() == "Add Variable":  # TODO: impliment
            print("Not implimented")
        elif q.text() == "Add Macro":  # TODO: impliment
            print("Not implimented")
        elif q.text() == "Show Variables":  # TODO: impliment
            print("Not implimented")
        elif q.text() == "Show Macros":  # TODO: impliment
            print("Not implimented")
        else:
            print("Error: function not supported")


# ToDo: A lot of unused Classes - Implement or delete
# class QOnOff(QPushButton):
#     """An On/Off button with a nice icon for on/off
#
#     Takes two functions that will be called when turning on/off
#     starts in an unkown state if not defined otherwise
#
#     if f_off is None: assume that f_on is a signal that can emit a boolian.
#     """
#
#     def __init__(self, f_on, f_off=None):
#         super().__init__()
#         self.setCheckable(True)
#
#         self.onText = "On"
#         self.offText = "Off"
#         self.unkownText = "status unkown"
#
#         self.onIcon = QIcon(
#             pkg_resources.resource_filename(
#                 "hardware_control", "icons/button-power-on.svg"
#             )
#         )
#         self.offIcon = QIcon(
#             pkg_resources.resource_filename(
#                 "hardware_control", "icons/button-power-off.svg"
#             )
#         )
#         self.unkownIcon = QIcon(
#             pkg_resources.resource_filename(
#                 "hardware_control", "icons/button-power-unkown.svg"
#             )
#         )
#
#         self.f_on = f_on
#         self.f_off = f_off
#         self.clicked.connect(self.click)
#
#         self.setText(self.unkownText)
#         self.setIcon(self.unkownIcon)
#         self.setIconSize(QtCore.QSize(30, 30))
#
#         self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
#
#     def click(self):
#         # we need a 'not' here since the button internally already
#         # changed state at this point
#         if not self.isChecked():
#             if self.f_off:
#                 self.f_off()
#             else:
#                 self.f_on.emit(False)
#             self.set_icon_off()
#         else:
#             if self.f_off:
#                 self.f_on()
#             else:
#                 self.f_on.emit(True)
#             self.set_icon_on()
#
#     def on(self):
#         if self.f_off:
#             self.f_on()
#         else:
#             self.f_on.emit(True)
#         self.set_icon_on()
#
#     def set_icon_on(self):
#         """Just set the icon to on. Useful during startup"""
#         self.setChecked(True)
#         self.setIcon(self.onIcon)
#         self.setText(self.onText)
#
#     def off(self):
#         if self.f_off:
#             self.f_off()
#         else:
#             self.f_on.emit(False)
#         self.set_icon_off()
#
#     def set_icon_off(self):
#         """Just set the icon to off. Useful during startup"""
#         self.setChecked(False)
#         self.setIcon(self.offIcon)
#         self.setText(self.offText)
#
#     def isOn(self):
#         return self.isChecked()


# class HC_Control(ABC):
#     """Create an abstract base class for instruments
#
#     This defines the interface that should be present for new instruments.
#
#     Functions that _have_to_ be implemented are decorated and functions
#     that _can_ be implemented raise a NotImplementedError.
#
#
#     Note: the real implementation can have different amount of arguments,
#     e.g. write could be write(channel, value).
#
#     """
#
#     @abstractmethod
#     def read(self):
#         """Read values from instrument.
#
#         If the instrument has multiple values to set, this should
#         function should take a channel arguments or something similar.
#         """
#
#         pass
#
#     @abstractmethod
#     def write(self, value):
#         """Write values to instrument.
#
#         This function should take a value or channel/value argument.
#         """
#
#         pass
#
#     @abstractmethod
#     def try_connect(self):
#         """Try to connect to instrument.
#
#         This function should check if we are already connected and in
#         that case do nothing. We should be able to call this function
#         as often as we want without much overhead.
#         """
#
#         pass
#
#     @abstractmethod
#     def close(self):
#         """Closes any connection that got opened by try_connect"""
#
#         pass
#
#     def is_on(self):
#         """Return True/False, if the instrument is on
#
#         This is an optional functions. It is listed here just to give
#         the recommended name for this function.
#         """
#
#         raise NotImplementedError


# class QOnOffIndicator(QSvgWidget):
#     """An On/Off indicator
#
#     Listens to signals for on/off and shows a green or red light with a tooltip for mouse-over events.
#
#     starts in an unkown state (both lights off)"""
#
#     def __init__(self, name):
#         self.name = name
#         self.onIcon = pkg_resources.resource_filename(
#             "hardware_control", "icons/on-off-indicator-on.svg"
#         )
#         self.offIcon = pkg_resources.resource_filename(
#             "hardware_control", "icons/on-off-indicator-off.svg"
#         )
#         self.unkownIcon = pkg_resources.resource_filename(
#             "hardware_control", "icons/on-off-indicator-unkown.svg"
#         )
#
#         super().__init__(self.unkownIcon)
#
#         self.setMouseTracking(True)
#         self.setToolTip(name)
#
#         self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
#
#     def sizeHint(self):
#         return QSize(10, 20)
#
#     def on(self):
#         self.renderer().load(self.onIcon)
#
#     def off(self):
#         self.renderer().load(self.offIcon)
#
#     def set(self, status):
#         if status:
#             self.on()
#         else:
#             self.off()
#
#
# class QFixedLabel(QLabel):
#     """A QLabel that fixes its width to the initial string"""
#
#     def __init__(self, label, color=None):
#         super().__init__(label)
#
#         font = QFont()
#         font.setPointSize(18)
#         font.setBold(False)
#         self.setFont(font)
#
#         fm = QFontMetrics(self.font())
#         self.setFixedWidth(fm.width(self.text()))
#
#         self.setAlignment(QtCore.Qt.AlignCenter)
#         self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
#         if color is not None:
#             self.setStyleSheet(
#                 f"color: white;background-color:{color}; padding: 5px;border: 1px solid black;"
#             )
#
#
# class FigureTab(QWidget):
#     """A single matplotlib figure"""
#
#     def __init__(self, parent=None, active=True):
#         super().__init__()
#
#         self.normalize = False
#         self.autoscale = True
#
#         self.fig, self.axes = plt.subplots()
#         self.plot = FigureCanvas(self.fig)
#         self.plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
#         self.nav = NavigationToolbar(self.plot, self)
#         self.nav.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
#
#         # custom toolbar
#         self.controls = QHBoxLayout()
#         self.normalizebutton = QPushButton("normalize")
#         self.normalizebutton.clicked.connect(self.toggle_normalize)
#         self.normalizebutton.setCheckable(True)
#         self.autoscalebutton = QPushButton("autoscale")
#         self.autoscalebutton.clicked.connect(self.toggle_autoscale)
#         self.autoscalebutton.setCheckable(True)
#         self.autoscalebutton.setChecked(True)
#         self.controls.addWidget(self.normalizebutton)
#         self.controls.addWidget(self.autoscalebutton)
#         self.controls.addStretch(1)
#
#         self.vbox = QVBoxLayout()
#         self.vbox.addLayout(self.controls)
#         self.vbox.addWidget(self.nav)
#         self.vbox.addWidget(self.plot)
#         self.vbox.addSpacing(50)
#
#         self.setLayout(self.vbox)
#
#         self.elements_and_name = []
#         self.data = defaultdict(deque)
#
#         self.interval = 1000
#         self.active = active
#
#         self.timer = QtCore.QTimer(self)
#         self.timer.timeout.connect(self.add_data)
#
#         # always get data
#         if self.active:
#             self.timer.start(self.interval)
#
#     def add_element(self, element, name):
#         self.elements_and_name.append((element, name))
#
#     def add_data(self):
#         t = time.time()
#         for e, n in self.elements_and_name:
#             self.data[n].append([t, getattr(e, n)])
#
#         # only save the last 10000 data points
#         for k, v in self.data.items():
#             while len(v) > 10000:
#                 v.popleft()
#
#     def toggle_autoscale(self):
#         self.autoscale = not self.autoscale
#
#     def toggle_normalize(self):
#         self.normalize = not self.normalize
#
#     def update(self):
#         xleft, xright = self.axes.get_xlim()
#         ybottom, ytop = self.axes.get_ylim()
#         self.axes.clear()
#         self.axes.set_xlabel("Time")
#         for k, v in self.data.items():
#             myX = np.array([x[0] for x in v])
#             myY = np.array([x[1] for x in v])
#             if self.normalize and len(myY) and myY.max() > 0:
#                 myY = myY / myY.max()
#             self.axes.plot_date(
#                 epoch2num(myX), myY, "o-", label=k, tz="America/Los_Angeles"
#             )
#         self.axes.legend(loc="best")
#         if not self.autoscale:
#             self.axes.set_xlim([xleft, xright])
#             self.axes.set_ylim([ybottom, ytop])
#         self.plot.draw()
#
#
# class RunFunctionsThread(QThread):
#     """Call a bunch of function to read data every <timeout> milliseconds"""
#
#     def __init__(self, functions):
#         super().__init__()
#         self.functions = functions
#         self.keep_running = True
#         self.pause = False
#         self.timeout = 1000  # ms
#
#     def __del__(self):
#         self.wait()
#
#     def addfunction(self, f):
#         self.functions.append(f)
#
#     def removefunction(self, f):
#         self.functions.remove(f)
#
#     def mystop(self):
#         self.keep_running = False
#
#     def start_pause(self):
#         self.pause = True
#
#     def stop_pause(self):
#         self.pause = False
#
#     def run(self):
#         while self.keep_running:
#             if not self.pause:
#                 for f in self.functions:
#                     f()
#             self.msleep(self.timeout)
#
#
class LoggerThread(QThread):
    """Write out the data to a log file"""

    def __init__(self, datadir: pathlib.PosixPath = None, dummy: bool = False):
        """Set up the logfile. Either create it or open for append"""

        super().__init__()
        self.elements = []
        self.keep_running = True
        self.pause = False

        if not datadir or not datadir.is_dir():
            self.keep_running = False
            QMessageBox.about(None, "Error", f"Cannot find logfile directory {datadir}")

        self.YYYYMMDD = datetime.datetime.today().strftime("%Y-%m-%d")
        logdir = datadir / self.YYYYMMDD
        logdir.mkdir(exist_ok=True, parents=True)
        self.logdir = logdir
        if dummy:
            self.logfilename = logdir / (self.YYYYMMDD + "-dummy.txt")
        else:
            self.logfilename = logdir / (self.YYYYMMDD + ".txt")

        # check if we need to write header
        if self.logfilename.exists() and self.logfilename.is_file():
            with self.logfilename.open("r") as f:
                self.oldlength = len(f.readlines())
        else:
            self.oldlength = 0

    def __del__(self):
        self.wait()

    def addelement(self, e):
        self.elements.append(e)

    def removeelement(self, e):
        self.elements.remove(e)

    def mystop(self):
        self.keep_running = False

    def start_pause(self):
        self.pause = True

    def stop_pause(self):
        self.pause = False

    def write_header(self):
        self.logfile.write(f"# {self.YYYYMMDD}\n# Logfile from hardware_control run\n")
        datastructure = "Time[s] " + " ".join([e.get_header() for e in self.elements])
        myhash = hashlib.sha256()
        myhash.update(datastructure.encode("utf-8"))
        version = myhash.hexdigest()
        self.logfile.write(f"# Version: {version}\n")
        self.logfile.write(
            f"{datastructure}\n"
        )  # no '#' so that it is easier for pandas to read

    def run(self):
        # wait a few seconds before starting the log, so that the
        # elements can start collecting data
        time.sleep(5)

        # now open file
        self.logfile = self.logfilename.open("a", buffering=1)

        # add header if file is empty
        if self.oldlength == 0:
            self.write_header()

        while self.keep_running:
            if not self.pause:
                line = f"{time.time()} "
                data = []
                for e in self.elements:
                    data.extend(e.get_values())
                line += " ".join([str(d) for d in data])
                self.logfile.write(line + "\n")
            self.sleep(1)

        self.logfile.close()


def setButtonState(button: QPushButton, value):
    """Sets the state of a QPushButton to checked
    or unchecked, accoridng to 'value'. Only applicable
    to QPushButtons with field 'checkable' set to true."""
    if type(value) == bool:
        if value:
            if not button.isChecked():
                button.toggle()
        else:
            if button.isChecked():
                button.toggle()
    elif type(value) == str:
        if value == "True" or value == "TRUE":
            if not button.isChecked():
                button.toggle()
        else:
            if button.isChecked():
                button.toggle()


def returnChannelNumber(s: str):
    """Return channel number for a string like 'CH###_TEMP' """
    if s[:2] == "CH":
        number = s[2 : s.find("_")]
        if number.isdigit():
            return number
    else:
        return None
