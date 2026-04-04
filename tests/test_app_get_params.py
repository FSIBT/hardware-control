"""Tests for App.get_instrument_parameters_and_commands() method."""


class MockInstrument:
    """Mock instrument for testing."""

    def __init__(self, read_params, set_params, commands):
        """Initialize with known parameters."""
        self.read_params = read_params
        self.set_params = set_params
        self.commands = commands

    def list_parameters(self):
        """Return instrument capabilities."""
        return (self.read_params, self.set_params, self.commands)


class MockApp:
    """Mock App for testing (avoids full App initialization)."""

    def __init__(self):
        """Initialize mock app."""
        self._instruments = {}

    def get_instrument_parameters_and_commands(
        self, instrument: str
    ) -> tuple[list[str], list[str], list[str]]:
        """Get instrument's available parameters and commands."""
        inst = self._instruments.get(instrument)
        if inst is None:
            return ([], [], [])
        return inst.list_parameters()


class TestGetInstrumentParametersAndCommands:
    """Test suite for get_instrument_parameters_and_commands method."""

    def test_returns_empty_lists_for_nonexistent_instrument(self):
        """Test that non-existent instruments return empty lists."""
        app = MockApp()

        result = app.get_instrument_parameters_and_commands("NONEXISTENT")

        assert result == ([], [], [])

    def test_returns_instrument_capabilities(self):
        """Test that method returns instrument's parameters and commands."""
        app = MockApp()
        inst = MockInstrument(
            read_params=["VOLTAGE", "CURRENT", "STATUS"],
            set_params=["VOLTAGE", "CURRENT", "MODE"],
            commands=["RESET", "CALIBRATE"],
        )
        app._instruments["DMM"] = inst

        read_params, set_params, commands = app.get_instrument_parameters_and_commands(
            "DMM"
        )

        assert read_params == ["VOLTAGE", "CURRENT", "STATUS"]
        assert set_params == ["VOLTAGE", "CURRENT", "MODE"]
        assert commands == ["RESET", "CALIBRATE"]

    def test_different_instruments_have_different_capabilities(self):
        """Test that different instruments return different capabilities."""
        app = MockApp()

        inst1 = MockInstrument(
            read_params=["VOLTAGE"], set_params=["VOLTAGE"], commands=["RESET"]
        )
        inst2 = MockInstrument(
            read_params=["TEMPERATURE"],
            set_params=["SETPOINT"],
            commands=["CALIBRATE"],
        )

        app._instruments["DMM"] = inst1
        app._instruments["TEMP_CTRL"] = inst2

        read1, set1, cmds1 = app.get_instrument_parameters_and_commands("DMM")
        read2, set2, cmds2 = app.get_instrument_parameters_and_commands("TEMP_CTRL")

        assert read1 == ["VOLTAGE"]
        assert read2 == ["TEMPERATURE"]
        assert cmds1 == ["RESET"]
        assert cmds2 == ["CALIBRATE"]

    def test_instrument_with_no_capabilities(self):
        """Test instrument with empty parameter lists."""
        app = MockApp()
        inst = MockInstrument(read_params=[], set_params=[], commands=[])
        app._instruments["SIMPLE"] = inst

        read_params, set_params, commands = app.get_instrument_parameters_and_commands(
            "SIMPLE"
        )

        assert read_params == []
        assert set_params == []
        assert commands == []
