# Raw SDK Access via `lib` and `ffi`

`tachywooting` exposes two CFFI handles at the top level:

```python
from tachywooting import lib, ffi
```

`lib` gives direct access to every C function in the Wooting Analog SDK.
`ffi` is the CFFI interface object used to allocate C buffers, read C strings, and create C arrays.

Both are `None` until `wooting-build-interface` has been run once. Check before using:

```python
from tachywooting import lib, ffi

if lib is None or ffi is None:
    raise RuntimeError("Run `wooting-build-interface` first.")
```

---

## SDK lifecycle

### `wooting_analog_initialise() → int`

Initialises the SDK and loads plugins. Must be called before any other function.

- Returns `>= 0`: number of devices found on startup.
- Returns `WootingAnalogResult_NoPlugins` (`-1995`): no plugins loaded.

```python
result = lib.wooting_analog_initialise()
if result < 0:
    raise RuntimeError(f"SDK init failed: {result}")
print(f"{result} device(s) found")
```

---

### `wooting_analog_is_initialised() → bool`

Returns `True` if the SDK is currently initialised.

```python
if lib.wooting_analog_is_initialised():
    print("SDK is ready")
```

---

### `wooting_analog_uninitialise() → WootingAnalogResult`

Shuts down the SDK and releases all resources.

- Returns `WootingAnalogResult_Ok` (`1`) on success.

```python
lib.wooting_analog_uninitialise()
```

---

## Version

### `wooting_analog_version() → int`

Returns the major version number of the loaded SDK. A mismatch with the expected major version indicates potential breaking changes.

```python
major = lib.wooting_analog_version()
```

### `wooting_analog_version_semver() → const char *`

Returns the full SemVer version string as a null-terminated C string.

```python
version_str = ffi.string(lib.wooting_analog_version_semver()).decode()
print(version_str)  # e.g. "0.9.1"
```

---

## Reading key values

### `wooting_analog_read_analog(code: unsigned short) → float`

Reads the analog value (0.0–1.0) for a single key across all connected devices.
`code` is a USB HID keycode (default mode) — use `convert_char_to_keycode` to convert from key names.

- Returns `0.0–1.0`: analog pressure.
- Returns `< 0`: a `WootingAnalogResult` error code.

```python
from tachywooting import lib, ffi, convert_char_to_keycode

keycode = convert_char_to_keycode(["A"])[0]   # → 4
value = lib.wooting_analog_read_analog(keycode)

if value < 0:
    print(f"Error: {int(value)}")
else:
    print(f"A key pressure: {value:.3f}")      # 0.0 = released, 1.0 = fully pressed
```

---

### `wooting_analog_read_analog_device(code, device_id) → float`

Same as `wooting_analog_read_analog` but targets a specific device by its `device_id`.

```python
value = lib.wooting_analog_read_analog_device(keycode, device_id)
```

---

### `wooting_analog_read_full_buffer(code_buffer, analog_buffer, len) → int`

Fills two pre-allocated C arrays with keycodes and their analog values for every currently-pressed key across all devices. Keys released since the last call appear once with a value of `0.0`.

- Returns `>= 0`: number of key/value pairs written.
- Returns `< 0`: a `WootingAnalogResult` error code.

```python
MAX_KEYS = 32
codes  = ffi.new(f"unsigned short[{MAX_KEYS}]")
values = ffi.new(f"float[{MAX_KEYS}]")

n = lib.wooting_analog_read_full_buffer(codes, values, MAX_KEYS)
if n >= 0:
    for i in range(n):
        print(f"keycode {codes[i]}: {values[i]:.3f}")
```

---

### `wooting_analog_read_full_buffer_device(code_buffer, analog_buffer, len, device_id) → int`

Same as `wooting_analog_read_full_buffer` but scoped to one device.

```python
n = lib.wooting_analog_read_full_buffer_device(codes, values, MAX_KEYS, device_id)
```

---

## Keycode mode

### `wooting_analog_set_keycode_mode(mode: unsigned int) → WootingAnalogResult`

Controls which keycode system the SDK uses for `read_analog` inputs and `read_full_buffer` outputs.

| Constant | Value | Description |
|---|---|---|
| `WootingAnalog_KeycodeType_HID` | `0` | USB HID keycodes (default, cross-platform) |
| `WootingAnalog_KeycodeType_ScanCode1` | `1` | Scan code set 1 |
| `WootingAnalog_KeycodeType_VirtualKey` | `2` | Windows Virtual Keys (Windows only) |
| `WootingAnalog_KeycodeType_VirtualKeyTranslate` | `3` | Windows Virtual Keys, locale-translated (Windows only) |

```python
HID_MODE = 0
lib.wooting_analog_set_keycode_mode(HID_MODE)
```

The package always uses HID mode internally. Only change this if you are bypassing the high-level API.

---

## Device enumeration

### `wooting_analog_get_connected_devices_info(buffer, len) → int`

Fills a C pointer array with `WootingAnalog_DeviceInfo_FFI` structs for every connected device.

- Returns `>= 0`: number of devices written into the buffer.
- Returns `< 0`: a `WootingAnalogResult` error code.
- The returned structs are only valid until the next call to this function — copy any data you need immediately.

```python
MAX_DEVICES = 8
buffer = ffi.new("WootingAnalog_DeviceInfo_FFI *[]", MAX_DEVICES)
n = lib.wooting_analog_get_connected_devices_info(buffer, MAX_DEVICES)

for i in range(n):
    d = buffer[i]
    name = ffi.string(d.device_name).decode() if d.device_name else "Unknown"
    manufacturer = ffi.string(d.manufacturer_name).decode() if d.manufacturer_name else "Unknown"
    print(f"{manufacturer} {name}  vid=0x{d.vendor_id:04x}  pid=0x{d.product_id:04x}  id={d.device_id}")
```

`device_id` from this struct can be passed to the `_device` variants of the read functions.

---

## Device event callback

### `wooting_analog_set_device_event_cb(cb) → WootingAnalogResult`

Registers a C callback that fires when a device connects or disconnects. The callback runs on a separate thread.

```python
@ffi.callback("void(WootingAnalog_DeviceEventType, WootingAnalog_DeviceInfo_FFI *)")
def on_device_event(event_type, device_info):
    name = ffi.string(device_info.device_name).decode() if device_info.device_name else "?"
    if event_type == 1:
        print(f"Connected: {name}")
    elif event_type == 2:
        print(f"Disconnected: {name}")

lib.wooting_analog_set_device_event_cb(on_device_event)
```

> **Note:** Copy any data from `device_info` inside the callback — the struct is freed immediately after the callback returns.

---

### `wooting_analog_clear_device_event_cb() → WootingAnalogResult`

Removes the currently registered device event callback.

```python
lib.wooting_analog_clear_device_event_cb()
```

---

## Error codes (`WootingAnalogResult`)

| Constant | Value | Meaning |
|---|---|---|
| `WootingAnalogResult_Ok` | `1` | Success |
| `WootingAnalogResult_UnInitialized` | `-2000` | SDK not initialised |
| `WootingAnalogResult_NoDevices` | `-1999` | No devices connected |
| `WootingAnalogResult_DeviceDisconnected` | `-1998` | Target device disconnected |
| `WootingAnalogResult_Failure` | `-1997` | Generic failure |
| `WootingAnalogResult_InvalidArgument` | `-1996` | Bad parameter |
| `WootingAnalogResult_NoPlugins` | `-1995` | No plugins found |
| `WootingAnalogResult_FunctionNotFound` | `-1994` | Symbol missing in library |
| `WootingAnalogResult_NoMapping` | `-1993` | No HID mapping for keycode |
| `WootingAnalogResult_NotAvailable` | `-1992` | Not supported on this platform |
| `WootingAnalogResult_IncompatibleVersion` | `-1991` | SDK version mismatch |
| `WootingAnalogResult_DLLNotFound` | `-1990` | Native library not found |

```python
result = lib.wooting_analog_initialise()
if result == -1995:
    print("No plugins found — is the Wooting SDK installed?")
elif result < 0:
    print(f"Unexpected error: {result}")
```

---

## When to use raw `lib`/`ffi`

The high-level `WOOTING_ACQUISITION` class covers the common research workflow (threshold detection, HDF5 logging, readiness checks). Use `lib`/`ffi` directly when you need:

- Custom device-selection logic using `device_id`.
- Real-time full-buffer polling at the lowest possible overhead.
- Device connect/disconnect notifications via the event callback.
- SDK version checks or diagnostics.
