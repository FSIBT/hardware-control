import time
import logging

from PyQt5.QtCore import QTimer

logger = logging.getLogger(__name__)


class MeasurementDirector:
    def __init__(self, app):

        self.app = app

        # List of MeasurementRequest objects to measure in this datapoint
        self.queue = []

        # Describes state of director and if new scan is
        # possible. Options: Ready - can add requests or start scan,
        # Busy - scanning, can not take new measurements or start
        # again, Error - an error occured. Details in err_str, Failed
        # - Last measurement failed. Details in err_str
        self.state = "Ready"
        self.err_str = ""

        # set of all instruments currently processing a MeasurementRequest
        self.occ_instruments = set()

        # List of parameter_strings of MeasurementRequests in the
        # queue that need to be relaunched once enough time has
        # elapsed
        self.relaunch_list = set()

        self.cancel_batch = False

        self.relaunch_timer = QTimer()
        self.relaunch_timer.timeout.connect(self.check_relaunch)
        self.relaunch_timer.start(250)

    def measure(self, meas_req):
        """Add a measurement to the list of MeasurementRequests"""

        # Make sure director is ready to take new commands
        if self.state != "Ready":
            self.error(
                f"Director cannot add measurements because it is in"
                f" state '{self.state}'. Error code: {self.err_str}"
            )
            return False

        # Get the next index (also checks that dataset is not corrupted)
        next_idx = self.app.data_sets[meas_req.dataset_name].len_same()
        if next_idx == -1:
            logger.error(
                f"Dataset {meas_req.dataset_name} corrupted."
                f" Tracked parameters have unequal number of datapoints.",
                True,
            )
            return False

        # Record next index in measurement_index
        meas_req.measurement_index = next_idx

        # Add measurement request to queue
        self.queue.append(meas_req)

        return True

    def start(self):
        self.cancel_batch = False

        if self.state == "Ready":
            self.state = "Busy"
            self.launch_avail()

    def stop(self):
        pass

    def backend_return_log(self, retval: str, param_str: str):

        ds_name, inst_name, param_name, _ = self.parse_parameter(param_str)
        if ds_name is None:
            return

        # Find set in queue
        meas_req = self.find_measurement_request(param_str)
        if meas_req is None:
            return

        if ds_name not in self.app.data_sets:
            self.err_str = f"{ds_name} not in app.data_sets"
            self.state = "Error"
            return

        data_set = self.app.data_sets[ds_name]

        # Increment number of iterations
        meas_req.iterations += 1

        # ****** Decide what to do...

        # If one measurement failed and batch is canceled, delete this data
        if self.cancel_batch:

            # Delete this MR from queue
            self.queue.remove(meas_req)

            logger.debug(
                f"MeasurementRequest with param_str {param_str} deleted itself"
                f" due to batch cancelation"
            )

            self.occ_instruments.discard(inst_name)

            # If length is zero, set state to ready
            if len(self.queue) == 0:
                self.state = "Ready"

            return

        # Add last measurement to MeasurementRequest
        if not meas_req.add_point(retval):
            self.err_str = "Failed to add point. Return value was invalid."
            self.state = "Error"
            return

        # Check if conditions are satisfied
        if meas_req.conditions_met():

            val = ""
            sep_idx = retval.find("=")
            if sep_idx != -1:  # Separator was found...
                key = retval[0:sep_idx]
                val = retval[sep_idx + 1 :]
            else:
                logger.error(f"Failed to find '=' in {retval}")
                return False  # Separator was not found, return early

            # record data
            data_key = f"{inst_name}:{param_name}"
            if meas_req.keep_as_string:
                data_set.data[data_key].append(val)
            else:
                try:
                    data_set.data[data_key].append(float(val))
                except Exception:
                    logger.error(f"bad float {val}", exc_info=True)
                    self.err_str = (
                        "Failed to add point. Return value could"
                        " not be converted to a float."
                    )
                    self.state = "Error"
                    return

            # If requested, add timestamp. (Will be added when first value returns)
            if data_set.async_add_timestamp:
                # If time not added for this set of measurements yet, add now
                if len(data_set.data["time:time"]) < meas_req.measurement_index + 1:
                    data_set.data["time:time"].append(str(time.time()))

            # Double check that correct number of points exist - ie. index == len()
            if len(data_set.data[data_key]) != meas_req.measurement_index + 1:
                logger.error("Wrong number of items in array after measurement")
                self.err_str = (
                    "Wrong number of items in array after adding measurement."
                )
                self.state = "Error"
                return

            # erase from queue
            logger.debug(
                f"Removing MesurementRequest with parameter {meas_req.param_name}."
                f" My parameter string is {param_str}"
            )
            self.queue.remove(meas_req)
            self.occ_instruments.discard(inst_name)

            # Launch available MeasurementRequests
            self.launch_avail()

        # Check if too many attempts have occured
        elif meas_req.meas_failed():

            logger.info(
                f"MeasurementRequest with parameter string {param_str} failed."
                f" Canceling batch."
            )

            # Mark as failed
            self.err_str = "Measurement failed"
            self.state = "Fail"
            self.cancel_batch = True

            # erase request from queue
            self.queue.remove(meas_req)

            # Batch canceled - remove all requests that haven't been launched
            self.queue = [mr for mr in self.queue if mr.launched]

            self.occ_instruments.discard(inst_name)

            if len(self.queue) == 0:
                self.state = "Ready"

        else:
            self.relaunch_list.add(param_str)

    def launch_avail(self):

        # TODO: Consider allowing one instrument to measure two things simultaneously...

        # Set state to ready if all requests in the queue have been processed
        if len(self.queue) == 0:
            self.state = "Ready"
            return

        for mr in self.queue:
            if (not mr.launched) and (mr.inst_name not in self.occ_instruments):
                self.launch(mr)

    def launch(self, meas_req):
        """Send measurement command to backend."""

        m = meas_req
        instrument = self.app.get_instrument_by_name(m.inst_name)

        m.launched = True

        if instrument:
            self.occ_instruments.add(instrument.name)

            param_str = (
                f"{m.dataset_name}:{m.inst_name}:{m.param_name}:{m.measurement_index}"
            )
            instrument.comm.command_log(meas_req.inst_command, param_str)
        else:
            logger.warning(
                f"Invalid Instrument in MeasurementRequest. Instrument: '{m.inst_name}'"
            )
            return False

    def check_relaunch(self):
        """Called automaticlly periodically via Qtimer.

        When a measurement needs to be repeated to ensure
        steady-state, it is added to the relaunch_list. This checks
        everything in the relaunch list and relaunches it if enough
        time has ellapsed.

        """

        # keep track of the relaunched MRs so we can remove them later
        # from relaunch_list
        remove_from_list = []

        for rmr in self.relaunch_list:
            meas_req = self.find_measurement_request(rmr)
            if meas_req is None:
                continue

            # If enough time has ellapsed...
            if time.time() - meas_req.last_launch_time >= meas_req.steady_dt:
                meas_req.last_launch_time = time.time()
                self.launch(meas_req)
                remove_from_list.append(rmr)

        for rfl in remove_from_list:
            self.relaunch_list.discard(rfl)

    def parse_parameter(self, parameter_str: str):
        """Parse parameter string and check for errros.

        Parameters
        ----------
        parameter_str : str
            The parameter string

        Returns
        -------
        dataset_name : str
        instrument_name : str
        parameter_name : str
        measurement_index : int

        """

        components = parameter_str.split(":")
        if len(components) != 4:
            self.err_str = (
                "Wrong number of components returned in param_str by hc.Comm."
            )
            self.state = "Error"
            return None, None, None, None

        try:
            int(components[3])
        except ValueError:
            self.err_str = f"Failed to read measurement index '{components[3]}'."
            self.state = "Error"
            return None, None, None, None

        return components[0], components[1], components[2], int(components[3])

    def find_measurement_request(self, parameter: str):
        """Find the MeasurementRequest in self.queue.

        Parameters
        ----------
        parameter : str

        Returns
        -------
        hc.MeasurementRequest or None

        """

        ds_name, inst_name, param_name, meas_index = self.parse_parameter(parameter)
        if ds_name is None:
            return None

        for mr in self.queue:
            if (
                mr.dataset_name == ds_name
                and mr.inst_name == inst_name
                and mr.param_name == param_name
                and mr.measurement_index == meas_index
            ):
                return mr

        self.err_str = (
            f"Failed to find MeasurementRequest specified"
            f" by parameteter string '{parameter}'."
        )
        self.state = "Error"
        return None
