# Migration Guide to Version 4.0.0

This guide helps you migrate your code from Hardware Control 3.x to 4.0.0.

## Breaking Changes

### Instrument Connection API Refactored

**Why this change?** The old API allowed users to accidentally create resource leaks by repeatedly creating device connections without properly closing old ones. This was especially problematic for USB devices on Windows, where orphaned connections could prevent reconnection.

**What changed?** The `try_connect()` method now uses the template method pattern and should **not be overridden**. Instead, override these new methods:

- `establish_connection()` - Create the device connection
- `cleanup_connection()` - Clean up device resources (optional)
- `on_connect()` - Send initialization commands after connection (optional)

### Old API (3.x) - Do Not Use

```python
class MyInstrument(Instrument):
    def try_connect(self):
        # Don't override try_connect anymore!
        if self._dummy:
            return True

        if self._online:
            return True

        try:
            # Create device
            self.device = create_my_device()
            self._online = True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._online = False

        return self._online
```

### New API (4.0.0) - Use This

```python
class MyInstrument(Instrument):
    def establish_connection(self):
        """Create the device connection. Return True on success."""
        # Just focus on creating self.device
        # No need to check _online or _dummy
        # No need to set _online
        # No need for try/except (handled by base class)

        self.device = create_my_device()
        return True  # or False if failed

    def on_connect(self):
        """Optional: Send initialization commands after connection."""
        # Called AFTER connection is verified
        self.device.send_init_command()
        self.device.configure_mode("safe")
```

## Migration Steps

### 1. Rename `try_connect()` to `establish_connection()`

**Before:**
```python
def try_connect(self):
    # ... connection code ...
```

**After:**
```python
def establish_connection(self):
    # ... connection code ...
```

### 2. Remove State Management

The base class now handles all online/offline state management.

**Remove these:**
- `if self._online:` checks
- `self._online = True` or `self._online = False` assignments
- `if self._dummy:` checks (handled automatically)
- Return statements based on `self._online`

**Before:**
```python
def try_connect(self):
    if self._online:
        return True  # ❌ Remove

    if self._dummy:  # ❌ Remove
        self._online = True
        return True

    # ... connection code ...
    self._online = True  # ❌ Remove
    return self._online  # ❌ Change to True/False
```

**After:**
```python
def establish_connection(self):
    # ✅ Just create the device and return success
    # ... connection code ...
    return True  # or False
```

### 3. Simplify Connection Logic

Focus only on creating `self.device` and returning success/failure.

**Before:**
```python
def try_connect(self):
    if self._online:
        return True

    try:
        self.device = MyDevice(self.connection_addr)
        self._online = True
    except Exception as e:
        logger.error(f"Failed: {e}")
        self._online = False
        return False

    return self._online
```

**After:**
```python
def establish_connection(self):
    self.device = MyDevice(self.connection_addr)
    return True
    # Note: try/except is handled by base class
```

### 4. Move Initialization Commands to `on_connect()`

If your old `try_connect()` sent commands after connection, move them to `on_connect()`.

**Before:**
```python
def try_connect(self):
    result = super().try_connect()  # ❌ Don't call super().try_connect()

    if self._online and self.device:
        self.device.clear_buffer()  # ❌ Move to on_connect()
        self.device.enable_user_mode()  # ❌ Move to on_connect()

    return result
```

**After:**
```python
def on_connect(self):
    """Called after connection is established and verified."""
    self.device.clear_buffer()
    self.device.enable_user_mode()
```

### 5. Add Custom Cleanup (If Needed)

If your device needs special cleanup, override `cleanup_connection()`.

**Only needed if:**
- Your device type doesn't have a `.close()` method
- You need to release additional resources
- You have custom cleanup logic

**Example:**
```python
def cleanup_connection(self):
    """Clean up custom device resources."""
    if self.device is not None:
        self.device.shutdown()
        self.device.release_hardware()
        self.device = None
```

## Real-World Examples

### Example 1: Simple USB Device (Vortran Stradus)

**Before (3.x):**
```python
def try_connect(self):
    if self._dummy:
        return True

    self.device = vortran.get_lasers()[self.laser_id]

    if self.device is None:
        raise ValueError(f"Laser at ID {self.laser_id} is not available")

    connection_result = self.device.open_connection()

    if connection_result == True:
        logger.info(f"Connection successful")
        self._online = True
    else:
        logger.error(f"Connection unsuccessful")

    return connection_result
```

**After (4.0.0):**
```python
def establish_connection(self):
    """Establish connection to Vortran Stradus laser via USB."""
    self.device = vortran.get_lasers()[self.laser_id]

    if self.device is None:
        raise ValueError(f"Laser at ID {self.laser_id} is not available")

    connection_result = self.device.open_connection()

    if connection_result:
        logger.info(f"Connection successful")
    else:
        logger.error(f"Connection unsuccessful")

    return connection_result
```

### Example 2: Custom Socket Type (ADAM Module)

**Before (3.x):**
```python
def try_connect(self):
    if self.connection_tries < 1:
        self.connection_tries += 1
        return False

    if self._dummy:
        super().try_connect()

    if not self._online:
        try:
            self.device = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.device.settimeout(0.950)
            self.device.connect(self.addr)
            self._online = True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._online = False
            return self._online
```

**After (4.0.0):**
```python
def establish_connection(self):
    """Establish DGRAM socket connection to ADAM module."""
    # Prevent connection during boot-up
    if self.connection_tries < 1:
        self.connection_tries += 1
        return False

    try:
        self.device = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.device.settimeout(0.950)
        self.device.connect(self.addr)
        return True
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False
```

### Example 3: With Initialization Commands (TPI)

**Before (3.x):**
```python
def try_connect(self):
    ret = super().try_connect()
    if self._online and not self._dummy:
        self.config()
        self.command("USER_CONTROL")
    return ret
```

**After (4.0.0):**
```python
def on_connect(self):
    """Initialize TPI after connection."""
    self.config()
    self.command("USER_CONTROL")
```

## Deprecation Timeline

- **Version 4.0.0**: Deprecation warnings added, old API still works
- **Version 4.1.0**: Warnings become louder
- **Version 5.0.0**: Old API will be removed, must use new API

## Already Migrated Drivers

These built-in drivers have been migrated to the new API:

- `Stradus` - Vortran laser (USB)
- `AdamBase` - Advantech ADAM modules (DGRAM socket)
- `Ni_9000` - National Instruments DAQ
- `Picoscope` - Picotech oscilloscopes
- `SRS_DG535` - Stanford Research Systems delay generator
- `TPI` - Trinity Power signal generator

You can use these as reference examples for your own migrations.

## Benefits of New API

✅ **No resource leaks** - Automatic cleanup before reconnection
✅ **Simpler code** - 30-50% less code in custom drivers
✅ **Clearer intent** - Separation of connection vs. initialization
✅ **Impossible to forget** - State management is automatic
✅ **Better errors** - Consistent error handling and logging

## Getting Help

If you encounter issues migrating your instrument drivers:

1. Check the [examples](https://github.com/your-repo/examples) for reference
2. Look at the migrated drivers listed above
3. File an issue on GitHub with your specific use case
4. See the [Adding Instruments](adding_instruments.md) guide for details

## Summary Checklist

When migrating an instrument driver:

- [ ] Rename `try_connect()` → `establish_connection()`
- [ ] Remove all `self._online` checks and assignments
- [ ] Remove all `self._dummy` checks
- [ ] Change return to `True` or `False` (not `self._online`)
- [ ] Move initialization commands to `on_connect()` if needed
- [ ] Add `cleanup_connection()` only if custom cleanup needed
- [ ] Test connection and reconnection behavior
- [ ] Test in dummy mode (should still work automatically)
