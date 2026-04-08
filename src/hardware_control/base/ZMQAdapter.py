import logging
import threading
import time
from typing import Any

import zmq
from setproctitle import setproctitle

from .zmq_helper import (
    handle_ZMQ_message_from_app,
    check_adapter_online,
    add_ZMQ_message_to_queue,
)
from .error_handling import safe_cleanup

logger = logging.getLogger(__name__)


class ZMQAdapter(threading.Thread):
    """Wraps an instrument driver into a thread and establishes ZMQ connections to the main app.

    ZMQAdapter takes an instrument driver argument, creates a thread, creates a
    ZMQ-publisher to publish any value changes, and listens to the
    ZMQ-app-publisher for requests.

    The run function gets executed when calling .start() on the thread
    and therefore hosts the custom event loop.
    """

    # Class constants for event loop timing
    CONNECTION_CHECK_INTERVAL = 50  # Check connection every N loop iterations
    POLL_TIMEOUT_MS = 100  # ZMQ poll timeout in milliseconds

    def __init__(
        self, instrument: Any, stopevent: Any, context: Any, publisher: str
    ) -> None:
        super().__init__(name=instrument.name)
        self.instrument = instrument
        self.stop = stopevent
        self.name = instrument.name
        self.online = False

        # priority queues for incoming commands
        self.priority_queue = {0: [], 1: [], 2: []}

        # subscribe to main app
        self.zmq_subscriber = context.socket(zmq.SUB)
        self.zmq_subscriber.connect(publisher)
        self.zmq_subscriber.subscribe(instrument.name)
        # +1 for extra whitespace after topic name
        self.zmq_topic_length = len(instrument.name) + 1

        # create our own publisher
        self.zmq_publisher_address = "tcp://" + self.get_address(publisher)
        self.zmq_publisher = context.socket(zmq.PUB)
        self.zmq_publisher_port = self.zmq_publisher.bind_to_random_port(
            self.zmq_publisher_address, min_port=4000, max_port=8000
        )

        logger.info(
            f"Set up ZMQ adapter for '{self.name}'. "
            f"listen to: {publisher} publishing at: {self.zmq_publisher_address}:{self.zmq_publisher_port}"
        )

    def get_address(self, ip_and_port: str) -> str:
        """Parses the ip address from the zmq connection string."""
        # strip 'tcp://'
        ip_and_port = ip_and_port[6:]
        ip, _ = ip_and_port.split(":")
        return ip

    def run(self) -> None:
        """Run custom event loop.

        Listens for ZMQ requests from the main app and if the
        instrument is not online, tries to reconnect to it.
        """
        # Set process title for easier identification in process lists
        setproctitle(f"hardware-control-{self.instrument.name}")

        # Set up ZMQ poller for efficient message handling
        poller = zmq.Poller()
        poller.register(self.zmq_subscriber, zmq.POLLIN)

        i = -1
        while not self.stop.is_set():
            i += 1
            # check if we are online and report status back to app
            if i % self.CONNECTION_CHECK_INTERVAL == 0:
                self.instrument.try_connect()
                check_adapter_online(self)

            # get all ZMQ messages using poller
            # Poll with short timeout to allow checking stop event regularly
            socks = dict(poller.poll(timeout=self.POLL_TIMEOUT_MS))
            if self.zmq_subscriber in socks:
                # Get all available messages
                get_messages = True
                while get_messages:
                    try:
                        msg = self.zmq_subscriber.recv_string(flags=zmq.NOBLOCK)
                        add_ZMQ_message_to_queue(self, msg)
                    except zmq.ZMQError:
                        get_messages = False

            # handle messages in queue
            handle_ZMQ_message_from_app(self)

        logger.debug(f"Closing the Instrument: {self.instrument.name}")
        self.instrument.close()

        # Clean up ZMQ resources when thread stops
        try:
            poller.unregister(self.zmq_subscriber)
        except Exception as e:
            logger.warning(
                f"Error unregistering subscriber from poller for '{self.name}': {e}"
            )

        self._cleanup_zmq_resources()

    def _cleanup_zmq_resources(self) -> None:
        """Clean up ZMQ sockets when the adapter thread stops."""
        safe_cleanup("ZMQ subscriber cleanup", self.zmq_subscriber.close, self.name)
        safe_cleanup("ZMQ publisher cleanup", self.zmq_publisher.close, self.name)
