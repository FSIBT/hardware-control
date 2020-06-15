class PlotTool(QWidget):
    """A single matplotlib figure"""

    def __init__(self, parent=None, active=True):
        super().__init__()

        self.normalize = False
        self.autoscale = True

        self.fig, self.axes = plt.subplots()
        self.plot = FigureCanvas(self.fig)
        self.plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.nav = NavigationToolbar(self.plot, self)
        self.nav.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # custom toolbar
        self.controls = QHBoxLayout()
        self.normalizebutton = QPushButton("normalize")
        self.normalizebutton.clicked.connect(self.toggle_normalize)
        self.normalizebutton.setCheckable(True)
        self.autoscalebutton = QPushButton("autoscale")
        self.autoscalebutton.clicked.connect(self.toggle_autoscale)
        self.autoscalebutton.setCheckable(True)
        self.autoscalebutton.setChecked(True)
        self.controls.addWidget(self.normalizebutton)
        self.controls.addWidget(self.autoscalebutton)
        self.controls.addStretch(1)

        self.vbox = QVBoxLayout()
        self.vbox.addLayout(self.controls)
        self.vbox.addWidget(self.nav)
        self.vbox.addWidget(self.plot)
        self.vbox.addSpacing(50)

        self.setLayout(self.vbox)

        self.elements_and_name = []
        self.data = defaultdict(deque)

        self.interval = 1000
        self.active = active

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.add_data)

        # always get data
        if self.active:
            self.timer.start(self.interval)

    def add_element(self, element, name):
        self.elements_and_name.append((element, name))

    def add_data(self):
        t = time.time()
        for e, n in self.elements_and_name:
            self.data[n].append([t, getattr(e, n)])

        # only save the last 10000 data points
        for k, v in self.data.items():
            while len(v) > 10000:
                v.popleft()

    def toggle_autoscale(self):
        self.autoscale = not self.autoscale

    def toggle_normalize(self):
        self.normalize = not self.normalize

    def update(self):
        xleft, xright = self.axes.get_xlim()
        ybottom, ytop = self.axes.get_ylim()
        self.axes.clear()
        self.axes.set_xlabel("Time")
        for k, v in self.data.items():
            myX = np.array([x[0] for x in v])
            myY = np.array([x[1] for x in v])
            if self.normalize and len(myY) and myY.max() > 0:
                myY = myY / myY.max()
            self.axes.plot_date(
                epoch2num(myX), myY, "o-", label=k, tz="America/Los_Angeles"
            )
        self.axes.legend(loc="best")
        if not self.autoscale:
            self.axes.set_xlim([xleft, xright])
            self.axes.set_ylim([ybottom, ytop])
        self.plot.draw()
