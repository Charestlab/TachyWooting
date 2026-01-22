import os
import glob
import time
from typing import Dict, List, Optional, Sequence, Tuple, Union, Iterable, Any, Literal
import shutil

import h5py
import numpy as np

from wooting_package.interface import lib, ffi

"""
Character to Keycode Converter Module

This module provides functionality to convert between keyboard characters and their
corresponding keycodes for Wooting keyboards. It supports both character-to-keycode
and keycode-to-character conversions, including special keys and modifiers.

The module maintains a comprehensive mapping of all supported keys and their
corresponding HID keycodes used by Wooting keyboards.
"""

def convert_char_to_keycode(input_values) -> list:
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
    """Return a package-local 'data' directory, creating it if needed.

    Returns:
        Absolute path to the data directory.
    """
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(base_path, exist_ok=True)
    return base_path


# Logging helpers
def _timestamped_if_exists(path: str) -> str:
    """Return `path` or a timestamped variant if it already exists."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    ts = time.strftime("%Y%m%d-%H%M%S")
    cand = f"{base}_{ts}{ext}"
    i = 1
    while os.path.exists(cand):
        cand = f"{base}_{ts}-{i}{ext}"
        i += 1
    return cand

def _write_trial_file(
    path: str,
    hier_trial: Dict[str, Dict[str, Dict[str, Sequence[float]]]],
) -> None:
    """Write one per-trial shard as hierarchical HDF5 (HDF5 only).

    Layout:
      /trials/<trial>/keys/<key>/values  (N×3: [position, time_to_threshold, time_abs])
    """
    with h5py.File(path, "a") as f:
        g_trials = f.require_group("trials")
        for t_str, keys in hier_trial.items():
            g_trial = g_trials.require_group(f"{int(t_str):04d}")
            g_keys  = g_trial.require_group("keys")
            for k_str, serie in keys.items():
                g_key = g_keys.require_group(f"{int(k_str):04d}")
                data = np.asarray(
                    list(zip(
                        serie.get("position", []),
                        serie.get("time_to_threshold", []),
                        serie.get("time_abs", []),
                    )),
                    dtype=np.float64,
                )
                if "values" in g_key:
                    ds = g_key["values"]
                    old = ds.shape[0]
                    ds.resize((old + data.shape[0], 3))
                    ds[old:] = data
                else:
                    ds = g_key.create_dataset(
                        "values",
                        data=data,
                        maxshape=(None, 3),
                        chunks=True,
                        compression="gzip",
                        shuffle=True,
                    )
                    ds.attrs["columns"] = np.array(
                        ["position", "time_to_threshold", "time_abs"], dtype="S"
                    )
    
def _combine_all_trials(staging_dir: str, final_dir: str, base: str) -> None:
    """Combine `{base}_trial*.hdf5` into one hierarchical HDF5, then clean up."""
    pattern = os.path.join(staging_dir, f"{base}_trial*.hdf5")
    files = sorted(glob.glob(pattern))
    if not files:
        return

    os.makedirs(final_dir, exist_ok=True)
    preferred_final_path = os.path.join(final_dir, f"{base}.hdf5")
    final_path = _timestamped_if_exists(preferred_final_path)
    with h5py.File(final_path, "a") as fout:
        g_out_trials = fout.require_group("trials")
        for shard in files:
            with h5py.File(shard, "r") as fin:
                if "trials" not in fin:
                    continue

                g_in_trials = fin["trials"]
                for trial_name in g_in_trials:
                    g_in_trial  = g_in_trials[trial_name]
                    g_out_trial = g_out_trials.require_group(trial_name)
                    g_out_keys  = g_out_trial.require_group("keys")
                    g_in_keys = g_in_trial.get("keys")
                    if g_in_keys is None:
                        continue

                    for key_name in g_in_keys:
                        g_in_key = g_in_keys[key_name]
                        if "values" not in g_in_key:
                            continue

                        data_in = g_in_key["values"][()]  # (N, 3)
                        g_out_key = g_out_keys.require_group(key_name)
                        if "values" in g_out_key:
                            ds = g_out_key["values"]
                            old = ds.shape[0]
                            ds.resize((old + data_in.shape[0], 3))
                            ds[old:] = data_in
                        else:
                            ds = g_out_key.create_dataset(
                                "values",
                                data=data_in,
                                maxshape=(None, 3),
                                chunks=True,
                                compression="gzip",
                                shuffle=True,
                            )
                            cols = g_in_key["values"].attrs.get("columns")
                            if cols is not None:
                                ds.attrs["columns"] = cols
    # cleanup shards
    for fp in files:
        try:
            os.remove(fp)
        except OSError:
            pass
    try:
        if not os.listdir(staging_dir):
            os.rmdir(staging_dir)
    except OSError:
        pass
    # safety: remove accidental combined-in-staging
    staging_combined_path = os.path.join(staging_dir, f"{base}.hdf5")
    if os.path.isfile(staging_combined_path):
        try:
            os.remove(staging_combined_path)
        except OSError:
            pass


_ACTIVE_LOGGERS = set()  # all instances with logging enabled (for global uninit)

class WOOTING_ACQUISITION:
    """Manage acquisition from Wooting analog keyboards with **hierarchical HDF5** logging.

    HDF5 layout (fixed):
        /trials/<trial4>/keys/<key4>/values  # shape=(N, 3)
            columns = ["position", "time_to_threshold", "time_abs"]

    Attributes:
        trial: Current trial index (1-based).
        logging_enabled: Whether logging is active.
        int_analog: Mode flag (1=int 0..255, 2=analog 0..1).
        log_dir: Output directory for logs.
        log_base: Base filename (without extension).
        trial_pad: Zero-padding for trial folder names.
        output_paths: Final output paths (HDF5 only).
        staging_dir: Directory for per-trial shards.

    Methods :
        setup_logging(): Configure HDF5 logging and staging folders.
        acquire_analog_values(): Acquire in analog mode; optionally log; return hier.
        acquire_integer_values(): Acquire in int mode; rescale to 0..255; optionally log.
        initialize_keyboard(): Init Wooting SDK; optionally print device info.
        uninitialize_keyboard(): Uninit SDK and merge any pending shards.
    """
    def __init__(self):
        """Initialize acquisition state (no hardware init, no logging yet)."""
        self.trial: int = 1
        self.logging_enabled: bool = False
        self.int_analog: Literal[1, 2] = 2  # 1=int (0..255), 2=analog (0..1)
        self.log_dir: str = os.getcwd()
        self.log_base: str = "wooting_logs"
        self.trial_pad: int = 4
        self.output_paths: Dict[str, str] = {}
        self.staging_dir: Optional[str] = None

    # ---------- Setup logging (new) ----------
    def setup_logging(self, name: str | None = None, path: str = None, int_analog: int = 2) -> None:
        """Configure hierarchical HDF5 logging (HDF5 only). Logs with per-trial files and then combine them.
           Final combine produces a single `{name}.hdf5` file with layout:
                /trials/<trial>/keys/<key>/values  (N×3: [position, time_to_threshold, time_abs])

        Args:
            name (str): Name of the log file.
                Default is "wooting_logs".
            path (str): Path for the log file.
                Default is os.getcwd(). 
            int_analog: Format for the positions. Either int (1) or analog (2).
                Default is 2 (analog).
        """
        self.log_dir = path if path is not None else os.getcwd()
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_base = "wooting_logs" if name is None else os.path.splitext(name)[0]
        self.output_paths = {"hdf5": os.path.join(self.log_dir, f"{self.log_base}.hdf5")}
        self.staging_dir = os.path.join(self.log_dir, f"{self.log_base}_trials")
        os.makedirs(self.staging_dir, exist_ok=True)
        if int_analog not in (1, 2):
            raise ValueError("int_analog must be 1 (int) or 2 (analog)")
        self.int_analog = int_analog
        self.logging_enabled = True

    def _write_hdf5_trial_shard(self, hier: Dict[str, Dict[str, Dict[str, Sequence[float]]]]) -> None:
        """Write one HDF5 shard for the current trial in hierarchical layout."""
        trial_path = os.path.join(self.staging_dir, f"{self.log_base}_trial{self.trial:0{self.trial_pad}d}.hdf5")
        _write_trial_file(trial_path, hier)

    def _combine_trials_for_all_formats(self) -> None:
        """Combine per-trial files from the staging folder into one file per format, and delete per-trial files."""
        if not self.logging_enabled or not self.staging_dir:
            return
        _combine_all_trials(self.staging_dir, self.log_dir, self.log_base)

    def _finalize_bins_to_hier(self, bins: Dict[Tuple[int, int], List[Tuple[float, float, float]]],
    ) -> Dict[str, Dict[str, Dict[str, np.ndarray]]]:
        """Build a hierarchical structure from (trial, key) bins.
        Each bin key is (trial, keycode) → list of (time_to_threshold, time_abs, position).
        For each key, samples are sorted by time_to_threshold to ensure chronological order.

        Returns:
        A dictionary of shape:
        { "<trial>": 
                    { "<key>": { "time_to_threshold": np.ndarray,
                                 "time_abs": np.ndarray,
                                 "position": np.ndarray
                    },
        }
        """
        hier: Dict[str, Dict[str, Dict[str, np.ndarray]]] = {}
        for (t, k), triplets in bins.items():
            triplets.sort(key=lambda x: x[0]) # Sort by time_to_threshold
            tth = np.fromiter((x[0] for x in triplets), dtype=np.float64, count=len(triplets))
            tabs = np.fromiter((x[1] for x in triplets), dtype=np.float64, count=len(triplets))
            pos  = np.fromiter((x[2] for x in triplets), dtype=np.float64, count=len(triplets))
            t_str, k_str = str(t), str(k)
            hier.setdefault(t_str, {})[k_str] = {"time_to_threshold": tth, "time_abs": tabs, "position": pos}
        return hier

    def _acquire_raw_values(
        self,
        target_keys: Sequence[Union[str, int]],
        threshold: float = 0.1,
        duration_after_threshold: float = 0.5,
        duration_before_threshold: Optional[float] = None,
        sampling_interval: float = 1 / 8000,
        verbose: bool = False,
    ) -> Dict[str, Dict[str, Dict[str, np.ndarray]]]:
        """Record samples around a threshold crossing and return hierarchical data.

        Args:
            target_keys: Keys as characters (e.g., 'z') or HID keycodes (ints).
            threshold: Crossing threshold in (0, 1].
            duration_after_threshold: Seconds to record after the first crossing.
            duration_before_threshold: Max seconds before the crossing to keep
                (None keeps all pre-threshold buffer).
            sampling_interval: Sleep between polls (seconds).
            verbose: Print runtime info.

        Returns:
            A hierarchical dictionary. Each time-point has [time_threshold, time_abs, position] 
            and is under a key, which is under a trial.
        """
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

        buffer_pre_threshold: List[Dict[str, Union[int, float]]] = []
        triggered = False
        trigger_time_ns: Optional[int] = None
        # bins[(trial, keycode)] -> list of (time_to_threshold, time_abs, position)
        bins: Dict[Tuple[int, int], List[Tuple[float, float, float]]] = {}
        if verbose:
            print(f"Waiting for any key in {target_keys} to exceed threshold {threshold}...")
        while True:
            current_time_ns = time.time_ns()
            snapshot = []
            for code in target_keys:
                value = lib.wooting_analog_read_analog(code)
                snapshot.append({'time_ns': current_time_ns, 'key': int(code), 'position': float(value)})
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
                    tth = (s['time_ns'] - trigger_time_ns) / 1e9  # type: ignore[arg-type]
                    tabs = s['time_ns'] / 1e9
                    pos  = s['position']
                    bins.setdefault((self.trial, s['key']), []).append((tth, tabs, pos))
                if (current_time_ns - trigger_time_ns) / 1e9 >= duration_after_threshold:  # type: ignore[operator]
                    break

            time.sleep(sampling_interval)

        for s in buffer_pre_threshold: # Add pre-threshold data 
            tth = (s['time_ns'] - trigger_time_ns) / 1e9  # type: ignore[arg-type]
            if duration_before_threshold is None or abs(tth) <= duration_before_threshold:
                tabs = s['time_ns'] / 1e9
                pos  = s['position']
                bins.setdefault((self.trial, s['key']), []).append((tth, tabs, pos))

        if verbose:
            total = sum(len(v) for v in bins.values())
            print(f"\nAcquisition complete ({total} samples captured).")

        hier = self._finalize_bins_to_hier(bins) # Return hierarchical structure (np arrays)
        return hier

    def acquire_analog_values(
        self,
        target_keys: Sequence[Union[str, int]],
        threshold: float = 0.1,
        duration_after_threshold: float = 0.5,
        duration_before_threshold: float = 0.2,
        sampling_interval: float = 1 / 8000,
        verbose: bool = False,
    ):
        """Acquire analog samples and return hierarchical data.

        When logging is enabled in analog mode, this writes one HDF5 shard for the
        current trial via `_write_hdf5_trial_shard(hier)`.

        Args:
            target_keys (Sequence[Union[str, int]]): Keys as characters or HID keycodes.
            threshold (float): Analog threshold in (0, 1], how much pressure to count key-press as a response.
                Default is 0.1 (10% of the maximum pressure).
            duration_after_threshold (float): Seconds to capture after crossing.
                Default is 0.5s logged after the threshold is reach.
            duration_before_threshold (float): Seconds to keep before crossing.
                Default is 0.2s logged before the threshold is reach.
            sampling_interval (float): Poll interval (seconds).
                Default is 1/8000s.
            verbose (bool) : Print runtime info.

        Returns:
            Hierarchical dict (trial → key → np.ndarrays with `position` as float64).
        """
        if self.logging_enabled and self.int_analog == 1:
            raise ValueError("Cannot use acquire_analog_values when logging in integer mode (int_analog=1). Use acquire_integer_values instead.")
        hier = self._acquire_raw_values(
            target_keys=target_keys,
            threshold=threshold,
            duration_after_threshold=duration_after_threshold,
            duration_before_threshold=duration_before_threshold,
            sampling_interval=sampling_interval,
            verbose=verbose,
        )
        if self.logging_enabled and self.int_analog == 2:
            self._write_hdf5_trial_shard(hier)
        self.trial += 1
        return hier


    def acquire_integer_values(
        self,
        target_keys: Sequence[Union[str, int]],
        threshold: int = 26,
        duration_after_threshold: float = 0.5,
        duration_before_threshold: float = 0.2,
        sampling_interval: float = 1 / 8000,
        verbose: bool = False,
    ):
        """Acquire integer-mode samples (0..255) and return hierarchical data.

        Wraps `_acquire_raw_values`, rescales 'position' to 0..255 (int16), and
        writes one HDF5 shard per trial if logging is enabled in integer mode.

        Args:
            target_keys (Sequence[Union[str, int]]): Keys as characters or HID keycodes.
            threshold (int): Integer threshold in [0..255], how much pressure to count key-press as a response.
                Default is 26 (≈10% max pressure point ≈ 26). 
            duration_after_threshold (float): Seconds to capture after crossing.
                Default is 0.5s logged after the threshold is reach.
            duration_before_threshold (float): Seconds to keep before crossing.
                Default is 0.2s logged before the threshold is reach.
            sampling_interval: Poll interval (seconds).
                Default is 1/8000s.
            verbose: Print runtime info.

        Returns:
            Hierarchical dict (trial → key → np.ndarrays with `position` as int16).
        """
        if self.logging_enabled and self.int_analog == 2:
            raise ValueError("Cannot use acquire_integer_values when logging in analog mode (int_analog=2). " \
            "Use acquire_analog_values instead.")
        hier = self._acquire_raw_values(
            target_keys=target_keys,
            threshold=threshold / 255.0,
            duration_after_threshold=duration_after_threshold,
            duration_before_threshold=duration_before_threshold,
            sampling_interval=sampling_interval,
            verbose=verbose,
        )
        for t_str, keys in hier.items(): 
            for k_str, serie in keys.items():
                serie["position"] = np.rint(serie["position"] * 255.0).astype(np.int16) # Rescale positions per key
        if self.logging_enabled and self.int_analog == 1:
            self._write_hdf5_trial_shard(hier)
        self.trial += 1
        return hier

    def initialize_keyboard(self, verbose: bool = False) -> bool:
        """Initialize the Wooting SDK for this process.

        Args:
            verbose: Print detected device info.

        Returns:
            True if initialization succeeds.

        Raises:
            ValueError: If initialization fails or interface is not ready.
            RuntimeError: If no devices are found.
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

    def uninitialize_keyboard(self) -> None:
        """Uninitialize the SDK and merge per-trial logs for this instance."""
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
            self._combine_trials_for_all_formats()

# ============================================================
# Maintenance helpers
# ============================================================

def delete_interface(file = None):
    """Remove compiled CFFI artifacts and common build leftovers.

    Args:
        file (Optional[str]): name of the file for the tracking.
    Deletes:
        - `wooting_interface*` in the interface folder
        - `__pycache__` under this package and its 'interface' subfolder
        - `plot.png` and `tracking.csv` one level above the package
        - `<project_root>/wooting_interface.egg-info`
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
    if file :
        for filename in ["plot.png", f"{file}"]:
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
