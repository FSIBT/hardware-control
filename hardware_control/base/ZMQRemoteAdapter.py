"""Code to enable running and connecting to instruments on a different computer."""
import json
import logging
import time

import zmq

from .zmq_helper import (
    handle_ZMQ_message_from_app,
    check_adapter_online,
    add_ZMQ_message_to_queue,
)
from .Instrument import Instrument

logger = logging.getLogger(__name__)


class ZMQSingleInstrument:
    """Wraps an instrument so that another app can connect to it.

    This is meant to be run outside the app, e.g., on another
    computer. The instrument driver in this case will create its own
    publisher, and we need to have the remote app subscribe to it and
    also subscribe to the publisher of the remote app.

    To solve the problems of subscribing to a remote app, we add a
    request/reply ZMQ channel with a fixed port. The remote app can
    then use this channel to supply this class with the ip address and
    port to be used to listen to commands.

    :class:`ZMQSingleInstrument` is meant to wrap a single
    instrument driver. It creates a single REQ/REP channel that a main App
    can use to establish connection. It then creates the standard ZMQ
    publisher and subscriber to talk to the remote App.

    Currently there is no way to end a :class:`ZMQSingleInstrument`
    instance and one needs to exit via Ctrl-C.

    Parameters
    ----------
    instrument
        An instrument driver
    address
        The ZMQ address for a REQ/REP socket that is used to estable the
        communication with a remote app. Should be in "<ipaddress>:<portnumber>" format
    """

    def __init__(self, instrument: Instrument, address: str):
        self.instrument = instrument
        self.name = instrument.name
        self.online = False

        # priority queues for incoming commands
        self.priority_queue = {0: [], 1: [], 2: []}

        self.zmq_context = zmq.Context()

        ipaddress, port = address.split(":")

        # socket to receive requests to connect
        logger.info(f"Setting up ZMQ REP/REQ at {ipaddress}:{port}")
        self.zmq_new = self.zmq_context.socket(zmq.REP)
        self.zmq_new.bind(f"tcp://{ipaddress}:{port}")

        # publisher to announce values and status
        self.zmq_publisher_address = f"tcp://{ipaddress}"
        self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
        self.zmq_publisher_port = self.zmq_publisher.bind_to_random_port(
            self.zmq_publisher_address, min_port=4000, max_port=8000
        )
        logger.info(
            f"Setting up ZMQ publisher at {ipaddress}:{self.zmq_publisher_port}"
        )

        # some time for ZMQ to set up publisher
        time.sleep(1)

        self.instrument.try_connect()

        while True:
            message = self.zmq_new.recv_string()

            if not message.startswith("APP"):
                self.zmq_new.send_string("Unknown command")
                continue

            _, self.app_publisher = message.split()

            # subscribe to remote app
            self.zmq_subscriber = self.zmq_context.socket(zmq.SUB)
            self.zmq_subscriber.connect(self.app_publisher)
            self.zmq_subscriber.subscribe(self.name)
            self.zmq_topic_length = len(self.name) + 1

            # some time for ZMQ to set up subscriber
            time.sleep(1)

            # let app know where to subscribe to
            self.zmq_new.send_string(
                f"{self.name} {ipaddress} {self.zmq_publisher_port}"
            )
            logger.info("Got remote request and sent ZMQ info")

            # enter new eventloop that will handle instrument communication
            keep_running = True
            i = 0
            while keep_running:
                i += 1
                if i % 50 == 0:
                    self.instrument.try_connect()
                    check_adapter_online(self)

                # get all ZMQ messages
                get_messages = True
                while get_messages:
                    try:
                        msg = self.zmq_subscriber.recv_string(flags=zmq.NOBLOCK)
                        add_ZMQ_message_to_queue(self, msg)
                    except zmq.ZMQError:
                        get_messages = False

                # handle messages in queue
                handle_ZMQ_message_from_app(self)

                print(f"\r{time.time()}", end="")

                # check for message on the REQ/REP socket
                try:
                    new_message = self.zmq_new.recv_string(flags=zmq.NOBLOCK)
                except zmq.ZMQError:
                    new_message = None
                if new_message == "STOP":
                    logger.info("Got STOP request")
                    keep_running = False
                    self.zmq_subscriber.close()
                    self.zmq_new.send_string("ACK")
                elif new_message == "LIST_PARAMETERS":
                    logger.info("Got parameter list request")
                    read_set_commands = self.instrument.list_parameters()
                    out = json.dumps(read_set_commands)
                    self.zmq_new.send_string(out)


class ZMQRemoteAdapter:
    """A placeholder for a remote instrument that, for example, could be running on a remote computer.

    To be able to connect to an instrument on a remote computer. The
    program on that computer needs to wrap the instrument driver in
    the :class:`ZMQSingleInstrument`.

    :class:`ZMQRemoteAdapter` is used in the main app to connect to
    :class:`ZMQSingleInstrument` and will handle all the REQ/REP commands
    that are needed.

    This class then sets up the required communication by using a separate ZMQ REQ/REP channel.

    The REQ/REP channel implements the following commands

    APP <publisher ip:publisher port>
       The ZMQ address the remote instrument needs to subscribe to. The remote end needs to respond
       with the remote ZMQ publisher that the app needs to connect to
    LIST_PARAMETERS
       List all available read and set parameters and command names
    STOP
       Unsubscribe the remote end and close the connection
    """

    def __init__(self, name, address, context, publisher):

        self.name = name

        ipaddress, port = address.split(":")

        logger.info(f"{name} Connecting to remote {ipaddress}:{port}")
        self.req_rep_socket = context.socket(zmq.REQ)
        self.req_rep_socket.connect(f"tcp://{ipaddress}:{port}")

        logger.info(f"{name} sending App publisher info")
        self.req_rep_socket.send_string(f"APP {publisher}")
        message = self.req_rep_socket.recv_string()
        logger.info(f"{name} receiving remote zmq information, publisher at: {message}")

        name, self.instrument_ipaddress, self.instrument_port = message.split()
        if name != self.name:
            logger.error(
                f"ZMQ remote connected to the wrong instrument. Expected {self.name}, but got {name}."
            )

    def list_parameters(self):
        """Get a list of all available parameters from the remote instrument.

        Needed so that the instrument can be registered with the `app`
        and the necessary `app._data` entries can be created.
        """
        logger.info(f"{self.name} requesting parameter list")
        self.req_rep_socket.send_string("LIST_PARAMETERS")
        message = self.req_rep_socket.recv_string()
        read_set_commands = json.loads(message)
        return read_set_commands

    def join(self):
        """Duck type to make this class behave similar to a Thread.

        At the end of the app, all instruments running in separate
        threads are ended and those threads are then joined back into
        the main app. This method provides the same interface and will
        disconnect the remote instrument from the app.
        """
        logger.info(f"{self.name} stopping remote")
        self.req_rep_socket.send_string("STOP")
        self.req_rep_socket.recv_string()
