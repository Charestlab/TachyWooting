"""
Wooting Keyboard Utilities

This module provides utilities for working with Wooting analog keyboards:
- Analog value acquisition and processing
- Keyboard initialization and management
- Keycode conversion and handling
"""

import os
import glob
import json
import time
import numpy as np
import pandas as pd

from wooting_package.interface import lib, ffi
import shutil

"""
Character to Keycode Converter Module

This module provides functionality to convert between keyboard characters and their
corresponding keycodes for Wooting keyboards. It supports both character-to-keycode
and keycode-to-character conversions, including special keys and modifiers.

The module maintains a comprehensive mapping of all supported keys and their
corresponding HID keycodes used by Wooting keyboards.
"""

def convert_char_to_keycode(input_values):
    """
    Convert between characters and keycodes for Wooting keyboards.

    This function performs bidirectional conversion between keyboard characters
    and their corresponding HID keycodes. It supports both individual characters
    and lists of characters/keycodes.

    Args:
        input_values (str or int or list): A single character/keycode or a list of
            characters/keycodes to convert.

    Returns:
        list: A list of converted values. If converting from characters to keycodes,
            returns a list of keycodes. If converting from keycodes to characters,
            returns a list of characters.

    Note:
        The function will print an error message and return None if:
        - A character is not found in the mapping
        - A keycode is not found in the mapping
        - The input type is neither string nor integer
    """
    # Comprehensive mapping of keys to their HID keycodes
    # Format: [key_name, keycode, width, height]
    key_mapping = [
        ['Esc', 41, 1, 1],
        ['', 0, 1, 1],
        ['F1', 58, 1, 1],
        ['F2', 59, 1, 1],
        ['F3', 60, 1, 1],
        ['F4', 61, 1, 1],
        ['F5', 62, 1, 1],
        ['F6', 63, 1, 1],
        ['F7', 64, 1, 1],
        ['F8', 65, 1, 1],
        ['F9', 66, 1, 1],
        ['F10', 67, 1, 1],
        ['F11', 68, 1, 1],
        ['F12', 69, 1, 1],
        ['Prnt', 70, 1, 1],
        ['Pse', 72, 1, 1],
        ['Scrl', 71, 1, 1],
        ['A1', 0, 1, 1],
        ['A2', 0, 1, 1],
        ['A3', 0, 1, 1],
        ['Mode', 0, 1, 1],
        ['`', 53, 1, 1],
        ['1', 30, 1, 1],
        ['2', 31, 1, 1],
        ['3', 32, 1, 1],
        ['4', 33, 1, 1],
        ['5', 34, 1, 1],
        ['6', 35, 1, 1],
        ['7', 36, 1, 1],
        ['8', 37, 1, 1],
        ['9', 38, 1, 1],
        ['0', 39, 1, 1],
        ['-', 45, 1, 1],
        ['=', 46, 1, 1],
        ['<-', 42, 1, 1],
        ['Ins', 73, 1, 1],
        ['Hme', 74, 1, 1],
        ['PgUp', 75, 1, 1],
        ['NumLck', 83, 1, 1],
        ['/', 84, 1, 1],
        ['*', 85, 1, 1],
        ['-', 86, 1, 1],
        ['Tab', 43, 1, 1],
        ['Q', 20, 1, 1],
        ['W', 26, 1, 1],
        ['E', 8, 1, 1],
        ['R', 21, 1, 1],
        ['T', 23, 1, 1],
        ['Y', 28, 1, 1],
        ['U', 24, 1, 1],
        ['I', 12, 1, 1],
        ['O', 18, 1, 1],
        ['P', 19, 1, 1],
        ['[', 47, 1, 1],
        [']', 48, 1, 1],
        ['#', 49, 1, 1],
        ['Del', 76, 1, 1],
        ['End', 77, 1, 1],
        ['PgDn', 78, 1, 1],
        ['7', 95, 1, 1],
        ['8', 96, 1, 1],
        ['9', 97, 1, 1],
        ['+', 87, 1, 2],
        ['Caps', 57, 1, 1],
        ['A', 4, 1, 1],
        ['S', 22, 1, 1],
        ['D', 7, 1, 1],
        ['F', 9, 1, 1],
        ['G', 10, 1, 1],
        ['H', 11, 1, 1],
        ['J', 13, 1, 1],
        ['K', 14, 1, 1],
        ['L', 15, 1, 1],
        [';', 51, 1, 1],
        ['\'', 52, 1, 1],
        ['Enter', 40, 2, 1],
        ['', 0, 1, 1],
        ['', 0, 1, 1],
        ['', 0, 1, 1],
        ['4', 92, 1, 1],
        ['5', 93, 1, 1],
        ['6', 94, 1, 1],
        ['Shift', 225, 1, 1],
        ['Z', 29, 1, 1],
        ['X', 27, 1, 1],
        ['C', 6, 1, 1],
        ['V', 25, 1, 1],
        ['B', 5, 1, 1],
        ['N', 17, 1, 1],
        ['M', 16, 1, 1],
        ['', 54, 1, 1],
        ['.', 55, 1, 1],
        ['/', 56, 1, 1],
        ['Shift', 229, 3, 1],
        ['', 0, 1, 1],
        ['^', 82, 1, 1],
        ['', 0, 1, 1],
        ['1', 89, 1, 1],
        ['', 0, 1, 1],
        ['2', 90, 1, 1],
        ['3', 91, 1, 1],
        ['Enter', 88, 1, 2],
        ['Ctrl', 224, 1, 1],
        ['Win', 227, 1, 1],
        ['Alt', 226, 1, 1],
        ['Space', 44, 7, 1],
        ['Alt', 230, 1, 1],
        ['Win', 231, 1, 1],
        ['Fn', 0, 1, 1],
        ['Ctrl', 228, 1, 1],
        ['<', 80, 1, 1],
        ['v', 81, 1, 1],
        ['>', 79, 1, 1],
        ['0', 98, 2, 1],
        ['.', 99, 1, 1]
    ]

    if not isinstance(input_values, list):
        if isinstance(input_values, (str, int)):
            input_values = [input_values]
        else:
            raise TypeError("Input must be a string, integer, or list of strings/integers.")

    
    # Transpose the list for easier access to columns
    key_names, keycodes, _, _ = zip(*key_mapping)
    converted = [None] * len(input_values)

    # Process each input value
    for i, val in enumerate(input_values):
        # Handle string input (character to keycode conversion)
        if isinstance(val, str):
            tgt = val.lower()
            for k_i, name in enumerate(key_names):
                if name.lower() == tgt:
                    converted[i] = keycodes[k_i]
                    break

            else:
                print("Problem, not finding the input value in the key codes list.")
                return

        # Handle integer input (keycode to character conversion)
        elif isinstance(val, int):
            for k_i, code in enumerate(keycodes):
                if code == val:
                    converted[i] = key_names[k_i]
                    break
            else:
                print("Problem, not finding the input value in the key codes list.")
                return
        else:
            print('Please use input_values of type char/string or integer')
            return

    return converted

def get_data_directory():
    """
    Return a data directory next to this file (create if missing).
    """
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(base_path, exist_ok=True)
    return base_path


# ============================================================
# Multi-format logging helpers
# ============================================================

_SUPPORTED_FORMATS = {"parquet", "csv", "json", "npy"}

def _ext_from_format(fmt: str) -> str:
    return {
        "parquet": "parquet",
        "csv": "csv",
        "json": "json",
        "npy": "npy",
    }[fmt]

def _df_from_records(records):
    return pd.DataFrame.from_records(
        records, columns=["trial", "key", "position", "time_to_threshold", "time_abs"]
    )

def _write_trial_file(fmt, path, records):
    """
    Write ONE per-trial file according to the requested format.
    Schema: trial, key, position, time_to_threshold
    """
    if fmt in ("parquet", "csv"):
        df = _df_from_records(records)
        if fmt == "parquet":
            df.to_parquet(path, index=False)
        else:
            df.to_csv(path, index=False)
    elif fmt == "json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False)
    elif fmt == "npy":
        arr = np.array(
            [
                (int(r["trial"]), int(r["key"]), float(r["position"]), float(r["time_to_threshold"]))
                for r in records
            ],
            dtype=[("trial", "i8"), ("key", "i8"), ("position", "f8"), ("time_to_threshold", "f8")],
        )
        np.save(path, arr)
    else:
        raise ValueError(f"Unknown format: {fmt}")

def _combine_all_trials(fmt, staging_dir, final_dir, base):
    """
    Combine all {staging_dir}/{base}_trial*.ext into {final_dir}/{base}.ext
    and delete the per-trial files. Removes the staging dir if empty.
    After combining, also deletes the combined file in the staging directory if it exists.
    """
    ext = _ext_from_format(fmt)
    pattern = os.path.join(staging_dir, f"{base}_trial*.{ext}")
    files = sorted(glob.glob(pattern))
    if not files:
        return  # nothing to do

    os.makedirs(final_dir, exist_ok=True)
    final_path = os.path.join(final_dir, f"{base}.{ext}")

    if fmt in ("parquet", "csv"):
        dfs = []
        for fp in files:
            if fmt == "parquet":
                dfs.append(pd.read_parquet(fp))
            else:
                dfs.append(pd.read_csv(fp))
        combined = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(
            columns=["trial", "key", "position", "time_to_threshold", "time_abs"]
        )
        if fmt == "parquet":
            combined.to_parquet(final_path, index=False)
        else:
            combined.to_csv(final_path, index=False)

    elif fmt == "json":
        all_records = []
        for fp in files:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_records.extend(data)
                else:
                    raise ValueError(f"JSON file is not an array: {fp}")
        with open(final_path, "w", encoding="utf-8") as f:
            json.dump(all_records, f, ensure_ascii=False)

    elif fmt == "npy":
        arrays = [np.load(fp, allow_pickle=False) for fp in files]
        if arrays:
            combined = np.concatenate(arrays, axis=0)
            np.save(final_path, combined)

    # Cleanup per-trial files
    for fp in files:
        try:
            os.remove(fp)
        except OSError:
            pass

    # Remove the staging directory if now empty
    try:
        if not os.listdir(staging_dir):
            os.rmdir(staging_dir)
    except OSError:
        pass

    # Delete the combined file in the staging directory if it exists
    staging_combined_path = os.path.join(staging_dir, f"{base}.{ext}")
    if os.path.isfile(staging_combined_path):
        try:
            os.remove(staging_combined_path)
        except OSError:
            pass


# ============================================================
# Acquisition class with multi-format logging + merge on uninit
# ============================================================

_ACTIVE_LOGGERS = set()  # all instances with logging enabled (for global uninit)

class WOOTING_ACQUISITION:
    """
    Acquisition manager for Wooting analog keyboards with multi-format logging.
    """

    def __init__(self):
        self.trial = 1
        self.logging_enabled = False
        self.int_analog = 2  # 1=int (0..255), 2=analog (0..1)
        self.log_dir = os.getcwd()      # final output directory
        self.log_base = "wooting_logs"
        self.log_formats = ["parquet"]  # can be list, e.g. ["csv","json"]

        # Number of digits for zero-padding trial numbers (e.g., 0001)
        self.trial_pad = 4

        # Final outputs per enabled format, e.g. {"csv": ".../tracking.csv"}
        self.output_paths = {}

        # Staging directory where per-trial files are written
        self.staging_dir = None

        # Deprecated compatibility shim (parquet_full_path)
        self._deprecated_warned = False    

    # --- Deprecated property kept for backward compatibility ---

    @property
    def parquet_full_path(self):
        # Replaced warning with a hard failure as requested
        raise ValueError("parquet_full_path is deprecated; use output_paths.get('parquet').")

    @parquet_full_path.setter
    def parquet_full_path(self, value):
        # Replaced warning with a hard failure as requested
        raise ValueError("Setting parquet_full_path is deprecated; set output_paths['parquet'] instead.")

    # ---------- Setup logging (new) ----------

    def setup_logging(self, name=None, path=None, int_analog=2, formats="parquet"):
        """
        Configure logging.
        - name: base name or name with extension (e.g., 'tracking.parquet' or 'tracking')
        - path: directory (defaults to CWD if None)
        - int_analog: 1 (integer 0..255) or 2 (analog 0..1)
        - formats: str or list[str] among {'parquet','csv','json','npy'}

        Creates per-trial files in a staging folder:
            {log_dir}/{log_base}_trials/{base}_trial{N}.{ext}
        On uninitialize, all trials are merged into:
            {log_dir}/{log_base}.{ext}
        """
        # Final output directory
        self.log_dir = path if path is not None else os.getcwd()
        os.makedirs(self.log_dir, exist_ok=True)

        # Formats
        if isinstance(formats, str):
            formats = [formats]
        for f in formats:
            if f not in _SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported format '{f}'. Choose among {_SUPPORTED_FORMATS}.")
        self.log_formats = list(dict.fromkeys(formats))  # dedupe, keep order

        # Base name (+ optional ext)
        if name is None:
            self.log_base = "wooting_logs"
        else:
            base, ext = os.path.splitext(name)
            if ext and ext.lstrip(".") in _SUPPORTED_FORMATS:
                # name provided with extension -> force that single format
                self.log_base = base
                self.log_formats = [ext.lstrip(".")]
            else:
                self.log_base = name

        # Final outputs per format
        self.output_paths = {
            fmt: os.path.join(self.log_dir, f"{self.log_base}.{fmt}") for fmt in self.log_formats
        }

        # Staging directory for per-trial files
        self.staging_dir = os.path.join(self.log_dir, f"{self.log_base}_trials")
        os.makedirs(self.staging_dir, exist_ok=True)

        # int/analog mode
        if int_analog not in (1, 2):
            raise ValueError("int_analog must be 1 (int) or 2 (analog)")
        self.int_analog = int_analog

        self.logging_enabled = True
        _ACTIVE_LOGGERS.add(self)

    # ---------- Internal helpers ----------

    def _write_logs_multi_(self, collected_data):
        """
        Write exactly one per-trial file (per enabled format) into the staging folder.
        """
        for fmt in self.log_formats:
            ext = _ext_from_format(fmt)
            trial_path = os.path.join(
                self.staging_dir,
                f"{self.log_base}_trial{self.trial:0{self.trial_pad}d}.{ext}"
            )
            _write_trial_file(fmt, trial_path, collected_data)

    def _combine_trials_for_all_formats(self):
        """
        Combine per-trial files from the staging folder into one file per format,
        then delete per-trial files and remove the staging folder if empty.
        """
        if not self.logging_enabled or not self.staging_dir:
            return
        for fmt in self.log_formats:
            _combine_all_trials(fmt, self.staging_dir, self.log_dir, self.log_base)

    # ---------- Acquisition core ----------

    def _acquire_raw_values(
        self,
        target_keys,
        threshold=0.1,
        duration_after_threshold=0.5,
        duration_before_threshold=None,
        sampling_interval=1/8000,  # Wooting Tachyon mode up to 8000 Hz
        verbose=False
    ):
        if isinstance(target_keys, list):
            if any(isinstance(k, str) for k in target_keys):
                target_keys = convert_char_to_keycode(target_keys)
        else:
            raise TypeError("target_keys must be a list of character(s) or integer(s)")

        if threshold <= 0 or threshold > 1:
            raise ValueError("Threshold must be between 0 and 1")
        if duration_after_threshold <= 0:
            raise ValueError("Duration after threshold must be positive")
        if sampling_interval <= 0:
            raise ValueError("Sampling interval must be positive")
        if duration_before_threshold is not None and duration_before_threshold <= 0:
            raise ValueError("Duration before threshold must be positive")

        buffer_pre_threshold = []
        collected_data = []
        triggered = False
        trigger_time_ns = None

        if verbose:
            print(f"Waiting for any key in {target_keys} to exceed threshold {threshold}...")

        while True:
            current_time_ns = time.time_ns()
            snapshot = []
            for code in target_keys:
                value = lib.wooting_analog_read_analog(code)
                snapshot.append({'time_ns': current_time_ns, 'key': code, 'position': value})

            if not triggered:
                for s in snapshot:
                    if s['position'] >= threshold:
                        trigger_time_ns = current_time_ns
                        triggered = True
                        if verbose:
                            char = convert_char_to_keycode([s['key']])[0]
                            print(f"\nThreshold reached on key {s['key']} ({char}) at t = {trigger_time_ns / 1e9:.6f}s")
                        break
                buffer_pre_threshold.extend(snapshot)

            if triggered:
                for s in snapshot:
                    collected_data.append({
                        'trial': self.trial,
                        'key': s['key'],
                        'position': s['position'],
                        'time_to_threshold': (s['time_ns'] - trigger_time_ns) / 1e9,
                        'time_abs': (s['time_ns']/10**9)
                    })
                
                if (current_time_ns - trigger_time_ns) / 1e9 >= duration_after_threshold:
                    break
            time.sleep(sampling_interval)

        for s in buffer_pre_threshold:
            time_to_threshold = (s['time_ns'] - trigger_time_ns) / 1e9
            if duration_before_threshold is None or abs(time_to_threshold) <= duration_before_threshold:
                collected_data.append({
                    'trial': self.trial,
                    'key': s['key'],
                    'position': s['position'],
                    'time_to_threshold': time_to_threshold,
                    'time_abs': (s['time_ns']/10**9)
                })
        collected_data.sort(key=lambda x: x['time_to_threshold'])
        if verbose:
            print(f"\nAcquisition complete ({len(collected_data)} samples captured).")
        return collected_data

    def acquire_analog_values(
        self,
        target_keys,
        threshold=0.1,
        duration_after_threshold=0.5,
        duration_before_threshold=None,
        sampling_interval=1/8000,
        verbose=False
    ):
        if self.logging_enabled and self.int_analog == 1:
            raise ValueError("Cannot use acquire_analog_values when logging in integer mode (int_analog=1). Use acquire_integer_values instead.")

        collected_data = self._acquire_raw_values(
            target_keys=target_keys,
            threshold=threshold,
            duration_after_threshold=duration_after_threshold,
            duration_before_threshold=duration_before_threshold,
            sampling_interval=sampling_interval,
            verbose=verbose
        )
        if self.logging_enabled and self.int_analog == 2:
            self._write_logs_multi_(collected_data)

        self.trial += 1
        return collected_data

    def acquire_integer_values(
        self,
        target_keys,
        threshold=26,
        duration_after_threshold=0.5,
        duration_before_threshold=None,
        sampling_interval=1/8000,
        verbose=False
    ):
        if self.logging_enabled and self.int_analog == 2:
            raise ValueError("Cannot use acquire_integer_values when logging in analog mode (int_analog=2). Use acquire_analog_values instead.")

        collected_data = self._acquire_raw_values(
            target_keys=target_keys,
            threshold=threshold/255,
            duration_after_threshold=duration_after_threshold,
            duration_before_threshold=duration_before_threshold,
            sampling_interval=sampling_interval,
            verbose=verbose
        )
        for d in collected_data:
            d['position'] = round(d['position'] * 255)

        if self.logging_enabled and self.int_analog == 1:
            self._write_logs_multi_(collected_data)

        self.trial += 1
        return collected_data

    # ---------- Optional instance-level init/uninit ----------

    def initialize_keyboard(self, verbose=False):
        """
        Initialize Wooting interface (instance helper).
        """
        if not lib.wooting_analog_initialise():
            raise ValueError("Error: Failed to initialize Wooting interface")
        if not lib.wooting_analog_is_initialised():
            raise ValueError("Error: Interface not properly initialized")

        device_count = lib.wooting_analog_initialise()
        if device_count <= 0:
            raise RuntimeError("No Wooting devices found.")

        buffer = ffi.new("WootingAnalog_DeviceInfo_FFI *[]", device_count)
        lib.wooting_analog_get_connected_devices_info(buffer, device_count)

        if verbose:
            device = buffer[0]
            vendor = f"0x{device.vendor_id:04x}"
            product = f"0x{device.product_id:04x}"
            manufacturer = ffi.string(device.manufacturer_name).decode() if device.manufacturer_name else "Unknown"
            device_name = ffi.string(device.device_name).decode() if device.device_name else "Unknown"
            print(f"""
Detected Wooting keyboard:
    - Vendor ID       : {vendor}
    - Product ID      : {product}
    - Device ID       : {device.device_id}
    - Device Type     : {device.device_type}
    - Manufacturer    : {manufacturer}
    - Device Name     : {device_name}
""")
        return True

    def uninitialize_keyboard(self):
        """
        Uninitialize interface and merge all per-trial logs (for this instance).
        """
        try:
            lib.wooting_analog_uninitialise()
        finally:
            self._combine_trials_for_all_formats()


# ============================================================
# Global init/uninit (backward compatible) + active logger merge
# ============================================================

def initialize_keyboard(verbose=False):
    """
    Initialize the Wooting keyboard interface (global).
    """
    if not lib.wooting_analog_initialise():
        raise ValueError("Error: Failed to initialize Wooting interface")
    if not lib.wooting_analog_is_initialised():
        raise ValueError("Error: Interface not properly initialized")

    device_count = lib.wooting_analog_initialise()
    if device_count <= 0:
        raise RuntimeError("No Wooting devices found.")

    buffer = ffi.new("WootingAnalog_DeviceInfo_FFI *[]", device_count)
    lib.wooting_analog_get_connected_devices_info(buffer, device_count)

    if verbose:
        device = buffer[0]
        vendor = f"0x{device.vendor_id:04x}"
        product = f"0x{device.product_id:04x}"
        manufacturer = ffi.string(device.manufacturer_name).decode() if device.manufacturer_name else "Unknown"
        device_name = ffi.string(device.device_name).decode() if device.device_name else "Unknown"
        print(f"""
Detected Wooting keyboard:
    - Vendor ID       : {vendor}
    - Product ID      : {product}
    - Device ID       : {device.device_id}
    - Device Type     : {device.device_type}
    - Manufacturer    : {manufacturer}
    - Device Name     : {device_name}
""")
    return True


def uninitialize_keyboard():
    """
    Uninitialize the Wooting keyboard interface (global) and
    merge all per-trial logs for ALL active loggers, then clear registry.
    """
    try:
        lib.wooting_analog_uninitialise()
    finally:
        # Merge for every active logger and clear registry
        for logger in list(_ACTIVE_LOGGERS):
            try:
                logger._combine_trials_for_all_formats()
            except Exception:
                pass
        _ACTIVE_LOGGERS.clear()


# ============================================================
# Maintenance helpers
# ============================================================

def delete_interface():
    """
    Deletes every file starting with 'wooting_interface' in the interface directory.
    Also cleans local __pycache__, plot.png, tracking.csv, and egg-info at project root.
    """
    interface_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interface")
    pattern = os.path.join(interface_dir, "wooting_interface*")
    files = glob.glob(pattern)
    for file_path in files:
        try:
            os.remove(file_path)
        except OSError:
            pass
    # Delete __pycache__ directories in wooting_package and wooting_package/interface
    for pycache_dir in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "__pycache__"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "interface", "__pycache__")
    ]:
        if os.path.isdir(pycache_dir):
            try:
                shutil.rmtree(pycache_dir)
            except Exception:
                pass
    # Delete "plot.png" and "tracking.csv" in the parent directory of wooting_package
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for filename in ["plot.png", "tracking.csv"]:
        file_path = os.path.join(parent_dir, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    # Delete "<project_root>/wooting_interface.egg-info" directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    egg_info_dir = os.path.join(project_root, "wooting_interface.egg-info")
    if os.path.isdir(egg_info_dir):
        try:
            shutil.rmtree(egg_info_dir)
        except Exception:
            pass
#delete_interface()