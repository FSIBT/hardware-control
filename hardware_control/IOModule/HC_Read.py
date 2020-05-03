"""
This is the Base class for reading modules
it provides a simple UI.
"""
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLabel, QWidget, QGridLayout, QLCDNumber, QSpacerItem

from hardware_control.base import HC_Instrument, HC_Comm
import logging

logger = logging.getLogger(__name__)


class HC_Read(HC_Instrument):
    # Convention: __init__(self, backend, window . . . )
    def __init__(
        self,
        backend,
        window,
        channels: list,  # just a list of numbers
        channelNames: list,  # and their names
        readCommand: str,  # command for reading e.g. TEMP / VOLT / CURR
        unit: str = "Units",
        name: str = "Read Module",
        showLCD=True,
    ):
        # initalizing
        super().__init__(window, name)

        self.settings = (
            {}
        )  # A dict to store all possible settings-Not used here,bc there are no settings
        self.backend = backend
        self.address = backend.connection_addr

        self.backend.dummy = self.window.app.dummy
        if backend in self.window.app.comms:
            self.comm = self.window.app.comms[backend]
            self.comm.addWidget(self)
        else:
            self.window.app.comms[backend] = HC_Comm(backend, self, 2000)
            self.comm = self.window.app.comms[backend]

        # self.filename = ""

        self.channels = channels
        self.channelNames = channelNames
        self.readCommand = readCommand
        self.showLCD = showLCD
        self.unit = unit

        if self.channels.__len__() == 0 or self.readCommand.__len__() != 4:
            raise Exception("Wrong Arguments")

        ###creating UI
        self.grid = QGridLayout()
        self.listOfWidgets = []
        # add all the needed channels
        for i, c in enumerate(self.channels):
            self.listOfWidgets.append(
                HC_singleChannelRead(
                    self, c, self.channelNames[i], self.readCommand, self.unit
                )
            )
            self.grid.addWidget(self.listOfWidgets[i], 0, i)
        # Add all the widgets to layout
        self.setLayout(self.grid)
        ####

        ### add your specific settings - there are none
        # self.settings[""] = None

        # Write state to Backend
        # this sends all settings, which are stored in the settings dictionary to the backend
        self.send_state()


class HC_singleChannelRead(QWidget):
    """A single Temperature LCD Widget, with a channelnumber and name"""

    def __init__(
        self,
        mainWindow,
        channelNumber: int,
        channelName: str,
        readCommand: str,
        unit: str,
    ):
        super().__init__()

        self.channelNumber = channelNumber
        self.channelName = channelName
        self.readCommand = readCommand
        self.unit = unit

        self.mainWindow = mainWindow

        # Create timer to query
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.mainWindow.globalRefreshRate)
        #

        ### Create UI
        self.subLayout = QGridLayout()
        self.name = QLabel()

        if self.mainWindow.showLCD:
            self.lcd = QLCDNumber()
            self.lcd.setSmallDecimalPoint(True)
            self.lcd.setMinimumHeight(self.mainWindow.globalLineHeight)
            self.subLayout.addWidget(self.lcd, 1, 0)

        self.name.setText(channelName + " " + unit)
        self.subLayout.addWidget(self.name, 0, 0)

        self.setMaximumSize(
            self.mainWindow.globalLineWidth, self.mainWindow.globalLineHeight * 3
        )

        self.setLayout(self.subLayout)

    # Updates the readout --moved from main class
    def update_readout(self):
        # Send a command for all the used channels
        # for i, c in enumerate(self.mainWindow.channels):
        self.mainWindow.command(
            "CH" + str(self.channelNumber) + "_TEMP?"
        )  # send request to backend
        mess = self.mainWindow.read_values(
            "CH" + str(self.channelNumber) + "_TEMP"
        )  # check for awnsers
        if mess:  # only write to UI if message not None
            mess = float(
                mess[0] + mess[2:7]
            )  # with that 00023.7632 is shown as 23.7 and signs are taken care of
            if self.mainWindow.showLCD:
                self.lcd.display(mess)  # write to actual widget/channel
            else:
                self.name.setText(f"{self.channelName} ({self.unit}) : {mess}")


# ToDo Max/min Value alert?
