"""A script that works together with the ZMQ-scope frontend to operate a pictotech scope remotely.

It uses a ZMQ socket to send commands and update the scope. We used this with a
raspberry pi as a controller on a HV floating rack

TODO: this is legacy code and should be rewritten using the backend class.

"""


import zmq
import sys

import time
import select
import json
import hashlib

import picoscope
from picoscope import ps5000a as PS

# set according to enum in labview
trigger_ch = ["A", "B", "C", "D", "External"]
trigger_direction = ["Rising", "Falling"]

# some default variables or variables to store current
current_hash = ""
j = [
    {"relativeInitialX": 0.0, "xIncrement": 0.1, "wfm": [0]},
    {"relativeInitialX": 0.0, "xIncrement": 0.1, "wfm": [0]},
    {"relativeInitialX": 0.0, "xIncrement": 0.1, "wfm": [0]},
    {"relativeInitialX": 0.0, "xIncrement": 0.1, "wfm": [0]},
]
json_last_shot = json.dumps(j, sort_keys=True)


setting = None
A = None
B = None
C = None
D = None

dt = 1

DEVICENAME = "picoscope02"


def print_setting():
    global setting
    print("Resolution: ", setting["Bit resolution"])
    print("Trigger channel:", setting["Trigger channel"])
    print("Trigger level:", setting["Trigger level"])
    print("Trigger edge:", setting["Trigger edge"])
    print(
        "Ch A: ",
        "  enabled: ",
        setting["Ch enable 1"],
        "  Coupling:",
        setting["AC/DC 1"],
        "  Bwlimit:",
        setting["bandwidth filter 1"] == "20MHZ",
        "  Vrange:",
        setting["Voltage range 1"],
        "  Voff:",
        setting["Voltage offset 1"],
    )
    print(
        "Ch B: ",
        "  enabled: ",
        setting["Ch enable 2"],
        "  Coupling:",
        setting["AC/DC 2"],
        "  Bwlimit:",
        setting["bandwidth filter 2"] == "20MHZ",
        "  Vrange:",
        setting["Voltage range 2"],
        "  Voff:",
        setting["Voltage offset 2"],
    )
    print(
        "Ch C: ",
        "  enabled: ",
        setting["Ch enable 3"],
        "  Coupling:",
        setting["AC/DC 3"],
        "  Bwlimit:",
        setting["bandwidth filter 3"] == "20MHZ",
        "  Vrange:",
        setting["Voltage range 3"],
        "  Voff:",
        setting["Voltage offset 3"],
    )
    print(
        "Ch D: ",
        "  enabled: ",
        setting["Ch enable 4"],
        "  Coupling:",
        setting["AC/DC 4"],
        "  Bwlimit:",
        setting["bandwidth filter 4"] == "20MHZ",
        "  Vrange:",
        setting["Voltage range 4"],
        "  Voff:",
        setting["Voltage offset 4"],
    )


def setup_scope():
    global scope, dt
    scope.stop()
    if setting is None:
        # load some default values
        scope.setChannel("A", "DC", VRange=2.0, VOffset=0.0)
        scope.setChannel("B", "DC", VRange=2.0, VOffset=0.0)
        scope.setChannel("C", "DC", VRange=2.0, VOffset=0.0)
        scope.setChannel("D", "DC", VRange=2.0, VOffset=0.0)

        obs_duration = 0.1
        sampling_interval = obs_duration / 4096

        a = scope.setSamplingInterval(sampling_interval, obs_duration)

        scope.setSimpleTrigger("D", threshold_V=-0.2, direction="Falling", timeout_ms=0)
        scope.setResolution("12")

        scope.runBlock(pretrig=0.1)
    else:
        print(setting)
        scope.setResolution(str(setting["Bit resolution"]))

        scope.setChannel(
            "A",
            setting["AC/DC 1"],
            VRange=setting["Voltage range 1"],
            VOffset=setting["Voltage offset 1"],
            enabled=setting["Ch enable 1"],
            BWLimited=(setting["bandwidth filter 1"] == "20MHZ"),
        )
        scope.setChannel(
            "B",
            setting["AC/DC 2"],
            VRange=setting["Voltage range 2"],
            VOffset=setting["Voltage offset 2"],
            enabled=setting["Ch enable 2"],
            BWLimited=(setting["bandwidth filter 2"] == "20MHZ"),
        )
        scope.setChannel(
            "C",
            setting["AC/DC 3"],
            VRange=setting["Voltage range 3"],
            VOffset=setting["Voltage offset 3"],
            enabled=setting["Ch enable 3"],
            BWLimited=(setting["bandwidth filter 3"] == "20MHZ"),
        )
        scope.setChannel(
            "D",
            setting["AC/DC 4"],
            VRange=setting["Voltage range 4"],
            VOffset=setting["Voltage offset 4"],
            enabled=setting["Ch enable 4"],
            BWLimited=(setting["bandwidth filter 4"] == "20MHZ"),
        )

        obs_duration = setting["Timebase"]
        sampling_interval = obs_duration / setting["Record Length"]

        if sampling_interval < 1e-9:
            sampling_interval = 1e-9
            obs_duration = sampling_interval * int(obs_duration / sampling_interval)

        print("setting time: ", sampling_interval, obs_duration)

        a = scope.setSamplingInterval(sampling_interval, obs_duration)
        dt, no, _ = a
        print("actual one used: ", a)

        trch = setting["Trigger channel"]
        trV = setting["Trigger level"]
        if trch == "A":
            VRange = setting["Voltage range 1"]
            VOffset = setting["Voltage offset 1"]
        if trch == "B":
            VRange = setting["Voltage range 2"]
            VOffset = setting["Voltage offset 2"]
        if trch == "C":
            VRange = setting["Voltage range 3"]
            VOffset = setting["Voltage offset 3"]
        if trch == "D":
            VRange = setting["Voltage range 4"]
            VOffset = setting["Voltage offset 4"]
        if trch == "External":
            VRange = 5
            VOffset = 0
        if trV < 0:
            trV = max(trV, -VRange + VOffset)
        else:
            trV = min(trV, VRange - VOffset)

        print("setting trigger: ", trch, trV, setting["Trigger edge"])
        scope.setSimpleTrigger(
            trch, threshold_V=trV, timeout_ms=0, direction=setting["Trigger edge"]
        )

        scope.runBlock(pretrig=setting["Ref Position (%)"] / 100.0)


scope = PS.PS5000a()
print("Setting up scope...")
setup_scope()
print("   Scope ready for operation")

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://192.168.0.30:6000")

poller = zmq.Poller()
poller.register(socket, zmq.POLLIN)
print("ZMQ setup done")

keep_running = True
while keep_running:
    sleep = True  # unless something happens, we sleep for 0.2s
    # this gets checked at the end

    # check ZMQ
    socks = dict(poller.poll(0))
    if socket in socks and socks[socket] == zmq.POLLIN:

        sleep = False
        command = socket.recv_string()

        if command == "get hash":
            socket.send_string(current_hash)
        elif command == "ping":
            socket.send_string("alive")
            print("got a ping request")
        elif command == "get graph":
            if setting is None:
                print("no setting data")
                socket.send_string("")
            else:
                print("sending graph data. Len=", len(json_last_shot))
                socket.send_string(json_last_shot)
        elif command == "get scope settings":
            socket.send_string(json.dumps(setting))
        elif command == "set scope settings":

            print("in set scope settings", flush=True)
            socket.send_string("JSON?")
            settings_JSON = socket.recv_string()
            socket.send_string("ok")
            setting = json.loads(settings_JSON)
            setup_scope()
        else:
            socket.send_string("unknown command")
            print(command)

    # check scope for trigger
    try:
        ready = scope.isReady()
    except:
        # try reconnect to scope on error
        print("!!! Lost scope connection... !!!")
        scope = PS.PS5000a()
        scope_setup()
        print("    reconnected")
        ready = False
    if ready:
        sleep = False
        print("*" * 24)
        print("***** got trigger *****")
        print("*" * 24)
        if setting["Ch enable 1"]:
            A = list(scope.getDataV("A"))
        else:
            A = [0] * scope.noSamples
        if setting["Ch enable 2"]:
            B = list(scope.getDataV("B"))
        else:
            B = [0] * scope.noSamples
        if setting["Ch enable 3"]:
            C = list(scope.getDataV("C"))
        else:
            C = [0] * scope.noSamples
        if setting["Ch enable 4"]:
            D = list(scope.getDataV("D"))
        else:
            D = [0] * scope.noSamples

        j = {
            "wave0": A,
            "wave1": B,
            "wave2": C,
            "wave3": D,
            "Actual Record Length": scope.noSamples,
            "Actual Sample Rate": 1.0 / scope.sampleInterval,
        }
        data = json.dumps(j, sort_keys=True)
        m = hashlib.md5()
        m.update(bytearray(data, "utf-8"))

        # send data back or save latest data in structure

        R = setting["Ref Position (%)"]
        T = scope.noSamples * dt
        T0 = -T * R / 100.0

        j = [
            {"t(0)": T0, "delta t": dt, "data": A},
            {"t(0)": T0, "delta t": dt, "data": B},
            {"t(0)": T0, "delta t": dt, "data": C},
            {"t(0)": T0, "delta t": dt, "data": D},
        ]
        json_last_shot = json.dumps(j, sort_keys=True)

        scope.runBlock(pretrig=setting["Ref Position (%)"] / 100.0)

    # check stdin
    i, o, e = select.select([sys.stdin], [], [], 0.0)
    if len(i) > 0 and i[0] == sys.stdin:
        sleep = False
        input = sys.stdin.readline()
        input = input[:-1]  # remove \n
        print("got input", input)
        if input in ["bye", "exit", "quit"]:
            print("exiting")
            keep_running = False
        elif input == "setting":
            if setting is None:
                print("nothing set")
            else:
                print(
                    "*** these are the requested settings, not necessaryly the ones of the scope ***"
                )
                print_setting()

    sys.stdout.flush()
    if sleep:
        time.sleep(0.2)

scope.close()
print("Good Bye!")
