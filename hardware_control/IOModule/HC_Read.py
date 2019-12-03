"""
This is the Base class for reading modules
it provides a simple UI.
"""
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLabel, QWidget, QGridLayout, QLCDNumber

from hardware_control.base import HC_Instrument, HC_Comm


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
        initialize_with: str = "INSTRUMENT",
        save_on_close: str = False,
    ):
        # initalizing
        super().__init__(window, name)

        self.settings = (
            {}
        )  # A dict to store all possible settings-Not used here,bc there are no settings
        self.save_on_close = save_on_close
        self.backend = backend
        self.comm = HC_Comm(backend, self)
        # self.filename = ""

        self.channels = channels
        self.channelNames = channelNames
        self.readCommand = readCommand
        self.unit = unit

        if self.channels.__len__() == 0 or self.readCommand.__len__() != 4:
            raise Exception("Wrong Arguments")

        ###creating UI
        self.grid = QGridLayout()
        self.listOfWidgets = []
        # add all the needed channels
        for i, c in enumerate(self.channels):
            self.listOfWidgets.append(
                HC_singleChannelADAM(
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


# ToDo add connect and stuff here
class HC_singleChannelADAM(QWidget):
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
        self.name = QLabel()
        self.name.setText(channelName + " " + unit)

        self.lcd = QLCDNumber()
        self.lcd.setSmallDecimalPoint(True)

        self.subLayout = QGridLayout()
        self.subLayout.addWidget(self.name, 0, 0)
        self.subLayout.addWidget(self.lcd, 0, 1)

        self.setMaximumHeight(80)

        self.setLayout(self.subLayout)

    # Updates the readout --moved from main class
    def update_readout(self):
        # Send a command for all the used channels
        # for i, c in enumerate(self.mainWindow.channels):
        self.mainWindow.command(
            "CH" + str(self.channelNumber) + "_TEMP?"
        )  # send request to backend
        mess = self.mainWindow.read_message(
            "CH" + str(self.channelNumber) + "_TEMP"
        )  # check for awnsers
        if mess:  # only write to UI if message not None
            mess = float(
                mess[0] + mess[2:7]
            )  # with that 00023.7632 is shown as 23.7 and signs are taken care of
            print(str(mess) + " " + self.channelName)
            self.lcd.display(mess)  # write to actual widget/channel
