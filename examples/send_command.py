import zmq

context = zmq.Context()

#  Socket to talk to server
print("Connecting to hello world server…")
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")
while True:
    socket.send(b"SET:Keysight:timebase:2e-3")
    print(socket.recv())
    print("Enter to continue...")
    x = input()
    if x == "exit":
        break
