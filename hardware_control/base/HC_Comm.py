import time
from colorama import Fore, Style
import logging

from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QObject, QTimer

logger = logging.getLogger(__name__)

ipy_logger = logging.getLogger("ipykernel")
ipy_logger.setLevel("ERROR")


class HC_Comm(QObject):
    """This object is used to automate creating threads and communication objects.
    By calling this object's functions, data can be safely transfered between the
    main thread and communication threads."""

    sigUpdateSettings = pyqtSignal(str, str, float)
    sigCommand = pyqtSignal(str, float)
    sigWrite = pyqtSignal(str, float)
    sigQuery = pyqtSignal(str, float)
    sigTryConnect = pyqtSignal(float)
    sigCommandList = pyqtSignal(str, float)
    sigCommandLog = pyqtSignal(str, float, str)
    sigClose = pyqtSignal()

    # TODO: @TImo Bauer Add 'try_connect' frequency
    def __init__(
        self, backend, instrument, try_connect_period=5000, lock_until_sync=False
    ):
        super().__init__()
        self.backend = backend
        self.instruments = [instrument]  # Calling instrument UI (eg. HC_scope)
        self.backend_model = backend.ID
        self.try_connect_period = try_connect_period

        self.lock_until_sync = lock_until_sync

        self.expire_time = 40
        self.list_expire_time = 5

        self.worker = HC_CommWorker(self.backend)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        # Connect Comm's signals for CommWorker's slots
        self.sigUpdateSettings.connect(self.worker.update_setting)
        self.sigCommand.connect(self.worker.command)
        self.sigWrite.connect(self.worker.write)
        self.sigQuery.connect(self.worker.query)
        self.sigTryConnect.connect(self.worker.try_connect)
        self.sigCommandList.connect(self.worker.command_listdata)
        self.sigCommandLog.connect(self.worker.command_log)
        self.sigClose.connect(self.worker.close)

        # Connect CommWorker's signals to Comm's slots
        self.worker.sigReturnValues.connect(self.backend_return)
        self.worker.sigReturnOnline.connect(self.backend_return_online)
        self.worker.sigReturnList.connect(self.backend_return_listdata)
        self.worker.sigReturnLog.connect(self.backend_return_log)

        # Connect timer
        self.try_connect_timer = QTimer(self)
        self.try_connect_timer.timeout.connect(self.try_connect)
        self.try_connect_timer.start(self.try_connect_period)

        self.dataset_states = []

    def __repr__(self):
        return f"HC_Comm {self.backend_model} @ {self.backend.connection_addr}  {hex(id(self))}"

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.backend.connection_addr}"

    def addWidget(self, new_instrument):
        """Adds a new instrument to HC_Comm. When HC_Comm gets a reply, it will
        go to all listed instruments"""

        self.instruments.append(new_instrument)

    def close(self):
        # TODO: Change logger messages to references address, not instr
        logger.debug(
            f"\tInstrument: '{self.instruments[0].name}' closing Comm with backend of type '{self.backend_model}'."
        )
        self.try_connect_timer.stop()  # Stop
        self.sigClose.emit()
        self.worker_thread.quit()  # Kill thread
        if self.instruments[0].window.app.print_close_info:
            print(
                Fore.BLUE
                + f"\t'{self.instruments[0].name}': Closing...\t\t\t--:-- sec"
                + Style.RESET_ALL,
                end="",
                flush=True,
            )
            start_time = time.time()
        # Wait for thread to join (otherwise, if main thread exists
        # first, stdout will be closed while the worker_thread may
        # still be running and try to write to stdout, causing an
        # error to arise)
        self.worker_thread.wait()
        if self.instruments[0].window.app.print_close_info:
            print(
                f"\r\t'{self.instruments[0].name}': Closed    \t\t\t"
                + "{:.2f}".format(time.time() - start_time)
                + " sec    "
            )

    def update_setting(self, setting: str, value: str):
        """Transfers the setting and value information to the worker thread"""

        if self.lock_until_sync:
            logger.debug(
                f"Instrument {self.instruments[0].name} block update_setting because UI has not yet synced with instrument"
            )

        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'update_setting()' for setting '{setting}' and sent message '{value}'."
        )
        self.sigUpdateSettings.emit(setting, value, time.time() + self.expire_time)

    def command(self, cmd: str):
        """Sends a command to the worker in the worker thread"""
        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'command()' and sent command: '{cmd}'."
        )
        self.sigCommand.emit(cmd, time.time() + self.expire_time)

    def write(self, msg: str):
        """Sends a command to be sent to the instrument by the worker in the worker thead"""
        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'write()' and sent message: '{msg}'."
        )
        self.sigWrite.emit(msg, time.time() + self.expire_time)

    def query(self, msg: str):
        """Sends a query statement to be sent to the instrument by the worker in the worker thead"""
        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'query()' and sent message: '{msg}'."
        )
        self.sigQuery.emit(msg, time.time() + self.expire_time)

    def try_connect(self):
        """Tells the worker to tell the backend to try to connect to the instrument"""
        self.sigTryConnect.emit(time.time() + self.expire_time)

    def command_listdata(self, cmd: str):
        """Sends a command to the worker in the worker thread just like command(),
        but returns two lists instead of a string."""
        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'command_listdata()' and sent command: '{cmd}'."
        )
        self.sigCommandList.emit(cmd, time.time() + self.list_expire_time)

    def command_log(self, cmd: str, param_str: str):
        """Sends a command to the worker in the worker thread"""

        # print(f"\n\t\tCOMMAND_LOG::HC_COMM\t{param_str}\n")

        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'command()' and sent command: '{cmd}'."
        )
        self.sigCommandLog.emit(cmd, time.time() + self.expire_time, param_str)

    @pyqtSlot(str)
    def backend_return(self, retval: str):
        """Receives a return value from the CommWorker and sends it to the instrument's
        backend_return function, which adds it to the instrument's values dictionary or
        , if overwritten, may process the return string immediately for example by
        updating the UI."""

        if retval == "SYNC_BACKEND":
            self.lock_until_sync = False

        logger.debug(
            f"Instrument: {self.instruments[0].name} received return from backend '{self.backend_model}'. Return message: {retval}"
        )
        for instr in self.instruments:
            instr.backend_return(retval)

    @pyqtSlot(bool)
    def backend_return_online(self, connected: bool):
        """ Gets called by the worker after the worker hears from the instrument if it successfully connected.
        Updates the state of the instrument - ie. if it is or is not online"""
        for instr in self.instruments:
            instr.backend_return_online(connected)

    @pyqtSlot(str, list, list)
    def backend_return_listdata(self, desc: str, data1: list, data2: list):
        """Receives a return value from the CommWorker and sends it to the instrument's
        backend_return_listdata function, which can be overwritten by the UI's author
        to process the data."""
        for instr in self.instruments:
            instr.backend_return_listdata(desc, data1, data2)

    @pyqtSlot(str, str)
    def backend_return_log(self, retval: str, param_str: str):
        """Receives a return value from the CommWorker and sends it to the instrument's
        backend_return function, which adds it to the instrument's values dictionary or
        , if overwritten, may process the return string immediately for example by
        updating the UI."""

        # print(f"\n\t\t\t\tBACKEND_RETURN_LOG::HC_COMM\t{param_str}\n")
        if len(self.instruments) > 0:
            self.instruments[0].window.app.director.backend_return_log(
                retval, param_str
            )

            logger.debug(
                f"Instrument: {self.instruments[0].name} received return from backend '{self.backend_model}'. Return message: {retval}"
            )
        for instr in self.instruments:
            instr.backend_return(retval)


class HC_CommWorker(QObject):
    """Uses signals + slots to receive data from HC_Comm and relays the information
    to the backend object. Then sends the return value back to HC_Comm via signals +
    slots, when HC_Comm then pushes onto the back of the isntrument's values dict"""

    sigReturnValues = pyqtSignal(str)
    sigReturnOnline = pyqtSignal(bool)
    sigReturnList = pyqtSignal(str, list, list)
    sigReturnLog = pyqtSignal(str, str)

    def __init__(self, backend):
        super().__init__()

        self.backend = backend

    def __repr__(self):
        return f"HC_CommWorker {self.backend.ID} @ {self.backend.connection_addr} {hex(id(self))}"

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.backend.connection_addr}"

    @pyqtSlot(str, str, float)
    def update_setting(self, setting: str, value: str, expire_time: float):
        """Transfers a setting and value to the backend"""

        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=SET: "{setting}" "{value}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.update_setting(setting, value)
        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(str, float)
    def command(self, cmd: str, expire_time: float):
        """Transfers a command to the backend"""

        if cmd in ["SYNC_BACKEND", "Misc?"]:
            self.sigReturnValues.emit(cmd)
            return

        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=CMD:"{cmd}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.command(cmd)

        # Set online to false if special 'offline' message comes across
        if ret_val == f"{self.backend.ID}-Offline":
            self.sigReturnOnline.emit(False)

        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(str, float)
    def write(self, msg: str, expire_time: float):
        """Transfers a command to be sent directly to the instrument to the backend"""
        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=WRT:"{msg}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.write(msg)

        # Set online to false if special 'offline' message comes across
        if ret_val == f"{self.backend.ID}-Offline":
            self.sigReturnOnline.emit(False)

        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(str, float)
    def query(self, msg: str, expire_time: float):
        """Transfers a query statement to be sent directly to the instrument to the backend"""
        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=QRY:"{msg}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.query(msg)

        # Set online to false if special 'offline' message comes across
        if ret_val == f"{self.backend.ID}-Offline":
            self.sigReturnOnline.emit(False)

        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(float)
    def try_connect(self, expire_time: float):
        """Is called by HC_Comm on a timer. Tells backend to check if is
        connected, else connect."""
        if time.time() > expire_time:  # Skip command if too old
            pass
        else:
            online = self.backend.try_connect()
            self.sigReturnOnline.emit(online)

    @pyqtSlot(str, float)
    def command_listdata(self, cmd: str, expire_time: float):
        """Transfers a command to the backend"""
        if time.time() > expire_time:  # Skip command if too old
            ret_val = (
                f'EXPIRED=CMD:"{cmd}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]',
                [],
                [],
            )
        else:
            ret_val = self.backend.command_listdata(cmd)
        self.sigReturnList.emit(ret_val[0], ret_val[1], ret_val[2])

    @pyqtSlot(str, float, str)
    def command_log(self, cmd: str, expire_time: float, param_str: str):
        """Transfers the command to the backend"""

        # print(f"\n\t\t\tCOMMAND_LOG::HC_COMMWORKER\t{param_str}\n")

        if time.time() > expire_time:  # Skip command if too old
            ret_val = f'EXPIRED=CMDLG:"{cmd}" \t[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]'
        else:
            ret_val = self.backend.command(cmd)

        self.sigReturnLog.emit(ret_val, param_str)

    @pyqtSlot()
    def close(self):
        """Tells backend to close the connection. Then reports if instrument is
        offline."""
        online = self.backend.close()
        self.sigReturnOnline.emit(online)
