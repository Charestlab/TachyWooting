# Python Interface for Wooting Analog SDK

A Python interface for the Wooting Analog SDK that enables reading analog key values and managing keyboard events. This library provides a high-level Python wrapper around the Wooting Analog SDK, making it easy to integrate analog keyboard support into Python applications.

---

## Features

- Read analog key values (0.0 to 1.0 range) or integers (0 to 255 range)
- Multi-device support
- Cross-platform (Windows and macOS)
- Event handling for device connections/disconnections
- Multiple keycode modes (HID, ScanCode1, VirtualKey)
- Simple and intuitive API

## Installation

```bash
pip install .
```

Or for development mode:
```bash
pip install -e .
```

### What happens during installation

The installation automatically:
1. **Compiles the CFFI interface** - Creates Python bindings for the Wooting SDK
2. **Sets up USB permissions** (Linux/macOS) - Configures udev rules following [Wootility recommendations](https://help.wooting.io/article/12-configuring-device-access-for-wootility-under-linux)
3. **Installs system plugins** - Deploys SDK and plugins to system directories

*Note: Steps 2 and 3 require sudo/admin privileges on Linux/macOS.*

### System Files Installed

| Platform | SDK Location | Plugin Location | Permissions |
|----------|-------------|-----------------|-------------|
| **Linux** | `/usr/local/lib/libwooting_analog_sdk.so` | `/usr/local/share/WootingAnalogPlugins/` | `/etc/udev/rules.d/70-wooting.rules`<br>(MODE 0660, GROUP input, TAG uaccess) |
| **macOS** | `/usr/local/lib/libwooting_analog_sdk.dylib` | `/usr/local/share/WootingAnalogPlugins/` | N/A |
| **Windows** | `C:\Program Files\WootingAnalogPlugins\` | Same as SDK | N/A |

### Plugin Management

For manual plugin installation, uninstallation, or troubleshooting, see [PLUGIN_MANAGEMENT.md](PLUGIN_MANAGEMENT.md).

#### CLI Commands:
```bash
# Install plugins manually
wooting-install-plugins

# Uninstall plugins
wooting-uninstall-plugins

# Complete cleanup (interface + plugins)
wooting-delete-interface --cleanup-plugins
```

#### Python API:
```python
# Manual installation
from wooting_package.post_install import install_plugins
install_plugins()

# Uninstall plugins only
from wooting_package.post_install import uninstall_plugins
uninstall_plugins()

# Complete cleanup (interface + plugins)
from wooting_package.wooting_utils import delete_interface
delete_interface(cleanup_plugins=True)
```

### Testing Installation

After installation, verify everything works:

```bash
wooting-demo
```

This demo monitors key presses and displays analog values in real-time.

### Command Line Tools

The package provides several CLI tools:

| Command | Description |
|---------|-------------|
| `wooting-demo` | Interactive analog key monitor with real-time visualization |
| `wooting-install-plugins` | Manually install SDK and plugins to system directories |
| `wooting-uninstall-plugins` | Remove SDK and plugins from system |
| `wooting-delete-interface` | Clean up compiled interface (add `--cleanup-plugins` to also remove plugins) |

**Examples:**
```bash
# Test keyboard
wooting-demo -k A

# Manual plugin management
wooting-install-plugins
wooting-uninstall-plugins

# Cleanup
wooting-delete-interface                    # Interface only
wooting-delete-interface --cleanup-plugins  # Interface + plugins
```

---

## Project Structure

```
wooting-analog/
├── setup.py                          # Installation with post-install hooks
├── pyproject.toml                    # Modern Python package configuration
├── requirements.txt
├── PLUGIN_MANAGEMENT.md              # Detailed plugin management guide
├── example_plugin_management.py      # Interactive plugin management script
└── wooting_package/
    ├── __init__.py                   # Auto-initialization logic
    ├── cli.py                        # wooting-demo CLI tool
    ├── post_install.py               # Installation and plugin management
    ├── wooting_utils.py              # High-level acquisition API
    ├── wooting_interface_builder.py  # CFFI interface builder
    ├── text_extraction.py            # Header parser for CFFI
    ├── visualize.py                  # HDF5 data visualizer
    ├── interface/                    # Compiled CFFI bindings (generated)
    │   ├── __init__.py
    │   └── wooting_interface*.so     # Platform-specific binary
    ├── libraries/                    # Native SDK libraries per platform
    │   ├── linux/
    │   ├── darwin/
    │   └── windows/
    └── permissions/                  # Platform-specific permission scripts
        ├── PERMISSIONS_linux.sh      # Udev rules setup (Wootility spec)
        └── PERMISSIONS_mac.sh        # macOS Gatekeeper setup
```

---

## Linux Permissions (Udev Rules)

On Linux, the installation automatically creates `/etc/udev/rules.d/70-wooting.rules` following [Wootility's official recommendations](https://help.wooting.io/article/12-configuring-device-access-for-wootility-under-linux):

- **MODE 0660**: Read/write for owner and group only (secure)
- **GROUP input**: Standard input device group
- **TAG uaccess**: ACL for currently logged-in user

This configuration:
- Supports all Wooting models (One, Two, UwU, 60HE, etc.)
- Includes update modes for firmware flashing
- Works with snap Chromium installations
- No manual group membership required

The rules are applied automatically during installation. If you encounter permission issues:
1. Unplug and replug the keyboard
2. Verify rules: `cat /etc/udev/rules.d/70-wooting.rules`
3. Check permissions: `ls -l /dev/hidraw*`

---

## Usage

### Analog Values
There are 251 possible values.
The possible analog values fall within the set `[0] ∪ [5, 255]`, meaning:

- Value `0` corresponds to **no pressure**
- The usable analog pressure values range from **5 to 255**, giving a total of **251 distinct values**
- Values `1` to `4` are **never logged** and therefore considered unavailable

#### Value Calculation

- The smallest non-zero analog value is approximately **0.01961** (5/255)
- Each subsequent pressure level increases by approximately **0.00392** (1/255)
- All pressure values follow the formula: `Pressure(n) = n / 255` for n ∈ [5, 255]

Example values:
- `5/255 ≈ 0.01961` (real value `0.019607843831181526`)
- `6/255 ≈ 0.02353` (real value `0.0235294122248888`)
- `...`
- `255/255 = 1.0`

#### Integer values function
A function has been made to make the conversion automatically.

```
from wooting_utils import WOOTING_ACQUISITION()

acquisition = WOOTING_ACQUISITION()
acquisition.acquire_integer_values(target_key=['1'])

```

### Key Functions

<<<<<<< HEAD
=======
#### `initialize_keyboard(verbose=False)`
Initialize the Wooting keyboard interface and optionally display device information.

#### `uninitialize_keyboard()`
Clean up and uninitialize the keyboard interface.

##### `wooting_plotting_response_test()`
Simple plot of position over time for a number of repetitions.

#### class WOOTING_ACQUISITION : 

#### `acquire_analog_values(target_keys, threshold, duration_after_threshold, ...)`
Acquire analog values for specified keys around threshold crossing.

#### `acquire_integer_values(target_keys, threshold, duration_after_threshold, ...)`
Acquire analog values and convert to integers (0-255).

### `setup_logging(name, path, int_analog)`
Configure logging (name and folder, int/analog mode). Creates staging directory for per-trial shards and registers the logger for automatic merge on uninit.


The package exposes the following key components:

>>>>>>> 4ad13f9 (changes)
- **WOOTING_ACQUISITION**  
  Main class for acquiring analog or integer key values from your Wooting keyboard.  
  Handles logging, acquisition, and interface management.

  - **initialize_keyboard(verbose=False)**  
    Initializes the Wooting interface and prints device info.  
    This is essential before any acquisition to ensure the keyboard is detected and ready.

  - **uninitialize_keyboard()**  
    Uninitializes the interface and merges temporary log files.  
    Always call this when done to properly close the connection and save logs.

  - **acquire_analog_values(target_keys, threshold, duration_after_threshold, ...)**  
    Acquires analog values (0.0–1.0) for specified keys around threshold crossing.

  - **acquire_integer_values(target_keys, threshold, duration_after_threshold, ...)**  
    Acquires analog values and converts them to integers (0–255).

  - **setup_logging(name=None, path=None, int_analog=2, formats="parquet")**  
    Configures logging for your acquisitions.  
    Allows you to specify the log file name, output directory, analog/int mode.  
    Creates per-trial files in a staging folder and merges them into a single file on uninitialization.

- **convert_char_to_keycode**  
  Utility function to convert a character or key name to its HID keycode (and vice versa).

- **lib**  
  CFFI object exposing native functions from the Wooting Analog SDK.

- **ffi**  
  CFFI object for managing native buffers and structures.

- **build_interface**  
  Function to rebuild the C interface if you modify the source files.

- **delete_interface**  
  Utility function to clean up generated interface files and caches.

---

## HDF5 layout (quick)

Final HDF5 file `{log_base}.hdf5` contains:

- /trials/0001/keys/0001/values  — dataset with rows [position, time_to_threshold, time_abs] (float64)
- Dataset attributes include column names as bytes: [b"position", b"time_to_threshold", b"time_abs"]

`time_abs` is the wall-clock timestamp (time.time()) recorded for each sample.

---

## Visualizer

A small interactive utility `wooting_package/visualize.py` helps explore/plot datasets inside a combined HDF5. Usage example:

```bash
python -m wooting_package.visualize path/to/wooting_logs.hdf5
```

It will list top-level entries, let you pick a trial, select a key, and plot the `values` dataset (position vs time_to_threshold). Useful for quick inspection.

---

### Error Codes

Negative values correspond to the following error codes:
- `NoMapping`: No keycode mapping found
- `UnInitialized`: SDK not initialized
- `NoDevices`: No devices connected

### Keycode Modes

The SDK supports multiple keycode modes that can be set using `wooting_analog_set_keycode_mode`:

- `HID`: Standard USB HID codes (default)
- `ScanCode1`: Scan codes set 1
- `VirtualKey`: Windows Virtual Key codes
- `VirtualKeyTranslate`: Windows Virtual Key codes translated to current layout (Windows only)

## Dependencies

- Python 3.6 or higher
    └── Using Python 3.12 and + may cause issues notably due to free-threading
- cffi >= 1.15.0
- Wooting Analog SDK (included in package)
- numpy
- matplotlib
- setuptools
- hdf5

## Platform Support

### Windows
- Requires Wooting Analog SDK installed
- Supports all keycode modes
- Uses DLL files for libraries

### macOS
- Requires Wooting Analog SDK installed
- Supports HID and ScanCode1 modes
- Uses dylib files for libraries

## Example + logging in parquet :

```python
from wooting_package import WOOTING_ACQUISITION

acq = WOOTING_ACQUISITION()
acq.initialize_keyboard()
acqu.setup_logging(path=os.getcwd(), name="tracking.hdf5", int_analog=1, formats="hdf5")
acq.acquire_integer_values(target_keys=['A'])
acq.uninitialize_keyboard()

```

This initializes the interface, acquires integer values for the "A" key, and then properly closes the connection.

## Contributing

Feel free to submit issues and enhancement requests!



Faire dictionnaire pour key et key

au final json, numpy et hdf5 pour logging