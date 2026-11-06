Web Monitor
===========

The web monitor shows the state of your experiments in a browser: which
experiments are online, their current values, plots of the last days, and
alarms. It consists of four parts:

* ``hc_web``, a small web **server** (Flask, SQLite, passkey login) with the
  ``hc-web`` command to administrate it.
* :class:`~hardware_control.web.publisher.WebPublisher`, which sends chosen parameters
  and alarms of a running hardware-control App to the server, buffers them
  while the server cannot be reached, and shows its state in the status bar.
* :class:`~hardware_control.instruments.hc_web.HCWebServer.HCWebServer`, an instrument
  driver that **pulls** channels of the server back into an App, so that one
  experiment can log the values of another one.
* ``client.py``, a single file without dependencies that other programs can
  copy to talk to the server (see `Using the API without hardware-control`_).

.. warning::

   The server is meant for a lab network or a VPN, behind a firewall that
   already keeps the internet out. It has passkey login and API tokens, but
   it has not been hardened for exposure to the whole internet.

Install
-------

On the machine that runs the server:

.. code-block:: bash

   uv pip install hardware-control[server]

The ``server`` extra adds Flask, ``webauthn``, gunicorn and ``plotly`` (only
for its bundled JavaScript). A plain ``pip install hardware-control`` does not
install them, and the lab computers that only publish or pull do not need
them. The server host also gets the normal dependencies of hardware-control
(Qt, ...), which it does not use.

Configuration
-------------

The server reads a TOML file, ``/etc/hc-web/config.toml`` or the file named by
the environment variable ``HC_WEB_CONFIG``. Every ``hc-web`` command also
accepts ``--config=<file>``.

.. literalinclude:: deploy/config.example.toml
   :language: toml

Only ``origin`` and ``database`` are required. A relative ``database`` is
relative to the directory of the config file.

.. note::

   Passkeys are bound to the hostname in ``origin``. If you change the
   hostname, every registered passkey stops working, and everyone has to be
   invited again.

Tokens and invites
------------------

Create the first administrator by creating an invite, and open the printed link
in a browser (it works once, and expires after 3 days unless you pass
``--expires``, e.g. ``--expires=12h``):

.. code-block:: bash

   hc-web invite --admin
   hc-web invite --expires=12h        # a viewer invite

On the page, register a passkey (there are no passwords). Later users are
invited the same way, or from the administrator page at ``/admin``, which also
manages users, tokens and shows warnings such as clock skew.

Programs use API tokens. A token belongs to one **experiment**, whose name is
chosen when the token is created (1 to 64 characters of ``A-Z a-z 0-9 _ . -``):

.. code-block:: bash

   hc-web token create B "beamline PC"            # may write channels of B
   hc-web token create B viewer --read-only       # may only read
   hc-web token list
   hc-web token revoke 3

The token is printed once and only a salted hash is stored. A token may write
only the channels of its own experiment, but **any token, also a read-only
one, can read the channels of all experiments**. The same is true for
everyone with a login.

Run the server
--------------

For a quick test, ``hc-web serve --port=5000`` starts the Flask development
server. For real use, run gunicorn behind a reverse proxy that provides TLS.
gunicorn only listens on the local machine:

.. code-block:: bash

   HC_WEB_CONFIG=/etc/hc-web/config.toml \
       gunicorn --workers 2 --bind 127.0.0.1:8000 'hc_web.app:create_app()'

As a service, use this systemd unit (adjust the paths):

.. literalinclude:: deploy/hc-web.service
   :language: ini

Apache terminates TLS and forwards requests to gunicorn. Apache needs
``ProxyPreserveHost On`` and has to say that the original request was
``https``:

.. literalinclude:: deploy/hc-web.apache.conf
   :language: apache

The server wraps Flask in ``ProxyFix``, so that it believes the
``X-Forwarded-For``, ``-Proto`` and ``-Host`` headers of that one proxy. The
option ``proxy_hops`` of the config file sets how many proxies are trusted
(default 1; 0 if clients reach gunicorn directly, never trust headers from
clients you do not control).

Certificates
~~~~~~~~~~~~

If the server is only reachable inside the lab, Let's Encrypt cannot reach it
with its usual HTTP check, but it can verify the domain with a DNS challenge,
for example:

.. code-block:: bash

   sudo certbot certonly --manual --preferred-challenges dns -d monitor.example.org

A DNS plugin of certbot for your DNS provider lets the renewal run without
you. The certificate files go into the two ``SSLCertificate`` lines of the
Apache configuration. Remember that the passkeys depend on the hostname.

Clocks and retention
~~~~~~~~~~~~~~~~~~~~

All machines (the server and every computer that publishes) need accurate
clocks, e.g. with NTP. Points keep the time of the publisher. The server only
warns on the administrator page if a publisher's clock differs by more than
5 s, and does not correct the data. A push that contains a time more than 60 s
(or one push interval, if that is longer) ahead of the server's clock is
rejected with HTTP 400, because it cannot be right.

Data older than ``retention_days`` (7 by default) is deleted, at most once an
hour while data arrives. ``hc-web cleanup`` does it right away, and
``hc-web status`` shows how much is stored.

What the pages show
-------------------

* **Overview**: a card per experiment with online or offline state, when it
  was last heard from, its current values and latched alarms, and a banner for the
  latched alarms of the experiments that are online. The button *Enable notifications* asks the browser for
  permission to show desktop notifications for new alarms and for experiments
  that go offline. They are only shown while a page of the monitor is open.
* **Experiment**: plots of the last days with zoom and pan. Times when the
  experiment was offline are shaded. State channels show their values as text.

An experiment is online as long as it keeps sending: it is shown as offline
after three times the push interval of the publisher without a push **arriving
at the server**, or at once when the App says that it is shutting down. This
is judged on the clock of the server, so a publisher with a wrong clock is
still shown as online (and gets a warning), and a push can never keep an
experiment online by claiming a time in the future. The data of the time
when it was offline is shown as unknown, never as a line. The values on the
overview card of an offline experiment are shown as *unknown* too; the last
known value is only in the tooltip. Likewise the publisher sends *unknown*
for the parameters of an instrument that the App has marked as offline
(``ONLINE`` is ``False``), instead of the last value it read, unless the App
runs in dummy mode.

Publish from an App
-------------------

A :class:`~hardware_control.web.publisher.WebPublisher` sends the parameters you choose
to the server, every ``interval`` seconds (default 10), together with the
alarms of the App. Use a write token of the experiment:

.. code-block:: python

   from hardware_control.web import WebPublisher, WebPublisherIndicator

   publisher = WebPublisher(app, "https://monitor.example.org", token, interval=10)
   publisher.publish("psu", "VOLTAGE", channel="hv", unit="V", label="HV")
   publisher.publish("gauge", "PRESSURE")  # channel "gauge_PRESSURE"
   publisher.publish("mw", "ON", channel="mw_on", kind="state", label="MW on")
   publisher.start()
   # in a main window, show the state in the status bar
   self.statusBar().addPermanentWidget(WebPublisherIndicator(publisher))

* A channel is ``sampled`` (a number) or ``state`` (a string such as ``on`` or
  ``<5V``). Both are sent at every interval; the server stores a state only
  when it changes, or when the experiment was offline in between, so that the
  state is known again right after a gap. Values that are not numbers in a
  sampled channel, ``nan`` and ``None`` are unknown.
* The server does not convert units. ``unit`` and ``label`` are only for the
  plots. Convert in your own code (see below).
* The publisher stops when the App quits, after a last push that tells the
  server that the shutdown is clean. You can also call ``publisher.stop()``.
* While the server cannot be reached, nothing is lost: the data is kept in a
  backlog file and sent later, oldest first. The file is in the user data
  directory, under ``web_backlog``, and is named after the server URL and the
  id of the token (never the secret), not after the App, so a restarted App
  sends what was left. Pass ``backlog_file=`` to choose another file. The indicator reads *Web ✓* (green), *Web:
  buffering N* (orange) or *Web: error* (red, hover for the reason, e.g. a
  refused token).
* Only one App can publish an experiment. If a second one starts while the
  first one is live, the server answers HTTP 409 and the second shows *Web:
  error*. Use a token of another experiment for it.
* Network problems are logged as warnings. They never raise an exception into
  the program or open a dialog.

A derived value, for example an indicator that is on when the microwave is on,
the high voltage is above 30 kV and the pressure is above 1 mTorr, is
calculated in your program and published through a virtual instrument:

.. code-block:: python

   import math
   from PyQt6.QtCore import QTimer

   self.app.add_virtual_instrument("derived", ["hv_kV", "plasma_on"])
   publisher.publish("derived", "hv_kV", unit="kV", label="HV")
   publisher.publish("derived", "plasma_on", kind="state", label="Plasma on")

   def update_derived():
       try:
           mw_on = self.app.get_instrument_parameter("mw", "ON") == "True"
           hv = float(self.app.get_instrument_parameter("psu", "VOLTAGE")) / 1000
           pressure = float(self.app.get_instrument_parameter("gauge", "PRESSURE")) * 1000
       except (TypeError, ValueError):
           hv = pressure = math.nan  # an input that is not available
       if math.isnan(hv) or math.isnan(pressure):
           on = "nan"  # unknown
       else:
           on = int(mw_on) * int(hv > 30) * int(pressure > 1)
       self.app.update_virtual_instrument_parameter("derived", "hv_kV", hv)
       self.app.update_virtual_instrument_parameter("derived", "plasma_on", on)

   self.derived_timer = QTimer(self)
   self.derived_timer.timeout.connect(update_derived)
   self.derived_timer.start(1000)

(The instrument and parameter names are examples; the virtual instrument has to
be added before it is published.)

Pull channels into an App
-------------------------

The driver :class:`~hardware_control.instruments.hc_web.HCWebServer.HCWebServer` reads
channels of any experiment from the server. A read token is enough:

.. code-block:: python

   import hardware_control as hc

   server = hc.instruments.HCWebServer(
       "server_B",
       "https://monitor.example.org",
       read_token,
       ["B/ng_on", "B/hv"],  # experiment/channel
       poll_interval=60,
   )
   app.add_instrument(server)

   dataset = hc.Dataset("from_B", app)
   dataset.track_instrument("server_B", "B_ng_on")
   dataset.track_instrument("server_B", "B_hv")
   dataset.start_updates(60)
   dataset.start_autosave(interval=300, file_format="JSON", filename="from_B")
   app.add_dataset(dataset)

``"B/ng_on"`` becomes the parameter ``B_ng_on``. Pass a dict
``{"ng_on": "B/ng_on"}`` to choose the parameter names. The parameter
``B_online`` is ``True`` or ``False`` for the experiment as a whole. Unknown
values (the experiment is offline, the channel has no value, the server cannot
be reached) are ``nan``. The command ``refresh`` polls right away.

The driver also keeps everything it receives, including state changes and the
times when the experiment was offline, in a history file (by default in the
user data directory, under ``web_history``). Read it with
:class:`~hardware_control.web.history.ChannelHistory`:

.. code-block:: python

   import time

   history = server.history
   frame = history.to_pandas("B/hv", start=time.time() - 3600)  # time, value
   points = history.points("B/ng_on")  # [(t, "1"), ...]
   gaps = history.gaps("B")  # [(start, end or None), ...]

``to_pandas`` adds a row with an unknown value at the start of each gap, so a
plot of the frame breaks there.

.. warning::

   * Pulled values can be up to one ``poll_interval`` old. **Do not use them as
     interlocks** or for anything where a late value is dangerous.
   * The driver polls from the thread of its adapter. If the server hangs, the
     connection check of the driver can be delayed by up to the timeout of the
     client (10 s) and so can other work of that thread.
   * Values cannot contain spaces: hardware-control sends values in messages
     that strip them. Use ``HV_on``, not ``HV on``, for state values (also
     when you push them with another client).
   * In dummy mode an App does not contact any hardware, and this driver then
     only returns ``nan``.

Using the API without hardware-control
--------------------------------------

Everything is plain JSON over HTTPS, with a token in the ``Authorization``
header. A minimal push, with a write token:

.. code-block:: bash

   URL=https://monitor.example.org
   TOKEN=<token>
   curl -H "Authorization: Bearer $TOKEN" \
        -d '{"points": [{"channel": "temp", "t": 1762200000, "v": 21.5}]}' \
        $URL/api/v1/push

``t`` is unix time in seconds and an unknown value is ``null``. Only ``points``
is required: unknown channels are created as numeric (``sampled``) channels,
and every push is also a heartbeat. Without an ``interval`` the server expects
a push every 60 s and shows the experiment as offline after three times that.
Times more than 60 s ahead of the server's clock are rejected with 400.
The answer is ``{"ok": true}``, or an error: 400 for a malformed body, 401
for a missing or unknown token, 403 for a read-only token, 409 if an App
publishes the same experiment (use an experiment of its own for scripts).

The endpoints (``/api/v1/``), for tokens of any scope except where noted:

* ``POST /push``: write token. Besides ``points``, the body may contain
  ``channels`` (``name``, ``kind`` ``sampled`` or ``state``, ``unit``,
  ``label``), ``run``, ``sent_at``, ``interval``, ``ticks``, ``events``,
  ``latched`` and ``shutdown``, which the App publisher uses.
* ``GET /data?channels=B/hv,B/ng_on&since=<t>[&until=<t>]``: points, periods
  when the experiment was offline (``gaps``) and the online state.
* ``GET /data.csv?channels=...&since=<t>``: the same points as a CSV download.
* ``GET /status``: online state, newest values and latched alarms of all
  experiments.
* ``GET /events?since=<t>[&after_id=<n>]``: alarm events, each with an ``id``.
  The ids grow in the order the events reach the server. To follow the events
  without missing late ones, remember ``last_id`` of the answer and ask for
  ``after_id=<last_id>`` next time (the overview page does this for its
  notifications).

A logged-in browser session may use the ``GET`` endpoints without a token.
Channel and experiment names use ``A-Z a-z 0-9 _ . -`` (up to 64 characters).

To use the same code as hardware-control from your own project, copy the one
file ``src/hc_web/client.py`` next to your script. It only uses the standard
library:

.. code-block:: python

   import time
   from client import WebClient, WebClientError

   web = WebClient("https://monitor.example.org", token)
   try:
       web.send([("temp", time.time(), 21.5), ("humidity", time.time(), None)])
   except WebClientError as e:
       print("push failed:", e, "status:", e.status)  # status None: no answer
   web.data(["B/temp"], since=time.time() - 3600)  # needs a read token or a write token
   web.status()

``examples/web_client_standalone.py`` is a complete script that only imports
that file. It runs from the repository as it is; in your own project, copy
``client.py`` next to it.

Demo
----

``examples/web_monitor_demo.py`` publishes two channels (a voltage and a
state) and pulls them back through an ``HCWebServer``. Use a config file with
``origin = "http://localhost:5000"`` and ``secure_cookies = false``, create an
experiment token, start a server, and run:

.. code-block:: bash

   export HC_WEB_CONFIG=config.toml
   hc-web token create demo "demo app" > token
   hc-web serve --port=5000 &
   python examples/web_monitor_demo.py --dummy --url=http://localhost:5000 \
       --token="$(cat token)" --alarm-after=60

After a minute the voltage goes over its limit, an alarm fires and the
overview page shows the banner. See ``--help`` for ``--interval`` and
``--seconds`` (quit after that long).

Reference
---------

.. autoclass:: hardware_control.web.WebPublisher
   :members: publish, start, stop, status_changed

.. autoclass:: hardware_control.web.WebPublisherIndicator
   :members:

.. autoclass:: hardware_control.web.WebClient
   :members:
