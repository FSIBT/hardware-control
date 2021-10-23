def handle_zmq_message_from_app(adapter, msg, logger):
    """Parses and handles the ZMQ messsage from the main app.

    First parse the message and then depending on the content execute
    a command, read or set a value in the instrument.

    Also check the onlnie status of the instrument and report back.

    This is one of the main part of handling the ZMQ communications,
    since it is used in ZMQAdapter and ZMQRemoteInstrument, we placed
    the code here in an external function.

    The possible messages have the following form:

    <instrument name> command <command name>
       This triggers a command

    <instrument name> get <parameter>
       This triggers a read request of the parameter

    <instrument name> set <parameter> <value>
       Set a parameter to a new value


    When reading a value, the return ZMQ message has the form:

    <instrument name> <parameter> <value>

    Parameters
    ----------
    adapter
       the ZMQAdapter for the instrument driver
    msg
       the ZMQ message received by the adapter
    logger
       the logger to be used for error and debug messages

    """

    # check online status
    if adapter.instrument.online != adapter.online:
        adapter.online = adapter.instrument.online
        adapter.zmq_publisher.send_string(
            f"{adapter.instrument.name} ONLINE {adapter.online}"
        )

    # remove topic
    logger.debug(f"in ZMQ parsing: {msg}")
    msg = msg[adapter.zmq_topic_length :]

    # the different messages are whitespace separated, so we can easily parse them
    msg = msg.split()
    if len(msg) == 1:
        logger.debug(f"'{adapter.name}' got invalid message '{msg}'")
        return
    elif len(msg) == 2:
        command = msg[0]
        if command == "command":
            command_name = msg[1]
            logger.debug(f"'{adapter.name}' got command '{command_name}'")
            adapter.instrument.command(command_name)
            return
        elif command == "get":
            parameter = msg[1]
            logger.debug(f"'{adapter.name}' got get request '{parameter}'")
            if parameter not in adapter.instrument.read_commands:
                logger.error(
                    f"'{msg[1]}' read command not available in instrument '{adapter.name}'"
                )
                return
            value = adapter.instrument.get_value(parameter)
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
            logger.debug(f"'{adapter.name}' setting '{parameter}' to '{value}'")
            adapter.instrument[parameter] = value
            return
