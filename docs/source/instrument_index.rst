Instrument Drivers
==================

Instrument drivers to control hardware directly. Instrument drivers
are written in a way so that they don't require Qt and can be
therefore easily used on the command line or in other
(non-hardware-control) apps.

Instrument drivers on their own also do not run in a separate thread
or set up any ZMQ communication. This only happens once you add an
instrument to an Hardware Control `App`.

.. toctree::
   :maxdepth: 2
   :caption: Supported instrument drivers by company:

   instruments/advantech
   instruments/alicat
   instruments/caen
   instruments/keysight
   instruments/ni
   instruments/picotech
   instruments/rigol
   instruments/siglent
   instruments/srs
   instruments/tdkl
