"""Remote access library for hardware-control Apps."""

from .client import HardwareControlClient
from .discovery import (
    cleanup_stale_files,
    discover_app,
    get_registry_dir,
    is_app_alive,
    list_running_apps,
)

__all__ = [
    "HardwareControlClient",
    "cleanup_stale_files",
    "discover_app",
    "get_registry_dir",
    "is_app_alive",
    "list_running_apps",
]
