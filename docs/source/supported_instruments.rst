List of supported instruments
=============================


- Delay Generator:

  The delay generator widget provides a UI for delay generator/trigger instruments.

  Included backends:
  - Stanford Research Systems DG535 (GPIB, via usb adaptor)

- Flow Controller:

  The flow controller widget provides a UI for gas flow controllers.

  Included backends:
  - Alicat M-Series (LAN & Modbus)

- Function Generator:

  The function generator widget provides a UI for arbitrary waveform
  generator or function generator instruments. The widget can be
  created with either one or two channels to fit various instrument
  models.

  Included backends:
  - Keysight 33500B (LAN)
  - Siglent SDG Series (LAN)

- IOModule:

  The IO Module provides a way to communicate with data acquisition
  instruments and digital to analog converters.

  Included backends:
  - National Instruments 9000 (LAN & USB)
  - Advantech ADAM 6015 (LAN)
  - Advantech ADAM 6024 (LAN)

- Oscilloscope:

  The oscilloscope widget provides a UI for oscilloscopes. The current
  implementation always displays four channels, although it can work
  with two channel oscilloscopes while ignoring the two additional
  channels.

  Included backends:
  - Keysight 4000X (LAN)
  - Rigol DS1000Z (LAN)
  - Picoscope 6000

- Power Supplies:

  Included backends:
  - CAEN series

