---
title: "Hardware-Control: Instrument control and automation package"
tags:
  - Python
  - Instrument Control
  - Automation
  - Data Collection
authors:
  - name: Grant Giesbrecht
    orcid: 0000-0003-2885-4801
    affiliation: 1
  - name: Ariel Amsellem
    orcid: 0000-0003-3433-2698
    affiliation: 1
  - name: Timo Bauer
    orcid: 0000-0003-2094-2612
    affiliation: "1, 2"
  - name: Brian Mak
    orcid: 0000-0001-7095-8108
    affiliation: 1
  - name: Brian Wynne
    orcid: 0000-0002-0593-2195
    affiliation: 1
  - name: Zhihao Qin
    orcid: 0000-0002-5577-1270
    affiliation: 1
  - name: Arun Persaud
    orcid: 0000-0003-3186-8358
    affiliation: 1
affiliations:
  - name: Lawrence Berkeley National Laboratory, Berkeley, CA 94720, USA
    index: 1
  - name: Technische Universität Darmstadt, 64289 Darmstadt, Hesse, Germany
    index: 2
date: 21 October 2021
bibliography: paper.bib
---

# Summary

Conducting experimental research often relies on the control of
laboratory instruments to, for example, control power supplies, move
stages, and measure data. Tasks, such as data logging or parameter
scans, often needs to be automated. Being able to easily create a user
interface to the hardware and to be able to reuse code is highly
desirable.

`Hardware-Control` is a Python package for instrument control and
automation. It provides reusable user interfaces and instrument
drivers to simplify writing control programs. `Hardware-Control` uses
PyQt5, a GUI framework [@pyqt], to create fast and efficient user
interfaces compatible with most major operating
systems. `Hardware-Control` is also designed so that new drivers can
be easily added for new hardware and used with existing user
interfaces. The package also provides means for simplifying data
collection with automatic data logging, plotting, and several export
formats. `Hardware-Control` was designed with the use case of
experiments in our laboratory in mind. Normally, this involves reading
and setting voltages, controlling power supplies and oscilloscopes,
updating values on external triggers, and automatically updating these
values on a timer with time scales of about a second. The program is
currently not well-fitted to do any real-time or near real-time
communications with instruments or to handle data that is, for example,
being streamed from a camera. The program interacts best with
message-based devices or devices that already have pythons modules
available to control them. The program's instrument drivers can
send messages to sockets, usb ports, serial ports, etc. or call a python
function to read or write a setting or call a command on the
interface. Most of the drivers rely on the excellent pyvisa [@pyvisa]
library, but drivers can also utilize pymodbus [@pymodbus], or the built-in
socket library.

For handling the data, we rely on numpy [@numpy], pandas [@pandas],
and many other common libraries that are available on pypi to do data analysis.

For communications within the library we rely on ZMQ [@ZMQ].

# Statement of need

Commercial systems, such as LabVIEW, already exist, and they often do
provide a wide range of instrument drivers (either directly or from
the manufacturer of the devices). However, we have found that the
resulting code is often hard to version control (LabVIEW files are
binary, so code reviews and pull requests on services such as
bitbucket and github are therefore difficult). Furthermore, although
backend code can be shared between projects, complex user interfaces
cannot easily be reused. The software package presented here tries to
address these issues. Specifically, it makes reusing frontend code
easier, integrates well with git, and provides an easy built-in
scripting solution (via an optional python REPL that has full access
to the GUI and all backends). The control through python during
execution makes one-off complex parameter scans easy to implement. The
software also makes it easy to develop and test the code without any
hardware connected to the system by running a program in 'dummy mode'
in which the hardware does not need to be present. When in dummy mode,
the user can specify return values for certain opperations in order to
test the program.

Similar packages already exist (see Scopefoundry.org
[@Barnard], pymeasure [@pymeasure], yaq [@yaq], etc.). A good overview
of available python packages can be found at Ref [@overview]. However,
for our experiments we had a specific usecase in mind, and we
therefore decided to implement the provided solution. This software is
currently actively used in our group at Lawrence Berkeley National
Laboratory.  Although our group is using `Hardware-Control`
specifically in beam physics applications, we believe that the code
can be useful for other experiments too.

In principle, we plan to continue to develop the code in the future by
adding more instrument drivers and custom widgets since we believe
that the current solution provides us several benefits compared to
prior solutions and we have working setups at our test
stands. Therefore, we are also open to community
contributions. However, we are also open to merge our code into one of
the pre-existing code bases and plan to explore these options going
forward.

# Acknowledgements

The information, data, or work presented herein was funded by the Advanced Research
Projects Agency-Energy (ARPA-E), U.S. Department of Energy, under Contract No. DE-AC02-
05CH11231.

# References
