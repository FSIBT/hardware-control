import logging

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QPushButton,
    QLabel,
    QGridLayout,
    QComboBox,
    QLCDNumber,
    QGroupBox,
)

from ..base import Instrument

logger = logging.getLogger(__name__)


class FunctionRunnerTool(QGroupBox):
    """Provide a button that runs a python function.

    Optionally add a countdown timer next to the button
    """

    def __init__(
        self,
        app,
        name: str,
        button_label: str,
        call_function,
        countdown: int = 0,
        countdown_callback=None,
    ):
        """
        The callback functions take one parameter: the main app.

        Parameters
        ----------
        app :
            The main app
        name : str
            Name of the QGrouBox
        button_label : str
            Label of the Pushbutton that will trigger the function call
        call_function : Callable
            The function to call when the button gets hit
        countdown : int
            If > 0 then add a countdown to the right of the button
        countdown_callback : Callable
            Call this function when the countdown reaches zero

        """
        super().__init__(name)
        self.app = app
        self.button_label = button_label
        self.countdown = countdown
        self.call_function = call_function
        self.countdown_callback = countdown_callback
        self.countdown_value = float(countdown)

        if not callable(self.call_function):
            raise TypeError("Function in Function Runner must be callable")

        if countdown_callback is not None and not callable(self.countdown_callback):
            raise TypeError("Callback function in Function Runner must be callable")

        # *************************Create GUI************************
        self.main = QGridLayout()
        self.run_button = QPushButton()
        self.run_button.setText(self.button_label)
        self.run_button.setCheckable(False)
        self.run_button.clicked.connect(self.run_function)

        if countdown:
            self.countdown_wdgt = QLCDNumber()
            self.countdown_wdgt.setSmallDecimalPoint(True)
            self.countdown_wdgt.display(f"{self.countdown_value:.1f}")

        self.main.addWidget(self.run_button, 0, 0)

        if countdown:
            self.main.addWidget(self.countdown_wdgt, 0, 1)

            self.countdown_timer = QTimer()
            self.countdown_timer.timeout.connect(self.update_countdown)

        self.setLayout(self.main)

    def update_countdown(self):
        self.countdown_value -= 0.1

        if self.countdown_value <= 0:
            self.countdown_value = 0
            self.countdown_timer.stop()

            if self.countdown_callback is not None:
                self.countdown_callback(self.app)

        self.countdown_wdgt.display(f"{self.countdown_value:.1f}")

    def run_function(self):
        if self.countdown:
            self.countdown_value = float(self.countdown)
            self.countdown_timer.start(100)

        self.call_function(self.app)
