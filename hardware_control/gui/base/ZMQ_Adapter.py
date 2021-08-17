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

    def __init__(self, backend, stopevent, context, publisher):
        super().__init__(name=backend.name)
        self.backend = backend
        self.stop = stopevent

        # subscribe to main app
        self.zmq_subscriber = context.socket(zmq.SUB)
        self.zmq_subscriber.connect(publisher)
        self.zmq_subscriber.subscribe(backend.name)
        self.zmq_topic_length = (
            len(backend.name) + 1
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

            # would add test here to call backend.connect iff offline

            try:
                msg = self.zmq_subscriber.recv_string(flags=zmq.NOBLOCK)
            except zmq.ZMQError:
                time.sleep(0.1)
                continue
            msg = self.remove_topic(msg)
            msg = msg.split()
            if len(msg) == 1:
                # requesting a value
                ret = self.backend[msg[0]]
                self.zmq_publisher.send_string(f"{self.backend.name} {msg[0]} {ret}")
                continue
            elif len(msg) == 2:
                if msg[1] == "command":
                    self.backend.command(msg[2])
                    continue
                # if it is not a command, we are trying to set a value
                self.backend[msg[0]] = msg[1]
