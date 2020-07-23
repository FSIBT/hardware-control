Hardware control reference
==========================

The hardware control package consists of several classes that define
the main functionality, e.g. a Qt-app and main window, classes to
start a thread that will communicate with an instrument, several
Qt-widgets that come in handy, for example, for plotting data and then
backend drivers for different hardware and their Qt-frontends. Some
hardware share the same Qt-frontend.

.. toctree::
   :maxdepth: 1
   :caption: Basics:

   base_and_backend

.. toctree::
   :maxdepth: 2
   :caption: Instruments:


   instruments/DelayGenerator
   instruments/FlowController
   instruments/FunctionGenerator
   instruments/IOModule
   instruments/Oscilloscope
   instruments/PowerSupply
