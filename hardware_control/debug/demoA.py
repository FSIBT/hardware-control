#!/usr/bin/env python3
"""
Usage:
demoA.py [<port>]

"""

import logging
import sys

import docopt

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QPushButton,
    QListWidget,
)
from PyQt5.QtCore import pyqtSlot
from PyQt5 import QtNetwork


logger = logging.getLogger(__name__)


class QDemoA(QMainWindow):
    def __init__(self, app, port):
        super().__init__()
        self.app = app
        self.accept = True
        self.enable = False

        self.server = QtNetwork.QTcpServer()

        self.setWindowTitle("Demo A")

        self.main_widget = QWidget(self)

        self.button_accept = QPushButton("Accept commands yes/no")
        self.button_accept.clicked.connect(self.toggle_commands)

        self.list = QListWidget()

        self.grid = QVBoxLayout()
        self.grid.addWidget(self.button_accept)
        self.grid.addWidget(self.list)

        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)

        self.server.listen(port=port)
        self.server.newConnection.connect(self.handle_connect)

        self.list.addItem("Ready")
        self.show()

    def toggle_commands(self):
        self.accept = not self.accept

        if self.accept:
            self.button_accept.setText("Accept commands yes")
        else:
            self.button_accept.setText("Accept commands no")

    def handle_connect(self):
        print("got connection")
        socket = self.server.nextPendingConnection()
        self.socket = Socket(self, socket)

        self.list.addItem("got connection")

    def close(self):
        pass


class Socket:
    def __init__(self, parent, socket):
        self.parent = parent
        self.socket = socket
        self.socket.readyRead.connect(self.readRequest)
        self.socket.disconnected.connect(self.deleteLater)
        self.data = ""

    def readRequest(self):
        rawdata = self.socket.readAll()
        print(rawdata)

        self.data += rawdata.data().decode("ascii")
        if "\n" not in self.data:
            return

        self.data = self.data.split("\n")[0]
        self.parent.list.addItem(f"->{self.data}<-")

        # handle settings and commands
        if self.data == "CH1?":
            print("in ch1?")
            out = f"{self.parent.enable}\n"
            nr = self.socket.write(out.encode("ascii"))
            print(f"wrote {nr} bytes :  {out}", flush=True)
            self.data = ""
            return
        if self.data.startswith("CH1"):
            print("in ch1")
            value = self.data.split(":")
            print(value)
            if len(value) == 2:
                value = value[1]
            else:
                self.data = ""
                return
            print("before convert")
            self.parent.enable = value == "True"
            print("after convert", self.parent.enable)
            self.data = ""
            return
        print("should not be here")

    def deleteLater(self):
        self.socket.close()


def start_demoA(port=7123):
    app = QApplication([])
    ex = QDemoA(app, port=port)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


if __name__ == "__main__":
    config = docopt.docopt(__doc__)
    port = config["<port>"]
    if port is None:
        port = 7123
    start_demoA(port=port)
