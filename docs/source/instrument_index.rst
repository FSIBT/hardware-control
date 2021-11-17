Instrument Drivers
==================

Instrument drivers to control hardware directly. Instrument drivers
are written in a way so that they don't require Qt and can
therefore be easily used on the command line or in other
(non-hardware-control) apps.

Instrument drivers on their own also do not run in a separate thread
or set up any ZMQ communication. This only happens once you add an
instrument to a Hardware Control `App`.

Most instrument drivers are based on sending and receiving strings
between the instrument and the driver and therefore this is the main
focus of our approach. However, instead of defining strings for the
commands that need to be send to the instrument, one can also define
arbitrary python function allowing the control of instrument with
existing python packages. Example for the latter usecase are the
drivers for the NI-DAQ modules and picoscopes.

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
