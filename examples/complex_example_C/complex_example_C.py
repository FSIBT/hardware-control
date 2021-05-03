#!/usr/bin/env python3
"""oscilloscope_example to control the hardware_control test stand

Usage:
  sts50_example [--dummy] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console
"""

import hashlib
import logging
import sys
from time import localtime, strftime
import warnings
import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QStyleFactory,
    QTabWidget,
    QGridLayout,
    QWidget,
    QSpacerItem,
    QSizePolicy,
    QGroupBox,
    QPushButton,
    QApplication,
)
from PyQt5.QtGui import QIcon, QDoubleValidator
from docopt import docopt
from PyQt5.QtCore import QTimer

import hardware_control.backends as hc_back
import hardware_control.gui as hc