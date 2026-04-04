"""Tests for ValidatedControl base class."""

import pytest

from hardware_control.base.gui_control import ValidatedControl


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
    """Simple test control (no Qt dependency)."""

    def __init__(self, app, instrument_name):
        super().__init__(app, instrument_name)
        self.app = app
        self.instrument = instrument_name


class TestValidatedControl:
    """Test suite for ValidatedControl class."""

    def test_init_sets_up_validation_system(self):
        """Test that __init__ sets up the validation system."""
        app = MockApp()
        control = SimpleControl(app, "TEST_INST")

        assert control.app is app
        assert control.instrument == "TEST_INST"
        assert control._required_params == {}
        assert control._validated is False
        assert hasattr(app, "_register_widget_parameter")

    def test_add_required_parameter_command(self):
        """Test adding a required command."""
        app = MockApp()
        control = SimpleControl(app, "TEST_INST")

        control._add_required_parameter("RESET", param_type="command")

        assert "RESET" in control._required_params
        assert control._required_params["RESET"]["type"] == "command"

    def test_add_required_parameter_read_only(self):
        """Test adding a read-only parameter."""
        app = MockApp()
        control = SimpleControl(app, "TEST_INST")

        control._add_required_parameter("STATUS", param_type="parameter", access="read")

        assert "STATUS" in control._required_params
        assert control._required_params["STATUS"]["type"] == "parameter"
        assert control._required_params["STATUS"]["access"] == "read"

    def test_add_required_parameter_write_only(self):
        """Test adding a write-only parameter."""
        app = MockApp()
        control = SimpleControl(app, "TEST_INST")

        control._add_required_parameter("MODE", param_type="parameter", access="write")

        assert "MODE" in control._required_params
        assert control._required_params["MODE"]["type"] == "parameter"
        assert control._required_params["MODE"]["access"] == "write"

    def test_add_required_parameter_read_write(self):
        """Test adding a read/write parameter (default)."""
        app = MockApp()
        control = SimpleControl(app, "TEST_INST")

        control._add_required_parameter("VOLTAGE")

        assert "VOLTAGE" in control._required_params
        assert control._required_params["VOLTAGE"]["type"] == "parameter"
        assert control._required_params["VOLTAGE"]["access"] == "read_write"

    def test_validate_parameters_no_requirements(self):
        """Test validation with no required parameters."""
        app = MockApp()
        control = SimpleControl(app, "TEST_INST")

        # Should not raise
        control._validate_parameters()

        assert control._validated is True

    def test_validate_parameters_all_present(self):
        """Test validation when all parameters are present."""
        app = MockApp(
            read_params=["VOLTAGE", "STATUS"],
            set_params=["VOLTAGE", "MODE"],
            commands=["RESET"],
        )
        control = SimpleControl(app, "TEST_INST")

        control._add_required_parameter(
            "VOLTAGE", param_type="parameter", access="read_write"
        )
        control._add_required_parameter("STATUS", param_type="parameter", access="read")
        control._add_required_parameter("MODE", param_type="parameter", access="write")
        control._add_required_parameter("RESET", param_type="command")

        # Should not raise
        control._validate_parameters()

        assert control._validated is True

    def test_validate_parameters_missing_command(self):
        """Test validation fails when command is missing."""
        app = MockApp(commands=[])
        control = SimpleControl(app, "TEST_INST")

        control._add_required_parameter("RESET", param_type="command")

        with pytest.raises(ValueError) as exc_info:
            control._validate_parameters()

        assert "RESET (command)" in str(exc_info.value)
        assert control._validated is False

    def test_validate_parameters_missing_readable(self):
        """Test validation fails when readable parameter is missing."""
        app = MockApp(read_params=[])
        control = SimpleControl(app, "TEST_INST")

        control._add_required_parameter("STATUS", param_type="parameter", access="read")

        with pytest.raises(ValueError) as exc_info:
            control._validate_parameters()

        assert "STATUS (readable)" in str(exc_info.value)
        assert control._validated is False

    def test_validate_parameters_missing_writable(self):
        """Test validation fails when writable parameter is missing."""
        app = MockApp(set_params=[])
        control = SimpleControl(app, "TEST_INST")

        control._add_required_parameter("MODE", param_type="parameter", access="write")

        with pytest.raises(ValueError) as exc_info:
            control._validate_parameters()

        assert "MODE (writable)" in str(exc_info.value)
        assert control._validated is False

    def test_validate_parameters_missing_read_write(self):
        """Test validation fails when read/write parameter is only readable."""
        app = MockApp(read_params=["VOLTAGE"], set_params=[])
        control = SimpleControl(app, "TEST_INST")

        control._add_required_parameter(
            "VOLTAGE", param_type="parameter", access="read_write"
        )

        with pytest.raises(ValueError) as exc_info:
            control._validate_parameters()

        assert "VOLTAGE (writable)" in str(exc_info.value)
        assert control._validated is False

    def test_validate_parameters_multiple_missing(self):
        """Test validation error message with multiple missing parameters."""
        app = MockApp(read_params=[], set_params=[], commands=[])
        control = SimpleControl(app, "TEST_INST")

        control._add_required_parameter(
            "VOLTAGE", param_type="parameter", access="read"
        )
        control._add_required_parameter("RESET", param_type="command")

        with pytest.raises(ValueError) as exc_info:
            control._validate_parameters()

        error_msg = str(exc_info.value)
        assert "VOLTAGE (readable)" in error_msg
        assert "RESET (command)" in error_msg
        assert "SimpleControl" in error_msg

    def test_validate_parameters_idempotent(self):
        """Test that calling _validate_parameters multiple times is safe."""
        app = MockApp(commands=["RESET"])
        control = SimpleControl(app, "TEST_INST")

        control._add_required_parameter("RESET", param_type="command")

        # First call
        control._validate_parameters()
        assert control._validated is True

        # Second call should not re-validate or raise
        control._validate_parameters()
        assert control._validated is True

    def test_append_required_params_to_docs(self):
        """Test that required parameters are appended to docstring."""
        app = MockApp(read_params=["STATUS"], set_params=["MODE"], commands=["RESET"])
        control = SimpleControl(app, "TEST_INST")

        control._add_required_parameter("STATUS", param_type="parameter", access="read")
        control._add_required_parameter("MODE", param_type="parameter", access="write")
        control._add_required_parameter("RESET", param_type="command")

        control._validate_parameters()

        # Check docstring was updated
        doc = control.__class__.__doc__
        assert doc is not None, "Docstring should not be None after validation"
        assert "**Required Instrument Parameters**" in doc
        assert "Read-only Parameters:" in doc
        assert "``STATUS``" in doc
        assert "Write-only Parameters:" in doc
        assert "``MODE``" in doc
        assert "Commands:" in doc
        assert "``RESET``" in doc

    def test_registration_function_filters_by_instrument(self):
        """Test that registration function only registers for matching instrument."""
        app = MockApp()
        control = SimpleControl(app, "INST1")

        # Register a parameter for INST1 (should be added)
        app._register_widget_parameter("INST1", "PARAM1", "parameter", "read")

        # Register a parameter for INST2 (should be ignored)
        app._register_widget_parameter("INST2", "PARAM2", "parameter", "read")

        assert "PARAM1" in control._required_params
        assert "PARAM2" not in control._required_params

    def test_cleans_up_registration_function_after_validation(self):
        """Test that _register_widget_parameter is removed after validation."""
        app = MockApp()
        control = SimpleControl(app, "TEST_INST")

        assert hasattr(app, "_register_widget_parameter")

        control._validate_parameters()

        assert not hasattr(app, "_register_widget_parameter")
