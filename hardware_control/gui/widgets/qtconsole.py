import numpy as np
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager


class Qtconsole(RichJupyterWidget):
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

        """
        self.kernel.gui = "qt"
        self.kernel.shell.push({"np": np, "app": app})
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
