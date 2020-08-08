from PyQt5.QtWidgets import QGridLayout, QWidget
import sys

import hardware_control.backends as hc_back
import hardware_control.gui as hc


class DemoProgram(hc.MainWindow):
    def __init__(self, app):

        super().__init__(app)

        scope_be = hc_back.Keysight_4000X("192.168.0.2")

        self.scope_wdgt = hc.Oscilloscope(app, scope_be, "Oscilloscope")

        # Create layout, add oscilloscope to row=0, column=0
        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.scope_wdgt, 0, 0)

        self.main_widget = QWidget(self)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

        self.show()

    def close(self):
        print("Closing")
        self.app.close()


def main():

    app = hc.App(dummy=True)
    demo_prog = DemoProgram(app)

    app.aboutToQuit.connect(demo_prog.close)
    sys.exit(app.exec_())


main()
