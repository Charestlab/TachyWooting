# Technical Documentation

## Overview

`tachywooting` provides a Python interface for the Wooting Analog SDK. It exposes high-level acquisition helpers for analog keyboard experiments while keeping the raw CFFI `lib` and `ffi` handles available for advanced SDK access.

## Installation Behavior

```bash
python -m pip install .
```

During installation, setuptools builds the CFFI extension from the bundled Wooting SDK headers and native libraries. If the native interface is missing or needs to be rebuilt manually, run:

```bash
wooting-build-interface
```

Editable development installs include all optional dependencies (CLI, visualization, and docs):

```bash
python -m pip install -e ".[dev]"
```

## Project Structure

```text
wooting-keyboard/
├── README.md
├── documentation.md
├── pyproject.toml
├── setup.py
├── requirements.txt
├── tests/
└── tachywooting/
    ├── __init__.py
    ├── cli.py
    ├── post_install.py
    ├── text_extraction.py
    ├── visualize.py
    ├── wooting_interface_builder.py
    ├── wooting_utils.py
    ├── interface/
    │   ├── __init__.py
    │   └── wooting_interface.*        # generated CFFI extension
    ├── libraries/
    │   ├── darwin/
    │   ├── linux/
    │   └── windows/
    └── permissions/
        ├── PERMISSIONS_linux.sh
        └── PERMISSIONS_mac.sh
```

## Native Interface

The package builds a CFFI extension named:

```text
tachywooting.interface.wooting_interface
```

`tachywooting.interface.__init__` imports this generated module and exposes:

- `lib`: Wooting Analog SDK functions.
- `ffi`: CFFI helper object for buffers, structs, and C strings.

If the extension is unavailable, pure-Python imports still work, but acquisition raises a clear setup error asking the user to run:

```bash
wooting-build-interface
```

## Permissions

The `permissions/` folder contains platform setup scripts:

- `PERMISSIONS_mac.sh`
- `PERMISSIONS_linux.sh`

On macOS, setup may remove Gatekeeper quarantine flags and ad-hoc sign bundled `.dylib` files. On Linux, setup helps ensure the user has permission to access the USB device used by the keyboard.

## Platform Support

### Windows

- Uses bundled `.dll` and `.lib` files.
- Supports SDK keycode modes such as HID, ScanCode1, VirtualKey, and VirtualKeyTranslate.

### macOS

- Uses bundled `.dylib` files.
- Selects `darwin/arm64` or `darwin/x86_64` based on the current CPU architecture.
- Uses `@loader_path` rpath so the generated extension finds bundled libraries at runtime.

### Linux

- Uses bundled `.so` and `.a` files.
- Uses `$ORIGIN` rpath so the generated extension finds bundled libraries at runtime.

## Analog Values

Wooting analog pressure values are represented as floats from `0.0` to `1.0` or integers from `0` to `255`.

The practical integer pressure set is:

```text
[0] ∪ [5, 255]
```

This means:

- `0` means no pressure.
- `5` is the smallest non-zero pressure value.
- `1` to `4` are not expected as logged pressure values.
- There are 251 usable non-zero pressure values.

The conversion is:

```text
pressure = integer_value / 255
```

Examples:

```text
5 / 255   = 0.0196078431
6 / 255   = 0.0235294118
255 / 255 = 1.0
```

## Keycode Conversion

`convert_char_to_keycode()` converts key labels to HID keycodes and keycodes back to labels.

```python
from tachywooting import convert_char_to_keycode

codes = convert_char_to_keycode(["A", "Esc", "Space"])
labels = convert_char_to_keycode([4, 41, 44])
```

## Acquisition API

### `WOOTING_ACQUISITION`

Main acquisition class for initialization, threshold detection, readiness checks, and logging.

```python
from tachywooting import WOOTING_ACQUISITION

acq = WOOTING_ACQUISITION(threshold=0.8)
acq.initialize_keyboard(verbose=True)
try:
    trial = acq.acquire_analog_values(target_keys=["A"])
finally:
    acq.uninitialize_keyboard()
```

### `initialize_keyboard(verbose=False)`

Initializes the Wooting SDK and validates that at least one compatible device is detected. With `verbose=True`, it prints basic device information.

### `uninitialize_keyboard()`

Uninitializes the SDK and merges pending HDF5 trial shards into the final combined log file.

### `acquire_analog_values(...)`

Acquires analog values in the `0.0` to `1.0` range around a threshold crossing.

### `acquire_integer_values(...)`

Acquires analog values and converts pressure to integer values in the `0` to `255` range.

```python
from tachywooting import WOOTING_ACQUISITION

acq = WOOTING_ACQUISITION()
acq.initialize_keyboard()
try:
    trial = acq.acquire_integer_values(target_keys=["A"])
finally:
    acq.uninitialize_keyboard()
```

### `setup_logging(name=None, path=None, int_analog=2)`

Enables HDF5 logging.

- `name`: base filename for the final log.
- `path`: output directory.
- `int_analog=1`: log integer pressure values.
- `int_analog=2`: log analog float pressure values.

```python
from tachywooting import WOOTING_ACQUISITION

acq = WOOTING_ACQUISITION()
acq.initialize_keyboard()
try:
    acq.setup_logging(name="tracking", path="logs", int_analog=1)
    acq.acquire_integer_values(target_keys=["A"])
finally:
    acq.uninitialize_keyboard()
```

## Finger Removal Tracking

Finger removal tracking is built into `WOOTING_ACQUISITION`. By default, it detects missing contact before the response threshold has been reached.

A trial is flagged if any monitored key falls below `finger_present_threshold` during pre-threshold acquisition. Set `count_post_threshold_removals=True` to also include post-threshold drops in the removal counters.

```python
from tachywooting import WOOTING_ACQUISITION

tracker = WOOTING_ACQUISITION(
    threshold=0.8,
    min_pressure_start=0.01,
    max_pressure_start=0.35,
    finger_present_threshold=0.01,
)
```

Available attributes:

```python
tracker.total_trials
tracker.removal_trials
tracker.removal_trial_indices
tracker.removal_trial_proportion
tracker.current_removal_streak
tracker.max_removal_streak
tracker.last_trial_had_removal
```

Helper methods:

```python
tracker.trial_contains_removal(trial_index)
tracker.reached_consecutive_removal_limit(n=2)
tracker.reached_total_removal_limit(n=5)
```

`reached_consecutive_removal_limit(n)` returns `True` when the current streak reaches at least `n`.

`reached_total_removal_limit(n)` returns `True` when the cumulative flagged-trial count reaches `n`, `2n`, `3n`, and so on.

## Acquisition Backends

`WOOTING_ACQUISITION` supports three readout backends:

- `backend="auto"`: uses `read_analog` for one key and `read_full_buffer` for multiple keys.
- `backend="read_analog"`: polls each target key separately.
- `backend="read_full_buffer"`: reads the SDK full buffer once per sampling tick.

For multi-key acquisition, `read_full_buffer` keeps only requested target keys. If a target key is absent from the SDK buffer at a given tick, the package records it as `position=0.0`.

## Light-press readiness

`wait_keys_light_press()` blocks until every target key is held within the
light-press interval (`min_pressure_start` … `max_pressure_start`) for
`hold_seconds`, then returns. It needs no display:

```python
acq.wait_keys_light_press(target_keys=["c", "z"], quit_key="q")
```

On-screen visual feedback — the interactive fixation cross,
`wait_light_press_visual()`, pressure text, and custom feedback widgets — lives
in **TachyPy**, not in this hardware package. Install `tachypy[wooting]` and use
the enriched acquisition class:

```python
from tachypy import WOOTING_ACQUISITION

acq.wait_light_press_visual(screen=screen, target_keys=["c", "z"])
```

## Timing Modes

`WOOTING_ACQUISITION` supports:

- `timing_mode="sleep"`: lower CPU usage, more jitter.
- `timing_mode="busy"`: higher CPU usage, tighter timing.
- `timing_mode="hybrid"`: sleeps most of the interval, then busy-waits near the target deadline.

## HDF5 Layout

Final HDF5 files use this layout:

```text
/trials/0001/keys/0004/values
```

Each `values` dataset is shaped as `N x 3` and stores:

```text
position, time_to_threshold, time_abs
```

Trial attributes may include:

- `backend`
- `trial_start_perf_ns`
- `stim_on_clock`

`time_abs` is the wall-clock timestamp from `time.time()` or equivalent epoch-based timing.

## Visualizer

The visualizer can list trials and plot key trajectories.

```bash
python -m tachywooting.visualize logs/tracking.hdf5 --list
python -m tachywooting.visualize logs/tracking.hdf5 --trial 1 --key 4
```

It plots position against `time_to_threshold` and shows `time_abs` on a secondary x-axis.

## SDK Error Codes

Negative SDK return values indicate errors. Common cases include:

- `NoMapping`: no keycode mapping found.
- `UnInitialized`: SDK was not initialized.
- `NoDevices`: no compatible device detected.

## Keycode Modes

The Wooting SDK supports multiple keycode modes through `wooting_analog_set_keycode_mode`:

- `HID`: standard USB HID codes.
- `ScanCode1`: scan code set 1.
- `VirtualKey`: Windows virtual key codes.
- `VirtualKeyTranslate`: Windows virtual key codes translated to the current layout.

## Maintenance Helpers

### `build_interface`

Rebuilds the generated CFFI interface.

### `delete_interface`

Removes generated CFFI artifacts and selected cache files.

## Development Checks

```bash
python -m compileall -q tachywooting tests
python -m build --sdist --wheel --no-isolation
```
