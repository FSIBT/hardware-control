"""Centralized error handling utilities for hardware-control package.

This module provides standardized error handling patterns to ensure consistent
logging, error categorization, and recovery strategies across the entire codebase.

Error Categories:
- Expected Control Flow: Normal operations (timeouts, type conversions)
- Recoverable Errors: Issues that don't break functionality (cleanup failures)
- Critical Errors: Issues that affect core functionality (connection failures)
- System Errors: Issues that should never be caught (KeyboardInterrupt, SystemExit)
"""

import logging
import functools
from typing import Any, Optional, Union
from collections.abc import Callable
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class HardwareControlError(Exception):
    """Base exception for hardware-control package."""

    pass


class InstrumentError(HardwareControlError):
    """Exception for instrument-related errors."""

    pass


class CommunicationError(InstrumentError):
    """Exception for communication/connection errors."""

    pass


class ConfigurationError(HardwareControlError):
    """Exception for configuration-related errors."""

    pass


# Exception types that should never be caught (system exceptions)
SYSTEM_EXCEPTIONS = (KeyboardInterrupt, SystemExit, SystemError)

# Common recoverable exceptions for different operations
CONNECTION_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
    CommunicationError,  # Our custom exception
)

FILE_OPERATION_EXCEPTIONS = (
    OSError,
    IOError,
    FileNotFoundError,
    PermissionError,
)

DATA_CONVERSION_EXCEPTIONS = (
    ValueError,
    TypeError,
    KeyError,
    IndexError,
)


def log_error(
    operation: str,
    exception: Exception,
    context: str = "",
    level: str = "error",
    set_offline: object | None = None,
    exc_info: bool = True,
) -> None:
    """
    Standard error logging with consistent formatting.

    Args:
        operation: Description of what was being attempted
        exception: The exception that occurred
        context: Additional context (instrument name, parameter, etc.)
        level: Logging level ('debug', 'info', 'warning', 'error')
        set_offline: Object to set _online=False on (for instruments)
        exc_info: Whether to include exception traceback
    """
    context_str = f" for {context}" if context else ""
    message = f"{operation} failed{context_str}: {exception}"

    # Set instrument offline if requested
    if set_offline and hasattr(set_offline, "_online"):
        set_offline._online = False
        message += " (instrument marked offline)"

    # Log at appropriate level
    log_func = getattr(logger, level.lower(), logger.error)
    log_func(message, exc_info=exc_info)


@contextmanager
def error_context(
    operation: str,
    context: str = "",
    expected_exceptions: tuple[type[Exception], ...] = (),
    recoverable_exceptions: tuple[type[Exception], ...] = (),
    reraise: bool = True,
    set_offline: object | None = None,
    default_return: Any = None,
):
    """
    Context manager for standardized error handling.

    Args:
        operation: Description of what's being attempted
        context: Additional context for logging
        expected_exceptions: Exceptions that are normal control flow (log at DEBUG)
        recoverable_exceptions: Exceptions that are warnings, not errors
        reraise: Whether to re-raise exceptions after logging
        set_offline: Object to set _online=False on for critical errors
        default_return: Value to return if exception caught and not re-raised

    Example:
        with error_context("Reading parameter", context=self.name,
                          expected_exceptions=(TimeoutError,),
                          recoverable_exceptions=(ConnectionError,),
                          set_offline=self):
            return self.device.query("*IDN?")
    """
    try:
        yield
    except SYSTEM_EXCEPTIONS:
        # Never catch system exceptions
        raise
    except expected_exceptions as e:
        # Expected control flow - log at debug level only
        log_error(operation, e, context, level="debug", exc_info=False)
        if not reraise:
            return default_return
        raise
    except recoverable_exceptions as e:
        # Recoverable errors - log as warnings
        log_error(operation, e, context, level="warning", exc_info=False)
        if not reraise:
            return default_return
        raise
    except Exception as e:
        # Critical errors - log as errors and set offline if requested
        log_error(operation, e, context, level="error", set_offline=set_offline)
        if not reraise:
            return default_return
        raise


def handle_connection_error(func: Callable) -> Callable:
    """
    Decorator for instrument connection methods.
    Automatically sets instrument offline on connection failures.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with error_context(
            operation=f"Connection operation ({func.__name__})",
            context=getattr(self, "name", "unknown"),
            recoverable_exceptions=CONNECTION_EXCEPTIONS,
            set_offline=self,
            reraise=False,
        ):
            return func(self, *args, **kwargs)

    return wrapper


def handle_communication_error(func: Callable) -> Callable:
    """
    Decorator for instrument communication methods.
    Sets instrument offline and re-raises communication errors.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with error_context(
            operation=f"Communication operation ({func.__name__})",
            context=getattr(self, "name", "unknown"),
            recoverable_exceptions=CONNECTION_EXCEPTIONS,
            set_offline=self,
            reraise=True,
        ):
            return func(self, *args, **kwargs)

    return wrapper


def handle_file_operation(func: Callable) -> Callable:
    """
    Decorator for file operations.
    Logs file errors but doesn't crash the application.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with error_context(
            operation=f"File operation ({func.__name__})",
            recoverable_exceptions=FILE_OPERATION_EXCEPTIONS,
            reraise=False,
        ):
            return func(*args, **kwargs)

    return wrapper


def safe_cleanup(operation: str, cleanup_func: Callable, context: str = "") -> None:
    """
    Safely execute cleanup operations with proper error handling.

    Args:
        operation: Description of cleanup operation
        cleanup_func: Function to execute for cleanup
        context: Additional context for logging
    """
    try:
        cleanup_func()
        logger.debug(
            f"{operation} completed successfully{f' for {context}' if context else ''}"
        )
    except Exception as e:
        logger.warning(f"{operation} failed{f' for {context}' if context else ''}: {e}")


def require_online(func: Callable) -> Callable:
    """
    Decorator that checks if instrument is online before executing method.
    Raises InstrumentError if instrument is offline.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not getattr(self, "_online", True):
            raise InstrumentError(
                f"Cannot execute {func.__name__}: {getattr(self, 'name', 'instrument')} is offline"
            )
        return func(self, *args, **kwargs)

    return wrapper


def log_optional_import(module_name: str, feature_name: str) -> bool:
    """
    Standard handling for optional dependencies.

    Args:
        module_name: Name of the module being imported
        feature_name: Description of the feature that will be unavailable

    Returns:
        True if import would succeed, False otherwise
    """
    try:
        __import__(module_name)
        return True
    except ImportError:
        logger.info(
            f"Optional dependency '{module_name}' not available - {feature_name} disabled"
        )
        return False


def validate_parameter(
    value: Any,
    param_name: str,
    allowed_types: tuple[type, ...] | None = None,
    allowed_values: list | range | set | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
) -> Any:
    """
    Validate parameter values with standardized error messages.

    Args:
        value: Value to validate
        param_name: Name of parameter for error messages
        allowed_types: Tuple of allowed types
        allowed_values: List/set/range of allowed values
        min_value: Minimum allowed value (for numeric types)
        max_value: Maximum allowed value (for numeric types)

    Returns:
        The validated value

    Raises:
        ValueError: If validation fails
    """
    # Type validation
    if allowed_types and not isinstance(value, allowed_types):
        type_names = [t.__name__ for t in allowed_types]
        raise ValueError(
            f"Parameter '{param_name}' must be of type {type_names}, got {type(value).__name__}"
        )

    # Value validation
    if allowed_values is not None and value not in allowed_values:
        raise ValueError(
            f"Parameter '{param_name}' must be one of {list(allowed_values)}, got {value}"
        )

    # Range validation
    if min_value is not None and value < min_value:
        raise ValueError(
            f"Parameter '{param_name}' must be >= {min_value}, got {value}"
        )

    if max_value is not None and value > max_value:
        raise ValueError(
            f"Parameter '{param_name}' must be <= {max_value}, got {value}"
        )

    return value


# Convenience functions for common error handling patterns
def handle_zmq_timeout(func: Callable) -> Callable:
    """Handle ZMQ timeout errors as expected control flow."""
    import zmq

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with error_context(
            operation=f"ZMQ operation ({func.__name__})",
            expected_exceptions=(zmq.ZMQError,),
            reraise=False,
        ):
            return func(*args, **kwargs)

    return wrapper


def handle_type_conversion(
    value: Any, target_type: type, param_name: str = "value"
) -> Any:
    """
    Safely convert value to target type with proper error handling.

    Args:
        value: Value to convert
        target_type: Target type to convert to
        param_name: Parameter name for error messages

    Returns:
        Converted value

    Raises:
        ValueError: If conversion fails
    """
    try:
        return target_type(value)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Cannot convert {param_name} '{value}' to {target_type.__name__}: {e}"
        )
