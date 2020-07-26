List of supported instruments
=============================


- Delay Generator:

  The delay generator widget provides a UI for delay generator/trigger instruments.

  Included backends:

  - `Stanford Research Systems DG535 <https://www.thinksrs.com/products/DG535.htm>`_ (GPIB, via usb adaptor)

- Flow Controller:

  The flow controller widget provides a UI for gas flow controllers.

  Included backends:

  - `Alicat M-Series <https://www.alicat.com/product/mass-flow-meters/>`_ (LAN & Modbus)

- Function Generator:

  The function generator widget provides a UI for arbitrary waveform
  generator or function generator instruments. The widget can be
  created with either one or two channels to fit various instrument
  models.

  Included backends:

  - `Keysight 33500B <https://www.keysight.com/us/en/products/waveform-and-function-generators/trueform-series-waveform-and-function-generators.html>`_ (LAN)
  - `Siglent SDG Series <https://www.siglent.eu/waveform-generators>`_ (LAN)

- IOModule:

  The IO Module provides a way to communicate with data acquisition
  instruments and digital to analog converters.

  Included backends:

  - `National Instruments 9000 <https://www.ni.com/en-us/shop/compactdaq.html>`_ (LAN & USB)
  - `Advantech ADAM 6015 <https://www.advantech.com/products/a67f7853-013a-4b50-9b20-01798c56b090/adam-6015/mod_9c835a28-5c91-49fc-9de1-ec7f1dd3a82d>`_ (LAN)
  - `Advantech ADAM 6024 <https://www.advantech.com/products/a67f7853-013a-4b50-9b20-01798c56b090/adam-6024/mod_99d243cd-2f38-48a3-a82c-eeb5e0f4e278>`_ (LAN)

- Oscilloscope:

  The oscilloscope widget provides a UI for oscilloscopes. The current
  implementation always displays four channels, although it can work
  with two channel oscilloscopes while ignoring the two additional
  channels.

  Included backends:

  - `Keysight 4000X <https://www.keysight.com/en/pcx-x205209/infiniivision-4000-x-series-oscilloscopes?cc=US&lc=eng>`_ (LAN)
  - `Rigol DS1000Z <https://www.rigolna.com/products/digital-oscilloscopes/1000z/>`_ (LAN)
  - `Picoscope 6000 <https://www.picotech.com/oscilloscope/picoscope-6000-series>`_

- Power Supplies:

  Included backends:

  - `CAEN series R803x <https://www.caen.it/subfamilies/up-to-6-kv-family-r803x/>`_
  - `CAEN series R14xxET <https://www.caen.it/subfamilies/rack-up-to-15-kv-reversible-polarity/>`_
  - `Keysight 36300 <https://www.keysight.com/us/en/products/dc-power-supplies/bench-power-supplies/e36300-series-triple-output-power-supply-80-160w.html>`_
  - `Rigol DP800 <https://www.rigolna.com/products/dc-power-loads/dp800/>`_
  - `TDKL GenH <https://www.us.lambda.tdk.com/products/programmable-power/genesys.html>`_
