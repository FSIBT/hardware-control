from PyQt5 import QtCore
from PyQt5.QtWidgets import QPushButton, QLabel, QGridLayout, QComboBox

from hardware_control.base import HC_Instrument


class HC_MacroRunnerTool(HC_Instrument):
    """A tool which allows the user to run macros from the main UI.
    'Buttons' specifies which buttons to add. value for dictionary is button label.
     Options include:
     1.) name of any macro, 2.) 'Dynamic', which gives one button with a dropdown
    letting the user pick whihc macro the button triggers.

    'Indicators' specifies which indicators are available to add to the widget.
    Options must be in dictionary, s.t. option is the key name, and it specifies
    a string value for the option. Options include:
     1.) 'Label' adds a plain text label, 2.) 'Light', which adds
    a tri-color light with values 'green', 'grey', 'red', and 3.) 'ProgBar' which
    adds a progress bar and takes a value between 0 and 100 for a value."""

    def __init__(
        self,
        window,
        debug: bool = False,
        name: str = "Macro Runner",
        buttons={"Dynamic": "Run Macro"},
        indicators={},
    ):

        super().__init__(window, name)
        self.debug = debug
        self.pDebug("")
        self.buttons = buttons
        self.indicators = indicators

        self.settings = {}
        self.name = name
        self.app = window.app
        self.ignore = True

        # *************************Create GUI************************

        self.button_panel = QGridLayout()
        allow_dynamic = True
        for idx, but in enumerate(self.buttons):  # Requests dynamic...

            if but == "Dynamic":

                # Prevent duplicate dynamic boxes
                allow_dynamic = False

                # Create macro selection dropdown label
                macro_drop_label = QLabel("Macro:")
                # macro_drop_label.setPixmap(QPixmap(pkg_resources.resource_filename("hardware_control", "ScanTool/graphics/arrow.png")))
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
                # run_button.setIcon(QIcon((QPixmap(pkg_resources.resource_filename("hardware_control", "ScanTool/graphics/scan.png")))))
                run_button.setCheckable(False)
                run_button.clicked.connect(
                    lambda: self.run_macro(self.macro_drop.currentText())
                )

                self.button_panel.addWidget(run_button, idx, 0)
                self.button_panel.addWidget(macro_drop_label, idx, 1)
                self.button_panel.addWidget(self.macro_drop, idx, 2)

            elif but in [
                x for x in self.window.app.macros
            ]:  # But is a valid macro name....

                run_button = QPushButton()
                run_button.setText(self.buttons[but])
                # run_button.setIcon(QIcon((QPixmap(pkg_resources.resource_filename("hardware_control", "ScanTool/graphics/scan.png")))))
                run_button.setCheckable(False)
                run_button.clicked.connect(lambda: self.run_macro(but))

                self.button_panel.addWidget(run_button, idx, 0)

            else:

                self.pDebug("Sry, not a thing!")
                self.window.app.add_log(
                    self.name,
                    "NO-HARDWARE-BACKEND",
                    "WARNING",
                    f"Macro '{but}' does not exist. Ignoring button.",
                )

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.button_panel, 0, 0)
        # self.master_layout.addLayout(self.middle_grid, 1, 0, 1, 2)
        # self.master_layout.addLayout(self.progress_grid, 2, 0, 1, 3)
        # self.master_layout.addWidget(self.scan_button, 3, 0)
        self.setLayout(self.master_layout)

    def run_macro(self, macro: str):
        try:
            cmds = self.app.macros[macro]
            self.pDebug(f"Running macro: {macro}\n\tCommands: {cmds}")
            self.app.run_macro(cmds)
        except Exception:
            self.pDebug(f"An exception occurred running macro {macro}")

    def set_macro(self, m: str):
        self.pDebug(f"Setting macro to {m}")
        self.settings["macro"] = m

    def update_macros(self):
        self.macro_drop.clear()
        names = []
        for m in self.app.macros:
            names.append(m)
            self.pDebug(f"Adding macro {m}")
        self.macro_drop.addItems(names)

    #
    # Create a default state object if can't get state from a file
    #
    def default_state(self):

        dflt = {}

        dflt["macro"] = "----------"
        dflt["progress"] = 0

        return dflt
