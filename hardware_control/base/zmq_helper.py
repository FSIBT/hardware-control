"""Functions that are commonly used for ZMQ functionality; these are primarily used in `ZMQAdapter` and `ZMQRemoteAdapter`."""
import logging
import time

logger = logging.getLogger(__name__)


def check_adapter_online(adapter) -> None:
    """Report change in online status to app."""
    if adapter.instrument._online != adapter.online:
        adapter.online = adapter.instrument._online
        adapter.zmq_publisher.send_string(
            f"{adapter.instrument.name} ONLINE {adapter.online}"
        )


def add_ZMQ_message_to_queue(adapter, msg: str) -> None:
    """Sort the messages into different queues that have different priorities.

    Since instruments can take a while to respond to a request, it can
    happen that there will be a large ZMQ message queue waiting for the
    instrument to handle the messages. In principle, this queue can also grow over
    time if the instrument is too slow to catch up. To avoid this we
    use different priorities for the ZMQ requests. A priority always
    needs to be defined for a request. The following options are
    possible:

    Priority options:
       - '0': if a new request for the same parameter arrives, the old
         one is dropped from the queue. These can be used for regular
         update requests of parameters from the instrument.
       - '1': if a new request for the same parameter arrives, the old
         one is dropped from the queue. These, however, are handled
         before any '0' priority item. These are used when a a user
         pushes a button on a UI.
       - '2': These are handled first and are never dropped from the
         queue. Usefule for automatted scanning.
    """
    logger.debug(f"{adapter.name} got ZMQ messages from App: {msg}")
    msg = msg[adapter.zmq_topic_length :]

    priority, msg_rest = msg.split(maxsplit=1)
    priority = int(priority)

    msg_compare = msg_rest
    if msg_rest.startswith("set "):
        msg_compare, value = msg_rest.rsplit(maxsplit=1)

    if priority == 0:
        if msg_compare not in adapter.priority_queue[0]:
            # special check for set where we ignore the value
            if msg_rest.startswith("set "):
                for i, m in enumerate(adapter.priority_queue[0]):
                    if m.startswith(msg_compare):
                        adapter.priority_queue[0].pop(i)
                        break
            adapter.priority_queue[0].append(msg_rest)
        return
    if priority == 1:
        if msg_compare not in adapter.priority_queue[1]:
            # special check for set where we ignore the value
            if msg_rest.startswith("set "):
                for i, m in enumerate(adapter.priority_queue[1]):
                    if m.startswith(msg_compare):
                        adapter.priority_queue[1].pop(i)
                        break
            adapter.priority_queue[1].append(msg_rest)
        return
    if priority == 2:
        adapter.priority_queue[2].append(msg_rest)
        return

    logger.error(
        f"'{adapter.name}' got invalid priority '{priority}' in message '{msg}'"
    )


def handle_ZMQ_message_from_app(adapter) -> None:
    """Parse and handle a ZMQ messsage from the main app.

    The function first parses the message and then, depending on the message's content,
    executes a command, reads a value, or sets a value in the instrument.

    The possible messages have the following form:

    <instrument name> <priority> command <command name>
       This triggers a command

    <instrument name> <priority> get <parameter>
       This triggers a read request of the parameter

    <instrument name> <priority> set <parameter> <value>
       This set a parameter to a new value

    When arriving at this function the first two arguments are already
    taken care of and have been removed from the incoming msg.

    When reading a value, the return ZMQ message has the form:

    <instrument name> <parameter> <value>
       This returns a parameter value from the instrument

    Parameters
    ----------
    adapter
       the ZMQAdapter/ZMQRemoteAdapter for the instrument driver
    msg
       the ZMQ message received by the adapter
    """
    # get a message from the priority queue or return if nothing to do
    for priority in [2, 1, 0]:
        if adapter.priority_queue[priority]:
            msg = adapter.priority_queue[priority].pop(0)
            break
    else:
        # nothing to do, let's sleep a bit
        time.sleep(0.1)
        return

    # the different messages are whitespace separated, so we can easily parse them
    logger.debug(f"'{adapter.name}' working on ZMQ message: {msg}")
    msg = msg.split()
    if len(msg) == 2:
        command = msg[0]
        if command == "command":
            command_name = msg[1]
            logger.debug(
                f"'{adapter.name}' got command '{command_name}' [priority={priority}]"
            )
            adapter.instrument.command(command_name)
            return
        if command == "get":
            parameter = msg[1]
            logger.debug(
                f"'{adapter.name}' got get request '{parameter}' [priority={priority}]"
            )
            if parameter not in adapter.instrument.read_commands:
                logger.error(
                    f"'{parameter}' read command not available in instrument '{adapter.name}'"
                )
                return
            value = adapter.instrument.get_value(parameter)
            # make sure that there are no spaces in the value string
            # since the app expects exactly three white-space-separated strings
            value = f"{value}"
            if " " in value:
                value = value.replace(" ", "")
                logger.warning(
                    f"In {adapter.name} - {parameter}: Found a white space(s) in returned value. Removing them."
                )

            logger.debug(f"sending value '{value}' back for {parameter}")
            if value is not None:
                adapter.zmq_publisher.send_string(
                    f"{adapter.instrument.name} {parameter} {value}"
                )
                return
    elif len(msg) == 3:
        command = msg[0]
        if command == "set":
            parameter = msg[1]
            value = msg[2]
            logger.debug(
                f"'{adapter.name}' setting '{parameter}' to '{value}' [priority={priority}]"
            )
            adapter.instrument[parameter] = value
            return
