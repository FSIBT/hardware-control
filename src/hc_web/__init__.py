"""Web monitor server for hardware-control.

This package ships in the same distribution as ``hardware_control`` (as the
``server`` extra) but must never import ``hardware_control`` or ``PyQt6``: it
runs on a headless server that has neither.
"""
