from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QPushButton, QLabel, QGridLayout, QComboBox, QLCDNumber

from hardware_control.base import HC_Instrument
import logging

logger = logging.getLogger(__name__)


class HC_MacroRunnerTool(HC_Instrument):
    """A tool which allows the user to run macros from the main UI.
    'Buttons' specifies which buttons to add. value for dictionary is button label.
     Options include:
     1.) name of any macro, 2.) 'Dynamic', which gives one button with a dropdown
    letting the user pick whihc macro the button triggers.

    'Indicators' specifies which indicators are available to add to the widget.
    Options must be in dictionary, s.t. option is the key name, and it specifies
    a string value for the option. Options include:
    1.) name of any application variable (value is populates a label describing
    the application variable's value)

     1.) 'Label' adds a plain text label, 2.) 'Light', which adds
    a tri-color light with values 'green', 'grey', 'red', and 3.) 'ProgBar' which
    adds a progress bar and takes a value between 0 and 100 for a value.

    Add countdown lets the user add an optional countdown timer which can be
    started with the start_countdown() function and calls the callback
    countdown_end when it reaches zero.
    """

    def __init__(
        self,
        window,
        name: str = "Macro Runner",
        buttons={"Dynamic": "Run Macro"},
        indicators={},
        add_countdown=False,
    ):

        super().__init__(window, name)
        self.buttons = buttons
        self.indicators = indicators

        self.settings = {}
        self.name = name
        self.app = window.app
        self.ignore = True
        self.label_widgets = {}

        self.countdown_end = None
        self.add_countdown = add_countdown
        self.countdown_val = 0

        # *************************Create GUI************************

        self.button_panel = QGridLayout()
        allow_dynamic = True
        self.button_widgets = []
        for idx, but in enumerate(self.buttons):  # Requests dynamic...

            if but == "Dynamic":

                # Prevent duplicate dynamic boxes
                allow_dynamic = False

                # Create macro selection dropdown label
                macro_drop_label = QLabel("Macro:")
                # macro_drop_label.setPixmap(QPixmap(pkg_resources.resource_filename("hardware_control", "ScanTool/icons/arrow.png")))
                macro_drop_label.setAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

                # Create macro selection dropdown
                self.macro_drop = QComboBox()
                self.macro_drop.addItems(["----------"])
                # macro_drop.setCurrentText(self.settings["parameter"])
                self.macro_drop.currentIndexChanged.connect(
                    lambda: self.set_macro(self.macro_drop.currentText())
                )

                run_button = QPushButton()
                run_button.setText(self.buttons[but])
                # run_button.setIcon(QIcon((QPixmap(pkg_resources.resource_filename("hardware_control", "ScanTool/icons/scan.png")))))
                run_button.setCheckable(False)
                run_button.clicked.connect(
                    lambda: self.run_macro(self.macro_drop.currentText())
                )
                self.button_widgets.append(run_button)

                self.button_panel.addWidget(run_button, idx, 0)
                self.button_panel.addWidget(macro_drop_label, idx, 1)
                self.button_panel.addWidget(self.macro_drop, idx, 2)

            # But is a valid macro name....
            elif but in [x for x in self.window.app.macros]:

                run_button = QPushButton()
                run_button.setText(self.buttons[but])
                # run_button.setIcon(QIcon((QPixmap(pkg_resources.resource_filename("hardware_control", "ScanTool/icons/scan.png")))))
                run_button.setCheckable(False)
                run_button.clicked.connect(lambda: self.run_macro(but))
                self.button_widgets.append(run_button)

                self.button_panel.addWidget(run_button, idx, 0)

            else:

                logger.error(f"Macro {but} does not exist. Ignoring button.")

        for idx, ind in enumerate(self.indicators):  # Requests dynamic...

            if ind in [x for x in self.window.app.variables]:

                # Create macro selection dropdown label
                ind_desc_label = QLabel(self.indicators[ind])
                ind_desc_label.setAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

                self.label_widgets[ind] = QLabel(self.window.app.variables[ind])
                self.label_widgets[ind].setAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

                self.button_panel.addWidget(ind_desc_label, idx + len(self.buttons), 0)
                self.button_panel.addWidget(
                    self.label_widgets[ind], idx + len(self.buttons), 1
                )

            else:

                logger.error(
                    f"Application variable {ind} does not exist. Ignoring indicator."
                )

        if add_countdown:
            self.countdown_wdgt = QLCDNumber()
            self.countdown_wdgt.setSmallDecimalPoint(True)
            self.countdown_wdgt.display(0)

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.button_panel, 0, 0)
        if add_countdown:
            self.master_layout.addWidget(self.countdown_wdgt, 0, 1)

        # self.master_layout.addLayout(self.progress_grid, 2, 0, 1, 3)
        # self.master_layout.addWidget(self.scan_button, 3, 0)
        self.setLayout(self.master_layout)

        if add_countdown:
            self.countdown_timer = QTimer()
            self.countdown_timer.timeout.connect(self.update_countdown)

    def update_countdown(self):

        self.countdown_val -= 0.1

        if self.countdown_val <= 0:
            self.countdown_val = 0
            self.countdown_timer.stop()

            if self.countdown_end is not None and callable(self.countdown_end):
                self.countdown_end(self)

        self.set_timer_readout(self.countdown_val)

    def set_timer_readout(self, val: float):

        if self.add_countdown:
            try:
                self.countdown_wdgt.display(val)
            except:
                logger.error(f"Failed to display {val} as number on countdown")
                self.countdown_wdgt.display(-1)

    def start_countdown(self, t_start: float):

        print("Start timer")

        self.set_timer_readout(t_start)

        self.countdown_val = t_start

        self.countdown_timer.start(100)

    def run_macro(self, macro: str):
        try:
            cmds = self.app.macros[macro]
            logger.info(f"Running macro: {macro}\n\tCommands: {cmds}")
            self.app.run_macro(cmds)
        except Exception:
            logger.error(f"An exception occurred running macro {macro}", exc_info=True)

    def set_macro(self, m: str):
        logger.debug(f"Setting macro to {m}")
        self.settings["macro"] = m

    def update_macros(self):

        try:

            self.macro_drop.clear()
            names = []
            for m in self.app.macros:
                names.append(m)
                logger.debug(f"Adding macro {m}")
            self.macro_drop.addItems(names)

        except:
            pass  # no macros to update

    def update_indicators(self):

        for idx, ind in enumerate(self.indicators):  # Requests dynamic...

            if ind in [x for x in self.window.app.variables]:

                # Create macro selection dropdown label
                self.label_widgets[ind].setText(self.window.app.variables[ind])

            else:

                logger.error(f"Macro {but} does not exist. Ignoring indicator.")

    #
    # Create a default state object if can't get state from a file
    #
    def default_state(self):

        dflt = {}

        dflt["macro"] = "----------"
        dflt["progress"] = 0

        return dflt
