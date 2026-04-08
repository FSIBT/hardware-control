"""Tests for ValidatedControl base class."""

import pytest

from hardware_control.base.gui_control import (
    ValidatedControl,
    document_required_parameters,
)


class MockApp:
    """Mock App class for testing."""

    def __init__(self, read_params=None, set_params=None, commands=None):
        """Initialize mock app with instrument capabilities."""
        self.read_params = read_params or []
        self.set_params = set_params or []
        self.commands = commands or []
        # Add a mock instrument to _data with capabilities
        self._data = {
            "TEST_INST": {
                "__capabilities__": {
                    "read_parameters": list(read_params or []),
                    "set_parameters": list(set_params or []),
                    "commands": list(commands or []),
                }
            }
        }

    @property
    def instruments(self):
        """Iterator over all instrument names."""
        yield from self._data

    def get_instrument_parameters_and_commands(self, instrument: str):
        """Return mock instrument capabilities."""
        if instrument not in self._data:
            return ([], [], [])

        capabilities = self._data[instrument].get("__capabilities__")
        if capabilities is None:
            return ([], [], [])

        return (
            capabilities["read_parameters"],
            capabilities["set_parameters"],
            capabilities["commands"],
        )


class MockWidget:
    """Mock Qt widget for testing (avoids Qt dependency)."""

    def __init__(self, *args, **kwargs):
        """Initialize mock widget."""
        pass


class SimpleControl(ValidatedControl, MockWidget):
    """Simple test control with no requirements (no Qt dependency)."""

    def __init__(self, app, instrument_name):
        super().__init__(app, instrument_name)


class ControlWithParameters(ValidatedControl, MockWidget):
    """Test control with required parameters."""

    _required_parameters = ["VOLTAGE"]
    _required_read_only = ["STATUS"]
    _required_write_only = ["MODE"]
    _required_commands = ["RESET"]

    def __init__(self, app, instrument_name):
        super().__init__(app, instrument_name)


class ControlWithReadWrite(ValidatedControl, MockWidget):
    """Test control with read/write parameter."""

    _required_parameters = ["VOLTAGE"]

    def __init__(self, app, instrument_name):
        super().__init__(app, instrument_name)


class ControlWithCommand(ValidatedControl, MockWidget):
    """Test control with command."""

    _required_commands = ["RESET"]

    def __init__(self, app, instrument_name):
        super().__init__(app, instrument_name)


class TestValidatedControl:
    """Test suite for ValidatedControl class."""

    def test_init_sets_app_and_instrument(self):
        """Test that __init__ sets up app and instrument attributes."""
        app = MockApp()
        control = SimpleControl(app, "TEST_INST")

        assert control.app is app
        assert control.instrument == "TEST_INST"

    def test_validation_passes_with_no_requirements(self):
        """Test validation passes when control has no requirements."""
        app = MockApp()
        # Should not raise
        control = SimpleControl(app, "TEST_INST")
        assert control.app is app

    def test_validation_passes_all_present(self):
        """Test validation passes when all requirements are met."""
        app = MockApp(
            read_params=["VOLTAGE", "STATUS"],
            set_params=["VOLTAGE", "MODE"],
            commands=["RESET"],
        )
        # Should not raise
        control = ControlWithParameters(app, "TEST_INST")
        assert control.app is app

    def test_validation_fails_missing_command(self):
        """Test validation fails when command is missing."""
        app = MockApp(commands=[])

        with pytest.raises(ValueError) as exc_info:
            ControlWithCommand(app, "TEST_INST")

        assert "RESET (command)" in str(exc_info.value)
        assert "ControlWithCommand" in str(exc_info.value)

    def test_validation_fails_missing_readable(self):
        """Test validation fails when readable parameter is missing."""
        app = MockApp(read_params=[], set_params=["VOLTAGE"])

        with pytest.raises(ValueError) as exc_info:
            ControlWithReadWrite(app, "TEST_INST")

        assert "VOLTAGE (readable)" in str(exc_info.value)

    def test_validation_fails_missing_writable(self):
        """Test validation fails when writable parameter is missing."""
        app = MockApp(read_params=["VOLTAGE"], set_params=[])

        with pytest.raises(ValueError) as exc_info:
            ControlWithReadWrite(app, "TEST_INST")

        assert "VOLTAGE (writable)" in str(exc_info.value)

    def test_validation_fails_multiple_missing(self):
        """Test validation error message with multiple missing parameters."""
        app = MockApp(read_params=[], set_params=[], commands=[])

        with pytest.raises(ValueError) as exc_info:
            ControlWithParameters(app, "TEST_INST")

        error_msg = str(exc_info.value)
        assert "VOLTAGE" in error_msg or "STATUS" in error_msg
        assert "ControlWithParameters" in error_msg

    def test_validation_fails_instrument_not_found(self):
        """Test validation fails when instrument doesn't exist."""
        app = MockApp()

        with pytest.raises(ValueError) as exc_info:
            ControlWithCommand(app, "MISSING_INST")

        assert "not found in app" in str(exc_info.value)
        assert "MISSING_INST" in str(exc_info.value)

    def test_documentation_decorator(self):
        """Test that documentation decorator adds parameters to docstring."""

        @document_required_parameters
        class TestControl(ValidatedControl, MockWidget):
            """Test control."""

            _required_parameters = ["VOLTAGE"]
            _required_commands = ["RESET"]

            def __init__(self, app, instrument_name):
                super().__init__(app, instrument_name)

        # Check docstring was updated
        doc = TestControl.__doc__
        assert doc is not None
        assert "**Required Instrument Parameters**" in doc
        assert "Read/Write Parameters:" in doc
        assert "``VOLTAGE``" in doc
        assert "Commands:" in doc
        assert "``RESET``" in doc

    def test_automatic_documentation_via_init_subclass(self):
        """Test that __init_subclass__ automatically applies decorator."""
        # ControlWithParameters should have docs auto-generated
        doc = ControlWithParameters.__doc__
        assert doc is not None
        assert "**Required Instrument Parameters**" in doc
        assert "``VOLTAGE``" in doc
        assert "``STATUS``" in doc
        assert "``MODE``" in doc
        assert "``RESET``" in doc

    def test_class_attributes_preserved(self):
        """Test that class attributes are accessible."""
        assert ControlWithParameters._required_parameters == ["VOLTAGE"]
        assert ControlWithParameters._required_read_only == ["STATUS"]
        assert ControlWithParameters._required_write_only == ["MODE"]
        assert ControlWithParameters._required_commands == ["RESET"]

    def test_instance_attributes_override_class_attributes(self):
        """Test that instance attributes can override class attributes for dynamic parameters."""

        class DynamicControl(ValidatedControl, MockWidget):
            """Control with dynamic parameters (e.g., multi-channel)."""

            # Class attributes show pattern in docs
            _required_parameters = ["CH{ch}_VOLTAGE"]

            def __init__(self, app, instrument_name, channels):
                # Expand pattern for actual channels before calling super
                self._required_parameters = [
                    param.replace("{ch}", str(ch))
                    for param in self.__class__._required_parameters
                    for ch in channels
                ]

                # Validation uses expanded instance attributes
                super().__init__(app, instrument_name)
                self.channels = channels

        # Create app with expanded parameters
        app = MockApp(
            read_params=["CH1_VOLTAGE", "CH2_VOLTAGE", "CH3_VOLTAGE"],
            set_params=["CH1_VOLTAGE", "CH2_VOLTAGE", "CH3_VOLTAGE"],
        )

        # Should validate successfully with expanded parameters
        control = DynamicControl(app, "TEST_INST", channels=[1, 2, 3])

        # Class attribute still has pattern (for docs)
        assert DynamicControl._required_parameters == ["CH{ch}_VOLTAGE"]

        # Instance attribute has expanded list (for validation)
        assert control._required_parameters == [
            "CH1_VOLTAGE",
            "CH2_VOLTAGE",
            "CH3_VOLTAGE",
        ]
