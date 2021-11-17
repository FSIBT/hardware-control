#!/usr/bin/env python3
"""Client example to run a remote instrument (could be on a different computer)

Usage:
  clint.py [--dummy] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console

"""

import logging

from docopt import docopt

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)

print("")
print(" *** End with Ctrl-c ***", flush=True)
print("")
print(" The instrument will take a few second to show up as online.")
print("")

flow_controller = hc.instruments.Alicat_M_Series("alicat", "192.168.0.15")
flow_controller._dummy = dummy

try:
    zmqadapter = hc.ZMQSingleInstrument(flow_controller, "127.0.0.1:4444")
except KeyboardInterrupt:
    print("\ndone. Goodbye")
