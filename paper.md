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
stages, and measure data. Task, such as data logging or parameter
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
collection with automatic data logging, plotting, and many export
formats. `Hardware-Control` was designed with the use case of
experiments in our laboratory in mind. Normally this involves reading
and setting voltages using power supplies and, for example,
oscilloscopes and updating these values on external triggers or
automatically on a timer on a time scale of a second. The program is
currently not well fitted to do any real-time or near real-time
communications with instruments or to handle data that is being
streamed, for example, from a camera. The focus of the program is on
message-based devices or devices already have pythons modules
available to control them. That is, an instrument driver can either
send messages to a socket, usb or serial ports, etc. or call a python
function to read or write a setting or call a command on the
interface. Most of the drivers rely on the excellent pyvisa [@pyvisa]
library, but we also have a driver using pymodbus [@pymodbus], or the built-in
socket library.

For handling the data, we rely on numpy [@numpy], pandas [@pandas],
and many other libraries that are available on pypi to do data analysis.

For communications within the library we rely on ZMQ [@ZMQ].

# Statement of need

Commercial systems, such as LabVIEW, already exist and they often do
provide a wide range of instrument drivers (either directly or from
the manufacturer of the devices). However, we found that the resulting
code is often hard to version control (LabVIEW files are binary and
code reviews and pull requests on services such as bitbucket and
github are therefore difficult). Furthermore, although backend code
can be easily shared between projects, complex user interfaces can not
easily be reused. The software package presented here treis to address
these issues. Specifically, it makes reusing frontend code easier,
integrates well with git (pure python code), and provides an easy
built-in scripting solution (via an optional python REPL that has full
access to the GUI and all backends). Especially the control through
python during execution make one-off complex parameter scans easy to
implement. The software also makes it easy to develop and test the
code without any hardware connected to the system, by implementing a
'dummy' mode in which the hardware does not need to be present and the
user can specify return values for certain opperations to be able to
test the programs.

Similar packages already exist, for example Scopefoundry.org
[@Barnard], pymeasure [@pymeasure], yaq [@yaq], etc. A good overview
of available python packages can be found at Ref [@overview].

However, for our experiments we had a specific usecase in mind and we
therefore decided to implement the provided solution. This software is
currently actively used in our group at Lawrence Berkeley National
Laboratory.  Although our group is using `Hardware-Control`
specifically in beam physics applications, we believe that the code
can be useful for other experiments too.

In principle, we plan to continue to develop the code in the future by
adding more instrument drivers and custom widgets, since we believe
that the current solution also provides us several benefits compared
to prior solution. Therefore, we are also open to community
contributions. However, we are also open to merge our code into one of
the pre-existing code bases and plan to explore these options going forward.

# Acknowledgements

The information, data, or work presented herein was funded by the Advanced Research
Projects Agency-Energy (ARPA-E), U.S. Department of Energy, under Contract No. DE-AC02-
05CH11231.

# References
