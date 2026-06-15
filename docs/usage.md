# Usage

## Keyboard Initialization

```python
from tachywooting import WOOTING_ACQUISITION

acq = WOOTING_ACQUISITION(
    threshold=0.8,
    min_pressure_start=0.33,
    max_pressure_start=0.66,
)
acq.initialize_keyboard(verbose=True)
```

## Light-press readiness

```python
acq.wait_keys_light_press(target_keys=["z", "c"], quit_key="q")
```

On-screen visual feedback (`wait_light_press_visual`) is provided by TachyPy —
install `tachypy[wooting]` and use `from tachypy import WOOTING_ACQUISITION`.

## Acquisition

```python
data = acq.acquire_analog_values(target_keys=["z", "c"])
```

## Logging

```python
acq.setup_logging(path="logs", name="participant_001", int_analog=2)
acq.acquire_analog_values(target_keys=["z", "c"])
acq.uninitialize_keyboard()
```
