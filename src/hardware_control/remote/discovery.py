"""Registry file management and App discovery."""

import json
from pathlib import Path

import psutil
from platformdirs import user_cache_dir


def get_registry_dir() -> Path:
    """Get platform-specific cache directory for registry files.

    Returns:
        Path to registry directory (created if doesn't exist)

    Platform-specific paths:
        - Linux: ~/.cache/hardware-control/apps/
        - macOS: ~/Library/Caches/hardware-control/apps/
        - Windows: C:\\Users\\<user>\\AppData\\Local\\hardware-control\\Cache\\apps\\
    """
    cache_dir = Path(user_cache_dir("hardware-control", "lbnl"))
    registry_dir = cache_dir / "apps"
    registry_dir.mkdir(parents=True, exist_ok=True)
    return registry_dir


def is_app_alive(pid: int) -> bool:
    """Check if a process with given PID exists.

    Args:
        pid: Process ID to check

    Returns:
        True if process exists, False otherwise
    """
    return psutil.pid_exists(pid)


def cleanup_stale_files() -> list[Path]:
    """Remove registry files for processes that no longer exist.

    Returns:
        List of paths that were cleaned up
    """
    registry_dir = get_registry_dir()
    cleaned = []

    for registry_file in registry_dir.glob("app_*.json"):
        try:
            with open(registry_file) as f:
                data = json.load(f)

            pid = data.get("pid")
            if pid is None or not is_app_alive(pid):
                registry_file.unlink()
                cleaned.append(registry_file)
        except (json.JSONDecodeError, OSError):
            # Invalid or inaccessible file, remove it
            try:
                registry_file.unlink()
                cleaned.append(registry_file)
            except OSError:
                pass

    return cleaned


def list_running_apps() -> list[dict]:
    """List all running hardware-control Apps.

    Returns:
        List of dicts with keys: app_name, pid, ipc_address, birth_time, platform
        Sorted by birth_time (oldest first)
    """
    cleanup_stale_files()
    registry_dir = get_registry_dir()
    apps = []

    for registry_file in registry_dir.glob("app_*.json"):
        try:
            with open(registry_file) as f:
                data = json.load(f)

            # Verify process still exists
            pid = data.get("pid")
            if pid and is_app_alive(pid):
                apps.append(data)
        except (json.JSONDecodeError, OSError):
            pass

    # Sort by birth_time
    apps.sort(key=lambda x: x.get("birth_time", ""))
    return apps


def discover_app(app_name: str | None = None, pid: int | None = None) -> dict:
    """Find a specific App or auto-select if only one is running.

    Args:
        app_name: Name of the App to find (optional)
        pid: Process ID to find (optional)

    Returns:
        Dict with app metadata (app_name, pid, ipc_address, etc.)

    Raises:
        RuntimeError: If no Apps found, multiple Apps found without specification,
                     or specified App not found
    """
    apps = list_running_apps()

    if not apps:
        raise RuntimeError("No hardware-control Apps are currently running")

    # Filter by PID if specified
    if pid is not None:
        apps = [app for app in apps if app.get("pid") == pid]
        if not apps:
            raise RuntimeError(f"No App found with PID {pid}")
        return apps[0]

    # Filter by name if specified
    if app_name is not None:
        apps = [app for app in apps if app.get("app_name") == app_name]
        if not apps:
            available = list_running_apps()
            if available:
                app_list = "\n".join(
                    f"  {app['app_name']} (pid: {app['pid']})" for app in available
                )
                raise RuntimeError(
                    f"No App found with name '{app_name}'\nAvailable Apps:\n{app_list}"
                )
            raise RuntimeError(f"No App found with name '{app_name}'")
        return apps[0]

    # Auto-select if only one App
    if len(apps) == 1:
        return apps[0]

    # Multiple Apps, user must specify
    app_list = "\n".join(f"  {app['app_name']} (pid: {app['pid']})" for app in apps)
    raise RuntimeError(
        f"Multiple Apps running. Specify one:\n{app_list}\n\n"
        f"Use: hc-query --app <name> or --pid <pid>"
    )
