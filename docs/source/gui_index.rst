GUI Elements
============

Developer Guides
----------------

.. toctree::
   :maxdepth: 1

   creating_gui_controls

Widgets
-------

Widgets that provide extra functionallity that we often use when
writing control programs for hardware.

This includes custom version of common Qt widgets, such as Labels,
LineEdits, etc. that are automatically connected to the value of an
instrument parameter stored in the main app. Also included are widgets that
don't have a direct Qt equivalent, such as plotting data over time or
showing the connection status of all instruments.

.. toctree::
   :maxdepth: 1
   :caption: Widget Reference:

   gui/widgets/connection_status
   gui/widgets/data_widget
   gui/widgets/function_runner
   gui/widgets/hc_widgets
   gui/widgets/plot
   gui/widgets/qtconsole
   gui/widgets/scan_widget
   gui/widgets/alarm_widgets

Controls
--------

Controls provide a complete user interface for a certain type of instrument. One example of such a control is a user interface for an oscilloscope that is ready to be used in a more complex app that controls multiple instruments.

.. toctree::
   :maxdepth: 1
   :caption: Control Reference:

   gui/controls/DelayGenerator
   gui/controls/FlowController
   gui/controls/FunctionGenerator
   gui/controls/IOModule
   gui/controls/KeysightPowerSupply
   gui/controls/Oscilloscope
   gui/controls/MultiPowerSupply
   gui/controls/RGA
   gui/controls/TempMonitor
