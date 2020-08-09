import logging
import time

from colorama import Fore, Style

from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QObject, QTimer

logger = logging.getLogger(__name__)


class Comm(QObject):
    """Class to manage communication between two threads.

    This object is used to automate creating threads and communication
    objects.  By calling this object's functions, data can be safely
    transfered between the main thread and communication threads. The
    intended usage is for an hc.Comm object to be created by each
    hc.Instrument class and use the hc.Comm to communicate with a
    backend in a separate thread.

    Parameters
    ----------
    backend
        Instrument backend. The commands passed through hc.Comm will be
        forwarded to this object. 'backend' should be a child of hc_back.Backend
    instrument
        The frontend/widget using this hc.Comm object for communication
    try_connect_period
        The time in milliseconds between attempts to connect to the instrument
    lock_until_sync
        If true, will block all calls to self.update_setting until the string
        'SYNC_BACKEND' is returned from the backend. This can be used by the
        widget to determine when the backend first comes online and when to
        initialize the backend and widget states.

    """

    sigUpdateSettings = pyqtSignal(str, str, float)
    sigCommand = pyqtSignal(str, float)
    sigWrite = pyqtSignal(str, float)
    sigQuery = pyqtSignal(str, float)
    sigTryConnect = pyqtSignal(float)
    sigCommandList = pyqtSignal(str, float)
    sigCommandLog = pyqtSignal(str, float, str)
    sigClose = pyqtSignal()

    def __init__(
        self, backend, instrument, try_connect_period=5000, lock_until_sync=False
    ):
        super().__init__()
        self.backend = backend
        self.instruments = [instrument]  # Calling instrument UI (eg. hc.scope)
        self.backend_model = backend.ID
        self.try_connect_period = try_connect_period

        self.lock_until_sync = lock_until_sync

        self.expire_time = 40
        self.list_expire_time = 5

        self.worker = CommWorker(self.backend)
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
        return (
            f"Comm {self.backend_model} @ {self.backend.connection_addr}"
            + f"  {hex(id(self))}"
        )

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.backend.connection_addr}"

    def addWidget(self, new_instrument):
        """Adds a new instrument to hc.Comm 'instruments' list.

        When hc.Comm gets a reply, it will send reply to all listed instruments.
        This function adds an instrument to that list.

        Parameters
        ----------
        new_instrument
            Intrument to add to hc.Comm instrument list"""

        self.instruments.append(new_instrument)

    def close(self):
        """ Safely closes the backend and thread.

        Sends the close signal to the backend's close function, stops attempting
        to connect to the instrument, closes any open connections, then kills
        the worker thread.
        """
        logger.debug(
            f"Closing hc.Comm with backend of class '{self.backend_model}' "
            + f"connected via {self.backend.connection_type} "
            + f"at address '{self.backend.connection_addr}'."
        )
        self.try_connect_timer.stop()  # Stop
        self.sigClose.emit()
        self.worker_thread.quit()  # Kill thread
        if self.instruments[0].app.print_close_info:
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
        if self.instruments[0].app.print_close_info:
            print(
                f"\r\t'{self.instruments[0].name}': Closed    \t\t\t"
                + "{:.2f}".format(time.time() - start_time)
                + " sec    "
            )

    def update_setting(self, setting: str, value: str):
        """ Transfers a new value for a specific setting to the worker thread

        Parameters
        ----------
        setting : str
            Name of setting to change
        value : str
            New value for setting
        """

        if self.lock_until_sync:
            logger.debug(
                f"Instrument {self.instruments[0].name} block update_setting"
                f" because UI has not yet synced with instrument"
            )

        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'update_setting()'"
            f" for setting '{setting}' and sent message '{value}'."
        )
        self.sigUpdateSettings.emit(setting, value, time.time() + self.expire_time)

    def command(self, cmd: str):
        """ Sends a command to the backend in the worker thread

        Parameters
        ----------
        cmd
            Command string to send to backend"""
        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'command()'"
            f" and sent command: '{cmd}'."
        )
        self.sigCommand.emit(cmd, time.time() + self.expire_time)

    def write(self, msg: str):
        """ Directly writes a message to the instrument

        Sends a message to the instrument. The string is not processed by the
        backend and is immediately sent to the instrument. This function should
        not be needed unless the user needs to use a command or feature in the
        instrument that is not implimented in the widget or backend.
        """
        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'write()'"
            f" and sent message: '{msg}'."
        )
        self.sigWrite.emit(msg, time.time() + self.expire_time)

    def query(self, msg: str):
        """ Directly queries the instrument

        Sends a message to the instrument. The string is not processed by the
        backend and is immediately sent to the instrument. This function should
        not be needed unless the user needs to use a command or feature in the
        instrument that is not implimented in the widget or backend."""
        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'query()'"
            f" and sent message: '{msg}'."
        )
        self.sigQuery.emit(msg, time.time() + self.expire_time)

    def try_connect(self):
        """Called on a timer, this function tells the backend to connect to
        the instrument.

        """
        self.sigTryConnect.emit(time.time() + self.expire_time)

    def command_listdata(self, cmd: str):
        """ Send a command to the backend which expects two lists to be returned.

        Sends a command to the worker in the worker thread just like command(),
        but returns two lists instead of a string."""
        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'command_listdata()'"
            f" and sent command: '{cmd}'."
        )
        self.sigCommandList.emit(cmd, time.time() + self.list_expire_time)

    def command_log(self, cmd: str, param_str: str):
        """Sends a command to the worker in the worker thread with details to
        help data acquisition.

        """

        # print(f"\n\t\tCOMMAND_LOG::hc.COMM\t{param_str}\n")

        logger.debug(
            f"Instrument: {self.instruments[0].name} called 'command()'"
            f" and sent command: '{cmd}'."
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
            f"Instrument: {self.instruments[0].name} received return"
            f" from backend '{self.backend_model}'. Return message: {retval}"
        )
        for instr in self.instruments:
            instr.backend_return(retval)

    @pyqtSlot(bool)
    def backend_return_online(self, connected: bool):
        """Gets called by the worker after the worker hears from the
        instrument if it successfully connected.  Updates the state of
        the instrument - ie. if it is or is not online

        """
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

        # print(f"\n\t\t\t\tBACKEND_RETURN_LOG::COMM\t{param_str}\n")
        if len(self.instruments) > 0:
            self.instruments[0].app.director.backend_return_log(retval, param_str)

            logger.debug(
                f"Instrument: {self.instruments[0].name} received return"
                f" from backend '{self.backend_model}'. Return message: {retval}"
            )
        for instr in self.instruments:
            instr.backend_return(retval)


class CommWorker(QObject):
    """Uses signals + slots to receive data from hc.Comm and relays the
    information to the backend object. Then sends the return value
    back to hc.Comm via signals + slots, when hc.Comm then pushes onto
    the back of the isntrument's values dict

    """

    sigReturnValues = pyqtSignal(str)
    sigReturnOnline = pyqtSignal(bool)
    sigReturnList = pyqtSignal(str, list, list)
    sigReturnLog = pyqtSignal(str, str)

    def __init__(self, backend):
        super().__init__()

        self.backend = backend

    def __repr__(self):
        return (
            f"CommWorker {self.backend.ID}"
            f" @ {self.backend.connection_addr} {hex(id(self))}"
        )

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.backend.connection_addr}"

    @pyqtSlot(str, str, float)
    def update_setting(self, setting: str, value: str, expire_time: float):
        """Transfers a setting and value to the backend"""

        if time.time() > expire_time:  # Skip command if too old
            ret_val = (
                f'EXPIRED=SET: "{setting}" "{value}" \t'
                f"[Exec: {time.time()}, Exp: {expire_time}] [{self.backend.ID}]"
            )
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
            ret_val = (
                f'EXPIRED=CMD:"{cmd}" \t[Exec: {time.time()},'
                f" Exp: {expire_time}] [{self.backend.ID}]"
            )
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
            ret_val = (
                f'EXPIRED=WRT:"{msg}" \t[Exec: {time.time()},'
                f" Exp: {expire_time}] [{self.backend.ID}]"
            )
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
            ret_val = (
                f'EXPIRED=QRY:"{msg}" \t[Exec: {time.time()},'
                f" Exp: {expire_time}] [{self.backend.ID}]"
            )
        else:
            ret_val = self.backend.query(msg)

        # Set online to false if special 'offline' message comes across
        if ret_val == f"{self.backend.ID}-Offline":
            self.sigReturnOnline.emit(False)

        self.sigReturnValues.emit(ret_val)

    @pyqtSlot(float)
    def try_connect(self, expire_time: float):
        """Is called by hc.Comm on a timer. Tells backend to check if is
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
                f'EXPIRED=CMD:"{cmd}" \t[Exec: {time.time()},'
                f" Exp: {expire_time}] [{self.backend.ID}]",
                [],
                [],
            )
        else:
            ret_val = self.backend.command_listdata(cmd)
        self.sigReturnList.emit(ret_val[0], ret_val[1], ret_val[2])

    @pyqtSlot(str, float, str)
    def command_log(self, cmd: str, expire_time: float, param_str: str):
        """Transfers the command to the backend"""

        # print(f"\n\t\t\tCOMMAND_LOG::COMMWORKER\t{param_str}\n")

        if time.time() > expire_time:  # Skip command if too old
            ret_val = (
                f'EXPIRED=CMDLG:"{cmd}" \t[Exec: {time.time()},'
                f" Exp: {expire_time}] [{self.backend.ID}]"
            )
        else:
            ret_val = self.backend.command(cmd)

        self.sigReturnLog.emit(ret_val, param_str)

    @pyqtSlot()
    def close(self):
        """Tells backend to close the connection. Then reports if instrument is
        offline."""
        online = self.backend.close()
        self.sigReturnOnline.emit(online)
