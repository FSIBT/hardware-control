"""Tests for error handling utilities."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hardware_control.base.error_handling import safe_cleanup


class TestSafeCleanup:
    """Test safe_cleanup function."""

    def test_safe_cleanup_successful(self):
        """Test safe_cleanup with successful cleanup function."""
        cleanup_called = {"value": False}

        def cleanup_func():
            cleanup_called["value"] = True

        # Should execute without raising
        safe_cleanup("test cleanup", cleanup_func, "test_instrument")

        # Cleanup should have been called
        assert cleanup_called["value"] is True

    def test_safe_cleanup_with_exception(self):
        """Test safe_cleanup when cleanup function raises exception."""

        def failing_cleanup():
            raise RuntimeError("Cleanup failed!")

        # Should not raise exception - it should be caught and logged
        safe_cleanup("test cleanup", failing_cleanup, "test_instrument")

        # If we get here, the exception was handled
        assert True

    def test_safe_cleanup_with_none_function(self):
        """Test safe_cleanup with None as cleanup function."""
        # Should handle None gracefully
        safe_cleanup("test cleanup", None, "test_instrument")
        assert True

    def test_safe_cleanup_returns_value(self):
        """Test that safe_cleanup calls the function (return value not used)."""

        def cleanup_with_return():
            return "cleaned"

        # Should execute without issues
        safe_cleanup("test cleanup", cleanup_with_return, "test_instrument")
        assert True

    def test_safe_cleanup_with_arguments(self):
        """Test safe_cleanup with lambda wrapping args."""
        result = {"value": None}

        def cleanup_with_args(arg1, arg2):
            result["value"] = arg1 + arg2

        # Wrap in lambda to pass arguments
        safe_cleanup(
            "test cleanup", lambda: cleanup_with_args(10, 20), "test_instrument"
        )

        assert result["value"] == 30

    def test_safe_cleanup_multiple_calls(self):
        """Test calling safe_cleanup multiple times."""
        counter = {"count": 0}

        def increment():
            counter["count"] += 1

        safe_cleanup("cleanup1", increment, "inst1")
        safe_cleanup("cleanup2", increment, "inst2")
        safe_cleanup("cleanup3", increment, "inst3")

        assert counter["count"] == 3

    def test_safe_cleanup_with_attribute_error(self):
        """Test safe_cleanup when cleanup raises AttributeError."""

        def cleanup_with_attribute_error():
            raise AttributeError("Object has no attribute 'close'")

        # Should handle AttributeError gracefully
        safe_cleanup("test cleanup", cleanup_with_attribute_error, "test_instrument")
        assert True

    def test_safe_cleanup_with_os_error(self):
        """Test safe_cleanup when cleanup raises OSError."""

        def cleanup_with_os_error():
            raise OSError("File not found")

        # Should handle OSError gracefully
        safe_cleanup("test cleanup", cleanup_with_os_error, "test_instrument")
        assert True

    def test_safe_cleanup_partial_cleanup(self):
        """Test safe_cleanup when cleanup partially succeeds."""
        cleanup_log = {"steps": []}

        def partial_cleanup():
            cleanup_log["steps"].append("step1")
            cleanup_log["steps"].append("step2")
            raise ValueError("Failed at step 3")

        # Should execute steps before exception
        safe_cleanup("test cleanup", partial_cleanup, "test_instrument")

        # First two steps should have executed
        assert "step1" in cleanup_log["steps"]
        assert "step2" in cleanup_log["steps"]

    def test_safe_cleanup_with_keyboard_interrupt(self):
        """Test safe_cleanup with KeyboardInterrupt (should not catch)."""

        def cleanup_with_interrupt():
            raise KeyboardInterrupt()

        # KeyboardInterrupt should propagate
        with pytest.raises(KeyboardInterrupt):
            safe_cleanup("test cleanup", cleanup_with_interrupt, "test_instrument")

    def test_safe_cleanup_with_system_exit(self):
        """Test safe_cleanup with SystemExit (should not catch)."""

        def cleanup_with_exit():
            raise SystemExit(0)

        # SystemExit should propagate
        with pytest.raises(SystemExit):
            safe_cleanup("test cleanup", cleanup_with_exit, "test_instrument")

    def test_safe_cleanup_different_operation_names(self):
        """Test safe_cleanup with different operation names for logging."""
        counter = {"count": 0}

        def cleanup():
            counter["count"] += 1

        # Different operation names should all work
        safe_cleanup("ZMQ publisher cleanup", cleanup, "inst1")
        safe_cleanup("Socket cleanup", cleanup, "inst2")
        safe_cleanup("Resource cleanup", cleanup, "inst3")
        safe_cleanup("Thread cleanup", cleanup, "inst4")

        assert counter["count"] == 4

    def test_safe_cleanup_with_custom_exception_types(self):
        """Test safe_cleanup with various exception types."""

        def cleanup_value_error():
            raise ValueError("Invalid value")

        def cleanup_type_error():
            raise TypeError("Wrong type")

        def cleanup_index_error():
            raise IndexError("Index out of range")

        # All should be handled gracefully
        safe_cleanup("test1", cleanup_value_error, "inst1")
        safe_cleanup("test2", cleanup_type_error, "inst2")
        safe_cleanup("test3", cleanup_index_error, "inst3")

        assert True
