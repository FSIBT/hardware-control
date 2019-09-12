# -*- coding: utf-8 -*-
from collections import defaultdict, deque
import datetime
import pkg_resources
import hashlib
import sys
import time
import pathlib

from PyQt5 import QtCore
from PyQt5.QtCore import QThread, QSize
from PyQt5.QtGui import QIcon, QFont, QFontMetrics
from PyQt5.QtWidgets import (QApplication, QSizePolicy, QPushButton, QLabel, QMessageBox,
                             QHBoxLayout, QVBoxLayout, QWidget, QGroupBox)
from PyQt5.QtSvg import QSvgWidget

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.dates import epoch2num
import numpy as np

class QInstrument(QGroupBox):

    def __init__(self, parent, name:str):
        super().__init__(name)
        self.settings = {}
        self.value = {}
        self.name = name
        self.status = False

        self.parent = parent

        parent.app.add_instrument(self)


class QHardwareApp(QApplication):
    """Subclass of QApplication that is aware of what hardware is connected to it and can log data"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instruments = []

    def add_instrument(self, widget):
        # check if name is already present
        if widget.name in [x.name for x in self.instruments]:
            raise KeyError(f"Intrument name '{widget.name}' is already present")

        self.instruments.append(widget)

    def save_settings(self, filename:str):
        """ Copys the settings dictionaries from each instrument into a new dictionary
        with the instrument's name serving as the key. The dictionary is then saved
        to a JSON file. """
        
        app_settings = {instr.name : instr.settings for instr in self.instruments}

        #Write JSON file
        try:
            with open(filename, 'w') as file:
                json.dump(app_settings, file)
                print(f"settings for {self.comm.instr.ID} saved to file '{filename}'")
        except Exception as e:
            print(f"ERROR: Failed to write file '{filename}'. State not saved.")
            print(f"\t{e}")

    def list_instruments(self):
        if self.instruments:
            print('Known instruments:')
        else:
            print('No instruments known')
        for i in self.instruments:
            print(f'  {i}')

    def check_instruments(self):
        """Make sure all instruments conform to specifications"""
        for i in self.instruments:
            try:
                i.name
            except AttributeError:
                print(f'Error: Instrument  {i} needs a .name')
        
class QOnOff(QPushButton):
    """An On/Off button with a nice icon for on/off

    Takes two functions that will be called when turning on/off
    starts in an unkown state if not defined otherwise

    if f_off is None: assume that f_on is a signal that can emit a boolian.
    """

    def __init__(self, f_on, f_off=None):
        super().__init__()
        self.setCheckable(True)

        self.onText = 'On'
        self.offText = 'Off'
        self.unkownText = 'status unkown'

        self.onIcon = QIcon(pkg_resources.resource_filename('hardware_control', 'icons/button-power-on.svg'))
        self.offIcon = QIcon(pkg_resources.resource_filename('hardware_control', 'icons/button-power-off.svg'))
        self.unkownIcon = QIcon(pkg_resources.resource_filename('hardware_control', 'icons/button-power-unkown.svg'))

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


class QOnOffIndicator(QSvgWidget):
    """An On/Off indicator

    Listens to signals for on/off and shows a green or red light with a tooltip for mouse-over events.

    starts in an unkown state (both lights off)"""

    def __init__(self, name):
        self.name = name
        self.onIcon = pkg_resources.resource_filename('hardware_control', 'icons/on-off-indicator-on.svg')
        self.offIcon = pkg_resources.resource_filename('hardware_control', 'icons/on-off-indicator-off.svg')
        self.unkownIcon = pkg_resources.resource_filename('hardware_control', 'icons/on-off-indicator-unkown.svg')

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
                f'color: white;background-color:{color}; padding: 5px;border: 1px solid black;')


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
        self.normalizebutton = QPushButton('normalize')
        self.normalizebutton.clicked.connect(self.toggle_normalize)
        self.normalizebutton.setCheckable(True)
        self.autoscalebutton = QPushButton('autoscale')
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
        self.axes.set_xlabel('Time')
        for k, v in self.data.items():
            myX = np.array([x[0] for x in v])
            myY = np.array([x[1] for x in v])
            if self.normalize and len(myY) and myY.max() > 0:
                myY = myY/myY.max()
            self.axes.plot_date(epoch2num(myX), myY, "o-",
                                label=k, tz='America/Los_Angeles')
        self.axes.legend(loc='best')
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

    def __init__(self, datadir:pathlib.PosixPath=None, dummy:bool=False):
        """Set up the logfile. Either create it or open for append"""

        super().__init__()
        self.elements = []
        self.keep_running = True
        self.pause = False

        if not datadir or not datadir.is_dir():
            self.keep_running = False
            QMessageBox.about(None, 'Error', f'Cannot find logfile directory {datadir}')

        self.YYYYMMDD = datetime.datetime.today().strftime('%Y-%m-%d')
        logdir = datadir / self.YYYYMMDD
        logdir.mkdir(exist_ok=True, parents=True)
        self.logdir = logdir
        if dummy:
            self.logfilename = logdir / (self.YYYYMMDD+"-dummy.txt")
        else:
            self.logfilename = logdir / (self.YYYYMMDD+".txt")

        # check if we need to write header
        if self.logfilename.exists() and self.logfilename.is_file():
            with self.logfilename.open('r') as f:
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
        self.logfile.write(f'# {self.YYYYMMDD}\n# Logfile from hardware_control run\n')
        datastructure = 'Time[s] ' + ' '.join([e.get_header() for e in self.elements])
        myhash = hashlib.sha256()
        myhash.update(datastructure.encode('utf-8'))
        version = myhash.hexdigest()
        self.logfile.write(f'# Version: {version}\n')
        self.logfile.write(f'{datastructure}\n')  # no '#' so that it is easier for pandas to read

    def run(self):
        # wait a few seconds before starting the log, so that the
        # elements can start collecting data
        time.sleep(5)

        # now open file
        self.logfile = self.logfilename.open('a', buffering=1)

        # add header if file is empty
        if self.oldlength == 0:
            self.write_header()

        while self.keep_running:
            if not self.pause:
                line = f'{time.time()} '
                data = []
                for e in self.elements:
                    data.extend(e.get_values())
                line += ' '.join([str(d) for d in data])
                self.logfile.write(line+'\n')
            self.sleep(1)

        self.logfile.close()
