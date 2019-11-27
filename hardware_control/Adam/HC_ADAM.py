from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QLabel,
    QWidget,
    QGridLayout,
    QLCDNumber,
)

from hardware_control.base import HC_Instrument, HC_Comm


class HC_ADAM(HC_Instrument):
    # Convention: __init__(self, backend, window . . . )
    def __init__(
            self,
            backend,
            window,
            channels: list,  # just a list of numbers
            channelNames: list,  # and their names
            name: str = "ADAM-Temperature",
            initialize_with: str = "INSTRUMENT",
            save_on_close: str = False,
    ):
        # initalizing
        super().__init__(window, name)
        self.settings = {}  # A dict to store all possible settings - Not used here, bc there are no settings
        self.save_on_close = save_on_close
        self.backend = backend
        self.comm = HC_Comm(backend, self)
        # self.filename = ""

        self.channels = channels
        self.channelNames = channelNames

        ###creating UI
        self.grid = QGridLayout()
        self.listOfWidgets = []
        # add all the needed channels
        for i, c in enumerate(self.channels):
            self.listOfWidgets.append(HC_singleChannelADAM(c, self.channelNames[i]))
            self.grid.addWidget(self.listOfWidgets[i], 0, i)
        # Add all the widgets to layout
        self.setLayout(self.grid)
        ####

        ### add your specific settings - there are none
        # self.settings[""] = None

        # Create timer to query
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(500)

        # Write state to Backend
        # this sends all settings, which are stored in the settings dictionary to the backend
        self.send_state()

    # Updates the readout
    def update_readout(self):
        # Send a command for all the used channels
        for i, c in enumerate(self.channels):
            self.command("CH" + str(c) + "_TEMP?")      #send request to backend
            mess = self.read_message("CH" + str(c) + "_TEMP")      #check for awnsers
            if mess:    #only write to UI if massige not None
                mess = float(mess[0] + mess[2:7])  # with that 00023.7632 is shown as 23.7 and signs are taken care of
                self.listOfWidgets[i].lcd.display(mess) #write to actual widget/channel

#ToDo add connect and stuff here
class HC_singleChannelADAM(QWidget):
    """A single Temperature LCD Widget, with a channelnumber and name"""

    def __init__(self, channelNumber: int, channelName: str):
        super().__init__()

        self.channelNumber = channelNumber
        self.channelName = channelName

        ### Create UI
        self.name = QLabel()
        self.name.setText(channelName + " (°C):")

        self.lcd = QLCDNumber()
        self.lcd.setSmallDecimalPoint(True)

        self.subLayout = QGridLayout()
        self.subLayout.addWidget(self.name, 0, 0)
        self.subLayout.addWidget(self.lcd, 0, 1)

        self.setMaximumHeight(80)

        self.setLayout(self.subLayout)
