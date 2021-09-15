def handle_zmq_message_from_app(adapter, msg, logger):
    """Parses and handles the ZMQ messsage from the main app.

    First parse the message and then depending on the content execute
    a command, read or set a value in the instrument.

    This is one of the main part of handling the ZMQ communications,
    since it is used in ZMQAdapter and ZMQRemoteInstrument, we placed
    the code here in an external function.

    """

    # remove topic
    logger.debug(f"in ZMQ parsing: {msg}")
    msg = msg[adapter.zmq_topic_length :]

    msg = msg.split()
    if len(msg) == 1:
        ret = adapter.instrument[msg[0]]
        adapter.zmq_publisher.send_string(f"{adapter.instrument.name} {msg[0]} {ret}")
        return
    elif len(msg) == 2:
        if msg[0] == "command":
            logger.debug(f"'{adapter.name}' got command '{msg[1]}'")
            adapter.instrument.command(msg[1])
            return
        if msg[0] == "get":
            logger.debug(f"'{adapter.name}' got get request '{msg[1]}'")
            if msg[1] not in adapter.instrument.read_commands:
                logger.error(
                    f"'{msg[1]}' read command not available in instrument '{adapter.name}'"
                )
                return
            value = adapter.instrument.get_value(msg[1])
            logger.debug(f"sending value '{value}' back for {msg[1]}")
            if value is not None:
                adapter.zmq_publisher.send_string(
                    f"{adapter.instrument.name} {msg[1]} {value}"
                )
                return
        # if it is not a command, we are trying to set a value
        logger.debug(f"'{adapter.name}' setting '{msg[0]}' to '{msg[1]}'")
        adapter.instrument[msg[0]] = msg[1]
        return
