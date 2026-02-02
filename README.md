# Wooting Analog SDK - Python Interface

A comprehensive Python interface for the Wooting Analog SDK enabling reading analog key positions from Wooting keyboards with high-precision timing and optional HDF5 logging.

## 🎯 Features

- **Analog Key Acquisition**: Read key positions (0.0–1.0) with microsecond-level timing
- **Threshold-Based Triggering**: Automatically capture key press trajectories around actuation threshold
- **HDF5 Logging**: Hierarchical per-trial logging with automatic shard merging
- **Multi-Key Support**: Efficiently read multiple keys simultaneously using full-buffer API
- **Cross-Platform**: Linux, macOS, and Windows support
- **Automatic Setup**: Self-contained installation with system configuration
- **CLI Tools**: Command-line utilities for plugin management and testing

## 📦 Installation

### Quick Start

```bash
pip install .
```

### What Happens During Installation

The installation automatically handles:

1. **CFFI Compilation** - Builds Python bindings for the Wooting SDK
2. **Permission Setup** (Linux/macOS) - Configures udev rules/Gatekeeper
3. **Plugin Installation** - Deploys SDK and plugins to system directories

On first use (e.g., `wooting-demo`), the package automatically:
- Sets up Linux permissions if needed
- Compiles the CFFI interface
- Installs SDK and plugins to system directories

**Note**: Steps 2-3 require `sudo`/admin privileges.

### Development Installation

```bash
pip install -e .
```

Same as above, but allows editing source files directly.

## 🗂️ System Files Installed

| Platform | SDK Location | Plugins Location | Permissions |
|----------|-------------|------------------|-------------|
| **Linux** | `/usr/local/lib/libwooting_analog_sdk.so` | `/usr/local/share/WootingAnalogPlugins/` | `/etc/udev/rules.d/70-wooting.rules` |
| **macOS** | `/usr/local/lib/libwooting_analog_sdk.dylib` | `/usr/local/share/WootingAnalogPlugins/` | N/A (Gatekeeper handled) |
| **Windows** | `C:\Program Files\WootingAnalogPlugins\` | Same directory | N/A |

## 🛠️ CLI Tools

| Command | Description |
|---------|-------------|
| `wooting-demo` | Real-time analog key monitor |
| `wooting-install-plugins` | Manually install SDK and plugins |
| `wooting-uninstall-plugins` | Remove SDK and plugins |
| `wooting-delete-interface [--cleanup-plugins]` | Clean up compiled interface (optionally remove plugins) |

### Examples

```bash
# Test keyboard connectivity
wooting-demo -k A

# Monitor key 'G'
wooting-demo -k G

# Manual plugin management
wooting-install-plugins
wooting-uninstall-plugins

# Complete system cleanup
wooting-delete-interface --cleanup-plugins
```

## 🚀 Usage

### Basic Analog Key Acquisition

```python
from wooting_package import WOOTING_ACQUISITION

# Initialize acquisition
acq = WOOTING_ACQUISITION(
    threshold=0.8,                    # Actuation threshold (0.0-1.0)
    max_pressure_start=0.35,          # Light press detection threshold
    backend="auto"                    # 'auto', 'read_analog', or 'read_full_buffer'
)

# Initialize keyboard
acq.initialize_keyboard(verbose=True)

# Acquire analog values around threshold crossing
data = acq.acquire_analog_values(
    target_keys=['A', 'B'],
    threshold=0.8,
    duration_before_threshold=0.2,    # seconds
    duration_after_threshold=0.5,     # seconds
    sampling_interval=1/8000          # 8kHz sampling
)

# Uninitialize when done
acq.uninitialize_keyboard()

# Data structure:
# {
#     "1": {                                    # trial number
#         "4": {                                # keycode
#             "position": array([0.0, 0.2, ...]),
#             "time_to_threshold": array([...]),
#             "time_abs": array([...])
#         }
#     }
# }
```

### Integer Values (0-255)

```python
# Similar to acquire_analog_values, but quantizes to integers
data = acq.acquire_integer_values(
    target_keys=['A'],
    duration_after_threshold=0.5,
    sampling_interval=1/8000
)
```

### With HDF5 Logging

```python
acq = WOOTING_ACQUISITION()
acq.initialize_keyboard()

# Setup logging (creates hierarchical HDF5 file)
acq.setup_logging(
    name="experiment_P001",           # output file: experiment_P001.hdf5
    path="/path/to/data",             # output directory
    int_analog=2                       # 2=analog (0..1), 1=integer (0..255)
)

# Each acquisition is written to a per-trial shard
for trial in range(10):
    data = acq.acquire_analog_values(
        target_keys=['A', 'B'],
        duration_after_threshold=0.5
    )

# On uninitialize, all shards are merged into one HDF5 file
acq.uninitialize_keyboard()  # Creates experiment_P001.hdf5
```

### Ready State Detection

Wait for user to prepare before a trial:

```python
# Wait for all target keys to be lightly pressed and held
start_time = acq.wait_keys_light_press(
    target_keys=['A'],
    quit_key='Esc',                   # Press Esc to cancel
    hold_seconds=0.3,                 # Hold for 300ms
    timeout_seconds=30.0,             # Timeout after 30s
    verbose=True                      # Print progress
)

# Now ready to acquire
data = acq.acquire_analog_values(
    target_keys=['A'],
    trial_start_ns=int(start_time * 1e9)
)
```

### Optional Timed Callback

Execute an action at precise timing (e.g., display stimulus):

```python
def show_stimulus():
    print("STIMULUS DISPLAYED")

# Execute callback 0.5s after trial start (unless threshold hit first)
data = acq.acquire_analog_values(
    target_keys=['A'],
    trial_start_ns=trial_start_ns,
    callback=show_stimulus,
    callback_delay=0.5                # seconds after trial_start
)
```

### Quit Key Detection

Detect if user pressed a key during acquisition (without stopping):

```python
data, quit_pressed = acq.acquire_analog_values(
    target_keys=['A'],
    quit_key='Esc',                   # Monitor this key
    duration_after_threshold=0.5
)

if quit_pressed:
    print("User pressed Esc during acquisition")
```

## 📊 HDF5 Data Structure

Output file structure after logging:

```
experiment_P001.hdf5
├── /trials/
│   ├── 0001/                        # Trial 1
│   │   ├── .attrs
│   │   │   ├── backend = b"read_full_buffer"
│   │   │   ├── trial_start_perf_ns = 123456789
│   │   │   └── stim_on_clock = b"perf"
│   │   └── keys/
│   │       ├── 0001/                # Key with code 1 (usually 'A')
│   │       │   └── values (N×3)     # [position, time_to_threshold, time_abs]
│   │       └── 0004/                # Key with code 4 (usually 'D')
│   │           └── values (M×3)
│   ├── 0002/
│   │   └── keys/ ...
│   └── ...
```

### Reading HDF5 Data

```python
import h5py
import numpy as np

with h5py.File("experiment_P001.hdf5", "r") as f:
    # List trials
    trials = list(f["trials"].keys())
    print(f"Trials: {trials}")
    
    # Access a trial
    trial_001 = f["trials"]["0001"]
    print(f"Backend: {trial_001.attrs['backend'].decode()}")
    
    # Access a key's values
    key_values = trial_001["keys"]["0001"]["values"][()]  # (N, 3) array
    positions = key_values[:, 0]
    time_to_threshold = key_values[:, 1]
    time_abs = key_values[:, 2]
```

## 🔑 Key Value Ranges

### Analog Values

Wooting keyboards report analog pressure as integer values in a specific range with important properties:

**Range Definition:**
- There are **251 possible values** that can be returned
- The set of possible values is: `[0] ∪ [5, 255]`
- **Value 0** = no pressure (key released)
- **Values 1-4** = never returned by the SDK (unavailable)
- **Values 5-255** = actual pressure levels (251 distinct values)

**Value Calculation:**

The actual analog pressure is calculated as:
$$\text{Pressure}(n) = \frac{n}{255} \text{ for } n \in [5, 255]$$

Examples:
- Minimum pressure: $5/255 \approx 0.01961$ (exact: 0.019607843831181526)
- Small increment: $6/255 \approx 0.02353$ (exact: 0.0235294122248888)
- Each step increases by: $1/255 \approx 0.00392$
- Maximum pressure: $255/255 = 1.0$ (full actuation)

**Summary:**
- **Smallest non-zero value**: ≈ 0.0196 (5/255)
- **Resolution**: ≈ 0.00392 per unit (1/255)
- **Range in Python**: 0.0 to 1.0

### Integer Values

- **Range**: 0 to 255 (direct mapping from SDK)
- **Conversion from analog**: `int(round(analog_value * 255))`
- **Conversion to analog**: `analog_value / 255`

## 📐 API Reference

### WOOTING_ACQUISITION

Main class for acquiring analog key data.

#### Constructor Parameters

```python
WOOTING_ACQUISITION(
    start_trial_number: int = 1,
    threshold: float = 0.8,
    max_pressure_start: float = 0.35,
    backend: str = "auto",
    timing_mode: str = "hybrid",
    spin_margin_s: float = 0.0003,
    full_buffer_len: int = 256
)
```

- `start_trial_number`: Trial numbering offset (default: 1)
- `threshold`: Actuation threshold [0.05, 1.0] (must be ≥ max_pressure_start + 0.2)
- `max_pressure_start`: Light press upper bound [0.0, 1.0]
- `backend`: Reading strategy
  - `"auto"`: read_analog for 1 key, read_full_buffer for multiple
  - `"read_analog"`: Per-key polling (slower for many keys)
  - `"read_full_buffer"`: Read all pressed keys in one call (faster)
- `timing_mode`: Timing control
  - `"sleep"`: Low CPU, higher jitter
  - `"busy"`: High CPU, lower jitter
  - `"hybrid"`: Sleep most, busy-spin near deadline (recommended)
- `spin_margin_s`: Final window for busy-waiting (seconds)

#### Key Methods

- `initialize_keyboard(verbose=False)` → bool
  - Initializes SDK and detects devices
  - Raises `RuntimeError` if no devices found

- `uninitialize_keyboard()` → None
  - Closes SDK connection
  - Merges HDF5 shards if logging enabled

- `setup_logging(name, path, int_analog)` → None
  - Configure hierarchical HDF5 logging
  - Creates staging directory for per-trial shards

- `acquire_analog_values(target_keys, ...)` → dict or (dict, bool)
  - Returns analog data (0.0-1.0)
  - If `quit_key` provided, returns (dict, quit_pressed)

- `acquire_integer_values(target_keys, ...)` → dict or (dict, bool)
  - Returns integer data (0-255)
  - If `quit_key` provided, returns (dict, quit_pressed)

- `wait_keys_light_press(target_keys, quit_key, hold_seconds, ...)` → bool
  - Waits for keys in light-press range
  - Returns False if quit_key pressed

- `wait_keys_released(target_keys, hold_seconds, release_max, ...)` → float
  - Waits for keys to be released and stay released
  - Returns perf_counter timestamp

### Utility Functions

```python
from wooting_package import (
    convert_char_to_keycode,      # char ↔ keycode conversion
    delete_interface,              # cleanup compiled bindings
    build_interface,               # rebuild CFFI interface
)

from wooting_package.post_install import (
    install_plugins,               # manually install SDK/plugins
    uninstall_plugins,             # manually uninstall
)
```

## 🐧 Linux Permissions

The installation creates `/etc/udev/rules.d/70-wooting.rules` following [Wootility's official recommendations](https://help.wooting.io/article/12-configuring-device-access-for-wootility-under-linux):

**Rule Configuration:**
- `MODE 0660`: Read/write for owner and group (secure, not world-readable)
- `GROUP input`: Standard Linux input device group
- `TAG uaccess`: ACL for currently logged-in user

**Coverage:**
- All Wooting models (One, Two, UwU, 60HE, etc.)
- Firmware update modes
- Snap Chromium installations

**Troubleshooting:**

If device not accessible after installation:

```bash
# Verify rules are in place
cat /etc/udev/rules.d/70-wooting.rules

# Check device permissions
ls -l /dev/hidraw*

# Replug the keyboard
# Udev rules are applied on device connection

# Manual rules reload (if needed)
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## 🏗️ Project Structure

```
wooting-analog/
├── setup.py                    # Installation hooks
├── pyproject.toml              # Modern package config
├── README.md                   # This file
├── PLUGIN_MANAGEMENT.md        # Detailed plugin docs
├── example_plugin_management.py
│
└── wooting_package/
    ├── __init__.py             # Auto-initialization
    ├── cli.py                  # wooting-demo CLI
    ├── cleanup_cli.py          # wooting-delete-interface CLI
    ├── post_install.py         # Installation and plugin mgmt
    ├── wooting_utils.py        # Core acquisition API
    ├── wooting_interface_builder.py
    ├── text_extraction.py
    ├── visualize.py            # HDF5 data visualizer
    ├── interface/              # Generated CFFI bindings
    ├── libraries/              # Native SDK per platform
    └── permissions/            # Permission setup scripts
```

## 🔧 Troubleshooting

### "No Wooting devices found or failed to initialize"

1. Verify keyboard is connected
2. Check USB connection (try different port)
3. On Linux: Verify udev rules and permissions
4. Reinstall plugins: `wooting-install-plugins`

### "Failed to build CFFI interface"

- Install build dependencies: `pip install cffi>=1.15.0`
- Ensure C compiler is available

### "Permission denied" when installing plugins

- Commands requiring `sudo` will prompt for password
- Ensure user is in `input` group on Linux: `groups $USER`

## 📚 More Information

- [Wooting Official](https://wooting.io)
- [Wootility Configuration](https://help.wooting.io/article/12-configuring-device-access-for-wootility-under-linux)
- [Plugin Management Guide](PLUGIN_MANAGEMENT.md)

## 📝 License

See [LICENSE](LICENSE) file.

## 👥 Authors

- Mathias Salvas-Hébert
- Guillaume Lalonde-Beaudoin
