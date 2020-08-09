import logging
import time

import numpy as np

logger = logging.getLogger(__name__)


class MeasurementRequest:
    """Describes state information for a single measurement. This state
    object is passed to hc.Comm's command_log() function to
    communicate options such as if to repeat measurement and check for
    stability, how many stable points to find, how to define 'stable',
    etc etc. hc.Comm keeps a list of these objects so it doesn't need
    to be passed back and forth between the backend. Instead, a unique
    interger called the measurement_id which is used to link a call to
    backend_return_log() to the corresponding MeasurementState
    object.

    """

    def __init__(
        self,
        dataset_name: str,
        instrument_name: str,
        parameter_name: str,
        cmd_str: str,
        steady_points: int = 3,
        equip_dt: float = 0.1,
        tol: float = 0.1,
        max_iterations: int = 10,
    ):

        # *** These parameters tell the director how to query and save the data
        self.dataset_name = dataset_name
        self.inst_name = instrument_name
        self.param_name = parameter_name
        # the index in the dataset arrays in which the measurement will be stored
        self.measurement_index = -1
        self.inst_command = cmd_str  # Command to send to the instrument

        # *** These parameters tell the director how to verify the measurement's stability
        # Number of points that must be measured and considered 'steady'
        self.steady_points = steady_points
        # change in time between points checked for steady state condition
        self.steady_dt = equip_dt
        # Tolerance (in percent/100 ie from 0 to 1) by which points
        # can differ and still be considered 'steady'
        self.tol = tol
        # Number of iterations, ie measurements, that have occcured
        self.iterations = 0
        # Maximum number of iterations before returns failure condition
        self.max_iterations = max_iterations
        # Previous data values measured (for comparison for steady
        # state determination)
        self.prev_data = []
        # Instructs MeasurementDirector to keep the returned data as
        # a string instead of a double. Disables all stability checks
        self.keep_as_string = False
        # Tells the MeasurementDirector if this request has already
        # been handled or if it needs to be sent to a backend
        self.launched = False
        # Tells the MeasurementDirector to count the point as corrupt
        # if convertable to float and > 1e35
        self.cap_at_1e35 = True

        self.last_launch_time = time.time()

    def __repr__(self):
        return (
            f"MeasurementRequest from {self.dataset_name} {self.inst_name}"
            f" {self.param_name} @ {hex(id(self))}"
        )

    def __str__(self):
        # return f"{self.manufacturer} {self.model}"
        return f"{self.dataset_name} {self.inst_name} {self.param_name}"

    def add_point(self, retval: str):
        """Checks if the last return value (passed as 'retva') qualifies as a steady
        state condition and adds the point to self.prev_data for later analysis.

        If the point can not be added (no separator found or can't convert to float),
        the function returns prematurely."""

        # Find separator and calculate val
        val = ""
        sep_idx = retval.find("=")
        if sep_idx != -1:  # Separator was found...
            key = retval[0:sep_idx]
            val = retval[sep_idx + 1 :]
        else:
            return False  # Separator was not found, return early

        # Try to convert returned value to a float, add to list
        try:
            self.prev_data.append(float(val))
        except:
            return False

        return True

    def conditions_met(self):
        """Determines if the completion criteria have been met, or if more points are
        required."""

        # If specified to keep data as string, return True if data
        # already aquired b/c all stability checks are disabled
        if self.keep_as_string and len(self.prev_data) > 0:
            return True

        # If less than the required number of points have been collected, then
        # the conditions can not have been met
        if len(self.prev_data) < self.steady_points:
            return False

        # Determine if all required points are in the steady state
        # Get the last however many datapoints must be within spec
        pts = self.prev_data[self.steady_points * -1 :]
        # Calculate the mean - this will be used in determining an
        # absolute value for the tolerance
        center = np.mean(pts)
        for p in pts:  # Check each point...
            if (abs(p - center) / center) > self.tol:  # If one point is out of spec
                return False
                # Report conditions are NOT met

            # Or if one point is greater that 1e35 and flag is set,
            # report conditions failed
            if p > 1e35 and self.cap_at_1e35:
                return False

        return True
        # Otherwise, all reqired points were within spec

    def meas_failed(self):
        return self.iterations >= self.max_iterations
