---
title: 'Hardware-Control: Instrument control and automation package'
tags:
  - Python
  - Instrument Control
  - Automation
  - Data Collection
authors:
  - name: Arun Persaud
    orcid: 0000-0003-3186-8358
    affiliation: 1
  - name: Grant Giesbrecht
    orcid: 0000-0003-2885-4801
    affiliation: 1
  - name: Timo Bauer
    orcid: 0000-0000-0000-0000
    affiliation: "1, 2" # (Multiple affiliations must be quoted)
affiliations:
 - name: Lawrence Berkeley National Laboratory, Berkeley, CA 94720, USA
   index: 1
 - name: Technische Universität Darmstadt
   index: 2
date: 20 August 2020
bibliography: paper.bib

---

# Summary

Conducting experimental research often presents a need to communicate with
laboratory instruments to facilitate running the experiment and collecting data.
Implementing a computer control system for an experiment can lead to quicker
results and a reduced chance of human error by minimizing the need for the
researcher to perform repeated tasks. Any software package for experiment
automation will require driver program to facilitate communication with the lab
instruments and some form of user interface to receive commands and present
data.

# Statement of need

`Hardware-Control` is a Python package for instrument control and
automation. It provides reusable user interfaces and instrument
drivers to simplify writing control programs. `Hardware-Control` uses
Qt, a GUI framework [@pyqt], to create fast and efficient user interfaces compatible with most
major operating systems. `Hardware-Control` is also designed so that
new drivers can be easily added for new instrument models and used
with existing user interfaces. The package also provides means for
simplifying data collection with automatic data logging, plotting, and
many export formats. `Hardware-Control` was designed to be a flexible
solution for a wide variety of experimental challenges.

A similar package with a slightly different approach can be found at Scopefoundry.org [@Barnard].

# Acknowledgements

The information, data, or work presented herein was funded by the Advanced Research
Projects Agency-Energy (ARPA-E), U.S. Department of Energy, under Contract No. DE-AC02-
05CH11231.

# References

