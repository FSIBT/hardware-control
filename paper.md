---
title: 'Hardware-Control: Instrument control and automation package'
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
  - name: Arun Persaud
    orcid: 0000-0003-3186-8358
    affiliation: 1
affiliations:
 - name: Lawrence Berkeley National Laboratory, Berkeley, CA 94720, USA
   index: 1
 - name: Technische Universität Darmstadt, 64289 Darmstadt, Hesse, Germany
   index: 2
date: 27 August 2020
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
Qt, a GUI framework [@pyqt], to create fast and efficient user
interfaces compatible with most major operating
systems. `Hardware-Control` is also designed so that new drivers can
be easily added for new hardware and used with existing user
interfaces. The package also provides means for simplifying data
collection with automatic data logging, plotting, and many export
formats. `Hardware-Control` was designed to be a flexible solution for
a wide variety of experimental challenges.


# Statement of need

Commercial systems, such as LabVIEW, already exist and they often do
provide a wide range of instrument drivers. However, we found that the
resulting code is often hard to version control (LabVIEW files are
binary and code reviews and pull requests on services such as
bitbucket and github are therefore difficult). Furthermore, although
backend code can be easily shared between projects, complex user
interfaces can not easily be reused. The software package presented
here solves the main issues that we have encountered in the
past. Specifically, it makes reusing frontend code easier, integrates
well with git (pure python code), and provides an easy built-in
scripting solution (via an optional python REPL that has full access
to the GUI and all backends). Especially the control through python
during execution make one-off complex parameter scans easy to
implement. The software also makes it easy to develop and test the
code without any hardware connected to the system.

A similar package with a slightly different approach can be found at
Scopefoundry.org [@Barnard]. However, our experiments have a lightly
different need and we therefore decided to implement the provided
solution.


# Acknowledgements

The information, data, or work presented herein was funded by the Advanced Research
Projects Agency-Energy (ARPA-E), U.S. Department of Energy, under Contract No. DE-AC02-
05CH11231.

# References

