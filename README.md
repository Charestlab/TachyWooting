# Python Interface for Wooting Analog SDK

A Python interface for the Wooting Analog SDK that enables reading analog key values and managing keyboard events. This library provides a high-level Python wrapper around the Wooting Analog SDK, making it easy to integrate analog keyboard support into Python applications.

## Features

- Read analog key values (0.0 to 1.0 range) or integers (0 to 255 range)
- Multi-device support
- Cross-platform (Windows and macOS)
- Event handling for device connections/disconnections
- Multiple keycode modes (HID, ScanCode1, VirtualKey)
- Simple and intuitive API

## Installation

```bash
pip install -r recquirements.txt
```

## Project Structure

```
wooting-keyboard/
├── setup.py
├── requirements.txt
├── wooting_package
    ├── text_extraction.py
    ├── wooting_interface_builder.py
    ├── wooting_utils.py
    ├── interface
        ├── ...                         # Built interface
        └── __init__.py 
    └── librairies                      # [Wooting components and headers](https://github.com/WootingKb/wooting-analog-sdk/releases) 
        ├── darwin
        ├── linux
        └── windows
```

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

```from wooting_utils import WOOTING_ACQUISITION()

acquisition = WOOTING_ACQUISITION()
acquisition.acquire_integer_values(target_key=['1'])
acquire_integer_values()

```

### Key Functions

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

### `parquet_acquisition(name, path, int_analog)`
Will log the pressed keys in a .parquet file.

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
- pandas
- pyarrow
- numpy
- matplotlib
- setuptools
- pyarrow

## Platform Support

### Windows
- Requires Wooting Analog SDK installed
- Supports all keycode modes
- Uses DLL files for libraries

### macOS
- Requires Wooting Analog SDK installed
- Supports HID and ScanCode1 modes
- Uses dylib files for libraries

## Example

```python
from wooting_utils import initialize_keyboard, acquire_analog_values, uninitialize_keyboard

# Initialize the keyboard
initialize_keyboard()

acquisition_obj = WOOTING_ACQUISITION()
print(acquisition_obj.acquire_integer_values())

uninitialize_keyboard()
```

## Example + logging in parquet :

```python
from wooting_utils import initialize_keyboard, acquire_analog_values, uninitialize_keyboard

initialize_keyboard()

acquisition_obj = WOOTING_ACQUISITION()

acquisition_obj.parquet_acquisition("FOLDER", "YOUR_FILE.parquet")    
acquisition_obj.acquire_integer_values()

uninitialize_keyboard()
```
## Contributing

Feel free to submit issues and enhancement requests!
