Welcome to Hardware-control's documentation!
============================================

Hardware-control is a Python package designed to simplify creating
instrument control programs (for example power supplies,
oscilloscopes, etc.). By using reusable front ends (widgets) and
backends (instrument controllers) hardware-control tries to minimize the
effort and code required to communicate with lab instruments.

Hardware_Control uses a few basic constructs to organize its
applications:

* Widgets: UI elements that control a specific instrument or function.
* Backends: Python objects that facilitate communication between the
  GUI and the physical instrument.

 Although the package is meant to create Qt based programs, the
 backends are designed so that they can also be used in programs
 without the use of Qt.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   installation
   overview.md
   supported_instruments
   howtos
   hardware_control
   how_to_contribute
   CHANGELOG.md

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
