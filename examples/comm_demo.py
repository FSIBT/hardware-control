#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""oscilloscope_example to control the hardware_control test stand

Usage:
  oscilloscope_example [--dummy]
  oscilloscope_example [--socket]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of visa
"""

from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
use_sockets = commands["--socket"]

