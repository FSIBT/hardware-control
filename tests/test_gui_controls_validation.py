"""Integration tests for GUI control parameter validation.

These tests verify that all GUI controls properly use the ValidatedControl
pattern by checking their class structure.

This is a lightweight integration test that verifies controls are properly
configured without actually instantiating them (which would require Qt).
"""

import pytest
import inspect


pytest.importorskip("PyQt6")  # Skip tests if PyQt6 not installed


class TestGUIControlsUseValidatedControl:
    """Test that all GUI controls inherit from ValidatedControl."""

    def test_delay_generator_uses_validated_control(self):
        """Test DelayGenerator inherits from ValidatedControl."""
        from hardware_control.gui.controls.DelayGenerator import DelayGenerator
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(DelayGenerator, ValidatedControl)
        assert hasattr(DelayGenerator, "_validate_parameters")
        assert hasattr(DelayGenerator, "_add_required_parameter")

    def test_flow_controller_uses_validated_control(self):
        """Test FlowController inherits from ValidatedControl."""
        from hardware_control.gui.controls.FlowController import FlowController
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(FlowController, ValidatedControl)
        assert hasattr(FlowController, "_validate_parameters")
        assert hasattr(FlowController, "_add_required_parameter")

    def test_function_generator_uses_validated_control(self):
        """Test FunctionGenerator inherits from ValidatedControl."""
        from hardware_control.gui.controls.FunctionGenerator import FunctionGenerator
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(FunctionGenerator, ValidatedControl)
        assert hasattr(FunctionGenerator, "_validate_parameters")
        assert hasattr(FunctionGenerator, "_add_required_parameter")

    def test_io_module_uses_validated_control(self):
        """Test IOModule inherits from ValidatedControl."""
        from hardware_control.gui.controls.IOModule import IOModule
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(IOModule, ValidatedControl)
        assert hasattr(IOModule, "_validate_parameters")
        assert hasattr(IOModule, "_add_required_parameter")

    def test_keysight_power_supply_uses_validated_control(self):
        """Test KeysightPowerSupply inherits from ValidatedControl."""
        from hardware_control.gui.controls.KeysightPowerSupply import (
            KeysightPowerSupply,
        )
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(KeysightPowerSupply, ValidatedControl)
        assert hasattr(KeysightPowerSupply, "_validate_parameters")
        assert hasattr(KeysightPowerSupply, "_add_required_parameter")

    def test_microwave_control_uses_validated_control(self):
        """Test MicrowaveController inherits from ValidatedControl."""
        from hardware_control.gui.controls.MicrowaveControl import MicrowaveController
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(MicrowaveController, ValidatedControl)
        assert hasattr(MicrowaveController, "_validate_parameters")
        assert hasattr(MicrowaveController, "_add_required_parameter")

    def test_multi_power_supply_uses_validated_control(self):
        """Test MultiPowerSupply inherits from ValidatedControl."""
        from hardware_control.gui.controls.MultiPowerSupply import MultiPowerSupply
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(MultiPowerSupply, ValidatedControl)
        assert hasattr(MultiPowerSupply, "_validate_parameters")
        assert hasattr(MultiPowerSupply, "_add_required_parameter")

    def test_oscilloscope_uses_validated_control(self):
        """Test Oscilloscope inherits from ValidatedControl."""
        from hardware_control.gui.controls.Oscilloscope import Oscilloscope
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(Oscilloscope, ValidatedControl)
        assert hasattr(Oscilloscope, "_validate_parameters")
        assert hasattr(Oscilloscope, "_add_required_parameter")

    def test_rga_uses_validated_control(self):
        """Test RGA inherits from ValidatedControl."""
        from hardware_control.gui.controls.RGA import RGA
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(RGA, ValidatedControl)
        assert hasattr(RGA, "_validate_parameters")
        assert hasattr(RGA, "_add_required_parameter")

    def test_temp_monitor_uses_validated_control(self):
        """Test TempMonitor inherits from ValidatedControl."""
        from hardware_control.gui.controls.TempMonitor import TempMonitor
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(TempMonitor, ValidatedControl)
        assert hasattr(TempMonitor, "_validate_parameters")
        assert hasattr(TempMonitor, "_add_required_parameter")

    def test_temp_monitor_adam_uses_validated_control(self):
        """Test TempMonitor_Adam inherits from ValidatedControl."""
        from hardware_control.gui.controls.TempMonitor_Adam import TempMonitor_Adam
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(TempMonitor_Adam, ValidatedControl)
        assert hasattr(TempMonitor_Adam, "_validate_parameters")
        assert hasattr(TempMonitor_Adam, "_add_required_parameter")

    def test_device_template_uses_validated_control(self):
        """Test DeviceType (template) inherits from ValidatedControl."""
        from hardware_control.gui.controls.DeviceTemplate import DeviceType
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(DeviceType, ValidatedControl)
        assert hasattr(DeviceType, "_validate_parameters")
        assert hasattr(DeviceType, "_add_required_parameter")
