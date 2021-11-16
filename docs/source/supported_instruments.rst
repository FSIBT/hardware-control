List of supported instruments
=============================

Note: Not all functions for all instruments are supported. If you need
a currently unsuported functionality, feel free to contact us or
provide a pull request.

- Delay Generator:

  The DelayGenerator control widget provides a UI for delay generator/trigger instruments.

  .. list-table::
     :widths: 50 50
     :header-rows: 0
     :align: left

     * - Included instruments:
       -
     * - `Stanford Research Systems DG535 <https://www.thinksrs.com/products/DG535.htm>`_ (GPIB, via usb adaptor)
       - .. image:: /images/DG535.jpg
           :height: 100


- Flow Controller:

  The FlowController control widget provides a UI for gas flow controllers.

  .. list-table::
     :widths: 50 50
     :header-rows: 0
     :align: left

     * - Included instruments:
       -
     * - `Alicat M-Series <https://www.alicat.com/product/mass-flow-meters/>`_ (LAN & Modbus)
       - .. image:: /images/Alicat_M-Series.jpg
           :height: 100


- Gas Analyzer:

  The RGA control widget provides a UI for gas analyzers (under development).

  .. list-table::
     :widths: 50 50
     :header-rows: 0
     :align: left

     * - Included instruments:
       -
     * - `Stanford Research Systems CIS Series <https://www.thinksrs.com/products/cis.html>`_
       - .. image:: /images/SRS_CIS.jpg
           :height: 100
     * - `Granville Phillips 835 <https://www.mksinst.com/f/835-vacuum-quality-monitor>`_
       - .. image:: /images/GP_VQM835.jpg
           :height: 100


- Temperature Monitor:

  The TempMonitor control widget provides a UI for temperature monitors.

  .. list-table::
     :widths: 50 50
     :header-rows: 0
     :align: left

     * - Included instruments:
       -
     * - `Lake Shore Model 224 <https://www.lakeshore.com/products/categories/overview/temperature-products/cryogenic-temperature-monitors/model-224-temperature-monitor>`_
       - .. image:: /images/Lake_Shore_224.png
           :height: 100


- Ion Gauge:

  There is currently no control widget for these instruments.

  .. list-table::
     :widths: 50 50
     :header-rows: 0
     :align: left

     * - Included instruments:
       -
     * - `Granville Phillips 356 <https://www.mksinst.com/f/356-micro-ion-plus-modules>`_
       - .. image:: /images/GP356.jpg
           :height: 100


- Function Generator:

  The FunctionGenerator control widget provides a UI for arbitrary waveform
  generator or function generator instruments. The widget can be
  created with either one or two channels to fit various instrument
  models.

  .. list-table::
     :widths: 50 50
     :header-rows: 0
     :align: left

     * - Included instruments:
       -
     * - `Keysight 33500B <https://www.keysight.com/us/en/products/waveform-and-function-generators/trueform-series-waveform-and-function-generators.html>`_ (LAN)
       - .. image:: /images/Keysight33500B.png
           :height: 100
     * - `Siglent SDG Series <https://www.siglent.eu/waveform-generators>`_ (LAN)
       - .. image:: /images/SDG1000X.png
           :height: 100


- IOModule:

  The IO Module control widget provides a UI for data acquisition
  instruments and digital to analog converters. We use these often to
  control, for example, power supplies via a analog inputs/outputs.

  .. list-table::
     :widths: 50 50
     :header-rows: 0
     :align: left

     * - Included instruments:
       -
     * - `National Instruments 9000 <https://www.ni.com/en-us/shop/compactdaq.html>`_ (LAN & USB)
       - .. image:: /images/NI9000.jpeg
           :height: 100
     * - `Advantech ADAM 6015 <https://www.advantech.com/products/a67f7853-013a-4b50-9b20-01798c56b090/adam-6015/mod_9c835a28-5c91-49fc-9de1-ec7f1dd3a82d>`_ (LAN)
       - .. image:: /images/ADAM-6015.jpg
           :height: 100
     * - `Advantech ADAM 6024 <https://www.advantech.com/products/a67f7853-013a-4b50-9b20-01798c56b090/adam-6024/mod_99d243cd-2f38-48a3-a82c-eeb5e0f4e278>`_ (LAN)
       - .. image:: /images/ADAM-6024.jpg
           :height: 100


- Oscilloscope:

  The Oscilloscope control widget provides a UI for oscilloscopes. The current
  implementation always displays four channels, although it can work
  with two channel oscilloscopes while ignoring the two additional
  channels.

  .. list-table::
     :widths: 50 50
     :header-rows: 0
     :align: left

     * - Included instruments:
       -
     * - `Keysight 4000X <https://www.keysight.com/en/pcx-x205209/infiniivision-4000-x-series-oscilloscopes?cc=US&lc=eng>`_ (LAN)
       - .. image:: /images/Keysight4000X.jpeg
           :height: 100
     * - `Rigol DS1000Z <https://www.rigolna.com/products/digital-oscilloscopes/1000z/>`_ (LAN)
       - .. image:: /images/RigolDS100Z.png
           :height: 100
     * - `Picoscope 6000 <https://www.picotech.com/oscilloscope/picoscope-6000-series>`_
       - .. image:: /images/Pico_6000.jpg
           :height: 100


- Power Supplies:

  The MultiPowerSupply control widget provides a UI for single- and multi-channel
  power supplies. The current implementation allows the user to select the
  number of channels utilized on each instrument.

  .. list-table::
     :widths: 50 50
     :header-rows: 0
     :align: left

     * - Included instruments:
       -
     * - `CAEN series R803x <https://www.caen.it/subfamilies/up-to-6-kv-family-r803x/>`_
       - .. image:: /images/CAENR803x.jpg
           :height: 100
     * - `CAEN series R14xxET <https://www.caen.it/subfamilies/rack-up-to-15-kv-reversible-polarity/>`_
       - .. image:: /images/CAENR14xxET.jpg
           :height: 100
     * - `Keysight 36300 <https://www.keysight.com/us/en/products/dc-power-supplies/bench-power-supplies/e36300-series-triple-output-power-supply-80-160w.html>`_
       - .. image:: /images/Keysight_E36312A.png
           :height: 100
     * - `Rigol DP800 <https://www.rigolna.com/products/dc-power-loads/dp800/>`_
       - .. image:: /images/RigolDP800.png
           :height: 100
     * - `TDKL GenH <https://www.us.lambda.tdk.com/products/programmable-power/genesys.html>`_
       - .. image:: /images/TDKLGenH.jpg
           :height: 100
