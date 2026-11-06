#!/usr/bin/env python3
"""Publish two channels to an hc_web server and read them back.

Start a server first (see the "Web monitor" page of the documentation):

  hc-web serve --config=config.toml
  hc-web token create demo "demo app"

then run

  web_monitor_demo.py --dummy --token=<the token>

A virtual instrument produces a sampled channel ("hv", in kV) and a state
channel ("mode"). A WebPublisher sends both to the server, and an HCWebServer
driver pulls them back, like another experiment would. Open the server in a
browser to see the experiment "demo". With --alarm-after the high voltage
jumps over its limit and an alarm fires, which shows up as a banner on the
server.

Usage:
  web_monitor_demo.py [--dummy] [--debug] [--console] [--info]
                      [--url=<url>] --token=<token> [--experiment=<name>]
                      [--interval=<s>] [--seconds=<s>] [--alarm-after=<s>]

Options:
  --dummy               no hardware is used by this demo; accepted like in the
                        other examples
  --debug               allow debug print statements
  --info                allow info print statements
  --console             Print logger output to console
  --url=<url>           address of the server [default: http://localhost:5000]
  --token=<token>       an API token for the experiment (a write token can
                        also read)
  --experiment=<name>   the experiment of the token [default: demo]
  --interval=<s>        seconds between pushes and between polls [default: 5]
  --seconds=<s>         quit after this many seconds (run until closed if not
                        given)
  --alarm-after=<s>     let the high voltage exceed the limit after this many
                        seconds
"""

import itertools
import logging
import math
import sys
import tempfile
from pathlib import Path

from docopt import docopt

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QVBoxLayout, QWidget

import hardware_control as hc
from hardware_control.instruments.hc_web import HCWebServer
from hardware_control.web import WebPublisher, WebPublisherIndicator

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)

HV_LIMIT = 30.0  # kV
MODES = ["off", "<5V", "on"]  # a state value is shown as it is, without spaces


class Demo(hc.HCMainWindow):
    def __init__(self, dummy, url, token, experiment, interval, alarm_after):
        super().__init__(dummy=dummy)
        self.setWindowTitle("Web Monitor Demo")
        self.interval = interval
        self.alarm_after = alarm_after
        self.ticks = itertools.count()

        # The demo should not leave files behind: the publisher's backlog and
        # the history of the pulled values live in a temporary directory. A
        # real program leaves both out and gets the default places.
        self.tmp = tempfile.TemporaryDirectory(prefix="web_monitor_demo_")
        tmp = Path(self.tmp.name)

        # -- publish: a virtual instrument with the values of "our" experiment
        self.app.add_virtual_instrument("source", ["hv", "mode"])
        self.publisher = WebPublisher(
            self.app, url, token, interval=interval, backlog_file=tmp / "backlog"
        )
        self.publisher.publish("source", "hv", channel="hv", unit="kV", label="HV")
        self.publisher.publish(
            "source", "mode", channel="mode", kind="state", label="Mode"
        )
        self.app.alarm_manager.add_alarm(
            hc.Alarm("source", "hv", "HV high", ">", HV_LIMIT, action=self.alarm_action)
        )

        # -- pull: the same two channels, as another experiment would read them
        self.pulled_channels = [f"{experiment}/hv", f"{experiment}/mode"]
        self.puller = HCWebServer(
            "server",
            url,
            token,
            self.pulled_channels,
            poll_interval=interval,
            history_file=tmp / "history.sqlite",
        )
        # A dummy App makes every instrument return placeholder values, but this
        # driver talks to a server and not to hardware: add it as a live one.
        self.app.dummy = False
        self.app.add_instrument(self.puller)
        self.app.dummy = dummy
        self.pulled = hc.Dataset("pulled", self.app)
        self.pulled.track_instrument("server", f"{experiment}_hv", alias="HV pulled")
        self.pulled.track_instrument("server", f"{experiment}_mode")
        self.pulled.start_updates(max(1, round(interval)))
        self.app.add_dataset(self.pulled)

        # -- window: what is published, what is pulled, the alarms
        layout = QVBoxLayout()
        for instrument, parameter, text in [
            ("source", "hv", "HV published (kV):"),
            ("source", "mode", "Mode published:"),
            ("server", f"{experiment}_hv", "HV pulled (kV):"),
            ("server", f"{experiment}_mode", "Mode pulled:"),
            ("server", f"{experiment}_online", "Experiment online:"),
        ]:
            layout.addWidget(
                hc.gui.widgets.HCLabel(self.app, instrument, parameter, text)
            )
        layout.addWidget(hc.gui.widgets.AlarmPanel(self.app))
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.statusBar().addPermanentWidget(WebPublisherIndicator(self.publisher))

        # new values every second, pushed every `interval` seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_values)
        self.timer.start(1000)
        self.update_values()
        self.publisher.start()
        self.show()

    def alarm_action(self, alarm):
        logger.warning(f"alarm {alarm.alias}: the high voltage is over its limit")

    def update_values(self):
        """Produce the next values: a slow wave, a mode that changes now and then."""
        n = next(self.ticks)
        hv = 15 + 10 * math.sin(n / 5)  # stays below the limit
        if self.alarm_after is not None and n >= self.alarm_after:
            hv = HV_LIMIT + 5
        self.app.update_virtual_instrument_parameter("source", "hv", f"{hv:.2f}")
        self.app.update_virtual_instrument_parameter(
            "source", "mode", MODES[(n // 10) % len(MODES)]
        )

    def report(self):
        """Say what came back through the driver (when the demo ends)."""
        for channel in self.pulled_channels:
            points = self.puller.history.points(channel)
            print(f"pulled {len(points)} points of {channel}, last: {points[-1:]}")
        self.puller.history.close()

    def close(self):
        if self.tmp is not None:  # closing can be asked for more than once
            self.report()
            # end the publisher's worker first: it still uses the backlog file
            # in the temporary directory
            self.publisher.stop()
            super().close()
            self.tmp.cleanup()
            self.tmp = None


main_window = Demo(
    dummy=dummy,
    url=commands["--url"],
    token=commands["--token"],
    experiment=commands["--experiment"],
    interval=float(commands["--interval"]),
    alarm_after=(
        float(commands["--alarm-after"]) if commands["--alarm-after"] else None
    ),
)
if commands["--seconds"]:
    QTimer.singleShot(round(float(commands["--seconds"]) * 1000), main_window.app.quit)
sys.exit(main_window.app.exec())
