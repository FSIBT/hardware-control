"""
This is the Base class for reading modules
it provides a simple UI.
"""
import logging

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLabel, QWidget, QGridLayout, QLCDNumber, QGroupBox


logger = logging.getLogger(__name__)


class Read(QGroupBox):
    """A simple UI for read-only modules"""

    def __init__(
        self,
        app,
        instrument,
        channels: list,  # just a list of numbers
        channelNames: list,  # and their names
        readCommand: str,  # command for reading e.g. TEMP / VOLT / CURR
        unit: str = "Units",
        name: str = "Read Module",
        showLCD=True,
    ):
        # initalizing
        super().__init__(app, name, instrument)

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
                SingleChannelRead(
                    self, c, self.channelNames[i], self.readCommand, self.unit
                )
            )
            self.grid.addWidget(self.listOfWidgets[i], 0, i)
        # Add all the widgets to layout
        self.setLayout(self.grid)

        ### add your specific settings - there are none
        # self.settings[""] = None

        # Write state to Backend
        # this sends all settings, which are stored in the settings dictionary to the backend
        self.send_state()

    def init_values(self):

        logger.info("Init values not implimented in Read")

    def settings_to_UI(self):

        pass


class SingleChannelRead(QWidget):
    """A single Temperature LCD Widget, with a channelnumber and name."""

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

    def update_readout(self):
        """Send a command for all the used channels."""
        # for i, c in enumerate(self.mainWindow.channels):
        self.mainWindow.command(f"CH{self.channelNumber}_TEMP?")
        mess = self.mainWindow.values.get(f"CH{self.channelNumber}_TEMP")
        if mess:  # only write to UI if message not None
            # show 00023.7632 as 23.7 and include signs correctly
            mess = float(mess[0] + mess[2:7])
            if self.mainWindow.showLCD:
                # write to actual widget/channel
                self.lcd.display(mess)
            else:
                self.name.setText(f"{self.channelName} ({self.unit}) : {mess}")
