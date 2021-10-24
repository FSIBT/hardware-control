import logging
import threading
import time

import zmq

from .zmq_helper import handle_zmq_message_from_app

logger = logging.getLogger(__name__)


class ZMQAdapter(threading.Thread):
    """Wraps an instrument driver into a thread and establishs ZMQ connections to the main app.

    Takes an instrument driver, creates a thread, creates a
    ZMQ-publisher to publish any value changes and listen to the
    ZMQ-app-publisher for requests.

    The run function gets execute when calling .start() on the thread
    and therefore hosts the custom event loop.

    """

    def __init__(self, instrument, stopevent, context, publisher):
        super().__init__(name=instrument.name)
        self.instrument = instrument
        self.stop = stopevent
        self.name = instrument.name
        self.online = False

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

    def get_address(self, ip_and_port):
        # strip 'tcp://'
        ip_and_port = ip_and_port[6:]
        ip, _ = ip_and_port.split(":")
        return ip

    def run(self):
        """Custom event loop.

        Listens for ZMQ requests from the main app and if the
        instrument is not online, tries to reconnect to it.

        """

        i = 0
        while not self.stop.is_set():

            # would add test here to call instrument.connect iff offline

            try:
                msg = self.zmq_subscriber.recv_string(flags=zmq.NOBLOCK)
            except zmq.ZMQError:
                time.sleep(0.1)
                continue
            if i % 50 == 0:
                self.instrument.try_connect()

            handle_zmq_message_from_app(self, msg, logger)
            i += 1
