# Wooting Plugin Management

## Overview

The Wooting SDK requires system plugins to function. These plugins enable the SDK to communicate with Wooting keyboards.

## Automatic Installation

Plugins are automatically installed during package installation or when running `wooting-demo` for the first time. The following files are installed:

### Linux
- **SDK**: `/usr/local/lib/libwooting_analog_sdk.so`
- **Plugin**: `/usr/local/share/WootingAnalogPlugins/libwooting_analog_plugin.so`
- **Udev rules**: `/etc/udev/rules.d/70-wooting.rules` (MODE 0660, GROUP input, TAG uaccess)

### macOS
- **SDK**: `/usr/local/lib/libwooting_analog_sdk.dylib`
- **Plugin**: `/usr/local/share/WootingAnalogPlugins/libwooting_analog_plugin.dylib`

### Windows
- **SDK & Plugin**: `C:\Program Files\WootingAnalogPlugins\`

## Manual Installation

### Using CLI:
```bash
wooting-install-plugins
```

### Using Python:
```python
from wooting_package.post_install import install_plugins
install_plugins()
```

**Note**: Requires sudo/admin privileges on Linux/macOS.

## Uninstallation

### Option 1: Complete uninstallation (interface + plugins)

**CLI:**
```bash
wooting-delete-interface --cleanup-plugins
```

**Python:**
```python
from wooting_package.wooting_utils import delete_interface
delete_interface(cleanup_plugins=True)
```

### Option 2: Plugins only

**CLI:**
```bash
wooting-uninstall-plugins
```

**Python:**
```python
from wooting_package.post_install import uninstall_plugins
uninstall_plugins()
```

### Option 3: Interface only

**CLI:**
```bash
wooting-delete-interface
```

**Python:**
```python
from wooting_package.wooting_utils import delete_interface
delete_interface(cleanup_plugins=False)  # or simply delete_interface()
```

## Verify Installation

To verify plugins are correctly installed:

```bash
# Linux
ls -lh /usr/local/lib/libwooting_analog_sdk.so
ls -lh /usr/local/share/WootingAnalogPlugins/

# macOS
ls -lh /usr/local/lib/libwooting_analog_sdk.dylib
ls -lh /usr/local/share/WootingAnalogPlugins/

# Windows
dir "C:\Program Files\WootingAnalogPlugins"
```

## Testing

After installation, test with:

```bash
wooting-demo
```

Or in Python:

```python
from wooting_package.interface import lib, ffi

# Initialize SDK
result = lib.wooting_analog_initialise()
print(f"Devices found: {result}")

# Verify initialization
is_init = lib.wooting_analog_is_initialised()
print(f"Initialized: {is_init}")

# Cleanup
lib.wooting_analog_uninitialise()
```

## Troubleshooting

### Error: "No Wooting devices found"

1. Verify plugins are installed
2. Check USB permissions (Linux)
3. Unplug and replug keyboard

### Error: "NoPlugins" (-1995)

Plugins are not installed in the correct directory. Reinstall:

```python
from wooting_package.post_install import install_plugins
install_plugins()
```

### Error: Incompatible version

The wrapper and SDK have incompatible versions. Reinstall:

```python
from wooting_package.post_install import uninstall_plugins, install_plugins
uninstall_plugins()
install_plugins()
```

## Complete Cleanup

For a complete system cleanup (useful before reinstallation):

```python
from wooting_package.wooting_utils import delete_interface

# Remove everything: interface, Python cache, and system plugins
delete_interface(cleanup_plugins=True)
```

This will remove:
- Compiled CFFI interface
- `__pycache__` files
- SDK from `/usr/local/lib/`
- Plugins from `/usr/local/share/WootingAnalogPlugins/`

## Security Notes

- Plugin installation requires sudo/admin privileges
- Files are installed in standard system directories
- Uninstallation completely removes these files
- No residual files remain after `delete_interface(cleanup_plugins=True)`
- Aucun fichier résiduel n'est laissé après `delete_interface(cleanup_plugins=True)`
