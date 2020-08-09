import time
import logging

from PyQt5.QtCore import QTimer

logger = logging.getLogger(__name__)


class MeasurementDirector:
    def __init__(self, app):

        # List of MeasurementRequest objects to measure in this datapoint
        self.queue = []

        # Describes state of director and if new scan is
        # possible. Options: Ready - can add requests or start scan,
        # Busy - scanning, can not take new measurements or start
        # again, Error - an error occured. Details in err_str, Failed
        # - Last measurement failed. Details in err_str
        self.state = "Ready"
        self.err_str = ""

        # List of all instruments currently processing a MeasurementRequest
        self.occ_instruments = []

        # List of parameter_strings of MeasurementRequests in the
        # queue that need to be relaunched once enough time has
        # elapsed
        self.relaunch_list = []

        self.cancel_batch = False

        self.app = app

        self.relaunch_timer = QTimer()
        self.relaunch_timer.timeout.connect(self.check_relaunch)
        self.relaunch_timer.start(250)

    def measure(self, meas_req):
        """Add a measurement to the list of MeasurementRequests"""

        # MAke sure director is ready to take new commands
        if self.state != "Ready":
            self.error(
                f"Director cannot add measurements because it is in"
                f" state '{self.state}'. Error code: {self.err_str}"
            )
            return False

        # Get the next index (also checks that dataset is not corrupted)
        next_idx = self.app.data_sets[meas_req.dataset_name].len()
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

    def get_state(self):
        return self.state

    def backend_return_log(self, retval: str, param_str: str):

        # Interpret 'param_str' to get variables to match in MeasurementRequest
        components = param_str.split(":")  # Split the command up into tokens
        if len(components) != 4:
            self.err_str = (
                "Wrong number of components returned in param_str by hc.Comm."
            )
            self.state = "Error"
            return

        m_idx = -1
        try:
            m_idx = int(components[3])
        except:
            midx_str = components[3]
            self.err_str = f"Failed to read measurement index '{midx_str}'."
            self.state = "Error"
            return

        # Find set in queue
        idx = -1
        for midx, mr in enumerate(self.queue):  # For evert meas. request...
            if (
                mr.dataset_name == components[0]
                and mr.inst_name == components[1]
                and mr.param_name == components[2]
                and mr.measurement_index == m_idx
            ):  # If identifiers match...
                idx = midx
                # The request was found, record its index
        if idx == -1:
            self.err_str = (
                f"Failed to find MeasurementRequest specified by"
                f" parameteter string '{param_str}'."
            )
            self.state = "Error"
            return

        # Increment number of iterations
        self.queue[idx].iterations += 1

        # ****** Decide what to do...

        # If one measurement failed and batch is canceled, delete this data
        if self.cancel_batch:

            # Delete this MR from queue
            self.queue.pop(idx)

            logger.debug(
                f"MeasurementRequest with param_str {param_str} deleted itself"
                f" due to batch cancelation"
            )

            # Remove instrument from occupied_instruments list
            inst_idx = 0
            while inst_idx < len(
                self.occ_instruments
            ):  # For each name in occupied instrumnt list...
                if (
                    self.occ_instruments[inst_idx] == components[1]
                ):  # IF matches last instrument...
                    self.occ_instruments.pop(inst_idx)  # Remove from list
                else:
                    inst_idx += 1

            # If length is zero, set state to ready
            if len(self.queue) == 0:
                self.state = "Ready"

            return

        # Add last measurement to MeasurementRequest
        if not self.queue[idx].add_point(retval):
            self.err_str = "Failed to add point. Return value was invalid."
            self.state = "Error"
            return

        # Check if conditions are satisfied
        if self.queue[idx].conditions_met():

            val = ""
            sep_idx = retval.find("=")
            if sep_idx != -1:  # Separator was found...
                key = retval[0:sep_idx]
                val = retval[sep_idx + 1 :]
            else:
                logger.error(f"Failed to find '=' in {retval}")
                return False  # Separator was not found, return early

            # record data
            data_key = components[1] + ":" + components[2]
            if self.queue[idx].keep_as_string:
                self.app.data_sets[components[0]].data[data_key].append(val)
            else:
                try:

                    if not data_key in self.app.data_sets[components[0]].data:
                        self.app.data_sets[components[0]].data[data_key] = []

                    self.app.data_sets[components[0]].data[data_key].append(float(val))

                except Exception as e:
                    logger.error(f"bad float {val}\n\t{str(e)}")
                    self.err_str = (
                        "Failed to add point. Return value could"
                        " not be converted to a float."
                    )
                    self.state = "Error"
                    return

            # If requested, add timestamp. (Will be added when first value returns)
            if self.app.data_sets[components[0]].async_add_timestamp:

                # If time column not yet added, add now
                if not "time:time" in self.app.data_sets[components[0]].data:
                    self.app.data_sets[components[0]].data["time:time"] = []

                # If time not added for this set of measurements yet, add now
                if (
                    len(self.app.data_sets[components[0]].data["time:time"])
                    < self.queue[idx].measurement_index + 1
                ):
                    self.app.data_sets[components[0]].data["time:time"].append(
                        str(time.time())
                    )

            # Double check that correct number of points exist - ie. index == len()
            if (
                len(self.app.data_sets[components[0]].data[data_key])
                != self.queue[idx].measurement_index + 1
            ):
                logger.error("Wrong number of items in array after measurement")
                self.err_str = (
                    "Wrong number of items in array after adding measurement."
                )
                self.state = "Error"
                return

            # erase from queue
            mes_str = self.queue[idx].param_name
            logger.debug(
                f"Removing index {idx} with parameter {mes_str}. My parameter"
                f" string is {param_str}"
            )
            self.queue.pop(idx)

            # Remove instrument from occupied_instruments list
            inst_idx = 0
            while inst_idx < len(
                self.occ_instruments
            ):  # For each name in occupied instrumnt list...
                if (
                    self.occ_instruments[inst_idx] == components[1]
                ):  # IF matches last instrument...
                    self.occ_instruments.pop(inst_idx)  # Remove from list
                else:
                    inst_idx += 1

            # Launch available MeasurementRequests
            self.launch_avail()

        # Check if too many attempts have occured
        elif self.queue[idx].meas_failed():

            logger.info(
                f"MeasurementRequest with parameter string {param_str} failed."
                f" Canceling batch."
            )

            # Mark as failed
            self.err_str = "Measurement failed"
            self.state = "Fail"
            self.cancel_batch = True

            # erase request from queue
            self.queue.pop(idx)

            # Batch canceled - remove all requests that haven't been launched
            midx = 0
            # For each request...
            while midx < len(self.queue):
                # If request hasn't been launched...
                if not self.queue[midx].launched:
                    # Remove request
                    self.queue.pop(midx)
                else:
                    midx += 1

            # Remove instrument from occupied_instruments list
            inst_idx = 0
            while inst_idx < len(
                self.occ_instruments
            ):  # For each name in occupied instrumnt list...
                if (
                    self.occ_instruments[inst_idx] == components[1]
                ):  # IF matches last instrument...
                    self.occ_instruments.pop(inst_idx)  # Remove from list
                else:
                    inst_idx += 1

            if len(self.queue) == 0:
                self.state = "Ready"

        else:

            # Relaunch MR
            if not param_str in self.relaunch_list:
                self.relaunch_list.append(param_str)

    def relaunch(self, meas_req):

        # Find instrument....
        instr_idx = -1
        for idx, inst in enumerate(self.app.instruments):
            if meas_req.inst_name == inst.name:
                instr_idx = idx

        if instr_idx != -1:
            param_str = (
                meas_req.dataset_name
                + ":"
                + meas_req.inst_name
                + ":"
                + meas_req.param_name
                + ":"
                + str(meas_req.measurement_index)
            )
            self.app.instruments[instr_idx].comm.command_log(
                meas_req.inst_command, param_str
            )
        else:
            logger.warning(
                f"Invalid Instrument in MeasurementRequest."
                f" Instrument: '{meas_req.inst_name}'"
            )
            return False

    def launch_avail(self):

        # TODO: Consider allowing one instrument to measure two things simultaneously...

        # Set state to ready if all requests in the queue have been processed
        if len(self.queue) == 0:
            self.state = "Ready"
            return

        for mr_idx, mr in enumerate(
            self.queue
        ):  # For every MeasurementRequest in queue...
            if (not mr.launched) and (
                mr.inst_name not in self.occ_instruments
            ):  # IF the request has NOT been launched and its instrument is NOT occupied...
                self.queue[mr_idx].launched = True  # Mark launched as true
                self.launch(mr)  # Launch request

    def launch(self, meas_req):

        # Find instrument....
        instr_idx = -1
        for idx, inst in enumerate(self.app.instruments):
            if meas_req.inst_name == inst.name:
                instr_idx = idx  # Record index
                self.occ_instruments.append(
                    inst.name
                )  # Add to list of occupied instruments

        if instr_idx != -1:
            param_str = (
                meas_req.dataset_name
                + ":"
                + meas_req.inst_name
                + ":"
                + meas_req.param_name
                + ":"
                + str(meas_req.measurement_index)
            )
            self.app.instruments[instr_idx].comm.command_log(
                meas_req.inst_command, param_str
            )
        else:
            logger.warning(
                f"Invalid Instrument in MeasurementRequest."
                f" Instrument: '{meas_req.inst_name}'"
            )
            return False

    def check_relaunch(self):
        """Called automaticlly periodically. When a measurement needs to be repeated to ensure
        steady-state, it is added to the relaunch_list. This checks everything in the relaunch
        list and relaunches it if enough time has ellapsed"""

        # BTW, keep track of the relaunch MRs so you can remove from the relaunch list
        remove_from_list = []

        # Scan through every item...
        for rmr_idx, rmr in enumerate(self.relaunch_list):

            components = rmr.split(":")  # Split the command up into tokens
            if len(components) != 4:
                self.err_str = (
                    "Wrong number of components returned in param_str by hc.Comm."
                )
                self.state = "Error"
                return

            m_idx = -1
            try:
                m_idx = int(components[3])
            except:
                midx_str = components[3]
                self.err_str = f"Failed to read measurement index '{midx_str}'."
                self.state = "Error"
                return

            # Find set in queue
            idx = -1
            for midx, mr in enumerate(self.queue):  # For every meas. request...
                # print(len(self.queue))
                if (
                    mr.dataset_name == components[0]
                    and mr.inst_name == components[1]
                    and mr.param_name == components[2]
                    and mr.measurement_index == m_idx
                ):  # If identifiers match...
                    idx = midx
                    # The request was found, record its index
            if idx == -1:
                self.err_str = (
                    f"Failed to find MeasurementRequest specified"
                    f" by parameteter string '{rmr}'."
                )
                self.state = "Error"
                return

            # If enough time has ellapsed...
            if (
                time.time() - self.queue[idx].last_launch_time
                >= self.queue[idx].steady_dt
            ):
                self.queue[idx].last_launch_time = time.time()
                self.relaunch(self.queue[idx])  # Relaunch measurement

                remove_from_list.append(rmr_idx)

        # Everything has been processed - remove the relaunched items
        for rfl in reversed(remove_from_list):
            self.relaunch_list.pop(rfl)
