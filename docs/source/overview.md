# Overview

Hardware-control is a Python package for controlling all kinds of
laboratory equipment. It has been developed to replace LabVIEW for
instrument control in the [Ion Beam Technology](https://ibt.lbl.gov) group at [Lawrence
Berkeley National Laboratory](https://lbl.gov).

The main goal is to provide easily re-usable user interfaces to control a
wide range of hardware. We try to reduce the amount of code a user has
to write and try to make it easy to combine different hardware in a
single graphical user interface.

Furthermore, the program will also run, if one or several of the
instruments are not connected and the program will automatically
detect once an instrument becomes available. To isolate the different
instruments and prevent blocking of the main application, each
instrument is controlled by a separate thread.

Hardware-control consists of several parts:

1. A base layer of different backends that talk to the different
   instruments. Each instrument has its own backend. The backend
   mainly has to implement a few functions:
   * A function to set parameter
   * A function to read parameters or query values
   * A test function to see if the instrument is online

   In the program, the user will always create a python instance of
   one of these backends for each instrument the user want to control.

   The actual backends can rely on different communication protocols,
   e.g. sockets, modbus, usb connection and use different python
   libraries to connect to the instruments, for example, pyvisa.

2. A Qt user interface class. Here, several backends might use the same
   user interface. During the creation of the user interface the
   hardware-control package will automatically create a background
   thread and set up communication channels between the main Qt-app
   and the backends. The communication follows a simple ASCII protocol
   to set and read values that gets triggered by the user interacting
   with the UI or by a timer. The backends then translates those
   requests to the actual commands that need to be send to the
   instrument.

3. A set of Qt-widgets that nicely interact with the hardware. For
   example to easily plot measured values vs. time or create logfiles
   of data that is automatically acquired every second.

4. The Qt-main app. This is the main user interface that will include
   all the instrument and plotting widgets. Hardware-control
   automatically keeps track of all the instruments connected, their
   settings, and the latest read-in data from the instrument. When
   plotting data or using settings values, the data stored in the
   Qt-main app should always be used and the instrument threads will
   update this data on demand or based on a timer.

