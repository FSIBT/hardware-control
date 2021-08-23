import threading
import time

import zmq


class ZMQAdapter(threading.Thread):
    """Wraps a backend into a thread and establishs ZMQ connections.

    Takes a backend, creates a thread, creates 2 sets of publisher and
    subscriber to be able to communicate both ways.

    The run function is what gets execute when calling .start() on a
    thread.

    """

    def __init__(self, instrument, stopevent, context, publisher):
        super().__init__(name=instrument.name)
        self.instrument = instrument
        self.stop = stopevent
        self.name = instrument.name

        # subscribe to main app
        self.zmq_subscriber = context.socket(zmq.SUB)
        self.zmq_subscriber.connect(publisher)
        self.zmq_subscriber.subscribe(instrument.name)
        self.zmq_topic_length = (
            len(instrument.name) + 1
        )  # +1 for extra whitespace after topic name

        # create our own publisher
        self.zmq_publisher_address = "tcp://127.0.0.1"
        self.zmq_publisher = context.socket(zmq.PUB)
        self.zmq_publisher_port = self.zmq_publisher.bind_to_random_port(
            self.zmq_publisher_address, min_port=4000, max_port=8000
        )

    def remove_topic(self, msg):
        """Remove the ZMQ topic from a message.

        In ZMQ pub/sub a subscriber can listen only to messages that
        start with a certain set of characters, called a topic.

        """
        return msg[self.zmq_topic_length :]

    def run(self):
        while not self.stop.is_set():

            # would add test here to call instrument.connect iff offline

            try:
                msg = self.zmq_subscriber.recv_string(flags=zmq.NOBLOCK)
            except zmq.ZMQError:
                time.sleep(0.1)
                continue
            msg = self.remove_topic(msg)
            msg = msg.split()
            if len(msg) == 1:
                # requesting a value
                ret = self.instrument[msg[0]]
                self.zmq_publisher.send_string(f"{self.instrument.name} {msg[0]} {ret}")
                continue
            elif len(msg) == 2:
                if msg[1] == "command":
                    self.instrument.command(msg[2])
                    continue
                if msg[1] == "get":
                    if msg[2] not in self.instrument.read_commands:
                        logger.error(
                            f"{msg[2]} read command not availabel in instrument '{self.name}'"
                        )
                        continue
                    value = self.instrument.get_value(msg[2])
                    if value is not None:
                        self.zmq_publisher.send_string(
                            f"{self.instrument.name} {msg[2]} {value}"
                        )
                    continue
                # if it is not a command, we are trying to set a value
                self.instrument[msg[0]] = msg[1]
