import json

import zmq


class ZMQSingleInstrument:
    """Wraps an instrument so that another app can connect to it.

    An instrument is supplied with a publisher for its result.

    To solve the problems of subscribing to a remote app, we add a
    request/reply ZMQ channel with a fixed port. The remote app can
    then use this channel to supply this class with the ip address and
    port to be used to listen to commands.

    In the remote app, we use ZMQRemoteInstrument to connect to this class.

    """

    def __init__(self, instrument, ipaddress, port):
        self.instrument = instrument
        self.name = instrument.name

        self.zmq_context = zmq.Context()

        # socket to receive requests to connect
        self.zmq_new = self.zmq_context.socket(zmq.REP)
        self.zmq_new.bind(f"tcp://{ipaddress}:{port}")

        # publisher to announce values and status
        self.zmq_publisher_address = f"tcp://{ipaddress}"
        self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
        self.zmq_publisher_port = self.zmq_publisher.bind_to_random_port(
            self.zmq_publisher_address, min_port=4000, max_port=8000
        )

        while True:
            message = self.zmq_new.recv_string()

            if message.startswith("App"):
                _, self.app_publisher = message.split()

                # subscribe to remote app
                self.zmq_subscriber = self.zmq_context(zmq.SUB)
                self.zmq_subscriber.connect(self.app_publisher)
                self.zmq_subscriber.subscribe(self.name)
                self.zmq_topic_length = len(self.name) + 1

                # let app know where to subscribe to
                self.zmq_new.send_string(f"{self.name} {ipaddress} {port}")

                keep_running = True
                while keep_running:
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
                        self.zmq_publisher.send_string(
                            f"{self.instrument.name} {msg[0]} {ret}"
                        )
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

                    # check if we should stop
                    try:
                        new_message = self.zmq_new.recv_string(flags=zmq.NOBLOCK)
                    except zmq.ZMQError:
                        new_message = None
                    if new_message == "STOP":
                        keep_running = False
                        self.zmq_subscriber.close()
                        self.zmq_new.send_string("ACK")
                    elif new_message == "LIST PARAMETERS":
                        read_set_commands = self.instruments.list_parameters()
                        out = json.dumps(read_set_commands)
                        self.zmq_new.send_string(out)

    def remove_topic(self, msg):
        """Remove the ZMQ topic from a message.

        In ZMQ pub/sub a subscriber can listen only to messages that
        start with a certain set of characters, called a topic.

        """
        return msg[self.zmq_topic_length :]


class ZMQRemoteInstrument:
    def __init__(self, name, ipaddress, port, context, publisher):

        self.name = name

        self.socket = context.socket(zmq.REQ)
        self.socket.connect("tcp://{ipaddress}:{port}")

        self.socket.send_string(f"App {publisher}")
        message = self.socket.recv_string()
        name, self.instrument_ipaddress, self.instrument_port = message.split()

    def list_parameters(self):
        self.socket.send_string(f"LIST PARAMETERS")
        message = self.socket.recv_string()
        read_set_commands = json.loads(message)
        return read_set_commands

    def join(self):
        self.socket.send_string("STOP")
        self.socket.recv_string()
