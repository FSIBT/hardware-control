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
        # Check that control has declared required parameters
        assert (
            hasattr(DelayGenerator, "_required_parameters")
            or hasattr(DelayGenerator, "_required_read_only")
            or hasattr(DelayGenerator, "_required_write_only")
            or hasattr(DelayGenerator, "_required_commands")
        )

    def test_flow_controller_uses_validated_control(self):
        """Test FlowController inherits from ValidatedControl."""
        from hardware_control.gui.controls.FlowController import FlowController
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(FlowController, ValidatedControl)
        # Check that control has declared required parameters
        assert (
            hasattr(FlowController, "_required_parameters")
            or hasattr(FlowController, "_required_read_only")
            or hasattr(FlowController, "_required_write_only")
            or hasattr(FlowController, "_required_commands")
        )

    def test_function_generator_uses_validated_control(self):
        """Test FunctionGenerator inherits from ValidatedControl."""
        from hardware_control.gui.controls.FunctionGenerator import FunctionGenerator
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(FunctionGenerator, ValidatedControl)
        # Check that control has declared required parameters
        assert (
            hasattr(FunctionGenerator, "_required_parameters")
            or hasattr(FunctionGenerator, "_required_read_only")
            or hasattr(FunctionGenerator, "_required_write_only")
            or hasattr(FunctionGenerator, "_required_commands")
        )

    def test_io_module_uses_validated_control(self):
        """Test IOModule inherits from ValidatedControl.

        Note: IOModule has fully dynamic parameters based on channel_data,
        so it doesn't declare class-level _required_* attributes.
        """
        from hardware_control.gui.controls.IOModule import IOModule
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(IOModule, ValidatedControl)
        # IOModule is a fully dynamic control - parameters depend on channel_data

    def test_keysight_power_supply_uses_validated_control(self):
        """Test KeysightPowerSupply inherits from ValidatedControl."""
        from hardware_control.gui.controls.KeysightPowerSupply import (
            KeysightPowerSupply,
        )
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(KeysightPowerSupply, ValidatedControl)
        # Check that control has declared required parameters
        assert (
            hasattr(KeysightPowerSupply, "_required_parameters")
            or hasattr(KeysightPowerSupply, "_required_read_only")
            or hasattr(KeysightPowerSupply, "_required_write_only")
            or hasattr(KeysightPowerSupply, "_required_commands")
        )

    def test_microwave_control_uses_validated_control(self):
        """Test MicrowaveController inherits from ValidatedControl."""
        from hardware_control.gui.controls.MicrowaveControl import MicrowaveController
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(MicrowaveController, ValidatedControl)
        # Check that control has declared required parameters
        assert (
            hasattr(MicrowaveController, "_required_parameters")
            or hasattr(MicrowaveController, "_required_read_only")
            or hasattr(MicrowaveController, "_required_write_only")
            or hasattr(MicrowaveController, "_required_commands")
        )

    def test_multi_power_supply_uses_validated_control(self):
        """Test MultiPowerSupply inherits from ValidatedControl.

        Note: MultiPowerSupply has fully dynamic parameters based on channels,
        so it doesn't declare class-level _required_* attributes.
        """
        from hardware_control.gui.controls.MultiPowerSupply import MultiPowerSupply
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(MultiPowerSupply, ValidatedControl)
        # MultiPowerSupply is a fully dynamic control - parameters depend on channels

    def test_oscilloscope_uses_validated_control(self):
        """Test Oscilloscope inherits from ValidatedControl."""
        from hardware_control.gui.controls.Oscilloscope import Oscilloscope
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(Oscilloscope, ValidatedControl)
        # Check that control has declared required parameters
        assert (
            hasattr(Oscilloscope, "_required_parameters")
            or hasattr(Oscilloscope, "_required_read_only")
            or hasattr(Oscilloscope, "_required_write_only")
            or hasattr(Oscilloscope, "_required_commands")
        )

    def test_rga_uses_validated_control(self):
        """Test RGA inherits from ValidatedControl."""
        from hardware_control.gui.controls.RGA import RGA
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(RGA, ValidatedControl)
        # Check that control has declared required parameters
        assert (
            hasattr(RGA, "_required_parameters")
            or hasattr(RGA, "_required_read_only")
            or hasattr(RGA, "_required_write_only")
            or hasattr(RGA, "_required_commands")
        )

    def test_temp_monitor_uses_validated_control(self):
        """Test TempMonitor inherits from ValidatedControl.

        Note: TempMonitor has fully dynamic parameters based on channels,
        so it doesn't declare class-level _required_* attributes.
        """
        from hardware_control.gui.controls.TempMonitor import TempMonitor
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(TempMonitor, ValidatedControl)
        # TempMonitor is a fully dynamic control - parameters depend on channels

    def test_temp_monitor_adam_uses_validated_control(self):
        """Test TempMonitor_Adam inherits from ValidatedControl.

        Note: TempMonitor_Adam has fully dynamic parameters based on channels,
        so it doesn't declare class-level _required_* attributes.
        """
        from hardware_control.gui.controls.TempMonitor_Adam import TempMonitor_Adam
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(TempMonitor_Adam, ValidatedControl)
        # TempMonitor_Adam is a fully dynamic control - parameters depend on channels

    def test_device_template_uses_validated_control(self):
        """Test DeviceType (template) inherits from ValidatedControl."""
        from hardware_control.gui.controls.DeviceTemplate import DeviceType
        from hardware_control.base.gui_control import ValidatedControl

        assert issubclass(DeviceType, ValidatedControl)
        # Check that control has declared required parameters
        assert (
            hasattr(DeviceType, "_required_parameters")
            or hasattr(DeviceType, "_required_read_only")
            or hasattr(DeviceType, "_required_write_only")
            or hasattr(DeviceType, "_required_commands")
        )
