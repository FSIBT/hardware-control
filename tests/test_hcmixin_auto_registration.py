"""Tests for HCMixin auto-registration functionality."""

from unittest.mock import patch

from hardware_control.gui.widgets.hc_widgets import HCMixin


# Mock Qt components to avoid Qt dependency in tests
class MockQLabel:
    """Mock QLabel for testing."""

    def __init__(self, text=""):
        """Initialize mock label."""
        self.text = text

    def setAlignment(self, alignment):
        """Mock setAlignment."""
        pass

    def hide(self):
        """Mock hide."""
        pass


class MockApp:
    """Mock App class for testing."""

    def __init__(self):
        """Initialize mock app."""
        self.registered_params = []

    def is_parameter(self, instrument, parameter):
        """Mock parameter check - always returns True for testing."""
        return True

    def add_widget(self, instrument, parameter, widget):
        """Mock add_widget."""
        pass

    def add_auto_update_instrument_parameter(self, instrument, parameter):
        """Mock auto-update registration."""
        pass

    def add_skip_update_instrument_parameter(self, instrument, parameter):
        """Mock skip update."""
        pass


class MockWidget:
    """Mock Qt widget for testing (avoids Qt dependency)."""

    def __init__(self, *args, **kwargs):
        """Initialize mock widget."""
        pass

    def hide(self):
        """Mock hide method."""
        pass


class MockHCMixin(HCMixin, MockWidget):
    """Test HC widget for testing."""

    def widget_update(self, value):
        """Required by HCMixin."""
        pass


class MockHCLabel(HCMixin, MockWidget):
    """Test HC label widget (read-only)."""

    __name__ = "HCLabel"  # Simulate the actual class name

    def __init__(self, *args, **kwargs):
        """Initialize with HCLabel name."""
        self.__class__.__name__ = "HCLabel"
        super().__init__(*args, **kwargs)

    def widget_update(self, value):
        """Required by HCMixin."""
        pass


class MockHCLineEdit(HCMixin, MockWidget):
    """Test HC line edit widget (read-write)."""

    __name__ = "HCLineEdit"

    def __init__(self, *args, **kwargs):
        """Initialize with HCLineEdit name."""
        self.__class__.__name__ = "HCLineEdit"
        super().__init__(*args, **kwargs)

    def widget_update(self, value):
        """Required by HCMixin."""
        pass


class TestAutoRegistration:
    """Test suite for HCMixin auto-registration."""

    @patch("hardware_control.gui.widgets.hc_widgets.QLabel", MockQLabel)
    def test_auto_register_when_function_exists(self):
        """Test that widget registers when _register_widget_parameter exists."""
        app = MockApp()
        registered = []

        def mock_register(inst, param, param_type="parameter", access="read_write"):
            registered.append(
                {
                    "instrument": inst,
                    "parameter": param,
                    "param_type": param_type,
                    "access": access,
                }
            )

        app._register_widget_parameter = mock_register

        widget = MockHCMixin(
            app=app, instrument="TEST_INST", parameter="VOLTAGE", label="Voltage"
        )

        assert len(registered) == 1
        assert registered[0]["instrument"] == "TEST_INST"
        assert registered[0]["parameter"] == "VOLTAGE"
        assert registered[0]["param_type"] == "parameter"
        assert registered[0]["access"] == "read_write"

    @patch("hardware_control.gui.widgets.hc_widgets.QLabel", MockQLabel)
    def test_no_register_when_function_missing(self):
        """Test that widget doesn't crash when _register_widget_parameter doesn't exist."""
        app = MockApp()

        # Should not raise - registration is optional
        widget = MockHCMixin(
            app=app, instrument="TEST_INST", parameter="VOLTAGE", label="Voltage"
        )

        assert widget.instrument == "TEST_INST"
        assert widget.parameter == "VOLTAGE"

    @patch("hardware_control.gui.widgets.hc_widgets.QLabel", MockQLabel)
    def test_infer_access_pattern_read_only(self):
        """Test access pattern inference for read-only widgets."""
        app = MockApp()
        widget = MockHCLabel(
            app=app, instrument="TEST_INST", parameter="STATUS", label="Status"
        )

        access = widget._infer_access_pattern()
        assert access == "read"

    @patch("hardware_control.gui.widgets.hc_widgets.QLabel", MockQLabel)
    def test_infer_access_pattern_read_write(self):
        """Test access pattern inference for read-write widgets."""
        app = MockApp()
        widget = MockHCLineEdit(
            app=app, instrument="TEST_INST", parameter="SETPOINT", label="Setpoint"
        )

        access = widget._infer_access_pattern()
        assert access == "read_write"

    @patch("hardware_control.gui.widgets.hc_widgets.QLabel", MockQLabel)
    def test_register_with_correct_access_for_read_only(self):
        """Test that read-only widgets register with 'read' access."""
        app = MockApp()
        registered = []

        def mock_register(inst, param, param_type="parameter", access="read_write"):
            registered.append({"access": access})

        app._register_widget_parameter = mock_register

        widget = MockHCLabel(
            app=app, instrument="TEST_INST", parameter="STATUS", label="Status"
        )

        assert len(registered) == 1
        assert registered[0]["access"] == "read"

    @patch("hardware_control.gui.widgets.hc_widgets.QLabel", MockQLabel)
    def test_register_with_correct_access_for_read_write(self):
        """Test that read-write widgets register with 'read_write' access."""
        app = MockApp()
        registered = []

        def mock_register(inst, param, param_type="parameter", access="read_write"):
            registered.append({"access": access})

        app._register_widget_parameter = mock_register

        widget = MockHCLineEdit(
            app=app, instrument="TEST_INST", parameter="SETPOINT", label="Setpoint"
        )

        assert len(registered) == 1
        assert registered[0]["access"] == "read_write"

    @patch("hardware_control.gui.widgets.hc_widgets.QLabel", MockQLabel)
    def test_multiple_widgets_register_separately(self):
        """Test that multiple widgets each register their own parameters."""
        app = MockApp()
        registered = []

        def mock_register(inst, param, param_type="parameter", access="read_write"):
            registered.append({"instrument": inst, "parameter": param})

        app._register_widget_parameter = mock_register

        widget1 = MockHCMixin(
            app=app, instrument="INST1", parameter="PARAM1", label="Param 1"
        )
        widget2 = MockHCMixin(
            app=app, instrument="INST1", parameter="PARAM2", label="Param 2"
        )
        widget3 = MockHCMixin(
            app=app, instrument="INST2", parameter="PARAM3", label="Param 3"
        )

        assert len(registered) == 3
        assert registered[0] == {"instrument": "INST1", "parameter": "PARAM1"}
        assert registered[1] == {"instrument": "INST1", "parameter": "PARAM2"}
        assert registered[2] == {"instrument": "INST2", "parameter": "PARAM3"}
