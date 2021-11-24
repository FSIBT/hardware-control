#!/usr/bin/env python3
"""Create custom hooks.

Usage:
  hooks.py [--dummy] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console
"""
import logging
import sys

from docopt import docopt

from PyQt5.QtWidgets import QGridLayout, QVBoxLayout, QWidget

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("Interactive Python Demo")

        instr1 = hc.instruments.Alicat_M_Series("alicat1", "192.168.0.15")
        instr2 = hc.instruments.Alicat_M_Series("alicat2", "192.168.0.16")

        # one could add hooks also directly at the instrument driver
        # here by using for example: instr1.add_post_hook or
        # instr1.add_pre_hook however, these don't get triggered in
        # "dummy" mode and therefore are not that useful here since
        # examples are probably mostly run directly in dummy mode

        # add both instruments ot the app
        self.app.add_instrument(instr1)
        self.app.add_instrument(instr2)

        self.instr_ctrl1 = hc.gui.FlowController(
            self.app, "alicat1", "Flow Controller A"
        )
        self.instr_ctrl2 = hc.gui.FlowController(
            self.app, "alicat2", "Flow Controller B"
        )

        # hooks in the app only apply to values in app._data they
        # should normally assume that the value is a string create an
        # output hook, that scales the RATE in alicat1 by a factor of
        # 100
        self.app.add_hook(
            "alicat1", "RATE", "post_read_hooks", lambda x: str(100 * float(x))
        )

        # we can also enable and disable other widgets depending on a value
        # here we enable/disable the RATE input for alicat1 depending on the
        # PRESSURE value of alicat2
        self.app.add_hook(
            "alicat2",
            "PRESSURE",
            "post_read_hooks",
            lambda x: self.enable_disable_hook(x),
        )
        # instead of using custom functions, there are also some
        # pre-defined hooks available in hc.hooks

        # create QT elements to show both GUIs in the main window
        self.main_widget = QWidget()

        self.container = QVBoxLayout()
        self.container.addWidget(self.instr_ctrl1)
        self.container.addWidget(self.instr_ctrl2)

        self.main_widget.setLayout(self.container)
        self.setCentralWidget(self.main_widget)
        self.show()

    def enable_disable_hook(self, value):
        """convert to float and modify some other UI element.

        We also just return the value as a string, so that the
        value still gets used in other hooks and gets updated.

        """
        myvalue = float(value)

        if myvalue > 5:
            self.instr_ctrl1.rate.setEnabled(False)
        else:
            self.instr_ctrl1.rate.setEnabled(True)
        return value


main_window = Demo(dummy=dummy)
sys.exit(main_window.app.exec_())
