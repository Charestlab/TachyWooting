# TachyWooting

[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](LICENSE)
[![Python versions](https://img.shields.io/pypi/pyversions/tachywooting)](https://pypi.org/project/tachywooting/)
[![Tests](https://github.com/mathiassalvas/wooting-analog/actions/workflows/CI.yml/badge.svg)](https://github.com/mathiassalvas/wooting-analog/actions/workflows/CI.yml)

Python bindings and acquisition utilities for Wooting analog keyboards.

For deeper implementation details, see [documentation.md](documentation.md).
Read the Docs/Sphinx sources live in [docs/](docs/) and use NumPy-style docstrings.
Console scripts are documented in [docs/scripts.md](docs/scripts.md).

## Project Documentation

- [README.md](README.md): project overview and quick start
- [documentation.md](documentation.md): technical details and architecture notes
- [development.md](development.md): maintainer workflow and SDK update process
- [PLUGIN_MANAGEMENT.md](PLUGIN_MANAGEMENT.md): plugin installation and troubleshooting
- [raw_sdk.md](raw_sdk.md): direct `lib`/`ffi` SDK reference for advanced use

- **Analog Key Acquisition**: Read key positions (0.0–1.0) with microsecond-level timing
- **Threshold-Based Triggering**: Automatically capture key press trajectories around actuation threshold
- **HDF5 Logging**: Hierarchical per-trial logging with automatic shard merging
- **Multi-Key Support**: Efficiently read multiple keys simultaneously using full-buffer API
- **Cross-Platform**: Linux, macOS, and Windows support
- **Automatic Setup**: Self-contained installation with system configuration
- **CLI Tools**: Command-line utilities for plugin management and testing

- Read analog key pressure as floats in the `0.0` to `1.0` range.
- Convert analog pressure to integer values in the `0` to `255` range.
- Acquire one or more keys around a threshold crossing.
- Log trials to hierarchical HDF5 files.
- Build against the bundled Wooting Analog SDK headers and native libraries.
- Inspect HDF5 logs with a small visualization CLI.

## Requirements

- Python 3.10 or newer.
- A supported Wooting analog keyboard.
- A local compiler toolchain for the CFFI interface build.
- Platform-specific permissions for USB/native library access.

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
python -m pip install -e ".[dev]"
wooting-build-interface
```

For visual TachyPy feedback support:

```bash
python -m pip install -e ".[tachypy]"
```

## Quick Start

```python
from tachywooting import WOOTING_ACQUISITION

acq = WOOTING_ACQUISITION(threshold=0.8)
acq.initialize_keyboard(verbose=True)

try:
    acq.setup_logging(name="tracking", path="logs", int_analog=2)
    trial = acq.acquire_analog_values(target_keys=["A"])
finally:
    acq.uninitialize_keyboard()
```

## CLI Demo

```bash
wooting-demo --key A --threshold 50
```

## Visual Readiness Feedback

```python
acq.wait_keys_light_press_visual(
    screen=screen,
    response_handler=response_handler,
    target_keys=["c", "z"],
)
```

## HDF5 Logging

`setup_logging()` writes one temporary shard per trial and merges shards when `uninitialize_keyboard()` is called.

Final files use this layout:

```text
/trials/0001/keys/0004/values
```

Each `values` dataset stores columns in this order:

```text
position, time_to_threshold, time_abs
```

## Visualize Logs

```bash
python -m tachywooting.visualize logs/tracking.hdf5 --list
python -m tachywooting.visualize logs/tracking.hdf5 --trial 1 --key 4
```

## Public API

- `WOOTING_ACQUISITION`: acquisition, threshold detection, readiness checks, and logging.
- `convert_char_to_keycode`: convert between key labels and HID keycodes.
- `load_trial`: load a single trial from an HDF5 log file.
- `load_session`: load all trials from an HDF5 log file.
- `trial_to_dataframe`: convert a trial dict to a pandas DataFrame.
- `build_interface`: rebuild the CFFI interface.
- `delete_interface`: remove generated CFFI artifacts.
- `lib` and `ffi`: raw CFFI handles for advanced SDK access.

## Troubleshooting

If importing works but acquisition fails with a missing native interface error, run:

```bash
wooting-build-interface
```

If no devices are detected, confirm the keyboard is connected, Wootility recognizes it, and platform permissions have been applied.

## Hardware Requirements

This package was developed and tested with the **Wooting UwU** keypad ([wooting.io/uwu](https://wooting.io/uwu)), and its use is strongly recommended for optimal results.

The UwU is a 3-key Hall effect keypad using [**Lekker L45 V2 linear switches**](https://wooting.io/product/lekker-switch-l45-v2) — contactless magnetic sensors with a smooth linear force curve (30–45 cN, no tactile bump). Keys can be configured to actuate at any depth from 0.1mm to 4.0mm.