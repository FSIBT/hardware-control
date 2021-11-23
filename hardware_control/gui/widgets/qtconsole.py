"""
    .. image:: /images/widgets/qtconsole.png
"""

import numpy as np
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager


class Qtconsole(RichJupyterWidget):
    """A python interface that allows for interaction with the main app."""

    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel = self.kernel_manager.kernel

        self.kernel.shell.banner1 += """
        Direct python interface

        You can access variables from the app through the main app widget

        app: main app widget
        np:  numpy

        To see a list of all instruments and parameters use_prefix
        app.list_instruments()
        app.list_instrument_parameters(<instrument name>)

        To access values for a specific setting:
        app.get_instrument_parameter(<inst>, <parameter>)

        To access the set value for a parameter (not the one that is read back)
        app.get_instrument_parameter(<inst>, <parameter>, return_set_value=True)

        To execute a command on an instrument:
        app.call_instrument_command(<inst>, <command>)

        Note: some commands fail with a logging.error message and will
        just return, which can result in unexpected behavior.
        """
        self.kernel.gui = "qt"
        self.kernel.shell.push({"np": np, "app": app})
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
