Welcome to Hardware-control's documentation!
============================================

Hardware-control is a Python package designed to simplify creating
instrument control programs (for example for power supplies,
oscilloscopes, etc.). By using reusable front ends (widgets) and
instrument drivers hardware-control tries to minimize the
effort and code required to communicate with instruments in the lab.

Hardware-control uses a few basic constructs to organize its
applications:

* Widgets: UI elements that control a specific instrument or function.
* Instrument drivers: Python objects that facilitate communication
  between the physical instrument and the program.

Although the package is meant to create Qt based frontends, the
instrument drivers are designed so that they can also be used in programs
without the use of Qt.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   overview.md
   installation
   supported_instruments
   howtos
   examples.md
   hardware_control
   how_to_contribute
   outlook.md
   CHANGELOG.md

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
