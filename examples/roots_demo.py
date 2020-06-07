#!/usr/bin/env python3
"""hardware_control-control to control the hardware_control test stand

Usage:
  hardware_control-control [--dummy] [--no-HV-limit] [--set-voltage <kV>]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand

  --no-HV-limit        don't restrict HV power supply to 40 kV min
  --set-voltage <kV>   initial setpoint for the HV [default: 0]
"""

# standardlib
import datetime
import faulthandler
import sys
import time
from pathlib import Path

import appdirs
import matplotlib.pyplot as plt
import numpy as np
import pyvisa
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QIntValidator
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QSizePolicy,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QCheckBox,
    QMessageBox,
    QWidget,
    QLineEdit,
    QPushButton,
    QAction,
    QGridLayout,
)

# third party
from docopt import docopt
from hardware_control.Adam.QAdam import AdamControl
from hardware_control.CAEN.QCAEN_channel import CAENControl, CAENcommunication
from hardware_control.Keysight.QKeysight import KeysightControl
from hardware_control.Logfile.plot_logfile import LogPlot
from hardware_control.STM_motor.QSTM_motor import QSTM_control
from hardware_control.STM_motor.control import STM
from hardware_control.Sairem.QSairem import SairemControl
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

# our own module
import hardware_control
from hardware_control.base import FigureTab, RunFunctionsThread, LoggerThread

faulthandler.enable()

commands = docopt(__doc__)
dummy = commands["--dummy"]
HVLIMIT = commands["--no-HV-limit"]
HVSETPOINT = float(commands["--set-voltage"])

dirs = appdirs.AppDirs("hardware_control")
appname = "HC_control"
appauthor = "hardware_control"
CACHEDIR = Path(appdirs.user_cache_dir(appname, appauthor)) / "tabs"
if not CACHEDIR.is_dir():
    CACHEDIR.mkdir(parents=True)


class motorControls(QHBoxLayout):
    def __init__(self):
        super().__init__()

        self.motor1_buttons = QSTM_control()
        self.motor2_buttons = QSTM_control()

        self.addLayout(self.motor1_buttons)
        self.addLayout(self.motor2_buttons)


class motorTab(QWidget):
    def __init__(self):
        super().__init__()

        self.fig, self.axes = plt.subplots(2, 2)
        self.fig.tight_layout()
        self.fig.set_figheight(6)
        self.plot = FigureCanvas(self.fig)
        self.plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.nav = NavigationToolbar(self.plot, self)
        self.nav.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.vboxPlot = QVBoxLayout()
        self.vboxPlot.addWidget(self.nav)
        self.vboxPlot.addWidget(self.plot)
        self.vboxPlot.addSpacing(50)

        self.start = QPushButton("START SCAN")
        self.start.setStyleSheet("background-color: cyan")

        self.labelMotor1 = QLabel("MOTOR 1:  ")
        self.labelStart1 = QLabel("Start")
        self.labelStop1 = QLabel("Stop")
        self.labelStep1 = QLabel("Step")
        self.inputStart1 = QLineEdit()
        self.inputStart1.setText("0")
        self.inputStop1 = QLineEdit()
        self.inputStop1.setText("0")
        self.inputStep1 = QLineEdit()
        self.inputStep1.setText("1")
        self.inputStart1.setValidator(QIntValidator(0, 2500))
        self.inputStop1.setValidator(QIntValidator(0, 2500))

        self.labelMotor2 = QLabel("MOTOR 2:  ")
        self.labelStart2 = QLabel("Start")
        self.labelStop2 = QLabel("Stop")
        self.labelStep2 = QLabel("Step")
        self.inputStart2 = QLineEdit()
        self.inputStart2.setText("0")
        self.inputStop2 = QLineEdit()
        self.inputStop2.setText("0")
        self.inputStep2 = QLineEdit()
        self.inputStep2.setText("1")
        self.inputStart2.setValidator(QIntValidator(0, 9999))
        self.inputStop2.setValidator(QIntValidator(0, 9999))

        self.grid = QGridLayout()
        self.grid.addWidget(self.labelMotor1, 1, 1)
        self.grid.addWidget(self.labelStart1, 2, 1)
        self.grid.addWidget(self.inputStart1, 2, 2, 1, 4)
        self.grid.addWidget(self.labelStop1, 3, 1)
        self.grid.addWidget(self.inputStop1, 3, 2, 1, 4)
        self.grid.addWidget(self.labelStep1, 4, 1)
        self.grid.addWidget(self.inputStep1, 4, 2, 1, 4)

        self.grid.addWidget(self.labelMotor2, 1, 6)
        self.grid.addWidget(self.labelStart2, 2, 6)
        self.grid.addWidget(self.inputStart2, 2, 7, 1, 4)
        self.grid.addWidget(self.labelStop2, 3, 6)
        self.grid.addWidget(self.inputStop2, 3, 7, 1, 4)
        self.grid.addWidget(self.labelStep2, 4, 6)
        self.grid.addWidget(self.inputStep2, 4, 7, 1, 4)

        self.grid.addWidget(self.start, 6, 5, 1, 2)

        self.vbox = QVBoxLayout()
        self.vbox.addLayout(self.vboxPlot)
        self.vbox.addLayout(self.grid)
        self.vbox.addSpacing(50)
        self.setLayout(self.vbox)


class InterlockTab(QWidget):
    def __init__(self, main):
        self.main = main
        super().__init__()

        self.bypass_target_HV = False
        self.HV_reason = []
        self.i = 0  # a counter for the update function

        self.vbox = QVBoxLayout()
        self.HV = QLabel("HV not-interlocked")
        self.target_bypass = QCheckBox("Target-HV bypass")
        self.vbox.addWidget(self.target_bypass)
        self.vbox.addWidget(self.HV)
        self.setLayout(self.vbox)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        # check every 100 ms
        self.timer.start(100)

    def update(self):
        """Check for interlocks

        This function should be fast and most functions should be no-ops if nothing has changed
        """
        self.i += 1

        self.bypass_target_HV = self.target_bypass.checkState()
        if self.bypass_target_HV:
            self.main.adam.set_interlock(False)
            if "Bypass" not in self.HV_reason:
                self.HV_reason.append("Bypass")
        else:
            if "Bypass" in self.HV_reason:
                self.HV_reason.remove("Bypass")
            if float(self.main.caen_channels["Target"].voltage) < 300:
                self.main.adam.set_interlock(True)
                if "Target not biased above 300 V" not in self.HV_reason:
                    self.HV_reason.append("Target not biased above 300 V")
            else:
                self.main.adam.set_interlock(False)
                if "Target not biased above 300 V" in self.HV_reason:
                    self.HV_reason.remove("Target not biased above 300 V")

        if self.i % 20 == 0:
            self.i = 0
            if self.HV_reason:
                reasons = ", ".join(self.HV_reason)
                self.HV.setText(f"HV interlocked: {reasons}")
            else:
                self.HV.setText(f"HV not interlocked")


class App(QMainWindow):
    """The main window"""

    prepare_shutdown = pyqtSignal()

    def __init__(self, dummy=False, app=None):
        super().__init__()
        self.app = app
        self.scan_time = 2  # seconds

        # set up the window
        self.dummy = dummy

        self.setWindowTitle("hardware_control Controls")
        if hasattr(QtCore.Qt, "AA_UseHighDpiPixmaps"):
            font = self.font()
            font.setPointSize(2 * font.pointSize())
            self.setFont(font)

        # file menue
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")
        self.tab_menu = self.menu.addMenu("Tabs")
        self.help_menu = self.menu.addMenu("Help")

        if sys.platform == "win32":
            QIcon.setThemeSearchPaths([r"c:\Program Files\Git\usr\share\icons"])
        QIcon.setThemeName("Adwaita")

        quitButton = QAction(QIcon.fromTheme("application-exit"), "Exit", self)
        quitButton.setShortcut("Ctrl+Q")
        quitButton.setStatusTip("Quit")
        quitButton.triggered.connect(self.close)
        self.file_menu.addAction(quitButton)

        aboutButton = QAction(QIcon.fromTheme("help-about"), "About", self)
        aboutButton.setStatusTip("About")
        aboutButton.triggered.connect(self.about)
        self.help_menu.addAction(aboutButton)

        self.main_widget = QWidget(self)
        self.main_window = QVBoxLayout()

        self.statusbar = QHBoxLayout()
        self.motorcontrols = motorControls()
        self.statusbar.addLayout(self.motorcontrols)
        self.main_window.addLayout(self.statusbar)

        self.tabs = QtWidgets.QTabWidget()

        self.main_window.addWidget(self.tabs)

        self.rm = pyvisa.ResourceManager()
        self.keysight = KeysightControl(self, rm=self.rm, dummy=dummy)

        self.caen_comm = CAENcommunication(dummy, parent=self)

        self.caen_channels = {}
        channels = {0: "NaI", 1: "LaBr", 2: "YAP", 3: "EJ", 4: "UCB", 5: "Target"}
        for i, c in channels.items():
            self.caen_comm.channels[c] = i
            self.caen_channels[c] = CAENControl(i, c, self.caen_comm, dummy)
            self.caen_comm.GUIs[c] = self.caen_channels[c]
        self.caen_comm.connect()
        self.prepare_shutdown.connect(self.caen_comm.stop_thread)
        self.caen_thread = QThread()
        self.caen_comm.moveToThread(self.caen_thread)
        self.caen_thread.start()

        # in V and uA
        max_voltages_currents = {
            "NaI": [2000, 300],
            "LaBr": [1000, 300],
            "YAP": [1100, 300],
            "EJ": [1705, 300],
            "UCB": [2000, 300],
            "Target": [500, 800],
        }
        for c, [maxV, maxI] in max_voltages_currents.items():
            self.caen_channels[c].set_maxV(maxV)
            self.caen_channels[c].set_maxI(maxI)

        # hvlimit ensures that we don't put a voltage between 0-40kV on
        # the system (can be bypassed with command line option)
        self.adam = AdamControl(
            IP="192.168.0.5", dummy=dummy, hvlimit=HVLIMIT, parent=self
        )
        self.adam.voltage_setpoint = HVSETPOINT

        self.sairem = SairemControl(dummy=dummy, parent=self)
        self.sairem.write_value.emit("reflected_power", 100)

        # not sure if we want to have all of these in the same thread
        self.getmydata = RunFunctionsThread([self.keysight.read])
        self.getmydata.start()

        self.logger = LoggerThread(
            datadir=(hardware_control.helper.get_data_dir() / "XIA-pulse-shape"),
            dummy=dummy,
        )
        self.logger.addelement(self.keysight)
        self.logger.addelement(self.adam)
        self.logger.addelement(self.caen_channels["NaI"])
        self.logger.addelement(self.caen_channels["LaBr"])
        self.logger.addelement(self.caen_channels["YAP"])
        self.logger.addelement(self.caen_channels["EJ"])
        self.logger.addelement(self.caen_channels["UCB"])
        self.logger.addelement(self.caen_channels["Target"])
        self.logger.addelement(self.sairem)
        self.logger.start()

        self.plot = FigureTab()
        self.plot.add_element(self.keysight.CH1, "current")
        self.plot.add_element(self.adam, "pressure")
        self.plot.add_element(self.sairem, "reflected")

        self.plotHV = FigureTab()
        self.plotHV.add_element(self.adam, "current")
        self.plotHV.add_element(self.adam, "voltage")

        self.controller = QWidget()
        self.controllervbox = QVBoxLayout()
        self.grid = QGridLayout()
        self.grid.addWidget(self.keysight, 0, 0)
        self.grid.addWidget(self.adam, 1, 0)
        self.grid.addWidget(self.sairem, 2, 0)
        self.grid.addWidget(self.caen_channels["NaI"], 0, 1)
        self.grid.addWidget(self.caen_channels["LaBr"], 0, 2)
        self.grid.addWidget(self.caen_channels["YAP"], 1, 1)
        self.grid.addWidget(self.caen_channels["EJ"], 1, 2)
        self.grid.addWidget(self.caen_channels["UCB"], 2, 1)
        self.grid.addWidget(self.caen_channels["Target"], 2, 2)
        self.controllervbox.addLayout(self.grid)
        self.controllervbox.addStretch(1)
        self.controller.setLayout(self.controllervbox)

        self.motor = motorTab()
        self.logfiler = LogPlot()
        self.interlock = InterlockTab(self)

        self.motor1 = STM("192.168.0.80", 55061, dummy=self.dummy)
        self.motor1.rotation_per_digit = 220  # seems to work better
        if self.motor1.online:
            # we also set the default motor speed in control.py for
            # the motor, but this command only gets executed when the
            # motor is on from the beginning! Needs to be fixed
            self.motor1.set_speed(rev_per_sec=0.5)

        self.motor2 = STM("192.168.0.90", 55062, dummy=self.dummy)
        if self.motor1.online:
            self.motor2.set_speed(rev_per_sec=0.5)

        # at the moment we don't have a Qwidget for the motors, so
        # they need their own timer to try to reconnect
        self.motor_timer = QtCore.QTimer(self)
        self.motor_timer.timeout.connect(self.motor1.try_connect)
        self.motor_timer.timeout.connect(self.motor2.try_connect)
        self.motor_timer.start(1000)

        self.motorcontrols.motor1_buttons.link(self.motor1)
        self.motorcontrols.motor2_buttons.link(self.motor2)

        self.motor.start.clicked.connect(self.motorscan)

        self.tabs.addTab(self.controller, "Controls")
        self.tabs.addTab(self.plot, "Getter Plot")
        self.tabs.addTab(self.plotHV, "HV Plot")
        self.tabs.addTab(self.motor, "Motor")
        self.tabs.addTab(self.logfiler, "Logfile")
        self.tabs.addTab(self.interlock, "Interlock")

        self.tabs.currentChanged.connect(self.tabchanged)

        self.main_widget.setLayout(self.main_window)
        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        self.timer = QtCore.QTimer(self)

        self.show()

    def motor_to_start(self, motor, startposition):
        diff = int(startposition - motor.position)
        # go to start position
        motor.step(diff * self.motor1.rotation_per_digit)
        motor.position += diff

    def motorscan(self):
        m1start = int(self.motor.inputStart1.text())
        m1stop = int(self.motor.inputStop1.text())
        m1step = int(self.motor.inputStep1.text())
        out = []
        starttime = time.time()
        # go to start position
        dx1 = m1step * self.motor1.rotation_per_digit
        diff1 = int(m1stop - m1start)
        if diff1 < 0:
            dx1 = -dx1
        self.motor_to_start(
            self.motor1, startposition=int(self.motor.inputStart1.text())
        )

        m2start = int(self.motor.inputStart2.text())
        m2stop = int(self.motor.inputStop2.text())
        m2step = int(self.motor.inputStep2.text())
        dx2 = m2step * self.motor2.rotation_per_digit
        self.m3step = 10
        diff2 = int(m2stop - m2start)
        if diff2 < 0:
            dx2 = -dx2
        self.motor2ToStart()
        self.motor_to_start(
            self.motor2, startposition=int(self.motor.inputStart2.text())
        )
        i_max = abs(int(diff1 / m1step))
        j_max = abs(int(diff2 / m2step))

        forward_data = np.zeros((i_max, j_max))
        reflected_data = np.zeros((i_max, j_max))
        pressure_data = np.zeros((i_max, j_max))
        current_data = np.zeros((i_max, j_max))

        for i in range(i_max):
            self.motor1.step(dx1)
            time.sleep(dx1 / 10000)

            for j in range(j_max):
                self.motor2.step(dx2)
                time.sleep(dx2 / 10000 + self.scan_time)

                forward = self.sairem.forward
                reflected = self.sairem.reflected
                pressure = self.adam.pressure
                current = self.adam.current
                out.append([forward, reflected, pressure, current, i, j])

                forward_data[i, j] = forward
                reflected_data[i, j] = reflected
                pressure_data[i, j] = pressure
                current_data[i, j] = current

                for ax, data, title in zip(
                    self.motor.axes.flatten(),
                    [current_data, pressure_data, reflected_data, forward_data],
                    ["Current", "Pressure", "Reflected Power", "Forward Power"],
                ):
                    ax.clear()
                    ax.imshow(data, origin="lower", cmap="jet")
                    ax.set_ylabel("Motor 1")
                    ax.set_xlabel("Motor 2")
                    ax.set_title(title)
                    ax.text(
                        j,
                        i,
                        "{:.2e}".format(data[i, j]),
                        ha="center",
                        va="center",
                        color="w",
                    )

                self.motor.plot.draw()
                # need to process some events from the main loop to execute the draw() command
                app.processEvents()
            self.motor2.step(-dx2 * j_max)
            time.sleep(2 * dx2 * j_max / 20000)
        self.motor1.position += diff1
        self.motor2.position += diff2

        t = datetime.datetime.today().strftime("%Y-%m-%d-%H-%M")
        np.savetxt(f"scanResults-{t}.txt", out)

        stoptime = time.time() - starttime
        print("End of motorscan, pos2 = " + str(self.motor2.position))
        print("Time elapsed: ", stoptime)

    def tabchanged(self, i):
        self.timer.stop()
        try:
            self.timer.timeout.disconnect()
        except TypeError:
            pass

        if self.tabs.tabText(i) == "Getter Plot":
            self.timer.timeout.connect(self.plot.update)
            self.plot.update()
            self.timer.start(1000)
        elif self.tabs.tabText(i) == "HV Plot":
            self.timer.timeout.connect(self.plotHV.update)
            self.plotHV.update()
            self.timer.start(1000)

    def close_connections(self):
        # send signal to threads
        self.prepare_shutdown.emit()

        # stop threads
        self.logger.mystop()
        self.logger.wait()
        # close instruments
        self.motor1.close()
        self.motor2.close()
        self.adam.comm_thread.quit()
        self.adam.comm.instrument.close()
        self.sairem.comm_thread.quit()
        self.sairem.comm.instrument.close()
        self.caen_thread.quit()
        self.caen_comm.instrument.close()
        self.caen_comm.rm.close()
        self.keysight.close()
        self.rm.close()
        # done
        print("Good Bye!")

    def about(self):
        pyversion = ".".join([str(i) for i in sys.version_info])
        QMessageBox.about(
            self,
            "About",
            "hardware control\n\n"
            + f"python-version: {pyversion}\n"
            + f"hardware_control-version: {hardware_control.__version__}",
        )


if __name__ == "__main__":
    app = QApplication([])
    ex = App(dummy, app)
    app.aboutToQuit.connect(ex.close_connections)
    sys.exit(app.exec_())

# Local Variables:
# mode: python
# coding: utf-8
# End:
