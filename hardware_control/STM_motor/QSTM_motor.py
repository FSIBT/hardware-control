from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QInputDialog


class QSTM_control(QHBoxLayout):
    """Creates a goto, +-1 and +-5 button"""

    def __init__(self, motor=None):
        super().__init__()

        self.motor = motor

        self.goto_button = QPushButton('Go to...')
        self.up1_button = QPushButton('+1')
        self.down1_button = QPushButton('-1')
        self.up5_button = QPushButton('+5')
        self.down5_button = QPushButton('-5')

        self.addWidget(self.goto_button)
        self.addWidget(self.up1_button)
        self.addWidget(self.down1_button)
        self.addWidget(self.up5_button)
        self.addWidget(self.down5_button)

        self.up1_button.clicked.connect(self.up1)
        self.down1_button.clicked.connect(self.down1)
        self.up5_button.clicked.connect(self.up5)
        self.down5_button.clicked.connect(self.down5)

    def link(self, motor):
        self.motor = motor
        self.goto_button.clicked.connect(lambda: self.goto(self.motor))

    def moveto(self, steps):
        if self.motor:
            self.motor.step(steps)
        else:
            print('STM motor: GUI not connected')

    def goto(self, motor):
        num1, ok = QInputDialog.getInt(None, "Go to...", "Enter current value")

        if ok:
            num2, ok = QInputDialog.getInt(None, "Go to", "Go to...")
            if ok:
                diff = num2 - num1
                self.moveto(diff*motor.rotation_per_digit)
                motor.position = num2

    def up1(self):
        self.moveto(200)

    def down1(self):
        self.moveto(-200)

    def up5(self):
        self.moveto(1000)

    def down5(self):
        self.moveto(-1000)
