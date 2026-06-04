# Wooting Analog

Python bindings and acquisition utilities for Wooting analog keyboards.

For deeper implementation details, see [documentation.md](documentation.md).
Read the Docs/Sphinx sources live in [docs/](docs/) and use NumPy-style docstrings.
Console scripts are documented in [docs/scripts.md](docs/scripts.md).

## Features

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

## Installation

```bash
python -m pip install -e ".[cli,visualize]"
wooting-build-interface
```

For visual TachyPy feedback support:

```bash
python -m pip install -e ".[tachypy]"
```

## Quick Start

```python
from wooting_package import WOOTING_ACQUISITION

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
python -m wooting_package.visualize logs/tracking.hdf5 --list
python -m wooting_package.visualize logs/tracking.hdf5 --trial 1 --key 4
```

## Public API

- `WOOTING_ACQUISITION`: acquisition, threshold detection, readiness checks, and logging.
- `convert_char_to_keycode`: convert between key labels and HID keycodes.
- `build_interface`: rebuild the CFFI interface.
- `delete_interface`: remove generated CFFI artifacts.
- `lib` and `ffi`: raw CFFI handles for advanced SDK access.

## Troubleshooting

If importing works but acquisition fails with a missing native interface error, run:

```bash
wooting-build-interface
```

If no devices are detected, confirm the keyboard is connected, Wootility recognizes it, and platform permissions have been applied.
