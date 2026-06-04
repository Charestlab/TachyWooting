"""
wooting_utils.py

Wooting analog acquisition + hierarchical HDF5 logging (per-trial shards → combined file).

Key features you asked for:
- Multi-key acquisition uses read_full_buffer (one call per tick) to get all pressed keys.
- Only target_keys are kept/used (other keys ignored).
- Even if read_full_buffer doesn't return a target key at a given tick, we still log it with position=0.0.
- Backend option:
    - backend="auto"  -> read_analog for single key, read_full_buffer for multi-key
    - backend="read_analog"
    - backend="read_full_buffer"
  and we store per-trial attribute /trials/<trial>.attrs["backend"] = b"..."
- NumPy 2.0+ compatible: uses bytes for HDF5 attrs (no np.string_).

IMPORTANT NOTE ABOUT "CLEARING" BUFFERS:
- You do NOT "clear" any SDK buffer from Python.
- read_full_buffer returns "currently pressed keys", and also (per SDK docs) may return
  a key once with analog=0.0 on the first call after release.
- In this implementation we DO NOT depend on that. We always explicitly output every
  target key each tick, defaulting to 0.0 if absent.
"""

from __future__ import annotations

import os
import glob
import time
import shutil
from typing import Dict, List, Optional, Sequence, Tuple, Union, Literal, Set

import h5py
import numpy as np

from wooting_package.interface import lib, ffi


# ============================================================
# Character <-> HID keycode conversion
# ============================================================

def convert_char_to_keycode(input_values) -> list | None:
    """
    Convert between characters and keycodes for Wooting keyboards (HID keycodes).

    Bidirectional:
    - If input is str -> returns keycode int
    - If input is int -> returns key name str

    Args:
        input_values (str|int|list): single or list

    Returns:
        list of converted values (or None on error).
    """
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
        ["'", 52, 1, 1],
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
        ['.', 99, 1, 1],
    ]

    if not isinstance(input_values, list):
        if isinstance(input_values, (str, int)):
            input_values = [input_values]
        else:
            raise TypeError("Input must be a string, integer, or list of strings/integers.")

    key_names, keycodes, _, _ = zip(*key_mapping)
    converted = [None] * len(input_values)

    for i, val in enumerate(input_values):
        if isinstance(val, str):
            tgt = val.lower()
            for k_i, name in enumerate(key_names):
                if str(name).lower() == tgt:
                    converted[i] = int(keycodes[k_i])
                    break
            else:
                print("Problem, not finding the input value in the key codes list.")
                return None

        elif isinstance(val, int):
            for k_i, code in enumerate(keycodes):
                if int(code) == int(val):
                    converted[i] = str(key_names[k_i])
                    break
            else:
                print("Problem, not finding the input value in the key codes list.")
                return None
        else:
            print("Please use input_values of type char/string or integer")
            return None

    return converted


# ============================================================
# Logging helpers
# ============================================================

def _timestamped_if_exists(path: str) -> str:
    """Return path or a timestamped variant if it already exists."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    ts = time.strftime("%Y-%m-%d-%H-%M-%S")
    cand = f"{base}_{ts}{ext}"
    i = 1
    while os.path.exists(cand):
        cand = f"{base}_{ts}-{i}{ext}"
        i += 1
    return cand


def _write_trial_file(
    path: str,
    hier_trial: Dict[str, Dict[str, Dict[str, Sequence[float]]]],
    backend: Optional[str] = None,
    trial_start_perf_ns: Optional[int] = None,
    stim_on_clock: Optional[str] = None,
    threshold: Optional[float] = None,
    threshold_time: Optional[float] = None,
    threshold_key: Optional[int] = None,
) -> None:

    """Write one per-trial shard as hierarchical HDF5.

    Layout:
      /trials/<trial4>/keys/<key4>/values (N×3: [position, time_to_threshold, time_abs])

    Adds:
      /trials/<trial4>.attrs["backend"] = b"..."
      /trials/<trial4>.attrs["threshold"] = float
      /trials/<trial4>.attrs["threshold_time"] = float (time since trial_start_ns when threshold was crossed)
      /trials/<trial4>.attrs["threshold_key"] = int (keycode that triggered threshold)
    """
    with h5py.File(path, "a") as f:
        g_trials = f.require_group("trials")

        for t_str, keys in hier_trial.items():
            g_trial = g_trials.require_group(f"{int(t_str):04d}")

            backend_str = "" if backend is None else str(backend)
            # NumPy 2.0+: store bytes explicitly
            g_trial.attrs["backend"] = backend_str.encode("utf-8")
            
            # --- per-trial metadata (stimulus onset reference) ---
            if trial_start_perf_ns is not None:
                g_trial.attrs["trial_start_perf_ns"] = np.int64(int(trial_start_perf_ns))

            if stim_on_clock is not None:
                g_trial.attrs["stim_on_clock"] = str(stim_on_clock).encode("utf-8")

            if threshold is not None:
                g_trial.attrs["threshold"] = np.float64(float(threshold))

            if threshold_time is not None:
                g_trial.attrs["threshold_time"] = np.float64(float(threshold_time))

            if threshold_key is not None:
                g_trial.attrs["threshold_key"] = np.int64(int(threshold_key))

            g_keys = g_trial.require_group("keys")
            for k_str, serie in keys.items():
                g_key = g_keys.require_group(f"{int(k_str):04d}")

                data = np.asarray(
                    list(
                        zip(
                            serie.get("position", []),
                            serie.get("time_to_threshold", []),
                            serie.get("time_abs", []),
                        )
                    ),
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
    
    if files:
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
                        g_in_trial = g_in_trials[trial_name]
                        g_out_trial = g_out_trials.require_group(trial_name)

                        # copy backend attr if present (keep first one encountered)
                        if "backend" in g_in_trial.attrs and "backend" not in g_out_trial.attrs:
                            g_out_trial.attrs["backend"] = g_in_trial.attrs["backend"]

                        if "trial_start_perf_ns" in g_in_trial.attrs and "trial_start_perf_ns" not in g_out_trial.attrs:
                            g_out_trial.attrs["trial_start_perf_ns"] = g_in_trial.attrs["trial_start_perf_ns"]

                        if "stim_on_clock" in g_in_trial.attrs and "stim_on_clock" not in g_out_trial.attrs:
                            g_out_trial.attrs["stim_on_clock"] = g_in_trial.attrs["stim_on_clock"]

                        if "threshold" in g_in_trial.attrs and "threshold" not in g_out_trial.attrs:
                            g_out_trial.attrs["threshold"] = g_in_trial.attrs["threshold"]

                        if "threshold_time" in g_in_trial.attrs and "threshold_time" not in g_out_trial.attrs:
                            g_out_trial.attrs["threshold_time"] = g_in_trial.attrs["threshold_time"]

                        if "threshold_key" in g_in_trial.attrs and "threshold_key" not in g_out_trial.attrs:
                            g_out_trial.attrs["threshold_key"] = g_in_trial.attrs["threshold_key"]
                        
                        g_out_keys = g_out_trial.require_group("keys")
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
    
    # cleanup staging directory (whether or not there were files)
    try:
        if os.path.isdir(staging_dir) and not os.listdir(staging_dir):
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


_ACTIVE_LOGGERS: Set["WOOTING_ACQUISITION"] = set()


# ============================================================
# Main acquisition class
# ============================================================

BackendMode = Literal["auto", "read_analog", "read_full_buffer"]
TimingMode = Literal["sleep", "busy", "hybrid"]


class WOOTING_ACQUISITION:
    """
    Acquire analog key positions from Wooting keyboards with optional hierarchical HDF5 logging.

    This class wraps the Wooting Analog SDK and provides a small, user-facing API for:
      1) Initializing the SDK / device,
      2) (Optionally) configuring on-disk logging,
      3) Recording key trajectories around a threshold crossing,
      4) (Optionally) enforcing a “ready” finger placement (light press) before trials.

    The implementation supports single-key polling and multi-key polling. For multi-key
    acquisition, it can use the SDK full-buffer API to read all pressed keys in one call,
    while only keeping the target keys you requested.

    Attributes (user-relevant)
    --------------------------
    start_trial_number : int
        Number of the first trial of the new WOOTING_ACQUISITION object.
        Objective is to allow an expirement to resume (after quitting) at any point without
        messing up the trial number. So if resuming at the trial 29 (1 based), set 
        start_trial_number = 29.

    threshold : float
        Actuation threshold in analog units [0..1]. A trial is triggered when ANY target key
        reaches or exceeds this value during acquisition. You can change it after init.

    max_pressure_start : float
        Upper bound for “light press” readiness checks (see wait_keys_light_press). Must be
        below `threshold` by design (threshold >= max_pressure_start + 0.2 enforced in __init__).

    self.initialized : bool
        Is False by Default and becomes True once initialize_keyboard() has been called.

    backend : Literal["auto", "read_analog", "read_full_buffer"]
        Readout strategy for key positions:
          - "auto": uses read_analog for a single target, read_full_buffer for multiple targets
          - "read_analog": polls each target key with the per-key SDK call
          - "read_full_buffer": reads pressed keys in one call and extracts only target keys

    timing_mode : Literal["sleep", "busy", "hybrid"]
        Cadence control mode used internally to keep a stable sampling rate:
          - "sleep": low CPU, higher jitter
          - "busy": high CPU, lower jitter
          - "hybrid": sleep most of the interval, spin near the deadline (recommended)

    spin_margin_s : float
        Only used when timing_mode="hybrid". Final time window (seconds) in which the loop
        busy-waits to hit the target sample time more precisely.

    trial : int
        Current trial counter (1-based). Increments after each acquisition call. When logging
        is enabled, this number is used for per-trial shard naming and HDF5 grouping.

    logging_enabled : bool
        Whether per-trial logging is enabled (set by setup_logging).

    int_analog : Literal[1, 2]
        Logging mode:
          - 1 = integer mode (positions saved as 0..255)
          - 2 = analog mode (positions saved as 0..1)
        Must match the acquisition method you use (integer vs analog).

    output_paths : dict[str, str]
        Paths for outputs (currently includes the combined HDF5 path when logging is enabled).

    last_backend : str
        Backend actually used on the most recent acquisition (useful for debugging / auditing).

    Public methods (intended for users)
    -----------------------------------
    setup_logging(name: str | None = None, path: str | None = None, int_analog: int = 2) -> None
        Enable hierarchical HDF5 logging. Internally, each trial is written as a shard file and
        all shards are merged into a single HDF5 file on uninitialize_keyboard().
        - name: base name (without extension) for the combined file (e.g., "tracking")
        - path: output directory (default: current working directory)
        - int_analog: 1 (integer 0..255) or 2 (analog 0..1)

    initialize_keyboard(verbose: bool = False) -> bool
        Initialize the Wooting SDK for the current process and detect connected devices.
        Must be called before acquisition. If verbose=True, prints device information.

    acquire_analog_values(
        target_keys,
        duration_after_threshold: float = 0.5,
        duration_before_threshold: float = 0.2,
        sampling_interval: float = 1/8000,
        verbose: bool = False,
        trial_start_perf_ns: Optional[int] = None,
    ) -> dict
        Acquire analog samples (0..1) for the given target keys around a threshold crossing.
        - The trial triggers when ANY target key crosses `threshold`.
        - Only target keys are returned/logged.
        - trial_start_perf_ns defines trial start (stimulus onset reference), if not giving 
        approximate it by starting a clock.

        Returns a hierarchical dict:
            { "<trial>": { "<keycode>": {"position", "time_to_threshold", "time_abs"} } }
        If logging is enabled with int_analog=2, the trial is written to the HDF5 shards.

    acquire_integer_values(
        target_keys,
        duration_after_threshold: float = 0.5,
        duration_before_threshold: float = 0.2,
        sampling_interval: float = 1/8000,
        verbose: bool = False,
        trial_start_perf_ns: Optional[int] = None,
    ) -> dict
        Same as acquire_analog_values, but positions are returned/logged as integers (0..255).
        Requires logging to be configured with int_analog=1 if you want on-disk logs.
        - trial_start_perf_ns defines trial start (stimulus onset reference), if not giving 
        approximate it by starting a clock.

    wait_keys_light_press(
        target_keys,
        hold_seconds: float = 0.30,
        timeout_seconds: float | None = None,
        verbose: bool = False,
    ) -> float
        “Ready” check before a trial: waits until ALL target keys are lightly pressed at the
        same time and remain in range for `hold_seconds`.
        - Low bound is fixed at 0.01.
        - High bound is `self.max_pressure_start`.
        - Sampling rate is fixed at 1000 Hz (internal).
        Returns the perf_counter() timestamp when the condition is satisfied.
        Raises TimeoutError if timeout_seconds is exceeded.

    Notes
    -----
    - Always call initialize_keyboard() before calling acquisition methods.
    - If logging is enabled, call uninitialize_keyboard() at the end to merge per-trial shards
      into the final combined HDF5 file.
    """

    def __init__(
        self,
        start_trial_number: int = 1,
        threshold: float = 0.8,
        max_pressure_start: float = 0.35,
        backend: BackendMode = "auto",
        timing_mode: TimingMode = "hybrid",
        spin_margin_s: float = 0.0003,
        full_buffer_len: int = 256,
    ):
        if threshold <= 0.05 or threshold > 1:
            raise ValueError("threshold must be between 0.05 and 1")
        if threshold < (max_pressure_start + 0.2):
            raise ValueError("threshold must be at least 0.2 higher than max_pressure_start")

        if backend not in ("auto", "read_analog", "read_full_buffer"):
            raise ValueError("backend must be 'auto', 'read_analog', or 'read_full_buffer'")

        if timing_mode not in ("sleep", "busy", "hybrid"):
            raise ValueError("timing_mode must be 'sleep', 'busy', or 'hybrid'")
        if spin_margin_s <= 0:
            raise ValueError("spin_margin_s must be positive")

        if full_buffer_len < 8:
            raise ValueError("full_buffer_len too small")

        self.threshold = float(threshold)
        self.max_pressure_start = float(max_pressure_start)

        self.initialized = False
        self.backend: BackendMode = backend
        self.last_backend: str = ""  # for logging / debug

        self.timing_mode: TimingMode = timing_mode
        self.spin_margin_s: float = float(spin_margin_s)

        if start_trial_number < 1:
            raise ValueError("start_trial_number must be >= 1 (1-based)")
        self.trial = int(start_trial_number) # 1 if not specified

        self.logging_enabled: bool = False
        self.int_analog: Literal[1, 2] = 2  # 1=int (0..255), 2=analog (0..1)
        self.log_dir: str = os.getcwd()
        self.log_base: str = "wooting_logs"
        self.trial_pad: int = 4
        self.output_paths: Dict[str, str] = {}
        self.staging_dir: Optional[str] = None

        # cache of last trial's stimulus-onset reference (persisted to HDF5)
        self._last_trial_start_perf_ns: Optional[int] = None
        self._last_stim_on_clock: Optional[str] = None
        self._last_threshold_time: Optional[float] = None
        self._last_threshold_key: Optional[int] = None

        # --- buffers for read_full_buffer ---
        self._fullbuf_len: int = int(full_buffer_len)
        self._code_buf = ffi.new(f"unsigned short[{self._fullbuf_len}]")
        self._analog_buf = ffi.new(f"float[{self._fullbuf_len}]")

        # cache for targets
        self._target_codes_cache: Optional[Tuple[int, ...]] = None
        self._target_set_cache: Optional[Set[int]] = None

    # ---------------- logging ----------------

        """
    setup_logging : Set up hierarchical HDF5 logging (per-trial shards -> combined file).

    Parameters
    ----------
    name : str | None
        Base name of the final HDF5 file (extension is ignored if provided).
        Example: name="P001_sess1" -> final file "P001_sess1.hdf5" (or timestamped variant).

    path : str | None
        Output directory for the combined HDF5 file. If None, uses os.getcwd().

    int_analog : int
        Logging format:
        - 2 : analog positions in [0..1]
        - 1 : integer positions in [0..255]
        This is a safeguard to prevent mixing formats across a session.

    WARNING
    -------
    - This logger writes one HDF5 shard per trial into a *staging* directory:
          <path>/<name>_trials_<run_id>/
      The combined HDF5 file is created only when you call `uninitialize_keyboard()`
      (or if you manually call the combine routine).

    - If your experiment crashes or is force-quit before `uninitialize_keyboard()`,
      the shards will remain on disk and will NOT be merged automatically.
      In that case, you can re-run your script and call `uninitialize_keyboard()`,
      or manually merge shards by calling the internal combine function 
      (_combine_all_trials(staging_dir: str, final_dir: str, base: str) with:
          staging_dir = <path> (path of the folder with the shards)
          final_dir   = <path> (path of where you want the final logging HDF5)
          base        = <name> (<path>/<name>_trials_<run_id>/, base name of the shards)

    - If a combined file "<name>.hdf5" already exists in <path>, a timestamp is appended
      to avoid overwriting (e.g., "<name>_YYYY-MM-DD-HH-MM-SS.hdf5"). Always check
      `self.output_paths["hdf5"]` (and/or the directory listing) to find the latest file.
    """

    def setup_logging(self, name: str | None = None, path: str = None, int_analog: int = 2) -> None:
        if not self.initialized :
            raise ValueError(
                "Keyboard must be initialized through \"initialize_keyboard()\"."
            )
        
        self.log_dir = path if path is not None else os.getcwd()
        os.makedirs(self.log_dir, exist_ok=True)

        self.log_base = "wooting_logs" if name is None else os.path.splitext(name)[0]
        self.output_paths = {"hdf5": os.path.join(self.log_dir, f"{self.log_base}.hdf5")}

        run_id = time.strftime("%Y-%m-%d--%H-%M-%S")
        self.staging_dir = os.path.join(self.log_dir, f"{self.log_base}_trials_{run_id}")
        os.makedirs(self.staging_dir, exist_ok=True)

        if int_analog not in (1, 2):
            raise ValueError("int_analog must be 1 (int) or 2 (analog)")
        self.int_analog = int_analog
        self.logging_enabled = True

        _ACTIVE_LOGGERS.add(self)

    def _write_hdf5_trial_shard(self, hier: Dict[str, Dict[str, Dict[str, Sequence[float]]]]) -> None:
        if not self.staging_dir:
            raise RuntimeError("Logging enabled but staging_dir is not set. Call setup_logging().")

        trial_path = os.path.join(
            self.staging_dir,
            f"{self.log_base}_trial{self.trial:0{self.trial_pad}d}.hdf5",
        )
        
        _write_trial_file(
            path                = trial_path,
            hier_trial          = hier,
            backend             = self.last_backend,
            trial_start_perf_ns = self._last_trial_start_perf_ns,
            stim_on_clock       = self._last_stim_on_clock,
            threshold           = self.threshold,
            threshold_time      = self._last_threshold_time,
            threshold_key       = self._last_threshold_key,
        )

    def _combine_trials(self) -> None:
        if not self.logging_enabled or not self.staging_dir:
            return
        _combine_all_trials(self.staging_dir, self.log_dir, self.log_base)

    # ---------------- init/uninit ---- ------------

    def initialize_keyboard(self, verbose: bool = False) -> bool:
        device_count = int(lib.wooting_analog_initialise())
        if device_count <= 0:
            raise RuntimeError("No Wooting devices found or failed to initialize.")
        if not lib.wooting_analog_is_initialised():
            raise RuntimeError("Wooting SDK reports not initialised after initialise().")

        n = max(device_count, 1)
        buffer = ffi.new("WootingAnalog_DeviceInfo_FFI *[]", n)
        lib.wooting_analog_get_connected_devices_info(buffer, n)

        if verbose:
            d = buffer[0]
            vendor = f"0x{d.vendor_id:04x}"
            product = f"0x{d.product_id:04x}"
            manufacturer = ffi.string(d.manufacturer_name).decode() if d.manufacturer_name else "Unknown"
            device_name = ffi.string(d.device_name).decode() if d.device_name else "Unknown"
            print(
                f"\nDetected Wooting device:\n"
                f"  - Vendor ID    : {vendor}\n"
                f"  - Product ID   : {product}\n"
                f"  - Device ID    : {d.device_id}\n"
                f"  - Device Type  : {d.device_type}\n"
                f"  - Manufacturer : {manufacturer}\n"
                f"  - Device Name  : {device_name}\n"
            )
        self.initialized = True
        return True

    def uninitialize_keyboard(self) -> None:
        try:
            lib.wooting_analog_uninitialise()
        finally:
            # merge everyone, then clear
            for logger in list(_ACTIVE_LOGGERS):
                try:
                    logger._combine_trials()
                except Exception:
                    pass
            _ACTIVE_LOGGERS.clear()

            # merge for this instance too (safe)
            self._combine_trials()

    # ---------------- helpers ----------------

    def _to_keycodes(self, target_keys: Sequence[Union[str, int]]) -> List[int]:
        if not isinstance(target_keys, list):
            raise TypeError("target_keys must be a list of character(s) or integer(s)")

        if len(target_keys) == 0:
            raise ValueError("target_keys cannot be empty")

        if any(isinstance(k, str) for k in target_keys):
            codes = convert_char_to_keycode(target_keys)
            if codes is None:
                raise ValueError("Could not convert some characters to keycodes.")
            return [int(c) for c in codes]

        if all(isinstance(k, int) for k in target_keys):
            return [int(k) for k in target_keys]

        raise TypeError("target_keys must be a list of all strings or all integers")

    def _ensure_target_cache(self, target_codes: Sequence[int]) -> Tuple[Tuple[int, ...], Set[int]]:
        tgt_tuple = tuple(int(c) for c in target_codes)
        if self._target_codes_cache != tgt_tuple:
            self._target_codes_cache = tgt_tuple
            self._target_set_cache = set(tgt_tuple)
        return self._target_codes_cache, self._target_set_cache  # type: ignore[return-value]

    def _read_positions_full_buffer(self, target_codes: Sequence[int]) -> Dict[int, float]:
        """One call per tick. Returns {code: position} for ALL targets, defaulting to 0.0."""
        tgt_tuple, tgt_set = self._ensure_target_cache(target_codes)

        n = int(lib.wooting_analog_read_full_buffer(self._code_buf, self._analog_buf, self._fullbuf_len))
        if n < 0:
            raise RuntimeError(f"wooting_analog_read_full_buffer error: {n}")

        out = {c: 0.0 for c in tgt_tuple}
        for i in range(n):
            code = int(self._code_buf[i])
            if code not in tgt_set:
                continue
            val = float(self._analog_buf[i])
            # if duplicates, keep max
            if val > out[code]:
                out[code] = val

        return out

    def _read_positions_read_analog(self, target_codes: Sequence[int]) -> Dict[int, float]:
        """Poll each target key. Returns {code: position} for all targets."""
        out: Dict[int, float] = {}
        for c in target_codes:
            v = float(lib.wooting_analog_read_analog(int(c)))
            if v < 0:
                raise RuntimeError(f"wooting_analog_read_analog error: {v}")
            out[int(c)] = v
        return out

    def _choose_backend(self, target_codes: Sequence[int]) -> str:
        if self.backend == "read_full_buffer":
            return "read_full_buffer"
        if self.backend == "read_analog":
            return "read_analog"
        # auto
        return "read_analog" if len(target_codes) <= 1 else "read_full_buffer"

    def _read_positions_for_targets(self, target_codes: Sequence[int]) -> Dict[int, float]:
        chosen = self._choose_backend(target_codes)
        self.last_backend = chosen
        if chosen == "read_full_buffer":
            return self._read_positions_full_buffer(target_codes)
        return self._read_positions_read_analog(target_codes)

    def _wait_until_next_tick(self, next_t: float) -> None:
        if self.timing_mode == "busy":
            while time.perf_counter() < next_t:
                time.sleep(0.001)
                pass
            return

        if self.timing_mode == "sleep":
            remaining = next_t - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)
            return

        # hybrid: sleep most, spin last spin_margin_s
        while True:
            remaining = next_t - time.perf_counter()
            if remaining <= 0:
                break
            if remaining > self.spin_margin_s:
                time.sleep(remaining - self.spin_margin_s)
            else:
                while time.perf_counter() < next_t:
                    time.sleep(0.001)
                    pass
                break

    def _finalize_bins_to_hier(
        self,
        bins: Dict[Tuple[int, int], List[Tuple[float, float, float]]],
    ) -> Dict[str, Dict[str, Dict[str, np.ndarray]]]:
        """bins[(trial, keycode)] = [(tth, tabs, pos), ...]"""
        hier: Dict[str, Dict[str, Dict[str, np.ndarray]]] = {}
        for (t, k), triplets in bins.items():
            triplets.sort(key=lambda x: x[0])  # by time_to_threshold
            tth = np.fromiter((x[0] for x in triplets), dtype=np.float64, count=len(triplets))
            tabs = np.fromiter((x[1] for x in triplets), dtype=np.float64, count=len(triplets))
            pos = np.fromiter((x[2] for x in triplets), dtype=np.float64, count=len(triplets))
            hier.setdefault(str(t), {})[str(k)] = {
                "time_to_threshold": tth,
                "time_abs": tabs,
                "position": pos,
            }
        return hier

    # ---------------- acquisition core ----------------

    def _acquire_raw_values(
        self,
        target_keys: Sequence[Union[str, int]],
        duration_after_threshold: float = 0.5,
        duration_before_threshold: Optional[float] = None,
        sampling_interval: float = 1 / 8000,
        verbose: bool = False,
        trial_start_ns: Optional[int] = None,
        trial_start_clock: str = "perf",
        callback=None,
        callback_delay=None,
        quit_key: Optional[Union[str, int]] = None,
    ) -> Dict[str, Dict[str, Dict[str, np.ndarray]]]:
        """
        Low-level acquisition of analog key positions around a threshold crossing.

        If `quit_key` is provided, the function also detects whether this key was pressed
        at any time during the trial and returns a boolean flag.

        Returns
        -------
        hier : dict
            Acquisition data.

        (hier, quit_pressed) : tuple
            Returned only if `quit_key` is provided.
        """

        target_codes = self._to_keycodes(target_keys)

        if duration_after_threshold <= 0:
            raise ValueError("duration_after_threshold must be positive")
        if sampling_interval <= 0:
            raise ValueError("sampling_interval must be positive")
        if duration_before_threshold is not None and duration_before_threshold <= 0:
            raise ValueError("duration_before_threshold must be positive")
        if trial_start_clock not in {"perf", "mono"}:
            raise ValueError("trial_start_clock must be 'perf' or 'mono'")

        # --- strict validation for timed callback ---
        if callback is not None:
            if callback_delay is None or callback_delay <= 0:
                raise ValueError("callback_delay must be > 0 when callback is provided.")

        # --- quit key handling (optional) ---
        quit_code: Optional[int] = None
        quit_pressed = False
        if quit_key is not None:
            q = self._to_keycodes([quit_key])
            if len(q) != 1:
                raise ValueError("quit_key must resolve to exactly one keycode.")
            quit_code = int(q[0])

        # Read codes: include quit_code for monitoring, but do NOT include it in snapshots/bins
        if quit_code is not None and quit_code not in target_codes:
            read_codes = list(target_codes) + [quit_code]
        else:
            read_codes = list(target_codes)

        # --- clock anchoring ---
        anchor_perf_ns = time.perf_counter_ns()
        anchor_mono_ns = time.monotonic_ns()

        if trial_start_ns is None:
            trial_start_perf_ns = int(anchor_perf_ns)
        else:
            if trial_start_clock == "perf":
                trial_start_perf_ns = int(trial_start_ns)
            else:
                trial_start_perf_ns = int(anchor_perf_ns + (int(trial_start_ns) - int(anchor_mono_ns)))

        # --- callback deadline ---
        callback_done = False
        callback_deadline_perf_ns = None
        if callback is not None:
            callback_deadline_perf_ns = int(trial_start_perf_ns + callback_delay * 1e9)

        self._last_trial_start_perf_ns = int(trial_start_perf_ns)
        self._last_stim_on_clock = str(trial_start_clock)
        self._last_threshold_time = None
        self._last_threshold_key = None

        buffer_pre_threshold = []
        triggered = False
        trigger_perf_ns = None
        trigger_key = None
        bins: Dict[Tuple[int, int], List[Tuple[float, float, float]]] = {}

        next_t = time.perf_counter()
        interval = float(sampling_interval)

        while True:
            sample_perf_ns = time.perf_counter_ns()
            sample_epoch_ns = time.time_ns()

            # --- timed callback ---
            if callback is not None and not callback_done and not triggered:
                if sample_perf_ns >= callback_deadline_perf_ns:
                    try:
                        callback()
                    except Exception as e:
                        raise RuntimeError("Timed callback failed.") from e
                    callback_done = True

            pos_map = self._read_positions_for_targets(read_codes)

            # --- detect quit key (does NOT stop trial) ---
            if quit_code is not None and not quit_pressed:
                if float(pos_map.get(quit_code, 0.0)) > 0.0:
                    quit_pressed = True
                    if verbose:
                        print(f"[quit_key] Detected press on {quit_key!r}")

            snapshot = [
                {
                    "perf_ns": sample_perf_ns,
                    "epoch_ns": sample_epoch_ns,
                    "key": int(code),
                    "position": float(pos_map.get(int(code), 0.0)),
                }
                for code in target_codes
            ]

            if not triggered:
                for s in snapshot:
                    if s["position"] >= self.threshold:
                        trigger_perf_ns = int(sample_perf_ns)
                        trigger_key = int(s["key"])
                        triggered = True
                        callback_done = True
                        break
                buffer_pre_threshold.extend(snapshot)

            if triggered:
                for s in snapshot:
                    tth = (int(s["perf_ns"]) - int(trial_start_perf_ns)) / 1e9
                    tabs = int(s["epoch_ns"]) / 1e9
                    bins.setdefault((self.trial, int(s["key"])), []).append(
                        (tth, tabs, float(s["position"]))
                    )

                if (sample_perf_ns - trigger_perf_ns) / 1e9 >= duration_after_threshold:
                    break

            next_t += interval
            self._wait_until_next_tick(next_t)

        for s in buffer_pre_threshold:
            dt = (int(s["perf_ns"]) - trigger_perf_ns) / 1e9
            if duration_before_threshold is None or abs(dt) <= duration_before_threshold:
                tth = (int(s["perf_ns"]) - int(trial_start_perf_ns)) / 1e9
                tabs = int(s["epoch_ns"]) / 1e9
                bins.setdefault((self.trial, int(s["key"])), []).append(
                    (tth, tabs, float(s["position"]))
                )

        # Store threshold crossing info
        if trigger_perf_ns is not None:
            self._last_threshold_time = (int(trigger_perf_ns) - int(trial_start_perf_ns)) / 1e9
            self._last_threshold_key = int(trigger_key) if trigger_key is not None else None

        hier = self._finalize_bins_to_hier(bins)

        if quit_code is not None:
            return hier, bool(quit_pressed)
        return hier
    
    def acquire_analog_values(
        self,
        target_keys: Sequence[Union[str, int]],
        duration_after_threshold: float = 0.5,
        duration_before_threshold: Optional[float] = 0.2,
        sampling_interval: float = 1 / 8000,
        verbose: bool = False,
        trial_start_ns: Optional[int] = None,
        trial_start_clock: str = "perf",
        callback=None,
        callback_delay=None,
        quit_key: Optional[Union[str, int]] = None,
    ):
        """
        Acquire analog key trajectories (0.0–1.0) around a threshold crossing.

        This user-facing function blocks until any of the `target_keys` crosses the
        acquisition threshold, then continues sampling for `duration_after_threshold`
        seconds. It also retains up to `duration_before_threshold` seconds of samples
        collected before the threshold crossing.

        Timing / alignment
        ------------------
        Internally, samples are timestamped with `time.perf_counter_ns()` (high-resolution,
        monotonic). If you provide `trial_start_ns` (typically stimulus onset), it is
        used as the reference to compute `time_to_threshold` (seconds since onset).

        Optional timed callback
        -----------------------
        You may provide a `callback` and `callback_delay` to execute a one-shot action
        at a precise time after `trial_start_ns`, *unless* the threshold is reached first.
        This is useful to display a stimulus or send a marker while preserving a single
        continuous acquisition timeline.

        Optional quit-key detection (no forced exit)
        -------------------------------------------
        If `quit_key` is provided, the function monitors that key during the trial and
        returns a boolean flag indicating whether it was pressed at least once.
        IMPORTANT: pressing `quit_key` does NOT stop acquisition; it only sets the flag.

        Parameters
        ----------
        target_keys : sequence of str or int
            Keys to monitor (characters like 'A' or integer keycodes).

        duration_after_threshold : float, default=0.5
            Duration (seconds) to keep sampling after the threshold is crossed.

        duration_before_threshold : float or None, default=0.2
            Maximum duration (seconds) of samples retained before the threshold crossing.
            If None, all samples from the start are retained (no time limit before threshold).

        sampling_interval : float, default=1/8000
            Target sampling interval (seconds). Actual timing depends on OS scheduling.

        verbose : bool, default=False
            If True, prints debug information (backend selection, trigger, etc.).

        trial_start_ns : int or None, default=None
            Timestamp for stimulus onset or other reference event.
            If None, acquisition start is used.

        trial_start_clock : {'perf', 'mono'}, default='perf'
            Clock domain of `trial_start_ns`:
            - 'perf': `time.perf_counter_ns()`
            - 'mono': `time.monotonic_ns()` (e.g., tachypy/SDL)
            If 'mono', it is projected into the perf_counter domain at acquisition start.

        callback : callable or None, default=None
            Optional one-shot callable (no args) executed after `callback_delay` seconds
            from `trial_start_ns`, unless the threshold occurs first (then it is canceled).

        callback_delay : float or None, default=None
            Delay (seconds) after `trial_start_ns` at which to execute `callback`.
            Must be > 0 if `callback` is provided.

        quit_key : str or int or None, default=None
            Optional key to monitor during acquisition (e.g., 'Esc').
            If provided, the function returns `(hier, quit_pressed)`.

        Returns
        -------
        hier : dict
            Hierarchical structure containing analog trajectories for each target key:
                hier[trial_id][keycode]['time_to_threshold']  (seconds since trial_start_ns)
                hier[trial_id][keycode]['time_abs']           (seconds since epoch)
                hier[trial_id][keycode]['position']           (float in [0, 1])
            
            Note: 'time_to_threshold' is a misnomer - it's actually "time since trial_start_ns".
            When duration_before_threshold=None, all samples before threshold are included,
            so times will be positive both before and after threshold crossing.

        (hier, quit_pressed) : tuple
            Returned only if `quit_key` is provided.
            `quit_pressed` is True if `quit_key` was pressed at least once during the trial.

        Raises
        ------
        ValueError
            If the keyboard is not initialized or parameters are invalid.

        RuntimeError
            If the timed callback raises an exception.
        """
        if not self.initialized:
            raise ValueError('Keyboard must be initialized through "initialize_keyboard()".')
        if self.logging_enabled and self.int_analog == 1:
            raise ValueError(
                "Cannot use acquire_analog_values when logging in integer mode (int_analog=1). "
                "Use acquire_integer_values instead."
            )

        result = self._acquire_raw_values(
            target_keys=target_keys,
            duration_after_threshold=duration_after_threshold,
            duration_before_threshold=duration_before_threshold,
            sampling_interval=sampling_interval,
            verbose=verbose,
            trial_start_ns=trial_start_ns,
            trial_start_clock=trial_start_clock,
            callback=callback,
            callback_delay=callback_delay,
            quit_key=quit_key,
        )

        # Unpack for logging: logging expects the dict
        if isinstance(result, tuple):
            hier, quit_pressed = result
        else:
            hier, quit_pressed = result, None

        if self.logging_enabled and self.int_analog == 2:
            self._write_hdf5_trial_shard(hier)

        self.trial += 1

        # Keep return shape consistent with quit_key usage
        return (hier, quit_pressed) if quit_key is not None else hier


    def acquire_integer_values(
        self,
        target_keys: Sequence[Union[str, int]],
        duration_after_threshold: float = 0.5,
        duration_before_threshold: Optional[float] = 0.2,
        sampling_interval: float = 1 / 8000,
        verbose: bool = False,
        trial_start_ns: Optional[int] = None,
        trial_start_clock: str = "perf",
        callback=None,
        callback_delay=None,
        quit_key: Optional[Union[str, int]] = None,
    ):
        """
        Acquire quantized (integer) key trajectories (0–255) around a threshold crossing.

        Identical to `acquire_analog_values`, except the returned positions are quantized
        to integer values in [0, 255] (rounded analog_value * 255). This is mainly useful
        for logging/storage pipelines that expect integer analog data.

        Optional timed callback
        -----------------------
        Same semantics as `acquire_analog_values`: a one-shot `callback()` can be executed
        after `callback_delay` seconds from `trial_start_ns`, unless the threshold occurs
        first (then it is canceled).

        Optional quit-key detection (no forced exit)
        -------------------------------------------
        If `quit_key` is provided, the function returns `(hier, quit_pressed)` where
        `quit_pressed` indicates whether the quit key was pressed at least once during
        the trial. Pressing the quit key does NOT stop acquisition.

        Parameters
        ----------
        (Same as acquire_analog_values; see that docstring for full details.)

        Returns
        -------
        hier : dict
            Same hierarchical structure, but `position` arrays are integers in [0, 255].
            
            Note: 'time_to_threshold' is actually "time since trial_start_ns".
            When duration_before_threshold=None, all samples before threshold are included.

        (hier, quit_pressed) : tuple
            Returned only if `quit_key` is provided.

        Raises
        ------
        ValueError
            If the keyboard is not initialized or parameters are invalid.

        RuntimeError
            If the timed callback raises an exception.
        """
        if not self.initialized:
            raise ValueError('Keyboard must be initialized through "initialize_keyboard()".')
        if self.logging_enabled and self.int_analog == 2:
            raise ValueError(
                "Cannot use acquire_integer_values when logging in analog mode (int_analog=2). "
                "Use acquire_analog_values instead."
            )

        result = self._acquire_raw_values(
            target_keys=target_keys,
            duration_after_threshold=duration_after_threshold,
            duration_before_threshold=duration_before_threshold,
            sampling_interval=sampling_interval,
            verbose=verbose,
            trial_start_ns=trial_start_ns,
            trial_start_clock=trial_start_clock,
            callback=callback,
            callback_delay=callback_delay,
            quit_key=quit_key,
        )

        if isinstance(result, tuple):
            hier, quit_pressed = result
        else:
            hier, quit_pressed = result, None

        # Quantize positions to int in [0, 255]
        for _, keys in hier.items():
            for _, serie in keys.items():
                serie["position"] = np.rint(
                    np.asarray(serie["position"], dtype=np.float64) * 255.0
                ).astype(np.int16)

        if self.logging_enabled and self.int_analog == 1:
            self._write_hdf5_trial_shard(hier)

        self.trial += 1

        return (hier, quit_pressed) if quit_key is not None else hier

    def wait_keys_light_press(
        self,
        target_keys,
        quit_key,
        hold_seconds: float = 0.30,
        timeout_seconds: float | None = None,
        verbose: bool = False,
    ) -> bool:
        """
        Wait until ALL target keys are lightly pressed at the same time and remain
        in that state for a fixed duration.

        quit_key (str | int):
            A key that, if pressed, stops the loop and returns False.
        """

        if not getattr(self, "initialized", False):
            raise ValueError('Keyboard must be initialized through "initialize_keyboard()".')

        LOW = 0.01
        HIGH = float(self.max_pressure_start)

        if not (0.0 < LOW < HIGH <= 1.0):
            raise ValueError("Invalid pressure range: require 0.01 < max_pressure_start <= 1.0")
        if hold_seconds <= 0:
            raise ValueError("hold_seconds must be > 0")
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0 if provided")

        # --- resolve keycodes ---
        target_codes = self._to_keycodes(target_keys)

        # >>> quit key resolution
        quit_codes = self._to_keycodes([quit_key]) if quit_key is not None else []
        quit_code = int(quit_codes[0]) if quit_codes else None

        interval = 1.0 / 1000.0  # fixed 1000 Hz
        next_t = time.perf_counter()

        start_time = time.perf_counter()
        deadline = None if timeout_seconds is None else (start_time + timeout_seconds)

        stable_start: float | None = None
        was_all_in_range = False

        PRINT_EVERY_S = 0.5
        last_print_t = 0.0
        last_reset_reason: str | None = None

        key_labels = None
        if verbose:
            try:
                key_labels = convert_char_to_keycode([int(c) for c in target_codes])
            except Exception:
                key_labels = None

            backend = self._choose_backend(target_codes)
            lbl = (
                ", ".join(f"{c}({key_labels[i]})" for i, c in enumerate(target_codes))
                if key_labels
                else ", ".join(str(c) for c in target_codes)
            )
            print(
                f"[wait_keys_light_press] targets={lbl} | quit={quit_code} "
                f"| range=[{LOW:.2f}, {HIGH:.3f}] | hold={hold_seconds:.3f}s | backend={backend} | fs=1000Hz"
            )
            last_print_t = time.perf_counter()

        def _vprint(msg: str) -> None:
            nonlocal last_print_t
            if not verbose:
                return
            nowp = time.perf_counter()
            if (nowp - last_print_t) >= PRINT_EVERY_S:
                print(msg)
                last_print_t = nowp

        while True:
            now = time.perf_counter()

            if deadline is not None and now >= deadline:
                raise TimeoutError("wait_keys_light_press: timeout exceeded")

            # --- read target keys ---
            pos_map = self._read_positions_for_targets(target_codes)

            # >>> quit key check (minimal + safe)
            if quit_code is not None:
                qv = float(self._read_positions_for_targets([quit_code]).get(quit_code, 0.0))
                if qv >= LOW:
                    if verbose:
                        print("[wait_keys_light_press] quit key pressed → abort")
                    return False

            all_in_range = True
            offenders_over: list[tuple[int, float]] = []
            offenders_under: list[tuple[int, float]] = []

            for code in target_codes:
                v = float(pos_map.get(int(code), 0.0))
                if v < LOW:
                    all_in_range = False
                    offenders_under.append((int(code), v))
                elif v > HIGH:
                    all_in_range = False
                    offenders_over.append((int(code), v))

            if offenders_over:
                time.sleep(0.010)

            if all_in_range and not was_all_in_range:
                was_all_in_range = True
                stable_start = now
                last_reset_reason = None

                if verbose:
                    forces = " | ".join(
                        f"{int(c)}={float(pos_map.get(int(c), 0.0)):.3f}" for c in target_codes
                    )
                    _vprint(
                        f"[wait_keys_light_press] all keys in range. "
                        f"Starting {hold_seconds:.3f}s timer. forces: {forces}"
                    )

            if all_in_range and stable_start is not None:
                elapsed = now - stable_start

                if verbose and elapsed < hold_seconds:
                    _vprint(f"[wait_keys_light_press] holding… {elapsed:.3f}/{hold_seconds:.3f}s")

                if elapsed >= hold_seconds:
                    if verbose:
                        _vprint("[wait_keys_light_press] condition satisfied.")
                    return True   # <<< SUCCESS

            if not all_in_range:
                if stable_start is not None or was_all_in_range:
                    stable_start = None
                    was_all_in_range = False

                if verbose:
                    if offenders_over and last_reset_reason != "over":
                        last_reset_reason = "over"
                        msg = ", ".join(f"{c}={v:.3f}>{HIGH:.3f}" for c, v in offenders_over)
                        _vprint(
                            f"[wait_keys_light_press] restart: pressure exceeded max ({HIGH:.3f}). "
                            f"Offenders: {msg}"
                        )
                    elif offenders_under and last_reset_reason != "under":
                        last_reset_reason = "under"
                        msg = ", ".join(f"{c}={v:.3f}<{LOW:.2f}" for c, v in offenders_under)
                        _vprint(
                            f"[wait_keys_light_press] restart: at least one key below min ({LOW:.2f}). "
                            f"Offenders: {msg}"
                        )

            next_t += interval
            now2 = time.perf_counter()
            if next_t < (now2 - 0.10):
                next_t = now2 + interval

            self._wait_until_next_tick(next_t)


    def wait_keys_released(
        self,
        target_keys,
        hold_seconds: float = 0.30,
        timeout_seconds: float | None = None,
        release_max: float = 0.01,
        verbose: bool = False,
    ) -> float:
        """
        Wait until ALL target keys are released at the same time and remain
        in that state for a fixed duration.

        Released definition:
            - key force <= release_max  (default: 0.01 to tolerate small sensor noise)

        Sampling rate is fixed at 1000 Hz.
        Timing precision follows the instance timing_mode (sleep / busy / hybrid).

        Typical use:
            acqui.wait_keys_released(['z', 'c'], hold_seconds=0.25)
            # then start the trial / flip screen / etc.

        Returns:
            perf_counter timestamp at which the condition was satisfied.

        Notes on stability:
            - We throttle verbose prints to at most once every 0.5s.
            - If any key is detected above release_max, we add a tiny pause (10 ms)
            to reduce CPU pegging and avoid UI stalls on some systems.
        """
        if not getattr(self, "initialized", False):
            raise ValueError('Keyboard must be initialized through "initialize_keyboard()".')

        if hold_seconds <= 0:
            raise ValueError("hold_seconds must be > 0")
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0 if provided")

        RELEASE_MAX = float(release_max)
        if not (0.0 <= RELEASE_MAX <= 1.0):
            raise ValueError("release_max must be in [0, 1]")

        target_codes = self._to_keycodes(target_keys)

        interval = 1.0 / 1000.0  # fixed 1000 Hz
        next_t = time.perf_counter()

        start_time = time.perf_counter()
        deadline = None if timeout_seconds is None else (start_time + timeout_seconds)

        stable_start: float | None = None
        was_all_released = False

        # ---- Print throttling ----
        PRINT_EVERY_S = 0.5
        last_print_t = 0.0
        last_reset_reason: str | None = None

        key_labels = None
        if verbose:
            try:
                key_labels = convert_char_to_keycode([int(c) for c in target_codes])
            except Exception:
                key_labels = None

            backend = self._choose_backend(target_codes)
            lbl = (
                ", ".join(f"{c}({key_labels[i]})" for i, c in enumerate(target_codes))
                if key_labels
                else ", ".join(str(c) for c in target_codes)
            )
            print(
                f"[wait_keys_released] targets={lbl} | release<= {RELEASE_MAX:.3f} "
                f"| hold={hold_seconds:.3f}s | backend={backend} | fs=1000Hz"
            )
            last_print_t = time.perf_counter()

        def _vprint(msg: str) -> None:
            nonlocal last_print_t
            if not verbose:
                return
            nowp = time.perf_counter()
            if (nowp - last_print_t) >= PRINT_EVERY_S:
                print(msg)
                last_print_t = nowp

        while True:
            now = time.perf_counter()

            if deadline is not None and now >= deadline:
                raise TimeoutError("wait_keys_released: timeout exceeded")

            pos_map = self._read_positions_for_targets(target_codes)

            all_released = True
            offenders_pressed: list[tuple[int, float]] = []

            for code in target_codes:
                v = float(pos_map.get(int(code), 0.0))
                if v > RELEASE_MAX:
                    all_released = False
                    offenders_pressed.append((int(code), v))

            # If any key is still pressed, tiny pause helps avoid pegging CPU / UI stalls
            if offenders_pressed:
                time.sleep(0.010)

            # Transition: not-released -> released
            if all_released and not was_all_released:
                was_all_released = True
                stable_start = now
                last_reset_reason = None

                if verbose:
                    forces = " | ".join(f"{int(c)}={float(pos_map.get(int(c), 0.0)):.3f}" for c in target_codes)
                    _vprint(
                        f"[wait_keys_released] all keys released. Starting {hold_seconds:.3f}s timer. "
                        f"forces: {forces}"
                    )

            # Released: accumulate time
            if all_released and stable_start is not None:
                elapsed = now - stable_start

                if verbose and elapsed < hold_seconds:
                    _vprint(f"[wait_keys_released] holding… {elapsed:.3f}/{hold_seconds:.3f}s")

                if elapsed >= hold_seconds:
                    if verbose:
                        _vprint("[wait_keys_released] condition satisfied.")
                    return now

            # Not released: reset timer and optionally warn
            if not all_released:
                if stable_start is not None or was_all_released:
                    stable_start = None
                    was_all_released = False

                if verbose:
                    if last_reset_reason != "pressed":
                        last_reset_reason = "pressed"
                        msg = ", ".join(f"{c}={v:.3f}>{RELEASE_MAX:.3f}" for c, v in offenders_pressed)
                        _vprint(
                            f"[wait_keys_released] restart: at least one key above release_max ({RELEASE_MAX:.3f}). "
                            f"Offenders: {msg}"
                        )

            next_t += interval

            # If we fell behind a lot (e.g., OS scheduling hiccup), re-anchor next_t
            now2 = time.perf_counter()
            if next_t < (now2 - 0.10):
                next_t = now2 + interval

            self._wait_until_next_tick(next_t)


# ============================================================
# Maintenance helper
# ============================================================

def delete_interface(file: Optional[str] = None, cleanup_plugins: bool = False):
    """
    Remove compiled CFFI artifacts and common build leftovers.
    
    Args:
        file: Optional specific file to delete in addition to standard cleanup.
        cleanup_plugins: If True, also removes system-wide installed plugins.
                        This requires sudo/admin privileges on Linux/macOS.
    """
    interface_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interface")
    pattern = os.path.join(interface_dir, "wooting_interface*")
    files = glob.glob(pattern)
    for file_path in files:
        try:
            os.remove(file_path)
        except OSError:
            pass

    for pycache_dir in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "__pycache__"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "interface", "__pycache__"),
    ]:
        if os.path.isdir(pycache_dir):
            try:
                shutil.rmtree(pycache_dir)
            except Exception:
                pass

    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if file:
        for filename in ["plot.png", f"{file}"]:
            file_path = os.path.join(parent_dir, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    egg_info_dir = os.path.join(project_root, "wooting_interface.egg-info")
    if os.path.isdir(egg_info_dir):
        try:
            shutil.rmtree(egg_info_dir)
        except Exception:
            pass
    
    # Cleanup plugins if requested
    if cleanup_plugins:
        try:
            # Set environment variable to skip auto-setup, then import uninstall function
            os.environ['WOOTING_SKIP_SETUP'] = '1'
            from wooting_package.post_install import uninstall_plugins
            uninstall_plugins()
        except Exception as e:
            print(f"Warning: Failed to uninstall plugins: {e}")
        finally:
            # Clean up environment variable
            os.environ.pop('WOOTING_SKIP_SETUP', None)


def main_delete_interface():
    """CLI entry point for delete_interface command."""
    import argparse
    import os
    
    # Parse args first to check if we need to skip setup
    parser = argparse.ArgumentParser(
        description='Clean up Wooting interface and optionally remove system plugins',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  wooting-delete-interface                 # Remove interface only
  wooting-delete-interface --cleanup-plugins  # Remove interface + plugins
        """
    )
    parser.add_argument(
        '--cleanup-plugins',
        action='store_true',
        help='Also remove system-wide installed plugins (requires sudo/admin)'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Additional file to delete'
    )
    
    args = parser.parse_args()
    
    # If cleaning up plugins, skip auto-setup to avoid reinstalling
    if args.cleanup_plugins:
        os.environ['WOOTING_SKIP_SETUP'] = '1'
    
    try:
        print("\n[Wooting] Cleaning up interface...")
        if args.cleanup_plugins:
            print("[Wooting] Plugins will also be removed...")
        
        delete_interface(file=args.file, cleanup_plugins=args.cleanup_plugins)
        
        print("[Wooting] Cleanup completed successfully.\n")
    except KeyboardInterrupt:
        print("\n[Wooting] Cleanup cancelled by user.")
        import sys
        sys.exit(1)
    except Exception as e:
        print(f"\n[Wooting] Cleanup failed: {e}")
        import sys
        sys.exit(1)
    finally:
        # Clean up environment variable
        os.environ.pop('WOOTING_SKIP_SETUP', None)

