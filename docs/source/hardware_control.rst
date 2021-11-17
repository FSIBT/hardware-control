Hardware control reference
==========================

The hardware control package consists of several classes that define
the main functionality, e.g. a Qt-app and Qt-main-window, classes to
start a thread that will communicate with an instrument, several custom
Qt-widgets that come in handy, for example, for plotting data and then
instrument drivers for different hardware and pre-defined
Qt-frontends. One main goal is to have reusable frontends for similar
types of instruments to make writing GUIs easy.

To make this easy, we provide custom versions of common Qt widgets and
other classes, which are based on Qt classes but have additional
methods to connect, for example, to the main `app._data`. As an example,
HCLabel populates the text of a Qt-Label with the read value from an
instrument.

The package is split into three parts:

.. toctree::
   :maxdepth: 1
   :caption: Main elements:

   base_index
   gui_index
   instrument_index
