from hardware_control.HC_Backend import HC_Backend
from hardware_control.helper import regex_compare


def boolstr_NR1(x: str):
    return int(x == "True")


class Key33500BCtrl(HC_Backend):
    def __init__(
        self,
        visa_addr,
        dummy: bool = False,
        print_commands: bool = False,
        use_sockets: bool = False,
        ip_addr: str = "",
        port_no=5025,
    ):
        super().__init__()
        self.ID = "KEYSIGHT-33500B"

        self.visa_addr = visa_addr
        self.online = False
        self.dummy = dummy
        self.print_commands = print_commands

        self.use_sockets = use_sockets
        self.port_no = port_no
        self.ip_addr = ip_addr

    def update_setting(self, setting: str, value):

        try:
            if self.dummy:
                return value
            else:
                # Note: We ignore channel number because there is only
                # one channel on this model of AWG
                if regex_compare("CH._enable", setting):
                    if value == "True":
                        self.write(":OUTP ON")
                    else:
                        self.write(":OUTP OFF")
                    rval = self.query(":OUTP?")
                    return str(rval == "1\n")
                elif regex_compare("CH._waveform", setting):
                    wvfm = "SIN"
                    if value == "Sine":
                        wvfm = "SIN"
                    elif value == "Square":
                        wvfm = "SQU"
                    elif value == "Triangle":
                        wvfm = "TRI"
                    elif value == "Ramp":
                        wvfm = "RAMP"
                    elif value == "Pulse":
                        wvfm = "PULS"
                    elif value == "PRBS":  # Pseudo-random binary sequence
                        wvfm = "PRBS"
                    elif value == "Noise":
                        wvfm = "NOIS"
                    elif value == "Arbitrary":
                        wvfm = "ARB"
                    elif value == "DC":
                        wvfm = "DC"
                    self.write(f":SOUR:FUNC {wvfm}")
                    rval = self.query(":SOUR:FUNC?")
                    return rval[:-1]  # Trim newline character
                elif regex_compare("CH._frequency", setting):
                    self.write(f":FREQ  {float(value):.6E}")
                    rval = self.query(":FREQ?")
                    return rval[:-1]
                elif regex_compare("CH._amplitude", setting):
                    self.write(f":VOLT  {float(value):.6E}")
                    rval = self.query(":VOLT?")
                    return rval[:-1]
                elif regex_compare("CH._offset", setting):
                    self.write(f":VOLT:OFFS  {float(value):.6E}")
                    rval = self.query(":VOLT:OFFS?")
                    return rval[:-1]
                elif regex_compare("CH._volts_div", setting):
                    chan = setting[2]
                    self.write(f":CHAN{chan}:SCAL  {float(value):.6E}")
                    return self.query(f":CHAN{chan}:SCAL?")
                elif setting == "timebase":
                    self.write(f":TIM:SCAL  {float(value):.6E}")
                    return self.query(":TIM:SCAL?")
                elif setting == "time_offset":
                    self.write(f":TIM:POS  {float(value):.6E}")
                    return self.query(":TIM:POS?")
                elif regex_compare("CH._offset", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:OFFS  {-1.0 * float(value):.6E}")
                    return self.query(f"CHAN{chan}:OFFS?")
                elif regex_compare("CH._BW_lim", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:BWL {boolstr_NR1(value)}")
                    return self.query(f"CHAN{chan}:BWL?")
                elif regex_compare("CH._active", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:DISP {boolstr_NR1(value)}")
                    return self.query(f"CHAN{chan}:DISP?")
                elif regex_compare("CH._impedance", setting):
                    chan = setting[2]
                    if value == "50":
                        self.write(f"CHAN{chan}:IMP FIFT")
                    else:
                        self.write(f"CHAN{chan}:IMP ONEM")
                    return self.query(f"CHAN{chan}:IMP?")
                elif regex_compare("CH._label", setting):
                    # Length is capped at 32 characters
                    if len(value) > 32:
                        value = value[0:32]
                    chan = setting[2]
                    self.write(f"CHAN{chan}:LAB {value}")
                    return self.query(f"CHAN{chan}:LAB?")
                elif setting == "labels_enabled":
                    self.write(f"DISP:LAB {boolstr_NR1(value)}")
                    print(f"DISP:LAB {boolstr_NR1(value)}")
                    return self.query(f"DISP:LAB?")
                elif regex_compare("CH._invert", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:INV {boolstr_NR1(value)}")
                    return self.query(f"CHAN{chan}:INV?")
                elif regex_compare("CH._probe_atten", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:PROB  {float(value):.6E}")
                    # ie. 10 gives x10 or 10:1 probe
                    return self.query(f"CHAN{chan}:PROB?")
                elif regex_compare("CH._coupling", setting):
                    chan = setting[2]
                    # Make sure valid value provided
                    if value not in ["AC", "DC"]:
                        value = "DC"
                    self.write(f"CHAN{chan}:COUP {value}")
                    return self.query(f"CHAN{chan}:COUP?")
                elif setting == "trigger_level":
                    self.write(f"TRIG:EDGE:LEV  {float(value):.6E}")
                    return self.query(f"TRIG:EDGE:LEV?")
                elif setting == "trigger_coupling":
                    # Make sure valid option given
                    if value not in ["AC", "DC", "LFReject"]:
                        value = "DC"
                    self.write(f"TRIG:COUP {value}")
                    return self.query(f"TRIG:COUP?")
                elif setting == "trigger_edge":
                    # Make sure valid option given
                    if value not in ["BOTH", "NEG", "POS", "ALT"]:
                        value = "POS"
                    self.write(f"TRIG:EDGE:SLOP {value}")
                    return self.query(f"TRIG:EDGE:SLOP?")
                elif setting == "trigger_channel":
                    self.write(f"TRIG:SOUR CHAN{int(value)}")
                    return self.query(f"TRIG:SOUR?")
        except Exception as e:
            print(
                "An error occured in Key33500BCtrl.py when sending SCPI commands to the instrument."
            )
            print(str(e))

    def command(self, cmd: str):
        pass

    def write(self, command: str):
        if self.online and not self.dummy:
            if not self.use_sockets:
                self.device.write(command)
            else:
                self.device.sendall(bytes(command + "\n", "utf-8"))
            if self.print_commands:
                print(f'\t{self.ID}< "{command}"')

    def query(self, command: str):
        if self.online and not self.dummy:
            if not self.use_sockets:
                reply = self.device.query(command)
            else:
                self.device.sendall(bytes(command + "\n", "utf-8"))
                reply_bytes = recvall(self.device)
                print(f"reply size: {len(reply_bytes)}")
                reply = str(reply_bytes)
                if len(reply) < 100:
                    print("\t\t" + reply)
                reply = reply[2 : len(reply) - 3]
            if self.print_commands:
                print(f'\t{self.ID}< "{command}"')
            return reply
        else:
            return ""


def recvall(sock):
    BUFF_SIZE = 4096  # 4 KiB
    data = b""
    while True:
        part = sock.recv(BUFF_SIZE)
        data += part
        t_str = str(part)
        if t_str[len(t_str) - 3 : len(t_str) - 1] == "\\n":
            break
    return data
