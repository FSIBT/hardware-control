#!/usr/bin/env python3
"""Push values to an hc_web server and read them back, without hardware-control.

To use this in your own project, copy ``client.py`` (one file, standard
library only) from ``src/hc_web/`` of the hardware-control repository next to
this script. Nothing else is needed: no hardware-control, no Qt, no Flask.

  python web_client_standalone.py http://localhost:5000 <token> --experiment=demo

The token must belong to the experiment (``hc-web token create demo "my pc"``).
A write token can also read the data back.
"""

import argparse
import sys
import time
from pathlib import Path

try:
    from client import WebClient, WebClientError
except ImportError:
    # Only for running this file from a checkout of the repository, where
    # client.py is not next to it. In your own project, copy client.py instead.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "hc_web"))
    from client import WebClient, WebClientError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("url", help="address of the server, e.g. http://localhost:5000")
    parser.add_argument("token", help="API token of the experiment")
    parser.add_argument(
        "--experiment", default="demo", help="experiment of the token (default: demo)"
    )
    parser.add_argument("--points", type=int, default=3, help="values to send")
    args = parser.parse_args()

    web = WebClient(args.url, args.token)
    start = time.time()
    try:
        # (channel, unix time in seconds, value); None is an unknown value.
        # Channels that do not exist yet are created as numeric channels.
        for i in range(args.points):
            t = time.time()
            web.send([("temp", t, 20.0 + i), ("humidity", t, None if i == 0 else 40.5)])
            time.sleep(0.2)
        # a push is also a heartbeat: the server shows the experiment as online
        status = web.status()["experiments"][args.experiment]
        print(
            "online:",
            status["online"],
            "channels:",
            [c["name"] for c in status["channels"]],
        )
        # channels are named "<experiment>/<channel>"
        data = web.data([f"{args.experiment}/temp"], since=start - 1)
        for t, v in data["channels"][f"{args.experiment}/temp"]["points"]:
            print(f"{t:.1f} {v}")
    except WebClientError as e:
        print("failed:", e, "(status:", e.status, ")", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
