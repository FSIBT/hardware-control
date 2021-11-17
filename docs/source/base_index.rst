Base Classes
============

A collection of base classes and helpers used throughout the
project. These classes provide the main features of our framework that
are not Qt oriented (although they might rely on Qt). For example, we
provide an `App` class that inherits from Qt but provides additional
methods, etc. to handle communication with instruments, provide a model
of all our data, etc. `Instrument` provides the base functionality to
write instrument drivers and so on.

.. toctree::
   :maxdepth: 1
   :caption: Base Classes:

   base/App
   base/Instrument
   base/HCMainWindow
   base/Dataset
   base/logging
   base/ZMQAdapter
   base/ZMQRemoteAdapter
   base/hooks
   base/zmq_helper
