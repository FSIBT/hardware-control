import json
import logging

from PyQt5.QtWidgets import QApplication

from .HC_MeasurementDirector import MeasurementDirector
from .Dataset import Dataset

logger = logging.getLogger(__name__)

ipy_logger = logging.getLogger("ipykernel")
ipy_logger.setLevel("ERROR")


class HC_App(QApplication):
    """Subclass of QApplication that is aware of what hardware is connected to it and can log data"""

    def __init__(self, dummy=False):
        # QApplication can take a list of strings, e.g. from sys.argv
        # we currently don't use this
        super().__init__([])
        self.instruments = []
        self.macros = {}  # Dict of hc-commands (used for scans + trigger buttons)
        self.variables = {}  # Dict of app variables
        self.function_handles = {}  # Dict of function handles for macros to call
        # self.saved_data = {}
        # Dict of data saved directly with query commmands
        self.dummy = dummy
        self.print_close_info = False
        self.comms = {}  # Dictionary of HC_Comm objects

        self.data_sets = {}  # Dict of datasets
        untitled_set = Dataset("Untitled")
        self.data_sets["Untitled"] = untitled_set

        self.director = MeasurementDirector(self)

        # Dictates if hc_commands are allowed to execute raw python code via calls to the
        # via teh 'exec' function
        self.exec_enabled = True

        self.macro_lock_end_time = None
        self.curr_macro = []
        self.curr_cmd_idx = 0

        # Start a timer to resume timer after any pauses
        # self.macro_timer = QTimer(self)
        # self.macro_timer.timeout.connect(self.resume_macro)
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
                logger.info(
                    f"settings for {self.comm.instr.ID} saved to file '{filename}'"
                )
        except Exception as e:
            logger.error(
                f"Failed to write file '{filename}'. State not saved.", exc_info=True
            )

    def list_instruments(self):

        if not self.instruments:
            print("No known instruments")
            return

        print("Known instruments:")
        for i in self.instruments:
            print(f"  {i}")

    def check_instruments(self):
        """Make sure all instruments conform to specifications"""
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
        """Closes all instruments"""
        for instr in self.instruments:
            try:  # User may not have initialized comm correctly as HC_Comm - error check here
                instr.comm.close()  # Send close signal to backend - stop connect timer
            except Exception as e:
                logger.error(
                    f"Failed to close instrument '{instr.name}'.", exc_info=True
                )

    def close(self):

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

    def add_variable(self, name: str, value: str):
        """Adds an application variable. Overwrites if variable already exists"""
        self.variables[name] = value

    def process_hc_command(self, command: str):
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
        if uptokens[0] == "SET":

            # Make sure the correct number of arguments are given
            if len(tokens) < 4:  # Requires: MODE:INSTRUMENT:PARAMETER:VALUE
                logger.warning(
                    f"Invalid HC-Command received. Wrong number of tokens. Command: '{command}'"
                )
                return "ERROR: Invalid command"

            tokens = command.split(":", 3)
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
                logger.warning(f"Instrument '{instr_str}' not found.")
                return "ERROR: Instrument not found"

            logger.debug(
                f"Executed Setting Update:\n\tInstrument: {instr_str}\n\tSetting: {setting_str}\n\tValue: {value_str}"
            )

        elif uptokens[0] == "CMD":

            # Recalculate tokens, with max of 2 splits. This allows colons to appear in the command
            tokens = command.split(":", 2)

            # Make sure the correct number of arguments are given
            if len(tokens) != 3:  # Requires: MODE:INSTRUMENT:PARAMETER:VALUE
                logger.warning(
                    f"Invalid HC-Command received. Wrong number of tokens. Command'{command}'"
                )
                return "ERROR: Invalid command"

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
                logger.warning(
                    f"Invalid HC-Command received. Wrong number of tokens. Command: '{command}'"
                )
                return "ERROR: Invalid command"

            logger.debug(
                f"Executed Command:\n\tInstrument: {instr_str}\n\tCommand: {command_str}"
            )

        elif uptokens[0] == "MEAS":
            if uptokens[1] == "REQ":

                # print("\n\tIN CMDLG\n")

                # Recalculate tokens, with max of 2 splits. This allows colons to appear in the command
                tokens = command.split(":", 9)

                # Format: CMDLG:group:instrument:parameter:cmd_str:steady_num:dt:tol:iterations

                # Make sure the correct number of arguments are given
                if len(tokens) != 10:  # Requires: MODE:INSTRUMENT:PARAMETER:VALUE
                    logger.warning(
                        f"Invalid HC-Command received. Wrong number of tokens. Command'{command}'"
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
                except Exception as e:
                    logger.warning(
                        f"Invalid HC-Command received. Failed to create MeasurementRequest from given arguments.",
                    )
                    return "False"

                # Find instrument....
                instr_idx = -1
                instr_str = tokens[2]
                command_str = tokens[5]
                for idx, inst in enumerate(self.instruments):
                    if instr_str == inst.name:
                        instr_idx = idx

                if not self.director.measure(meas_req):
                    logger.warning(f"Failed to add MeasurementRequest to director'")
                    return "False"

                logger.debug(
                    f"Executed Command:\n\tInstrument: {instr_str}\n\tCommand: {command_str}"
                )

            elif uptokens[1] == "START":

                self.director.start()

                return "Started"

            elif uptokens[1] == "PSTATE":

                print(self.director.get_state())
                if self.director.state == "Error":
                    print(f"\tError message: {self.director.err_str}")
                print(self.director.get_state())

            elif uptokens[1] == "GETSTATE":

                return self.director.get_state()

        elif uptokens[0] == "EXEC":

            # Recalculate tokens, with max of 2 splits. This allows colons to appear in the command
            tokens = command.split(":", 1)

            if self.exec_enabled:
                try:
                    exec(tokens[1])
                except Exception as e:
                    ec = tokens[1]
                    logger.error(
                        f"Failed to execute command '{ec}'.\n\t{e}", exc_info=True
                    )
            else:
                logger.warning(
                    "Failed to execute code. Executing python code from HC-Commands has been disabled."
                )

        elif uptokens[0] == "FUNC":
            # 'FUNC' indicates that the command is calling an internal function

            # Ensure more tokens exist
            if len(tokens) < 2:
                logger.warning(
                    f"Invalid HC-Command received. FUNC requires arguments.",
                )
                return "False"

            if uptokens[1] == "LEVEL":  # Turn debug mode on or off

                # Ensure more tokens exist
                if len(tokens) < 3:
                    logger.warning(
                        f"Invalid HC-Command received. FUNC:LEVEL requires arguments.",
                    )
                    return "False"

                loggers = [logging.getLogger()]  # get the root logger
                for name in logging.root.manager.loggerDict:
                    if "hardware_control" in name:
                        loggers.append(logging.getLogger(name))

                # Change value
                if uptokens[2] == "DEBUG":
                    for lgr in loggers:
                        lgr.setLevel(logging.DEBUG)
                elif uptokens[2] == "INFO":
                    for lgr in loggers:
                        lgr.setLevel(logging.INFO)
                elif uptokens[2] == "WARNING":
                    for lgr in loggers:
                        lgr.setLevel(logging.WARNING)
                elif uptokens[2] == "ERROR":
                    for lgr in loggers:
                        lgr.setLevel(logging.ERROR)
                elif uptokens[2] == "CRITICAL":
                    for lgr in loggers:
                        lgr.setLevel(logging.CRITICAL)
                else:
                    logger.warning(
                        f"Invalid HC-Command received. Invalid logging level provided."
                    )

            elif uptokens[1] == "UPDATE":

                # Ensure more tokens exist
                if len(tokens) < 3:
                    logger.warning(
                        f"Invalid HC-Command received. FUNC:UPDATE requires arguments.",
                    )
                    return "False"

                # Change value
                if uptokens[2] == "MACRO_IND":
                    for inst in self.instruments:
                        if (
                            inst.name == "Macro Runner"
                        ):  # TODO: Fix how it ID's the runner tool
                            inst.update_indicators()
                else:
                    logger.warning(
                        f"Invalid HC-Command received. Invalid update option provided."
                    )

            elif uptokens[1] == "SYNC":

                for instr in self.instruments:
                    instr.settings_to_UI()

            elif uptokens[1] == "HANDLE":

                # Ensure more tokens exist
                if len(tokens) < 3:
                    logger.warning(
                        f"Invalid HC-Command received. FUNC:handle requires arguments.",
                    )
                    return "False"

                # Make sure handle exists
                if tokens[2] in self.function_handles:

                    if not callable(self.function_handles[tokens[2]]):
                        func_name = tokens[2]
                        logger.warning(
                            f"Non-callable object provided as function handle '{func_name}'"
                        )
                        return "False"

                    # Run function - note: this can become recursive and get stuck in
                    # an infinite loop if the user runs a function that calls itself
                    if len(tokens) > 3:
                        tokens = command.split(":", 3)
                        return self.function_handles[tokens[2]](token_handles[3])
                    else:
                        return self.function_handles[tokens[2]]()

                else:
                    logger.warning(f"Requested macro to run does not exist.",)
                    return "False"

            elif uptokens[1] == "SVSTATE":

                # Make sure the correct number of arguments are given
                if len(tokens) != 4:  # Requires: FUNC:SVSTATE:INSTRUMENT:filename
                    logger.warning(
                        f"Invalid HC-Command received. Wrong number of tokens. Command: '{command}'"
                    )
                    return "ERROR: Invalid command"

                instr_str = tokens[2]
                filename_str = tokens[3]

                # If instrument exists...
                if instr_str in [x.name for x in self.instruments]:

                    # Find instrument....
                    for inst in self.instruments:
                        if instr_str == inst.name:
                            inst.save_state(filename_str)
                else:
                    logger.warning(f"Instrument '{instr_str}' not found.")
                    return "ERROR: Instrument not found"

            elif uptokens[1] == "LDSTATE":

                # Make sure the correct number of arguments are given
                if len(tokens) != 4:  # Requires: FUNC:LDSTATE:INSTRUMENT:filename
                    logger.warning(
                        f"Invalid HC-Command received. Wrong number of tokens. Command: '{command}'"
                    )
                    return "ERROR: Invalid command"

                instr_str = tokens[2]
                filename_str = tokens[3]

                # If instrument exists...
                if instr_str in [x.name for x in self.instruments]:

                    # Find instrument....
                    for inst in self.instruments:
                        if instr_str == inst.name:
                            inst.load_state(filename_str)
                else:
                    logger.warning(f"Instrument '{instr_str}' not found.")
                    return "ERROR: Instrument not found"

            elif uptokens[1] == "RUN":

                # Ensure more tokens exist
                if len(tokens) < 3:
                    logger.warning(
                        f"Invalid HC-Command received. FUNC:run requires arguments.",
                    )
                    return "False"

                # Make sure macro exists
                if tokens[2] in self.macros:

                    # Run macro - note: this can become recursive and get stuck in
                    # an infinite loop if the user runs a macro that calls itself
                    return self.run_macro(self.macros[tokens[2]])

                else:
                    logger.warning(f"Requested macro to run does not exist.",)
                    return "False"

            elif uptokens[1] == "VAR":  # Change or create variable

                # Ensure more tokens exist
                if len(tokens) < 4:
                    logger.warning(
                        f"Invalid HC-Command received. FUNC:var requires arguments.",
                    )
                    return "False"

                # Update/create variable
                self.variables[tokens[2]] = tokens[3]

            elif uptokens[1] == "DISP":  # Display data

                # Ensure more tokens exist
                if len(tokens) < 3:
                    logger.warning(
                        f"Invalid HC-Command received. FUNC:disp requires arguments.",
                    )
                    return "False"

                if uptokens[2] == "VAR":  # Show all variables

                    print("Application Variables:")
                    for v in self.variables:
                        val = self.variables[v]
                        print(f"\t{v} = {val}")

                elif uptokens[2] == "MACRO":  # Show all macros

                    print("Application Macros:")
                    for m in self.macros:
                        cmds = self.macros[m]
                        print(f"\t{m}: {cmds}")

                elif uptokens[2] == "STR":  # Show a string...

                    # Recalculate tokens w/ all after string counting as 1 token
                    tokens = command.split(":", 3)

                    if len(tokens) < 4:  # Blank line
                        print("")
                    else:  # Display remaining text
                        print(tokens[3])

                else:
                    logger.warning(f"Invalid HC-Command received.")
                    return "False"

            elif uptokens[1] == "LSDATA":

                print("All Data:")
                for set_key in self.data_sets:
                    print(f"\tSet '{set_key}':")
                    for param_key in self.data_sets[set_key].data:
                        temp = self.data_sets[set_key].data[param_key]
                        print(f"\t\t{temp}")

        elif tokens[0] == "DEV":

            # Ensure more tokens exist
            if len(tokens) < 2:
                logger.warning(f"Invalid HC-Command received. DEV requires arguments.")
                return "False"

            # Set MeasurementDirector state to ready. Don't use this unless you know what you're doing. It can get measurement batches out of sync if used at the wrong time
            elif uptokens[1] == "MEAS-SET-READY":

                self.director.state = "Ready"

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
            self.process_hc_command(cmd)

    def load_state_from_file(self, filename: str):
        """ Reads a JSON file to overwrite instrument's settings dictionaries.
        Expectss JSON to be a dictionary of dictionaries. The first-level key in the
        instrument name, the value for that key is the instrument's settings
        dictionary. If a parameter in the file does not exist in the instrment's
        settings dictionary it is ignored. If the file does not specify a parameter
        held by th instrument's settings dictionary then that parameter is unchanged.
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

    def save_all_states(self, filename: str):

        all_states = {}

        # Combine all widgets into one state object
        for inst in self.instruments:
            all_states[inst.name] = inst.settings

        # Save to file
        try:
            with open(filename, "w") as file:
                json.dump(all_states, file)
                logger.info(f"Settings for all instruments saved to file '{filename}'")
        except Exception as e:
            logger.error(
                f"Failed to write file '{filename}'. settings not saved.",
                exc_info=True,
            )

    def settings_to_backends(self):

        for instr in self.instruments:
            instr.send_state()

    def backends_to_settings(self):

        for instr in self.instruments:
            instr.read_state_from_backend()
