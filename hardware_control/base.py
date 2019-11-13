# -*- coding: utf-8 -*-
from collections import defaultdict, deque, OrderedDict
import datetime
import pkg_resources
import hashlib
import sys
import time
import pathlib

from PyQt5 import QtCore
from PyQt5.QtCore import QThread, QSize, QObject, pyqtSignal, pyqtSlot, QObject, QTimer
from PyQt5.QtGui import QIcon, QFont, QFontMetrics
from PyQt5.QtWidgets import (
    QApplication,
    QSizePolicy,
    QPushButton,
    QLabel,
    QMessageBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QGroupBox,
)
from PyQt5.QtSvg import QSvgWidget

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.dates import epoch2num
import numpy as np
from abc import ABC, abstractmethod


class HC_Comm(QObject):
    """This object is used to automate creating threads and communication objects.
    By calling this object's functions, data can be safely transfered between the
    main thread and communication threads."""

    sigUpdateSettings = pyqtSignal(str, str)
    sigCommand = pyqtSignal(str)
    sigWrite = pyqtSignal(str)
    sigQuery = pyqtSignal(str)
    sigTryConnect = pyqtSignal()
    sigClose = pyqtSignal()

    def __init__(self, backend, instrument):
        super().__init__()
        self.backend = backend
        self.instrument = instrument  # Calling instrument UI (eg. HC_scope)
        self.backend_model = backend.ID

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
        self.sigClose.connect(self.worker.close)

        # Connect CommWorker's signals to Comm's slots
        self.worker.sigReturnValues.connect(self.backend_return)
        self.worker.sigReturnOnline.connect(self.backend_return_online)

        # Connect timer
        self.try_connect_timer = QTimer(self)
        self.try_connect_timer.timeout.connect(self.try_connect)
        self.try_connect_timer.start(1000)

    def close(self):
        if self.instrument.window.app.print_debug:
            print(
                f"\tInstrument: '{self.instrument.name}' closing Comm with backend of type '{self.backend_model}'."
            )
        self.try_connect_timer.stop()  # Stop
        self.sigClose.emit()
        self.worker_thread.quit()  # Kill thread
        if self.instrument.window.app.print_debug:
            print(
                f"\t\tInstrument: '{self.instrument.name}' called quit() for worker thread."
            )
        self.worker_thread.wait()  # Wait for thread to join (otherwise, if main thread exists first, stdout will be closed while the worker_thread may still be running and try to write to stdout, causing an error to arise)
        if self.instrument.window.app.print_debug:
            print(
                f"\t\tInstrument: '{self.instrument.name}' joined with worker thread."
            )

    def update_setting(self, setting: str, value: str):
        """Transfers the setting and value information to the worker thread"""
        if self.instrument.window.app.print_debug:
            print(
                f"Instrument: {self.instrument.name} called 'update_setting()' for setting '{setting}' and sent message '{value}'."
            )
        self.sigUpdateSettings.emit(setting, value)
        self.instrument.window.app.add_log(
            self.instrument.name, self.backend_model, "SET", setting, value
        )

    def command(self, cmd: str):
        """Sends a command to the worker in the worker thread"""
        if self.instrument.window.app.print_debug:
            print(
                f"Instrument: {self.instrument.name} called 'command()' and sent command: '{cmd}'."
            )
        self.sigCommand.emit(cmd)
        self.instrument.window.app.add_log(
            self.instrument.name, self.backend_model, "CMD", cmd
        )

    def write(self, msg: str):
        """Sends a command to be sent to the instrument by the worker in the worker thead"""
        if self.instrument.window.app.print_debug:
            print(
                f"Instrument: {self.instrument.name} called 'write()' and sent message: '{msg}'."
            )
        self.sigWrite.emit(msg)
        self.instrument.window.app.add_log(
            self.instrument.name, self.backend_model, "WRT", setting
        )

    def query(self, msg: str):
        """Sends a query statement to be sent to the instrument by the worker in the worker thead"""
        if self.instrument.window.app.print_debug:
            print(
                f"Instrument: {self.instrument.name} called 'query()' and sent message: '{msg}'."
            )
        self.sigQuery.emit(msg)
        self.instrument.window.app.add_log(
            self.instrument.name, self.backend_model, "QRY", setting
        )

    def try_connect(self):
        """Tells the worker to tell the backend to try to connect to the instrument"""
        self.sigTryConnect.emit()

    @pyqtSlot(str)
    def backend_return(self, retval: str):
        """Receives a return value from the CommWorker and adds the return value to the back of the inbox"""
        if self.instrument.window.app.print_debug:
            print(
                f"Instrument: {self.instrument.name} received return from backend '{self.backend_model}'. Return message: {retval}"
            )
        self.instrument.inbox.append(retval)

    @pyqtSlot(bool)
    def backend_return_online(self, connected: bool):
        """ Gets called by the worker after the worker hears from the instrument if it successfully connected.
        Updates the state of the instrument - ie. if it is or is not online"""
        self.instrument.online = connected


class HC_CommWorker(QObject):
    """Uses signals + slots to receive data from HC_Comm and relays the information
    to the backend object. Then sends the return value back to HC_Comm via signals +
    slots, when HC_Comm then pushes onto the back of the isntrument's inbox"""

    sigReturnValues = pyqtSignal(str)
    sigReturnOnline = pyqtSignal(bool)

    def __init__(self, backend):
        super().__init__()

        self.backend = backend

    @pyqtSlot(str, str)
    def update_setting(self, setting: str, value: str):
        """Transfers a setting and value to the backend"""
        ret_val = self.backend.update_setting(setting, value)
        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(str)
    def command(self, cmd: str):
        """Transfers a command to the backend"""
        ret_val = self.backend.command(cmd)
        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(str)
    def write(self, msg: str):
        """Transfers a command to be sent directly to the instrument to the backend"""
        ret_val = self.backend.write(msg)
        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(str)
    def query(self, msg: str):
        """Transfers a query statement to be sent directly to the instrument to the backend"""
        ret_val = self.backend.query(msg)
        self.sigReturnValues.emit(ret_val)

    @pyqtSlot()
    def try_connect(self):
        """Is called by HC_Comm on a timer. Tells backend to check if is
        connected, else connect."""
        online = self.backend.try_connect()
        self.sigReturnOnline.emit(online)

    @pyqtSlot()
    def close(self):
        """"Tells backend to close the connection. Then reports if instrument is
        offline."""
        online = self.backend.close()
        self.sigReturnOnline.emit(online)


class HC_Instrument(QGroupBox):
    def __init__(self, window, name: str):
        super().__init__(name)
        self.settings = OrderedDict()
        self.values = OrderedDict()
        self.values_unit = []
        self.name = name
        self.manufacturer = None
        self.company = None
        self.online = False
        self.comm = None
        self.ignore = (
            False
        )  # Dictates if instrument should be ignored by ConnectionTool and ScanTool widgets
        self.inbox = []  # Receives strings from the HC_comm object

        self.window = (
            window
        )  # parent needs to have a field called 'app' which is an instance of 'HC_App'

        window.app.add_instrument(self)

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.name}"

    def get_header(self):
        """Supply a header for a log file"""
        header = f"{self.manufacturer}-{self.model}-"
        header += "-".join(
            [
                f"{vname}[{vunit}]"
                for vname, vunit in zip(self.values.keys(), self.values_unit)
            ]
        )
        return header

    def get_values(self):
        """Return current list of values for logging"""
        return self.values.values()

    def update_setting(self, setting: str, value):
        """Update a setting in settings and values dictionary for the instrument"""
        try:
            self.settings[setting] = value
        except KeyError:
            print(
                "ERROR: Key '{parameter}' does not exist for instrument '{self.name}' in settings dictionary."
            )

        if self.comm is not None:
            try:
                self.values[setting] = self.comm.update_setting(setting, value)
            except KeyError:
                print(
                    "ERROR: Key '{parameter}' does not exist for instrument '{self.name}' in values dictionary."
                )

    def command(self, cmd_str: str):
        """Update a setting in settings and values dictionary for the instrument"""

        if self.comm is not None:
            self.comm.command(setting, value)

    def set_setting(self, parameter: str, value: str):
        """Adjusts a parameter in 'self.settings' and updates any GUI elements to reflect the change."""

        # Find instrument, get current setting for parameter
        try:
            current_val = self.settings[parameter]
        except KeyError:
            print(
                "ERROR: Key '{parameter}' does not exist for instrument '{self.name}'."
            )

        if type(current_val) == str:
            try:
                self.settings[parameter] = value
            except:
                print(f"ERROR: Failed to convert {type(value)} '{value}' to string.")
                print("Exiting scan")
                return False
        elif type(current_val) == int or type(current_val) == float:
            try:
                self.settings[parameter] = float(value)
            except:
                print(f"ERROR: Failed to convert {type(value)} '{value}' to float.")
                print("Exiting scan")
                return False

        else:
            print("ERROR: Settings must have string, float, or int datatype.")
            print(
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
                print(f"settings for {self.name} read from file '{filename}'")
        except:
            print(f"ERROR: Failed to read file '{filename}'. Using defualt case.")
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
                print(f"settings for {self.name} saved to file '{filename}'")
        except Exception as e:
            print(f"ERROR: Failed to write file '{filename}'. settings not saved.")
            print(f"\t{e}")

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
            self.window.app.add_log(self.name, "NO-HARDWARE-BACKEND", "NOTE", note)

    def read_message(self, prefix: str):
        """Looks for a string in self.inbox, starting from the back (ie. most
        recent), which starts with the string specified by argument 'prefix'. If
        such a string is found, it returns the contents after prefix and deletes
        the string from self.inbox. Returns None if no such message found"""

        rval = None
        for idx, i in reversed(list(enumerate(self.inbox))):

            if i[0 : len(prefix)] == prefix:  # If prefix matches begining...
                rval = i[len(prefix) :]  # Save remainder to return value
                self.inbox.pop(idx)  # Erase the read message
                break
                # Quit looping

        return rval


class HC_App(QApplication):
    """Subclass of QApplication that is aware of what hardware is connected to it and can log data"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instruments = []
        self.log = []  # List of strings for debugging/logging purposes

        self.print_debug = False

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
                print(f"settings for {self.comm.instr.ID} saved to file '{filename}'")
        except Exception as e:
            print(f"ERROR: Failed to write file '{filename}'. State not saved.")
            print(f"\t{e}")

    def list_instruments(self):
        if self.instruments:
            print("Known instruments:")
        else:
            print("No instruments known")
        for i in self.instruments:
            print(f"  {i}")

    def check_instruments(self):
        """Make sure all instruments conform to specifications"""
        for i in self.instruments:
            try:
                i.name
            except AttributeError:
                print(f"Error: Instrument  {i} needs a .name")
            if i.manufacturer is None:
                print(f"Error: Instrument  {i} needs a .manufacturer")
            if i.model is None:
                print(f"Error: Instrument  {i} needs a .model")

    def close(self):
        """Closes all instruments"""
        for instr in self.instruments:
            try:  # User may not have initialized comm correctly as HC_Comm - error check here
                instr.comm.close()  # Send close signal to backend - stop connect timer
            except Exception as e:
                print(f"Failed to close instrument '{instr.name}'.")
                print(str(e))

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
        ):
            self.log.append(
                f'{instr_name}: \t{log_type} "{arg1}" \t[{datestr}] \t[{backend_model}]'
            )
        else:
            print(f"Invalid log type code '{log_type}' received")

    def close(self):

        for instr in self.instruments:
            if self.print_debug:
                print(f"HC_App called 'close()' for instrument: '{instr.name}'.")
            instr.close()


class QOnOff(QPushButton):
    """An On/Off button with a nice icon for on/off

    Takes two functions that will be called when turning on/off
    starts in an unkown state if not defined otherwise

    if f_off is None: assume that f_on is a signal that can emit a boolian.
    """

    def __init__(self, f_on, f_off=None):
        super().__init__()
        self.setCheckable(True)

        self.onText = "On"
        self.offText = "Off"
        self.unkownText = "status unkown"

        self.onIcon = QIcon(
            pkg_resources.resource_filename(
                "hardware_control", "icons/button-power-on.svg"
            )
        )
        self.offIcon = QIcon(
            pkg_resources.resource_filename(
                "hardware_control", "icons/button-power-off.svg"
            )
        )
        self.unkownIcon = QIcon(
            pkg_resources.resource_filename(
                "hardware_control", "icons/button-power-unkown.svg"
            )
        )

        self.f_on = f_on
        self.f_off = f_off
        self.clicked.connect(self.click)

        self.setText(self.unkownText)
        self.setIcon(self.unkownIcon)
        self.setIconSize(QtCore.QSize(30, 30))

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def click(self):
        # we need a 'not' here since the button internally already
        # changed state at this point
        if not self.isChecked():
            if self.f_off:
                self.f_off()
            else:
                self.f_on.emit(False)
            self.set_icon_off()
        else:
            if self.f_off:
                self.f_on()
            else:
                self.f_on.emit(True)
            self.set_icon_on()

    def on(self):
        if self.f_off:
            self.f_on()
        else:
            self.f_on.emit(True)
        self.set_icon_on()

    def set_icon_on(self):
        """Just set the icon to on. Useful during startup"""
        self.setChecked(True)
        self.setIcon(self.onIcon)
        self.setText(self.onText)

    def off(self):
        if self.f_off:
            self.f_off()
        else:
            self.f_on.emit(False)
        self.set_icon_off()

    def set_icon_off(self):
        """Just set the icon to off. Useful during startup"""
        self.setChecked(False)
        self.setIcon(self.offIcon)
        self.setText(self.offText)

    def isOn(self):
        return self.isChecked()


class HC_Control(ABC):
    """Create an abstract base class for instruments

    This defines the interface that should be present for new instruments.

    Functions that _have_to_ be implemented are decorated and functions
    that _can_ be implemented raise a NotImplementedError.


    Note: the real implementation can have different amount of arguments,
    e.g. write could be write(channel, value).

    """

    @abstractmethod
    def read(self):
        """Read values from instrument.

        If the instrument has multiple values to set, this should
        function should take a channel arguments or something similar.
        """

        pass

    @abstractmethod
    def write(self, value):
        """Write values to instrument.

        This function should take a value or channel/value argument.
        """

        pass

    @abstractmethod
    def try_connect(self):
        """Try to connect to instrument.

        This function should check if we are already connected and in
        that case do nothing. We should be able to call this function
        as often as we want without much overhead.
        """

        pass

    @abstractmethod
    def close(self):
        """Closes any connection that got opened by try_connect"""

        pass

    def is_on(self):
        """Return True/False, if the instrument is on

        This is an optional functions. It is listed here just to give
        the recommended name for this function.
        """

        raise NotImplementedError


class QOnOffIndicator(QSvgWidget):
    """An On/Off indicator

    Listens to signals for on/off and shows a green or red light with a tooltip for mouse-over events.

    starts in an unkown state (both lights off)"""

    def __init__(self, name):
        self.name = name
        self.onIcon = pkg_resources.resource_filename(
            "hardware_control", "icons/on-off-indicator-on.svg"
        )
        self.offIcon = pkg_resources.resource_filename(
            "hardware_control", "icons/on-off-indicator-off.svg"
        )
        self.unkownIcon = pkg_resources.resource_filename(
            "hardware_control", "icons/on-off-indicator-unkown.svg"
        )

        super().__init__(self.unkownIcon)

        self.setMouseTracking(True)
        self.setToolTip(name)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def sizeHint(self):
        return QSize(10, 20)

    def on(self):
        self.renderer().load(self.onIcon)

    def off(self):
        self.renderer().load(self.offIcon)

    def set(self, status):
        if status:
            self.on()
        else:
            self.off()


class QFixedLabel(QLabel):
    """A QLabel that fixes its width to the initial string"""

    def __init__(self, label, color=None):
        super().__init__(label)

        font = QFont()
        font.setPointSize(18)
        font.setBold(False)
        self.setFont(font)

        fm = QFontMetrics(self.font())
        self.setFixedWidth(fm.width(self.text()))

        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if color is not None:
            self.setStyleSheet(
                f"color: white;background-color:{color}; padding: 5px;border: 1px solid black;"
            )


class FigureTab(QWidget):
    """A single matplotlib figure"""

    def __init__(self, parent=None, active=True):
        super().__init__()

        self.normalize = False
        self.autoscale = True

        self.fig, self.axes = plt.subplots()
        self.plot = FigureCanvas(self.fig)
        self.plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.nav = NavigationToolbar(self.plot, self)
        self.nav.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # custom toolbar
        self.controls = QHBoxLayout()
        self.normalizebutton = QPushButton("normalize")
        self.normalizebutton.clicked.connect(self.toggle_normalize)
        self.normalizebutton.setCheckable(True)
        self.autoscalebutton = QPushButton("autoscale")
        self.autoscalebutton.clicked.connect(self.toggle_autoscale)
        self.autoscalebutton.setCheckable(True)
        self.autoscalebutton.setChecked(True)
        self.controls.addWidget(self.normalizebutton)
        self.controls.addWidget(self.autoscalebutton)
        self.controls.addStretch(1)

        self.vbox = QVBoxLayout()
        self.vbox.addLayout(self.controls)
        self.vbox.addWidget(self.nav)
        self.vbox.addWidget(self.plot)
        self.vbox.addSpacing(50)

        self.setLayout(self.vbox)

        self.elements_and_name = []
        self.data = defaultdict(deque)

        self.interval = 1000
        self.active = active

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.add_data)

        # always get data
        if self.active:
            self.timer.start(self.interval)

    def add_element(self, element, name):
        self.elements_and_name.append((element, name))

    def add_data(self):
        t = time.time()
        for e, n in self.elements_and_name:
            self.data[n].append([t, getattr(e, n)])

        # only save the last 10000 data points
        for k, v in self.data.items():
            while len(v) > 10000:
                v.popleft()

    def toggle_autoscale(self):
        self.autoscale = not self.autoscale

    def toggle_normalize(self):
        self.normalize = not self.normalize

    def update(self):
        xleft, xright = self.axes.get_xlim()
        ybottom, ytop = self.axes.get_ylim()
        self.axes.clear()
        self.axes.set_xlabel("Time")
        for k, v in self.data.items():
            myX = np.array([x[0] for x in v])
            myY = np.array([x[1] for x in v])
            if self.normalize and len(myY) and myY.max() > 0:
                myY = myY / myY.max()
            self.axes.plot_date(
                epoch2num(myX), myY, "o-", label=k, tz="America/Los_Angeles"
            )
        self.axes.legend(loc="best")
        if not self.autoscale:
            self.axes.set_xlim([xleft, xright])
            self.axes.set_ylim([ybottom, ytop])
        self.plot.draw()


class RunFunctionsThread(QThread):
    """Call a bunch of function to read data every <timeout> milliseconds"""

    def __init__(self, functions):
        super().__init__()
        self.functions = functions
        self.keep_running = True
        self.pause = False
        self.timeout = 1000  # ms

    def __del__(self):
        self.wait()

    def addfunction(self, f):
        self.functions.append(f)

    def removefunction(self, f):
        self.functions.remove(f)

    def mystop(self):
        self.keep_running = False

    def start_pause(self):
        self.pause = True

    def stop_pause(self):
        self.pause = False

    def run(self):
        while self.keep_running:
            if not self.pause:
                for f in self.functions:
                    f()
            self.msleep(self.timeout)


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
