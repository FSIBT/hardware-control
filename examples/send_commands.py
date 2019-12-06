import zmq

context = zmq.Context()
print("Connecting to hardware_control ZMQConnectionTool…")
print("\tSend HC-Commands to App. 'EXIT' to exit")
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

while True:

    line = input("> ")

    if line.upper() == "EXIT":
        break

    socket.send(str.encode(line))
    rval = socket.recv()

    print(rval)
