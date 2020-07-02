import datetime
import hashlib
import pathlib
import sys
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from colorama import Fore, Style
import json
import logging
import numpy as np
import os
import pickle
from sys import platform

from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QObject, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QAction,
    QGroupBox,
    QInputDialog,
    QFileDialog,
)
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
from hardware_control.utility import convertibleToFloat

logger = logging.getLogger(__name__)

ipy_logger = logging.getLogger("ipykernel")
ipy_logger.setLevel("ERROR")

# ramp_mode options
MANUAL = "manual"
AUTOMATIC = "automatic"
OFF = "off"


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
    sigCommandLog = pyqtSignal(str, float, str)
    sigClose = pyqtSignal()

    # TODO: @TImo Bauer Add 'try_connect' frequency
    def __init__(
        self, backend, instrument, try_connect_period=5000, lock_until_sync=False
    ):
        super().__init__()
        self.backend = backend
        self.instruments = [instrument]  # Calling instrument UI (eg. HC_scope)
        self.backend_model = backend.ID
        self.try_connect_period = try_connect_period

        self.lock_until_sync = lock_until_sync

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
        self.sigCommandLog.connect(self.worker.command_log)
        self.sigClose.connect(self.worker.close)

        # Connect CommWorker's signals to Comm's slots
        self.worker.sigReturnValues.connect(self.backend_return)
        self.worker.sigReturnOnline.connect(self.backend_return_online)
        self.worker.sigReturnList.connect(self.backend_return_listdata)
        self.worker.sigReturnLog.connect(self.backend_return_log)

        # Connect timer
        self.try_connect_timer = QTimer(self)
        self.try_connect_timer.timeout.connect(self.try_connect)
        self.try_connect_timer.start(self.try_connect_period)

        self.dataset_states = []

    def __repr__(self):
        return f"HC_Comm {self.backend_model} @ {self.backend.connection_addr}  {hex(id(self))}"

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.backend.connection_addr}"

    def addWidget(self, new_instrument):
        """Adds a new instrument to HC_Comm. When HC_Comm gets a reply, it will
        go to all listed instruments"""

        self.instruments.append(new_instrument)

    def close(self):  # TODO: Change logger messages to references address, not instr
        logger.debug(
            f"\tInstrument: '{self.instruments[0].name}' closing Comm with backend of type '{self.backend_model}'."
        )
        self.try_connect_timer.stop()  # Stop
        self.sigClose.emit()
        self.worker_thread.quit()  # Kill thread
        if self.instruments[0].window.app.print_close_info:
            print(
                Fore.BLUE
                + f"\t'{self.instruments[0].name}': Closing...\t\t\t--:-- sec"
                + Style.RESET_ALL,
                end="",
                flush=True,
            )
            start_time = time.time()
        self.worker_thread.wait()  # Wait for thread to join (otherwise, if main thread exists first, stdout will be closed while the worker_thread may still be running and try to write to stdout, causing an error to arise)
        if self.instruments[0].window.app.print_close_info:
            print(
                f"\r\t'{self.instruments[0].name}': Closed    \t\t\t"
                + "{:.2f}".format(time.time() - start_time)
                + " sec    "
            )

    def update_setting(self, setting: str, value: str):
        """Transfers the setting and value information to the worker thread"""

        if self.lock_until_sync:
            logger.debug(
                f"Instrument {self.instruments[0].name} block update_setting because UI has not yet synced with instrument"
            )

        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'update_setting()' for setting '{setting}' and sent message '{value}'."
        )
        self.sigUpdateSettings.emit(setting, value, time.time() + self.expire_time)

    def command(self, cmd: str):
        """Sends a command to the worker in the worker thread"""
        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'command()' and sent command: '{cmd}'."
        )
        self.sigCommand.emit(cmd, time.time() + self.expire_time)

    def write(self, msg: str):
        """Sends a command to be sent to the instrument by the worker in the worker thead"""
        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'write()' and sent message: '{msg}'."
        )
        self.sigWrite.emit(msg, time.time() + self.expire_time)

    def query(self, msg: str):
        """Sends a query statement to be sent to the instrument by the worker in the worker thead"""
        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'query()' and sent message: '{msg}'."
        )
        self.sigQuery.emit(msg, time.time() + self.expire_time)

    def try_connect(self):
        """Tells the worker to tell the backend to try to connect to the instrument"""
        self.sigTryConnect.emit(time.time() + self.expire_time)

    def command_listdata(self, cmd: str):
        """Sends a command to the worker in the worker thread just like command(),
        but returns two lists instead of a string."""
        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'command_listdata()' and sent command: '{cmd}'."
        )
        self.sigCommandList.emit(cmd, time.time() + self.list_expire_time)

    # def command_log(self, cmd:str, state):
    #     """Functions the same way as command(), except it: 1.) immediately records
    #     the returned data 2.) allows for automatically repeated queries to ensure
    #     the measured value is in a steady-state and that the measurement is not
    #     fluctuating beyond the specified tolerance."""
    #
    #     state.repeat_command = cmd;
    #     state.iterations += 1
    #
    #     #Cancel command if
    #     if state.iterations > state.max_iterations:
    #         return
    #
    #     #Check if ID is blacklisted if dataset already exists
    #     if ((state.dataset_name in self.window.app.data_sets) and (self.window.app.data_sets[state.dataset_name].is_blacklisted(state.measurement_id))):
    #         return
    #
    #     add_to_list = True
    #     for s_idx, s in enumerate(self.dataset_states):
    #         if s.measurement_id == state.measurement_id: #Ensure there is not already a state with the assigned ID number
    #             self.dataset_states[s_idx] = state; #Update state
    #             add_to_list = False
    #
    #     #Add state information to HC_Comm's list of states
    #     if add_to_list:
    #         self.dataset_states.append(state)
    #
    #     self.sigCommandLog.emit(cmd, time.time() + self.expire_time, state.measurement_id)

    def command_log(self, cmd: str, param_str: str):
        """Sends a command to the worker in the worker thread"""

        # print(f"\n\t\tCOMMAND_LOG::HC_COMM\t{param_str}\n")

        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'command()' and sent command: '{cmd}'."
        )
        self.sigCommandLog.emit(cmd, time.time() + self.expire_time, param_str)

    @pyqtSlot(str)
    def backend_return(self, retval: str):
        """Receives a return value from the CommWorker and sends it to the instrument's
        backend_return function, which adds it to the instrument's values dictionary or
        , if overwritten, may process the return string immediately for example by
        updating the UI."""

        if retval == "SYNC_BACKEND":
            self.lock_until_sync = False

        logger.debug(
            f"Instrument: {self.instruments[0].name} received return from backend '{self.backend_model}'. Return message: {retval}"
        )
        for instr in self.instruments:
            instr.backend_return(retval)

    @pyqtSlot(bool)
    def backend_return_online(self, connected: bool):
        """ Gets called by the worker after the worker hears from the instrument if it successfully connected.
        Updates the state of the instrument - ie. if it is or is not online"""
        for instr in self.instruments:
            instr.backend_return_online(connected)

    @pyqtSlot(str, list, list)
    def backend_return_listdata(self, desc: str, data1: list, data2: list):
        """Receives a return value from the CommWorker and sends it to the instrument's
        backend_return_listdata function, which can be overwritten by the UI's author
        to process the data."""
        for instr in self.instruments:
            instr.backend_return_listdata(desc, data1, data2)

    @pyqtSlot(str, str)
    def backend_return_log(self, retval: str, param_str: str):
        """Receives a return value from the CommWorker and sends it to the instrument's
        backend_return function, which adds it to the instrument's values dictionary or
        , if overwritten, may process the return string immediately for example by
        updating the UI."""

        # print(f"\n\t\t\t\tBACKEND_RETURN_LOG::HC_COMM\t{param_str}\n")

        self.instrument.window.app.director.backend_return_log(retval, param_str)
        logger.debug(
            f"Instrument: {self.instrument.name} received return from backend '{self.backend_model}'. Return message: {retval}"
        )
        for instr in self.instruments:
            instr.backend_return(retval)

    # @pyqtSlot(str, int, str)
    # def backend_return_log(self, retval:str, param_str:str):
    #     """ """
    #
    #     #Find the state objeect with a matching ID
    #     set_idx = -1;
    #     for s_idx, s in enumerate(self.dataset_states):
    #         if s.measurement_id == id:
    #             set_idx = s_idx;
    #
    #     #Ensure a state variable was found
    #     if set_idx == -1:
    #         #An error has occured an a dataset_state with a matching ID can not be found
    #         error_message = f"backend_return_log() was called, but a state object with a matching ID ({id}) cannot be found"
    #         self.intrument.backend_return(error_message)
    #
    #     #Check if req number of steady points is satisfied
    #     if self.dataset_states[set_idx].steady_points > 0:
    #
    #         #Add the last measurement to the state object
    #         self.dataset_states.add_point(retval)
    #
    #
    #         if self.dataset_states[set_idx].conditions_met():
    #             self.instrument.backend_return(retval) #If all conditions have been met, send the return value to the UI
    #         else:
    #             #All confitions have not been met, request another measurement
    #             self.command(self.dataset_states[set_idx].repeat_command, self.dataset_states[set_idx]);
    #
    #     else:
    #         #If no steeady state condition is required, immediately return the response
    #         self.instrument.backend_return(retval)


class HC_CommWorker(QObject):
    """Uses signals + slots to receive data from HC_Comm and relays the information
    to the backend object. Then sends the return value back to HC_Comm via signals +
    slots, when HC_Comm then pushes onto the back of the isntrument's values dict"""

    sigReturnValues = pyqtSignal(str)
    sigReturnOnline = pyqtSignal(bool)
    sigReturnList = pyqtSignal(str, list, list)
    sigReturnLog = pyqtSignal(str, str)

    def __init__(self, backend):
        super().__init__()

        self.backend = backend

    def __repr__(self):
        return f"HC_CommWorker {self.backend.ID} @ {self.backend.connection_addr} {hex(id(self))}"

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.backend.connection_addr}"

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

        if cmd == "SYNC_BACKEND":
            self.sigReturnValues.emit(cmd)
            return

        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=CMD:"{cmd}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.command(cmd)

        # Set online to false if special 'offline' message comes across
        if ret_val == f"{self.backend.ID}-Offline":
            self.sigReturnOnline.emit(False)

        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(str, float)
    def write(self, msg: str, expire_time: float):
        """Transfers a command to be sent directly to the instrument to the backend"""
        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=WRT:"{msg}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.write(msg)

        # Set online to false if special 'offline' message comes across
        if ret_val == f"{self.backend.ID}-Offline":
            self.sigReturnOnline.emit(False)

        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(str, float)
    def query(self, msg: str, expire_time: float):
        """Transfers a query statement to be sent directly to the instrument to the backend"""
        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=QRY:"{msg}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.query(msg)

        # Set online to false if special 'offline' message comes across
        if ret_val == f"{self.backend.ID}-Offline":
            self.sigReturnOnline.emit(False)

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

    @pyqtSlot(str, float, str)
    def command_log(self, cmd: str, expire_time: float, param_str: str):
        """Transfers the command to the backend"""

        # print(f"\n\t\t\tCOMMAND_LOG::HC_COMMWORKER\t{param_str}\n")

        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=CMDLG:"{cmd}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.command(cmd)

        self.sigReturnLog.emit(ret_val, param_str)

    @pyqtSlot()
    def close(self):
        """Tells backend to close the connection. Then reports if instrument is
        offline."""
        online = self.backend.close()
        self.sigReturnOnline.emit(online)


class MeasurementRequest:
    """Describes state information for a single measurement. This state object is
    passed to HC_Comm's command_log() function to communicate options such as
    if to repeat measurement and check for stability, how many stable points to find,
    how to define 'stable', etc etc. HC_Comm keeps a list of these objects so it
    doesn't need to be passed back and forth between the backend. Instead, a unique
    interger called the measurement_id which is used to link a call to
    backend_return_log() to the corresponding MeasurementState object."""

    def __init__(
        self,
        dataset_name: str,
        instrument_name: str,
        parameter_name: str,
        cmd_str: str,
        steady_points: int = 3,
        equip_dt: float = 0.1,
        tol: float = 0.1,
        max_iterations: int = 10,
    ):

        # ******* These parameters tell the director how to query and save the data *******************************
        #
        self.dataset_name = (
            dataset_name  # This is the name of the dataset it is a member of
        )
        self.inst_name = (
            instrument_name  # This is the name of the instrument from which to measure
        )
        self.param_name = parameter_name  # This is the name of the parameter to measure
        self.measurement_index = (
            -1
        )  # This is the index in the dataset arrays in which the measurement will be stored
        self.inst_command = cmd_str  # Command to send to the instrument

        # ********* These parameters tell the director how to verify the measurement's stability ******************
        #
        self.steady_points = steady_points  # Number of points that must be measured and considered 'steady'
        self.steady_dt = (
            equip_dt  # change in time between points checked for steady state condition
        )
        self.tol = tol  # Tolerance  (in percent/100 ie from 0 to 1) by which points can differ and still be considered 'steady'
        self.iterations = 0  # Number of iterations, ie measurements, that have occcured
        self.max_iterations = max_iterations  # Maximum number of iterations before returns failure condition

        self.prev_data = (
            []
        )  # Previous data values measured (for comparison for steady state determination)
        self.keep_as_string = False  # Instructs MeasurementDirector to keep the returned data as a string instead of a double. Disables all stability checks
        self.launched = False  # Tells the MeasurementDirector if this request has already been handled or if it needs to be sent to a backend
        self.cap_at_1e35 = True  # Tells the MeasurementDirector to count the point as corrupt if convertable to float and > 1e35

        self.last_launch_time = time.time()

    def __repr__(self):
        return f"MeasurementRequest from {self.dataset_name} {self.inst_name} {self.param_name} @ {hex(id(self))}"

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.dataset_name} {self.inst_name} {self.param_name}"

    def add_point(self, retval: str):
        """Checks if the last return value (passed as 'retva') qualifies as a steady
        state condition and adds the point to self.prev_data for later analysis.

        If the point can not be added (no separator found or can't convert to float),
        the function returns prematurely."""

        # Find separator and calculate val
        val = ""
        sep_idx = retval.find("=")
        if sep_idx != -1:  # Separator was found...
            key = retval[0:sep_idx]
            val = retval[sep_idx + 1 :]
        else:
            return False  # Separator was not found, return early

        # Try to convert returned value to a float, add to list
        try:
            self.prev_data.append(float(val))
        except:
            return False

        return True

    def conditions_met(self):
        """Determines if the completion criteria have been met, or if more points are
        required."""

        # If specified to keep data as string, return True if data already aquired b/c all stability checks are disabled
        if self.keep_as_string and len(self.prev_data) > 0:
            return True

        # If less than the required number of points have been collected, then
        # the conditions can not have been met
        if len(self.prev_data) < self.steady_points:
            return False

        # Determine if all required points are in the steady state
        pts = self.prev_data[
            self.steady_points * -1 :
        ]  # Get the last however many datapoints must be within spec
        center = np.mean(
            pts
        )  # Calculate the mean - this will be used in determining an absolute value for the tolerance
        for p in pts:  # Check each point...
            if (abs(p - center) / center) > self.tol:  # If one point is out of spec
                return False
                # Report conditions are NOT met

            # Or if one point is greater that 1e35 and flag is set, report conditions failed
            if p > 1e35 and self.cap_at_1e35:
                return False

        return True
        # Otherwise, all reqired points were within spec

    def meas_failed(self):
        return self.iterations >= self.max_iterations


class MeasurementDirector:
    def __init__(self, app):

        # List of MeasurementRequest objects to measure in this datapoint
        self.queue = []

        # Describes state of director and if new scan is possible. Options: Ready - can add requests or start scan, Busy - scanning, can not take new measurements or start again, Error - an error occured. Details in err_str, Failed - Last measurement failed. Details in err_str
        self.state = "Ready"
        self.err_str = ""

        # List of all instruments currently processing a MeasurementRequest
        self.occ_instruments = []

        # List of parameter_strings of MeasurementRequests in the queue that need to be relaunched once enough time has elapsed
        self.relaunch_list = []

        self.cancel_batch = False

        self.app = app

        self.relaunch_timer = QTimer()
        self.relaunch_timer.timeout.connect(self.check_relaunch)
        self.relaunch_timer.start(250)

    def measure(self, meas_req):
        """Add a measurement to the list of MeasurementRequests"""

        # MAke sure director is ready to take new commands
        if self.state != "Ready":
            self.error(
                f"Director cannot add measurements because it is in state '{self.state}'. Error code: {self.err_str}"
            )
            return False

        # Get the next index (also checks that dataset is not corrupted)
        next_idx = self.app.data_sets[meas_req.dataset_name].len()
        if next_idx == -1:
            logger.error(
                f"Dataset {meas_req.dataset_name} corrupted. Tracked parameters have unequal number of datapoints.",
                True,
            )
            return False

        # Record next index in measurement_index
        meas_req.measurement_index = next_idx

        # Add measurement request to queue
        self.queue.append(meas_req)

        return True

    def start(self):

        self.cancel_batch = False

        if self.state == "Ready":
            self.state = "Busy"
            self.launch_avail()

    def stop(self):
        pass

    def get_state(self):
        return self.state

    def backend_return_log(self, retval: str, param_str: str):

        # Interpret 'param_str' to get variables to match in MeasurementRequest
        components = param_str.split(":")  # Split the command up into tokens
        if len(components) != 4:
            self.err_str = (
                "Wrong number of components returned in param_str by HC_Comm."
            )
            self.state = "Error"
            return

        m_idx = -1
        try:
            m_idx = int(components[3])
        except:
            midx_str = components[3]
            self.err_str = "Failed to read measurement index '{midx_str}'."
            self.state = "Error"
            return

        # Find set in queue
        idx = -1
        for midx, mr in enumerate(self.queue):  # For evert meas. request...
            if (
                mr.dataset_name == components[0]
                and mr.inst_name == components[1]
                and mr.param_name == components[2]
                and mr.measurement_index == m_idx
            ):  # If identifiers match...
                idx = midx
                # The request was found, record its index
        if idx == -1:
            self.err_str = f"Failed to find MeasurementRequest specified by parameteter string '{param_str}'."
            self.state = "Error"
            return

        # Increment number of iterations
        self.queue[idx].iterations += 1

        # ****** Decide what to do...

        # If one measurement failed and batch is canceled, delete this data
        if self.cancel_batch:

            # Delete this MR from queue
            self.queue.pop(idx)

            logger.debug(
                f"MeasurementRequest with param_str {param_str} deleted itself due to batch cancelation"
            )

            # Remove instrument from occupied_instruments list
            inst_idx = 0
            while inst_idx < len(
                self.occ_instruments
            ):  # For each name in occupied instrumnt list...
                if (
                    self.occ_instruments[inst_idx] == components[1]
                ):  # IF matches last instrument...
                    self.occ_instruments.pop(inst_idx)  # Remove from list
                else:
                    inst_idx += 1

            # If length is zero, set state to ready
            if len(self.queue) == 0:
                self.state = "Ready"

            return

        # Add last measurement to MeasurementRequest
        if not self.queue[idx].add_point(retval):
            self.err_str = "Failed to add point. Return value was invalid."
            self.state = "Error"
            return

        # Check if conditions are satisfied
        if self.queue[idx].conditions_met():

            val = ""
            sep_idx = retval.find("=")
            if sep_idx != -1:  # Separator was found...
                key = retval[0:sep_idx]
                val = retval[sep_idx + 1 :]
            else:
                logger.error(f"Failed to find '=' in {retval}")
                return False  # Separator was not found, return early

            # record data
            data_key = components[1] + ":" + components[2]
            if self.queue[idx].keep_as_string:
                self.app.data_sets[components[0]].data[data_key].append(val)
            else:
                try:

                    if not data_key in self.app.data_sets[components[0]].data:
                        self.app.data_sets[components[0]].data[data_key] = []

                    self.app.data_sets[components[0]].data[data_key].append(float(val))

                except Exception as e:
                    logger.error(f"bad float {val}\n\t{str(e)}")
                    self.err_str = "Failed to add point. Return value could not be converted to a float."
                    self.state = "Error"
                    return

            # Double check that correct number of points exist - ie. index == len()
            if (
                len(self.app.data_sets[components[0]].data[data_key])
                != self.queue[idx].measurement_index + 1
            ):
                logger.error("Wrong number of items in array after measurement")
                self.err_str = (
                    "Wrong number of items in array after adding measurement."
                )
                self.state = "Error"
                return

            # erase from queue
            mes_str = self.queue[idx].param_name
            logger.debug(
                f"Removing index {idx} with parameter {mes_str}. My parameter string is {param_str}"
            )
            self.queue.pop(idx)

            # Remove instrument from occupied_instruments list
            inst_idx = 0
            while inst_idx < len(
                self.occ_instruments
            ):  # For each name in occupied instrumnt list...
                if (
                    self.occ_instruments[inst_idx] == components[1]
                ):  # IF matches last instrument...
                    self.occ_instruments.pop(inst_idx)  # Remove from list
                else:
                    inst_idx += 1

            # Launch available MeasurementRequests
            self.launch_avail()

        # Check if too many attempts have occured
        elif self.queue[idx].meas_failed():

            logger.info(
                f"MeasurementRequest with parameter string {param_str} failed. Canceling batch."
            )

            # Mark as failed
            self.err_str = "Measurement failed"
            self.state = "Fail"
            self.cancel_batch = True

            # erase request from queue
            self.queue.pop(idx)

            # Batch canceled - remove all requests that haven't been launched
            midx = 0
            while midx < len(self.queue):  # For each request...
                if not self.queue[midx].launched:  # If request hasn't been launched...
                    self.queue.pop(midx)  # Remove request
                else:
                    midx += 1

            # Remove instrument from occupied_instruments list
            inst_idx = 0
            while inst_idx < len(
                self.occ_instruments
            ):  # For each name in occupied instrumnt list...
                if (
                    self.occ_instruments[inst_idx] == components[1]
                ):  # IF matches last instrument...
                    self.occ_instruments.pop(inst_idx)  # Remove from list
                else:
                    inst_idx += 1

            if len(self.queue) == 0:
                self.state = "Ready"

        else:

            # Relaunch MR
            if not param_str in self.relaunch_list:
                self.relaunch_list.append(param_str)

    def relaunch(self, meas_req):

        # Find instrument....
        instr_idx = -1
        for idx, inst in enumerate(self.app.instruments):
            if meas_req.inst_name == inst.name:
                instr_idx = idx

        if instr_idx != -1:
            param_str = (
                meas_req.dataset_name
                + ":"
                + meas_req.inst_name
                + ":"
                + meas_req.param_name
                + ":"
                + str(meas_req.measurement_index)
            )
            self.app.instruments[instr_idx].comm.command_log(
                meas_req.inst_command, param_str
            )
        else:
            logger.warning(
                f"Invalid Instrument in MeasurementRequest. Instrument: '{meas_req.inst_name}'"
            )
            return False

    def launch_avail(self):

        # TODO: Consider allowing one instrument to measure two things simultaneously...

        # Set state to ready if all requests in the queue have been processed
        if len(self.queue) == 0:
            self.state = "Ready"
            return

        for mr_idx, mr in enumerate(
            self.queue
        ):  # For every MeasurementRequest in queue...
            if (mr.launched == False) and (
                mr.inst_name not in self.occ_instruments
            ):  # IF the request has NOT been launched and its instrument is NOT occupied...
                self.queue[mr_idx].launched = True  # Mark launched as true
                self.launch(mr)  # Launch request

    def launch(self, meas_req):

        # Find instrument....
        instr_idx = -1
        for idx, inst in enumerate(self.app.instruments):
            if meas_req.inst_name == inst.name:
                instr_idx = idx  # Record index
                self.occ_instruments.append(
                    inst.name
                )  # Add to list of occupied instruments

        if instr_idx != -1:
            param_str = (
                meas_req.dataset_name
                + ":"
                + meas_req.inst_name
                + ":"
                + meas_req.param_name
                + ":"
                + str(meas_req.measurement_index)
            )
            self.app.instruments[instr_idx].comm.command_log(
                meas_req.inst_command, param_str
            )
        else:
            logger.warning(
                f"Invalid Instrument in MeasurementRequest. Instrument: '{meas_req.inst_name}'"
            )
            return False

    def check_relaunch(self):
        """Called automaticlly periodically. When a measurement needs to be repeated to ensure
        steady-state, it is added to the relaunch_list. This checks everything in the relaunch
        list and relaunches it if enough time has ellapsed"""

        # BTW, keep track of the relaunch MRs so you can remove from the relaunch list
        remove_from_list = []

        # Scan through every item...
        for rmr_idx, rmr in enumerate(self.relaunch_list):

            components = rmr.split(":")  # Split the command up into tokens
            if len(components) != 4:
                self.err_str = (
                    "Wrong number of components returned in param_str by HC_Comm."
                )
                self.state = "Error"
                return

            m_idx = -1
            try:
                m_idx = int(components[3])
            except:
                midx_str = components[3]
                self.err_str = "Failed to read measurement index '{midx_str}'."
                self.state = "Error"
                return

            # Find set in queue
            idx = -1
            for midx, mr in enumerate(self.queue):  # For every meas. request...
                # print(len(self.queue))
                if (
                    mr.dataset_name == components[0]
                    and mr.inst_name == components[1]
                    and mr.param_name == components[2]
                    and mr.measurement_index == m_idx
                ):  # If identifiers match...
                    idx = midx
                    # The request was found, record its index
            if idx == -1:
                self.err_str = f"Failed to find MeasurementRequest specified by parameteter string '{rmr}'."
                self.state = "Error"
                return

            # If enough time has ellapsed...
            if (
                time.time() - self.queue[idx].last_launch_time
                >= self.queue[idx].steady_dt
            ):
                self.queue[idx].last_launch_time = time.time()
                self.relaunch(self.queue[idx])  # Relaunch measurement

                remove_from_list.append(rmr_idx)

        # Everything has been processed - remove the relaunched items
        for rfl in reversed(remove_from_list):
            self.relaunch_list.pop(rfl)


class Dataset(QObject):
    """Represents a complete dataset (ie. a collection of datapoints, which are
    collections of individual measurements)."""

    def __init__(self, name: str):

        super().__init__()

        # Name of dataset
        self.name = name

        self.autosave = False  # Whether or not to enable autosave
        self.autosave_interval = 120  # Seconds
        self.autosave_format = "JSON"  # Save format
        self.autosave_filename = f"autosave_{self.name}"
        self.autosave_next_row = 0
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
        self.data = {}

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

        self.data = {}
        self.autosave_next_row = 0

    def name_channel(self, channel: str, name: str):
        """
        Channel must be a string listing the instrument and parameter of the channel
        to rename. THe instrument:parameter pair must be listed in self.data.
        """

        # Set name
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
            f"Dataset {self.name} activated autosave. Interval: {self.autosave_interval} s"
        )

    def start_asynch(self, interval: float = 10, add_timestamp: bool = True):
        """ Converts the dataset to an asynchronous logging dataset. """

        self.async_log_interval = interval
        self.async_add_timestamp = add_timestamp
        self.asynchronous_mode = True

        self.async_log_timer.start(1e3 * self.async_log_interval)

        logger.info(
            f"Dataset {self.name} activated asynchronous mode. Interval: {self.async_log_interval} s"
        )

    def set_save_interval(self, interval: float):

        self.autosave_interval = interval

        self.autosave_timer.setInterval(1e3 * self.autosave_interval)

    def set_async_interval(self, interval: float):

        self.async_log_interval = interval

        self.async_log_timer.setInterval(1e3 * self.async_log_interval)

    def len(self):
        """Returns the length of all of the values in self.data. If they aren't
        all the same length (they should be), returns -1."""

        datalen = -2
        for key in self.data:  # For each instrument/parameter pair...

            if datalen == -2:  # For first time through loop, record length as benchmark
                datalen = len(self.data[key])
            else:  # For everyother time, compare length against benchmark, see if all the same
                if datalen != len(self.data[key]):  # If any don't match, return -1
                    return -1

        if len(self.data) == 0:
            return 0

        return datalen  # Otherwise return current length (which is the next index)

    def len_min(self):
        """Returns the length of the shortest list in self.data."""

        return min([len(self.data[key]) for key in self.data])

    def exec_autosave(self):
        """ Called by the autosave timer. Triggers a call to self.save() """

        logger.info(f"Dataset {self.name} autosaveing to file {self.autosave_filename}")

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
                        f"# {datetime.datetime.today().strftime('%Y-%m-%d')}\n# Logfile from hardware_control run\n"
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

        else:
            logger.warning(f"unrecognized file format '{format}'.")

    def log_async(self):
        """ Periodically called by timer, logs values from included instruments
        to the datasets. Logs timestamp if requested. """

        # Return immediately if not in async mode
        if not self.asynchronous_mode:
            return

        logger.debug(f"Dataset {self.name} logging asynchronous data")

        # Check that all requested parameters are available. If they aren't, don't
        # log anything. This ensures the dataset's columns are all the same length
        if self.require_all:
            for ai in self.async_instruments:
                name = ai[0].name
                vkeys = ai[0].get_value_keys(ai[1])

                if vkeys is None:
                    logger.info(
                        f"Async log for dataset {self.name} aborted because not all values present"
                    )
                    return

            # If all values must be valid (because require_all is true) and all
            # values must be convertible to float, check that values are valid num
            if self.async_require_float:
                for ai in self.async_instruments:
                    for vk in vkeys:
                        try:
                            float(ai[0].values[vk])
                        except:
                            v = ai[0].values[vk]
                            logger.info(
                                f"Async log for dataset {self.name} aborted because value '{v}' for parameter '{vk}' cannot be converted to a float."
                            )
                            return

        # Add timestamp if requested
        if self.async_add_timestamp:
            try:
                self.data["time:time"].append(str(time.time()))
            except:
                self.data["time:time"] = [str(time.time())]

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
                    try:
                        self.data[f"{name}:{vk}"].append(None)
                        logger.debug(f"Adding data: data[{name}:{vk}] = None")
                    except:
                        self.data[f"{name}:{vk}"] = [None]
                    continue

                # Check that parameter exists
                if self.async_require_float and not convertibleToFloat(
                    ai[0].values[vk]
                ):
                    try:
                        self.data[f"{name}:{vk}"].append(None)
                        logger.debug(f"Adding data: data[{name}:{vk}] = None")
                    except:
                        self.data[f"{name}:{vk}"] = [None]
                    continue

                # Otherwise add raw data
                try:
                    self.data[f"{name}:{vk}"].append(ai[0].values[vk])
                    nd = ai[0].values[vk]
                    logger.debug(f"Adding data: data[{name}:{vk}]='{nd}'")
                except:
                    self.data[f"{name}:{vk}"] = [ai[0].values[vk]]

    def get_corresponding_arrays(self, set_names: list, convert_to_float=False):
        """ Returns lists for each of the parameters specified in set_names (
        indicated as <instrument>:<parameter>). If 'None' appears in any of the
        specified lists, all data points at that index for all returned lists are
        removed. This guarantees all returned lists have the same length and that
        the lists indecies correspond with eachother.

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
                if self.data[sn][idx] == None:  # If 'None' present, skip to next index
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


class HC_Instrument(QGroupBox):
    def __init__(self, window, name: str, backend=None, lock_until_sync=False):
        super().__init__(name)
        # ToDo Why ordered dict??
        self.settings = OrderedDict()
        self.values = OrderedDict()
        self.values_unit = OrderedDict()
        self.name = name
        self.manufacturer = None
        self.company = None
        self.online = False
        self.comm = None
        self.window = window
        self.ignore = (
            False  # Dictates if instrument should be ignored by connectiontool
        )
        self.address = ""  # This is used mostly for displaying the instrument's
        # address to the user

        self.online_callback = None

        if backend is not None:
            if backend.connection_addr in self.window.app.comms:
                self.comm = self.window.app.comms[backend.connection_addr]
                self.comm.addWidget(self)
            else:
                self.window.app.comms[backend.connection_addr] = HC_Comm(
                    backend, self, lock_until_sync=lock_until_sync
                )
                self.comm = self.window.app.comms[backend.connection_addr]

        self.us_hooks = []  # Run every time update settings is called
        self.ramp_hooks = []  # Run every time update_ramp is called
        self.ramp_mode = OFF
        self.ramp_val = OrderedDict()
        self.ramp_target = OrderedDict()
        self.default_ramp_speed = 100  # Units/sec
        self.ramp_speed = {}  # Override default_ramp_speed for specific parameters here
        self.ramp_update_period = 1e3  # time between ramp steps in ms

        # Global Constants
        self.globalRefreshRate = 1000  # ms refresh
        # this is a global reference for limiting the scaling the widgets
        self.globalLineHeight = 50  # Lineheight of athe average  spinbox
        self.globalLineWidth = 300  # Linewidth of athe average  spinbox
        self.online_color = (
            "Green"  # Color of online light for status tool. Can be Green or Blue
        )

        # ConnectionTool and ScanTool widgets

        self.window = window  # parent needs to have a field called 'app' which
        # is an instance of 'HC_App'

        window.app.add_instrument(self)

        self.ramp_timer = QTimer(self)
        self.ramp_timer.timeout.connect(self.update_ramp)

    def __repr__(self):
        return f"HC_Instrument {self.name} {self.manufacturer} @ {self.address} online:{self.online}"

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.name}"

    def init_values(self):
        """
        This function should be overwritten by child classes to initialize the
        values dictionary. The child class (such as HC_MultiPowerSupply) can
        then initialize its values dict such that all queryable values are
        listed.

        The values loaded into the values dict by this function will also be used
        by the read_state_from_backend() function to initialize the settings
        dictionary and/or UI.
        """
        pass

    def set_online_callback(self, callback_function):
        """
        This function allows the user to specify a callback function which will
        be called when the backend reports 'online' the next time.
        """

        if not callable(callback_function):
            logger.warning(
                f"Specified a non-callable object ({callback_function}) for a callback function. "
            )
            return

        self.online_callback = callback_function

    def update_ramp(self):

        # List of parameters to remove from ramp_target after for loop. Note that
        # removing items from dict while iterating over dict is not well-defined,
        # hence why 'pop_list' is neccesary
        pop_list = []

        if self.ramp_mode == MANUAL:

            # For each parameter being ramped
            for key in self.ramp_target:

                # Get current value. Set to 0 if not specified
                curr = 0
                if key in self.ramp_val:
                    curr = self.ramp_val[key]
                elif key in self.values:
                    curr = self.values[key]
                try:
                    curr = float(curr)
                except:
                    logger.warning("Invalid value for 'curr'. Ramping from 0.")
                    curr = 0

                # Run all hooks
                for rhook in self.ramp_hooks:

                    if callable(rhook):
                        try:
                            curr = rhook(self, key, curr, self.ramp_target[key])
                        except:
                            logger.warning(
                                f"Call to hook '{rhook}' failed. skipping. ",
                                exc_info=True,
                            )

                # If curr == None, that indicates ramp is complete. Delete value from targets
                if curr == None:
                    pop_list.append(key)
                else:
                    self.ramp_val[key] = curr
                    self.comm.update_setting(key, str(curr))

            for pkey in pop_list:
                self.ramp_target.pop(pkey, None)

        if self.ramp_mode == AUTOMATIC:

            logger.debug("Callback Automatic ramp")

            # For each parameter being ramped
            for key in self.ramp_target:

                logger.debug(f"Handling ramp for parameter {key}")

                # Get current value. Set to 0 if not specified
                curr = 0
                if key in self.ramp_val:
                    curr = self.ramp_val[key]
                elif key in self.values:
                    curr = self.values[key]
                try:
                    curr = float(curr)
                except:
                    logger.warning("Invalid value for 'curr'. Ramping from 0.")
                    curr = 0

                logger.debug(f"Value at start for parameter {key} was {curr}")

                # Get increment
                if key in self.ramp_speed:
                    dVal = self.ramp_speed[key]
                else:
                    dVal = self.default_ramp_speed
                try:
                    dVal = float(dVal)
                except:
                    logger.error(
                        "Ramp speeds must be floats. Cannot ramp. Changing ramp_mode to OFF."
                    )
                    self.ramp_mode = OFF
                    self.ramp_timer.stop()
                    return

                logger.debug(f"Increment for parameter {key} will be {dVal}")

                # Update value
                if self.ramp_target[key] > curr:
                    curr = min(curr + dVal, self.ramp_target[key])
                else:
                    curr = max(curr - dVal, self.ramp_target[key])

                logger.debug(f"New value for parameter {key} will be {curr}")

                # If curr == None, that indicates ramp is complete. Delete value from targets
                if curr == self.ramp_target[key]:
                    pop_list.append(key)

                self.ramp_val[key] = curr
                self.comm.update_setting(key, str(curr))

            for pkey in pop_list:
                self.ramp_target.pop(pkey, None)

        # IF all ramps complete, stop timer
        if len(self.ramp_target) < 1:
            logger.debug("Killing ramp timer")
            self.ramp_timer.stop()

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
            logger.error(
                f"Key '{setting}' does not exist for instrument '{self.name}' in settings dictionary.",
                exc_info=True,
            )

        if self.comm is not None:

            # If ramp mode is on, set the target value and activate the timer
            if self.ramp_mode in [AUTOMATIC, MANUAL]:
                try:
                    self.ramp_target[setting] = float(value)
                except:
                    logger.warning(
                        f"Cannot set received value '{value}' as ramp target value because it cannot be converted to a float. Setting '{setting}' directly to '{value}'."
                    )
                    self.values[setting] = self.comm.update_setting(setting, value)
                    return
                if not self.ramp_timer.isActive():
                    self.ramp_timer.start(self.ramp_update_period)
                return

            self.values[setting] = self.comm.update_setting(setting, value)

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
            logger.error(
                "Key '{parameter}' does not exist for instrument '{self.name}'.",
                exc_info=True,
            )

        if type(current_val) == str:
            try:
                self.settings[parameter] = value
            except:
                logger.error(
                    f"Failed to convert {type(value)} '{value}' to string.",
                    exc_info=True,
                )
                return False
        elif type(current_val) == int or type(current_val) == float:
            try:
                self.settings[parameter] = float(value)
            except:
                logger.error(
                    f"Failed to convert {type(value)} '{value}' to float. Exiting scan.",
                    exc_info=True,
                )
                return False

        else:
            logger.error(
                "Settings must have string, float, or int datatype.\n\tInstrument '{self.name}' setting {parameter} has type: {type(current_val)}"
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
                logger.info(f"settings for {self.name} read from file '{filename}'")
        except:
            logger.error(
                f"Failed to read file '{filename}'. Using defualt case.", exc_info=True
            )
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
                logger.info(f"settings for {self.name} saved to file '{filename}'")
        except Exception as e:
            logger.error(
                f"Failed to write file '{filename}'. settings not saved.", exc_info=True
            )

    def send_state(self):
        """Writes the entire state/settings dicitonary to the oscilloscope"""
        for key in self.settings:
            if self.comm is not None:
                self.comm.update_setting(key, str(self.settings[key]))
                x = str(self.settings[key])

    def read_state_from_backend(self):

        # Send a query to the backend for every possible value
        for v in self.values:
            self.comm.command(f"{v}?")

        # Send a 'sync' command to the backend. It will be returned
        # immediately and used by the backend as an indicator for when all
        # of the previous commands have been processed
        self.comm.command("SYNC_BACKEND")

    def close(self):
        if self.comm is not None:
            self.comm.close()

    def read_values(self, prefix: str):
        """Looks for an entry in self.values with the key 'prefix'. If found, the
        key's value is returned, else it returns None."""

        if prefix in self.values:  # If prefix exists as key, return vale
            rval = self.values[prefix]
        else:  # Else return None
            rval = None

        return rval

    def sync_backend_called(self):
        """
        This function is called when 'SYNC_BACKEND' is received from HC_Comm. It
        is used in read_state_from_backend to indicate when the backend has sent
        all queried values back to the front end.
        """

        # Transfer 'values' to 'settings'
        for v in self.values:
            if v in self.settings:
                self.settings[v] = self.values[v]

        # Transfer 'settings' to UI
        self.settings_to_UI()

    def backend_return(self, retval: str):
        """Is called by self.comm when the backend returns a value. The return string
        is converted here into a dictionary's key/value pair and added to self.values.
        An equals sign ('=') is used to separate the key and value, with key coming
        first."""

        if retval == "SYNC_BACKEND":
            self.sync_backend_called()

        sep_idx = retval.find("=")
        if sep_idx != -1:  # Separator was found...

            # # Check for asterisk at end of key, ie. right before '='. This indicates
            # # that this command unlocks HC_App's Macro runner and that the parameter
            # # needs to be logged in HC_App.saved_data immediately by appending the
            # # received value to the back of the list in HC_App.saved_data with the
            # # key specified by the returned value.
            # if sep_idx > 0 and retval[sep_idx - 1] == "*":
            #
            #     self.window.app.macro_locked = False
            #     # Unlock macro
            #
            #     sep_idx -= 1
            #     # Remove asterisk from key
            #     key = retval[0:sep_idx]  # Get key
            #     val = retval[sep_idx + 2 :]  # Get value
            #
            #     val_f = -1
            #     try:
            #         val_f = float(val)
            #     except:
            #         logger.error(f"Failed to convert {val} to a float", exc_info=True)
            #
            #     try:  # Append data
            #         self.window.app.saved_data[key].append(val_f)
            #     except:  # Does not exist, create list and key
            #         self.window.app.saved_data[key] = [val_f]
            #
            # else:

            key = retval[0:sep_idx]
            val = retval[sep_idx + 1 :]

            self.values[key] = val

        else:  # If no separator, put under 'Misc'

            self.values["Misc"] = retval

    def backend_return_online(self, connected: bool):
        """Is called by self.comm when the backend returns an online status."""

        self.online = connected

        if self.online_callback is None:
            return

        if not callable(self.online_callback):
            self.online_callback = None
            return

        self.online_callback(self)
        self.online_callback = None

    def backend_return_listdata(self, descr: str, data1: list, data2: list):
        """Is called by self.comm when the backend returns from command_listdata,
        which returns a string and two lists. The author of the UI can overwrite
        this function to procses the return data."""
        pass

    def backend_return_log(self, retval: str, point_data):
        """Performs the logging action before backend_return() updates the UI.

        When HC_Comm's command_log() returns, backend_return_log() is called
        prior to backend_return(). backend_return_log() stores the value in
        self.values, or whatever else it may be configured to do.
        """

        found = False
        for ds in self.window.app.data_sets:
            if point_data.dataset_name == ds.name:

                sep_idx = retval.find("=")
                if sep_idx == -1:
                    logger.error(
                        "Failed to find '=' in return string after call to command_log()",
                        exc_info=True,
                    )
                    return False

                key_param = retval[0:sep_idx]
                val = retval[sep_idx + 1 :]

                key_name = point_data.instrument_name + ":" + key_param
                ds.data[key_name].append(val)
                found = True

        if not found:
            return False

        return True

        # TODO: Record 'id' for each measurement
        # TODO: Erase measurements with corresponding ID if one fails

    def get_header(self, parameters=None):
        """ Returns a header to describe what is returned by get_values(). It
        must be overwritten by the instrument if the instrument is to be
        compatible with asynchronous logging datasets.

            Example 1:
                return ' '.join([ch.get_header() for ch in self.channels])

            Example 2:
                return 'HV-Voltage[V] HV-Current[A] Pressure[mTorr]' """

        # Make sure parameters is list or None
        if type(parameters) != list and parameters is not None:
            return None

        #
        header = ""
        for v in self.values:

            # If parameters is a list (not None) and 'v' is not listed, skip
            if v is not None and v not in parameters:
                continue

            header = header + v
            if v in self.values_unit:
                unit = self.values_unit[v]
                header = header + f"[{unit}] "
            else:
                self.values_unit[v] = "?"
                header = header + " "
        return header

    def get_value_keys(self, parameters=None, require_all: bool = True):
        """ Returns the keys of the values tracked by the instrument. This
        function is called by datasets during asynchronous logging. If an
        instrument is to work with asynchronous logging, it must overwrite this
        function to return the parameters it wants to track. These parameters
        must match what is listed in get_header().

        If require_all is true and not all requested parameters are present the
        function returns None.

        Example:
            return ['voltage', 'current', 'pressure'] """

        # If nothing specified, return all values
        if parameters is None:
            return [str(v) for v in self.values]

        # Otherwise make sure is list
        if type(parameters) != list:
            logger.info(
                f"get_value_keys() received bad 'parameter' argument. type must be list or None but was '{type(parameter)}'."
            )
            return None

        rval = []
        for p in parameters:

            if not require_all:
                rval.append(p)
                continue

            if p in self.values:
                rval.append(p)
            else:
                logger.warning(
                    f"get_value_keys() skipped parameter '{p}' because it was not listed in values ({self.values})"
                )
                return None
        return rval

    def settings_to_UI(self):
        """ Overwrites the values in the UI with the values in self.settings """
        logger.warning(f"settings_to_UI not implimented for instrument {self.name}")


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

                    # Run function - note: this can become recursive and get stuck in
                    # an infinite loop if the user runs a function that calls itself
                    if len(tokens) > 3:
                        tokens = command.split(":", 3)
                        try:
                            return self.function_handles[tokens[2]](token_handles[3])
                        except:
                            return "Error"
                    else:
                        try:
                            return self.function_handles[tokens[2]]()
                        except:
                            return "Error"

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
        self.clear_data_act = QAction("Clear Data", self)
        self.clear_data_act.setShortcut("Ctrl+Shift+K")
        self.file_menu.addAction(self.clear_data_act)
        #
        self.new_group_act = QAction("New Dataset", self)
        self.new_group_act.setShortcut("Ctrl+Shift+N")
        self.file_menu.addAction(self.new_group_act)
        #
        self.file_menu.addSeparator()
        #

        if platform == "linux" or platform == "linux2" or platform == "darwin":
            self.close_act = QAction("Close Window", self)
            self.close_act.setShortcut("Ctrl+W")
        elif platform == "win32":
            self.close_act = QAction("Exit", self)
            self.close_act.setShortcut("Ctrl+Q")
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
        self.sync_from_file_act = QAction("Refresh UI", self)
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

        if q.text() == "Save Instrument States":

            filename = ""

            # Use file dialog to get save location
            dlg = QFileDialog()
            name_tuple = dlg.getSaveFileName()
            filename = name_tuple[0]
            if not filename:  # If cancel bttonw as hit, name will be null
                return

            self.app.save_all_states(filename)

        elif q.text() == "Save Data":

            self.save_all()

        elif q.text() == "Clear Data":

            for ds_name in self.app.data_sets:
                self.app.data_sets[ds_name].clear()

        elif q.text() == "New Dataset":

            self.create_new_group()

            for inst in self.app.instruments:
                if (
                    inst.name == "Data Logger"
                ):  # TODO: Find resilient way to automatically identify LoggerTool objects to update their group lists
                    inst.update_groups()

        elif q.text() == "Exit" or q.text() == "Close Window":
            self.close()
            sys.exit(0)
        else:
            logger.error("function not supported")

    def process_instr_menu(self, q):

        if q.text() == "Sync from Instrument":  # TODO: impliment

            self.app.backends_to_settings()
            self.app.settings_to_UI()

        elif q.text() == "Sync from UI":

            self.app.settings_to_backends()

        elif q.text() == "Sync from File":

            filename = ""

            # Use file dialog to get save location
            dlg = QFileDialog()
            name_tuple = dlg.getOpenFileName()
            filename = name_tuple[0]
            if not filename:  # If cancel bttonw as hit, name will be null
                return

            self.app.load_state_from_file(filename)

        elif q.text() == "Refresh UI":

            for instr in self.app.instruments:
                instr.settings_to_UI()

        elif q.text() == "Print Addresses":

            print("Instrument Addresses")
            for inst in self.app.instruments:

                try:
                    addr = inst.address
                except Exception as e:
                    addr = "---"

                if addr == "" or addr == None:
                    addr = "---"

                print(f"\t{inst.name}:\t {addr}")

        else:
            logger.error("function not supported")

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
            logger.error("Not implimented")
        elif q.text() == "Add Variable":  # TODO: impliment
            logger.error("Not implimented")
        elif q.text() == "Add Macro":  # TODO: impliment
            logger.error("Not implimented")
        elif q.text() == "Show Variables":  # TODO: impliment
            logger.error("Not implimented")
        elif q.text() == "Show Macros":  # TODO: impliment
            logger.error("Not implimented")
        else:
            logger.error("function not supported")

    def save_all(self):
        """ Save all datasets to a file, specified by a file dialog """

        filename = ""

        # Use file dialog to get save location
        dlg = QFileDialog()
        name_tuple = dlg.getSaveFileName()
        filename = name_tuple[0]
        if not filename:  # If cancel bttonw as hit, name will be null
            return

        # print(filename)

        all_data = {}

        # Collect all datasets data in one dictionary
        for ds_name in self.app.data_sets:
            set_name = self.app.data_sets[ds_name].name
            all_data[f"{set_name}"] = self.app.data_sets[ds_name].data

        # Add extension if not specified
        ext = os.path.splitext(filename)[-1].lower()
        if ext == "":
            filename = filename + ".json"

        # Write file
        with open(filename, "w", encoding="utf-8") as outfile:
            json.dump(all_data, outfile, ensure_ascii=False, indent=4)

    def save_data(self, dataset_name: str):
        """Saves the data stored in the app's data_sets object. Saves the dataset
        with name specified by 'dataset_name'. If 'sets' is empty string, will save
        all datasets."""

        # Use file dialog to get save location
        dlg = QFileDialog()
        name_tuple = dlg.getSaveFileName()
        name = name_tuple[0]
        if not name:  # If cancel bttonw as hit, name will be null
            return

        # Use input dialog to get save file type
        save_types = ("JSON", "Pickle", "NPY", "TXT")
        file_type, okay = QInputDialog.getItem(
            self, "Select File Type", "File Type:", save_types, 0, False
        )

        print(f"Save set '{dataset_name}' to file '{name}' with type '{file_type}'")

        if okay and file_type:
            logger.info(f"Saving as {file_type} with name {name}")
            try:
                self.app.data_sets[dataset_name].save(name, file_type)
            except:
                logger.error(
                    f"Failed to find and save dataset with name '{dataset_name}'",
                    exc_info=True,
                )
        else:
            logger.info("Save canceled")

        # if file_type == "Pickle (*.p)":
        #     logger.error("Not yet implimented")
        # elif file_type == "NumPy (*.npy)":
        #     logger.error("Not yet implimented")
        # elif file_type == "JSON (*.json)":
        #
        #     # Open file...
        #     with open(name, "w") as f:
        #
        #         # Create buffer object
        #         save_data_obj = {}
        #
        #         if len(sets) > 0:  # If groups are specified...
        #             for grp in sets:  # Save each specified group if it exists
        #                 try:
        #                     save_data_obj[
        #                         self.app.data_sets[grp].name
        #                     ] = self.app.data_sets[grp].data
        #                 except:
        #                     pass
        #         else:  # Else save all...
        #
        #             for ds_key in self.app.data_sets:
        #                 save_data_obj[
        #                     self.app.data_sets[ds_key].name
        #                 ] = self.app.data_sets[ds_key].data
        #
        #         json.dump(save_data_obj, f)

    def create_new_group(self):

        dlg = QInputDialog(self)
        dlg.setInputMode(QInputDialog.TextInput)
        dlg.setLabelText("New dataset name:")
        dlg.resize(500, 100)
        okPressed = dlg.exec_()
        text = dlg.textValue()

        if okPressed and text != "":
            temp_ds = Dataset(text)
            self.app.data_sets[text] = temp_ds


class HC_ConsoleWidget(RichJupyterWidget):
    def __init__(self, main_app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel = self.kernel_manager.kernel

        self.kernel.shell.banner1 += """
        Direct python interface

        You can access variables from the app through the main app widget

        app: main app widget
        np:  numpy

        """
        self.kernel.gui = "qt"
        self.kernel.shell.push({"np": np, "app": main_app})
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()


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
