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
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union, Literal, Set

import h5py
import numpy as np

from wooting_package.interface import MISSING_INTERFACE_MESSAGE, lib, ffi
from wooting_package.feedback import PressureFeedbackConfig, PressureFeedbackState


_UNSET = object()


def _require_native_interface() -> None:
    """Fail only when native SDK access is actually needed."""
    if lib is None or ffi is None:
        raise RuntimeError(MISSING_INTERFACE_MESSAGE)


# ============================================================
# Character <-> HID keycode conversion
# ============================================================

def convert_char_to_keycode(input_values) -> list | None:
    """Convert between key labels and HID keycodes.

    Parameters
    ----------
    input_values : str, int, or list
        Key label, integer HID keycode, or list of labels/keycodes. String inputs
        are converted to integer keycodes. Integer inputs are converted back to
        key labels.

    Returns
    -------
    list or None
        Converted values. Returns ``None`` when no mapping exists.

    Examples
    --------
    >>> convert_char_to_keycode("A")
    [4]
    >>> convert_char_to_keycode([4])
    ["A"]
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

    min_pressure_start : float
        Lower bound for light-press readiness checks and visual pressure feedback.

    max_pressure_start : float
        Upper bound for “light press” readiness checks (see wait_keys_light_press). Must be
        below `threshold` by design.

    finger_present_threshold : float
        Minimum analog pressure used to consider that a monitored key still has finger contact
        before the response threshold is reached.

    count_post_threshold_removals : bool
        If True, post-threshold drops below `finger_present_threshold` are also counted
        in the removal statistics. Defaults to False.

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

    total_trials : int
        Number of completed acquisition trials tracked by this object.

    removal_trials : int
        Number of completed trials where at least one counted finger removal was detected.

    removal_trial_indices : list[int]
        Trial numbers where at least one counted finger removal was detected.

    removal_trial_proportion : float
        Proportion of completed trials containing at least one finger removal.

    current_removal_streak : int
        Number of consecutive most-recent trials containing finger removals.

    max_removal_streak : int
        Longest consecutive-removal streak observed since object creation.

    last_trial_had_removal : bool
        Whether the most recently completed trial contained at least one finger removal.

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

    trial_contains_removal(trial_index: int) -> bool
        Return whether the given trial index was flagged for a finger removal.

    reached_consecutive_removal_limit(n: int) -> bool
        Return True when the current consecutive-removal streak is at least `n`.

    reached_total_removal_limit(n: int) -> bool
        Return True when the cumulative number of flagged trials reaches `n`, `2n`, `3n`, etc.

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
        min_pressure_start: float = 0.01,
        max_pressure_start: float = 0.35,
        light_press_hold_seconds: float = 0.30,
        finger_present_threshold: float = 0.01,
        count_post_threshold_removals: bool = False,
        backend: BackendMode = "auto",
        timing_mode: TimingMode = "hybrid",
        spin_margin_s: float = 0.0003,
        full_buffer_len: int = 256,
    ):
        """
        Create a Wooting acquisition helper.

        Parameters
        ----------
        start_trial_number : int, default=1
            First trial number to use. Set this when resuming an interrupted experiment.

        threshold : float, default=0.8
            Response threshold. Acquisition triggers once any monitored key reaches this value.

        min_pressure_start : float, default=0.01
            Minimum pressure required for light-press readiness checks.

        max_pressure_start : float, default=0.35
            Maximum pressure allowed for light-press readiness checks.

        light_press_hold_seconds : float, default=0.30
            Default hold duration used by visual light-press readiness checks when no
            method-level `hold_seconds` is provided.

        finger_present_threshold : float, default=0.01
            Minimum pressure required to count a monitored key as still touched after the
            acquisition loop has started. Values below this threshold are counted as
            finger removals before the response threshold is reached.

        count_post_threshold_removals : bool, default=False
            Whether drops below `finger_present_threshold` after the response threshold
            should also count in removal-trial statistics.

        backend : {"auto", "read_analog", "read_full_buffer"}, default="auto"
            SDK readout strategy.

        timing_mode : {"sleep", "busy", "hybrid"}, default="hybrid"
            Sampling cadence strategy.

        spin_margin_s : float, default=0.0003
            Busy-wait window used by hybrid timing mode.

        full_buffer_len : int, default=256
            Size of the C buffers used by the SDK full-buffer readout.
        """
        if threshold <= 0.05 or threshold > 1:
            raise ValueError("threshold must be between 0.05 and 1")
        if not (0.0 <= min_pressure_start < max_pressure_start < threshold):
            raise ValueError("Require 0 <= min_pressure_start < max_pressure_start < threshold")
        if light_press_hold_seconds <= 0:
            raise ValueError("light_press_hold_seconds must be > 0")
        if not (0.0 <= finger_present_threshold < threshold):
            raise ValueError("finger_present_threshold must be >= 0 and lower than threshold")

        if backend not in ("auto", "read_analog", "read_full_buffer"):
            raise ValueError("backend must be 'auto', 'read_analog', or 'read_full_buffer'")

        if timing_mode not in ("sleep", "busy", "hybrid"):
            raise ValueError("timing_mode must be 'sleep', 'busy', or 'hybrid'")
        if spin_margin_s <= 0:
            raise ValueError("spin_margin_s must be positive")

        if full_buffer_len < 8:
            raise ValueError("full_buffer_len too small")
        _require_native_interface()

        self.threshold = float(threshold)
        self.min_pressure_start = float(min_pressure_start)
        self.max_pressure_start = float(max_pressure_start)
        self.hold_seconds = float(light_press_hold_seconds)
        self.finger_present_threshold = float(finger_present_threshold)
        self.count_post_threshold_removals = bool(count_post_threshold_removals)

        self.initialized = False
        self.backend: BackendMode = backend
        self.last_backend: str = ""  # for logging / debug

        self.timing_mode: TimingMode = timing_mode
        self.spin_margin_s: float = float(spin_margin_s)

        if start_trial_number < 1:
            raise ValueError("start_trial_number must be >= 1 (1-based)")
        self.trial = int(start_trial_number)  # 1 if not specified

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

        self.total_trials: int = 0
        self.removal_trials: int = 0
        self.removal_trial_indices: List[int] = []
        self._removal_trial_index_set: Set[int] = set()
        self.current_removal_streak: int = 0
        self.max_removal_streak: int = 0
        self.last_trial_had_removal: bool = False
        self._pending_trial_had_removal: bool = False

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
        """Enable HDF5 logging for subsequent acquisition trials.

        Parameters
        ----------
        name : str, optional
            Base filename for the combined HDF5 output. The extension is ignored;
            ``.hdf5`` is used for the final file.
        path : str, optional
            Directory where staging files and the final HDF5 file are written.
            Defaults to the current working directory.
        int_analog : {1, 2}, default=2
            Logging mode. Use ``1`` for integer pressure values in ``[0, 255]``
            and ``2`` for analog pressure values in ``[0, 1]``.

        Raises
        ------
        ValueError
            If the keyboard is not initialized or if ``int_analog`` is invalid.

        Notes
        -----
        Trial shards are written to a staging directory and merged into the final
        file when :meth:`uninitialize_keyboard` is called.
        """
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
        """Initialize the Wooting Analog SDK and detect a connected device.

        Parameters
        ----------
        verbose : bool, default=False
            If ``True``, print basic information about the detected device.

        Returns
        -------
        bool
            ``True`` when initialization succeeds.

        Raises
        ------
        RuntimeError
            If the native CFFI interface is missing, no Wooting device is found,
            or the SDK reports that initialization failed.
        """
        _require_native_interface()
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
        """Uninitialize the Wooting SDK and merge any pending log shards.

        Notes
        -----
        Always call this at the end of an experiment when logging is enabled so
        per-trial staging files are merged into the final HDF5 file.
        """
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

    @property
    def removal_trial_proportion(self) -> float:
        """float: Proportion of completed trials containing finger removals."""
        if self.total_trials == 0:
            return 0.0
        return self.removal_trials / self.total_trials

    def trial_contains_removal(self, trial_index: int) -> bool:
        """Return whether a completed trial had a finger removal.

        Parameters
        ----------
        trial_index : int
            One-based trial index to query.

        Returns
        -------
        bool
            ``True`` if the trial was flagged for at least one counted finger removal.
            By default only pre-threshold removals are counted; post-threshold removals
            are included when `count_post_threshold_removals=True`.
        """
        return int(trial_index) in self._removal_trial_index_set

    def reached_consecutive_removal_limit(self, n: int) -> bool:
        """Return whether the current removal streak reached a threshold.

        Parameters
        ----------
        n : int
            Consecutive-removal threshold.

        Returns
        -------
        bool
            ``True`` if the current streak is at least ``n``.
        """
        if n <= 0:
            raise ValueError("n must be positive")
        return self.current_removal_streak >= int(n)

    def reached_total_removal_limit(self, n: int) -> bool:
        """Return whether the cumulative removal count reached an interval.

        Parameters
        ----------
        n : int
            Cumulative interval. For example, ``n=5`` returns ``True`` at
            5, 10, 15, ... flagged trials.

        Returns
        -------
        bool
            ``True`` when the number of removal trials is a positive multiple of
            ``n``.
        """
        if n <= 0:
            raise ValueError("n must be positive")
        return self.removal_trials > 0 and self.removal_trials % int(n) == 0

    def get_response_key(
        self,
        hier: Dict[str, Dict[str, Dict[str, Any]]],
        target_keys: Sequence[Union[str, int]],
        trial_index: Optional[int] = None,
    ) -> int:
        """Return the keycode of the target key that was pressed in the last acquired trial.

        Pass the ``hier`` dict returned by :meth:`acquire_analog_values` or
        :meth:`acquire_integer_values`. The key with the highest peak position
        in that trial is returned — in a standard yes/no response where only one
        key is pressed, this uniquely identifies the response.

        Parameters
        ----------
        hier : dict
            Acquisition output from ``acquire_analog_values`` or
            ``acquire_integer_values``.
        target_keys : sequence of str or int
            The same keys that were passed to the acquire call.
        trial_index : int, optional
            Trial index to look up in ``hier``. Defaults to ``self.trial - 1``,
            which is correct when called immediately after acquisition.

        Returns
        -------
        int
            Keycode of the key with the highest peak position.
        """
        t = str(self.trial - 1 if trial_index is None else trial_index)
        target_codes = self._to_keycodes(target_keys)
        return max(
            target_codes,
            key=lambda c: np.asarray(
                hier.get(t, {}).get(str(c), {}).get("position", [0.0])
            ).max(),
        )

    def _record_trial_removal_status(self, trial_index: int, had_removal: bool) -> None:
        self.total_trials += 1
        self.last_trial_had_removal = bool(had_removal)

        if had_removal:
            self.removal_trials += 1
            self.removal_trial_indices.append(int(trial_index))
            self._removal_trial_index_set.add(int(trial_index))
            self.current_removal_streak += 1
            self.max_removal_streak = max(self.max_removal_streak, self.current_removal_streak)
            return

        self.current_removal_streak = 0

    @staticmethod
    def _snapshot_has_finger_removal(snapshot, finger_present_threshold: float) -> bool:
        """Return True when any monitored sample is below the contact threshold."""
        return any(float(sample["position"]) < finger_present_threshold for sample in snapshot)

    def _wait_until_next_tick(self, next_t: float) -> None:
        if self.timing_mode == "busy":
            while time.perf_counter() < next_t:
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
        trial_had_removal = False
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
                if self._snapshot_has_finger_removal(snapshot, self.finger_present_threshold):
                    trial_had_removal = True

                for s in snapshot:
                    if s["position"] >= self.threshold:
                        trigger_perf_ns = int(sample_perf_ns)
                        trigger_key = int(s["key"])
                        triggered = True
                        callback_done = True
                        break
                buffer_pre_threshold.extend(snapshot)

            if triggered:
                if getattr(self, "count_post_threshold_removals", False) and self._snapshot_has_finger_removal(
                    snapshot,
                    self.finger_present_threshold,
                ):
                    trial_had_removal = True

                for s in snapshot:
                    key = int(s["key"])
                    position = float(s["position"])

                    tth = (int(s["perf_ns"]) - int(trial_start_perf_ns)) / 1e9
                    tabs = int(s["epoch_ns"]) / 1e9
                    bins.setdefault((self.trial, key), []).append((tth, tabs, position))

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
        self._pending_trial_had_removal = bool(trial_had_removal)

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

        self._record_trial_removal_status(
            trial_index=self.trial,
            had_removal=getattr(self, "_pending_trial_had_removal", False),
        )
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

        self._record_trial_removal_status(
            trial_index=self.trial,
            had_removal=getattr(self, "_pending_trial_had_removal", False),
        )
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
        Wait for keys to remain in the light-press range.

        Parameters
        ----------
        target_keys : sequence of str or int
            Keys that must all stay between ``min_pressure_start`` and
            ``max_pressure_start``.
        quit_key : str or int
            Key that aborts the wait when pressed. The method returns ``False``
            if this key reaches the lower light-press threshold.
        hold_seconds : float, default=0.30
            Required continuous duration in the accepted range.
        timeout_seconds : float, optional
            Maximum time to wait before raising ``TimeoutError``.
        verbose : bool, default=False
            Print state transitions and reset reasons.

        Returns
        -------
        bool
            ``True`` when all keys are held in range for ``hold_seconds``.
            ``False`` when ``quit_key`` is pressed.

        Raises
        ------
        ValueError
            If the keyboard is not initialized or parameters are invalid.
        TimeoutError
            If ``timeout_seconds`` is reached.
        """

        if not getattr(self, "initialized", False):
            raise ValueError('Keyboard must be initialized through "initialize_keyboard()".')

        LOW = self.min_pressure_start
        HIGH = float(self.max_pressure_start)

        if not (0.0 < LOW < HIGH <= 1.0):
            raise ValueError("Invalid pressure range: require 0 < min_pressure_start < max_pressure_start <= 1")
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

    def wait_keys_light_press_visual(
        self,
        screen,
        target_keys,
        hold_seconds: float | None = None,
        timeout_seconds: float | None = None,
        widget=None,
        fixation_cross=None,
        center=None,
        half_width: float | object = _UNSET,
        half_height: float | object = _UNSET,
        thickness: float | object = _UNSET,
        background_color=(128, 128, 128),
        initial_color=_UNSET,
        target_color=_UNSET,
        vertical_color=None,
        show_pressure_text: bool | object = _UNSET,
        left_pressure_label: str | None = None,
        right_pressure_label: str | None = None,
        response_handler=None,
        exit_keys=("escape", "esc", "enter", "return", "space", "q"),
        verbose: bool = False,
    ) -> bool:
        """
        Wait for two keys to stay in the light-press range while showing visual feedback.

        This is the high-level visual readiness API. In the common case, users
        only provide a TachyPy screen, a TachyPy response handler, and two target
        keys. The method creates the default interactive fixation-cross widget,
        reads Wooting pressure values, updates the widget each frame, flips the
        screen, and returns when the participant holds both keys in range.

        Parameters
        ----------
        screen : object
            TachyPy `Screen`-like object. It must expose `flip()`. If it exposes
            `fill(color)`, the screen is filled with `background_color` each
            frame before drawing.

        target_keys : sequence of str or int
            Exactly two target keys. The first key controls the left side of the
            visual feedback; the second key controls the right side. Labels for
            pressure text are inferred from these values unless
            `left_pressure_label` / `right_pressure_label` are provided.

        hold_seconds : float, optional
            Required continuous hold duration, in seconds. If omitted, the value
            stored on the acquisition object (`self.hold_seconds`) is used.

        timeout_seconds : float, optional
            Maximum time to wait. If provided and exceeded, `TimeoutError` is
            raised.

        widget : PressureFeedbackWidget, optional
            Advanced override. If provided, this widget is used directly and no
            TachyPy widget is created. When `widget` is provided, do not also
            pass auto-widget configuration arguments such as `fixation_cross`,
            `half_width`, `target_color`, or `show_pressure_text`; doing so
            raises `ValueError`.

        fixation_cross : object, optional
            Existing TachyPy `FixationCross`-like object used to configure the
            automatically-created widget. Its `center`, `half_width`,
            `half_height`, `thickness`, and `color` are reused when present.
            `color` becomes the widget `target_color`.

        center : tuple[float, float], optional
            Manual center for the automatically-created widget. Ignored when
            `fixation_cross` provides a center. Invalid with `widget`.

        half_width, half_height : float, optional
            Manual horizontal and vertical half-size for the automatically-created
            widget. Invalid with `widget`.

        thickness : float, optional
            Manual line thickness for the automatically-created widget. Invalid
            with `widget`.

        background_color : tuple[int, int, int], default=(128, 128, 128)
            RGB color used to clear the screen each frame and to validate that
            the widget's initial color is visible.

        initial_color : tuple[int, int, int], optional
            Starting RGB color for the interactive horizontal line while hold
            progress is zero. Defaults to `(100, 100, 100)` when the widget is
            created automatically. Invalid with `widget`.

        target_color : tuple[int, int, int], optional
            Final RGB color reached when hold progress reaches one. Defaults to
            `(0, 0, 0)` unless copied from `fixation_cross.color`. Invalid with
            `widget`.

        vertical_color : tuple[int, int, int], optional
            RGB color for the vertical fixation line. If omitted, the vertical
            line uses the same interpolated color as the horizontal line.
            Invalid with `widget`.

        show_pressure_text : bool, optional
            Whether the automatically-created widget shows pressure text for keys
            outside the acceptable pressure interval. Defaults to `True` for this
            high-level method. Invalid with `widget`.

        left_pressure_label, right_pressure_label : str, optional
            Text labels for left and right pressure readouts. If omitted, labels
            are inferred from `target_keys`. Invalid with `widget`.

        response_handler : object, optional
            TachyPy `ResponseHandler`-like object. If provided, the method calls
            `get_events()`, checks `should_quit()`, and checks key presses
            against `exit_keys` on each frame. A quit request returns `False`.

        exit_keys : sequence of str, default=("escape", "esc", "enter", "return", "space", "q")
            Key names that stop the visual wait early when `response_handler` is
            provided.

        verbose : bool, default=False
            Print a message when readiness is reached.

        Returns
        -------
        bool
            `True` when both keys were held in the acceptable pressure interval
            for `hold_seconds`. `False` when the user exits through
            `response_handler`.

        Raises
        ------
        ValueError
            If the keyboard is not initialized, if pressure/timing arguments are
            invalid, if `target_keys` does not contain exactly two keys, or if a
            custom `widget` is combined with auto-widget configuration arguments.

        TimeoutError
            If `timeout_seconds` is provided and reached before readiness.

        RuntimeError
            If TachyPy support is required to create the default widget but is not
            installed.

        Priority
        --------
        Widget creation follows this precedence:

        1. If `widget` is provided, it is used directly. All auto-widget
           configuration arguments are invalid in this case because they would
           not be applied.
        2. If `widget` is not provided and `fixation_cross` is provided, the
           automatic widget copies `center`, `half_width`, `half_height`,
           `thickness`, and `target_color` from the fixation cross. In this case,
           `fixation_cross.center` takes priority over `center`,
           `fixation_cross.half_width` over `half_width`,
           `fixation_cross.half_height` over `half_height`,
           `fixation_cross.thickness` over `thickness`, and
           `fixation_cross.color` over `target_color`.
        3. If neither `widget` nor `fixation_cross` provides a value, explicit
           method arguments are used (`center`, `half_width`, `half_height`,
           `thickness`, `target_color`, etc.).
        4. If no explicit method argument is provided, default widget values are
           used. If `center` remains unset, the widget computes the center from
           `screen.width` / `screen.height`.
        5. Pressure text labels use `left_pressure_label` /
           `right_pressure_label` when provided. Otherwise they are inferred from
           `target_keys`.

        Examples
        --------
        Minimal usage:

        >>> acq.wait_keys_light_press_visual(
        ...     screen=screen,
        ...     response_handler=response_handler,
        ...     target_keys=["c", "z"],
        ... )

        Reuse an existing TachyPy fixation cross:

        >>> acq.wait_keys_light_press_visual(
        ...     screen=screen,
        ...     response_handler=response_handler,
        ...     target_keys=["c", "z"],
        ...     fixation_cross=fixation,
        ... )

        Complex usage with explicit visual settings:

        >>> acq.wait_keys_light_press_visual(
        ...     screen=screen,
        ...     response_handler=response_handler,
        ...     target_keys=["c", "z"],
        ...     hold_seconds=0.30,
        ...     timeout_seconds=10.0,
        ...     center=(screen.width // 2, screen.height // 2),
        ...     half_width=80,
        ...     half_height=80,
        ...     thickness=10,
        ...     background_color=(128, 128, 128),
        ...     initial_color=(80, 80, 80),
        ...     target_color=(0, 0, 0),
        ...     vertical_color=(0, 0, 0),
        ...     show_pressure_text=True,
        ...     exit_keys=("escape", "enter", "space", "q"),
        ... )

        Advanced usage with a custom widget:

        >>> widget = TachyPyInteractiveFixationCross(
        ...     screen=screen,
        ...     acquisition=acq,
        ...     show_pressure_text=False,
        ... )
        >>> acq.wait_keys_light_press_visual(
        ...     screen=screen,
        ...     response_handler=response_handler,
        ...     target_keys=["c", "z"],
        ...     widget=widget,
        ... )
        """
        if not getattr(self, "initialized", False):
            raise ValueError('Keyboard must be initialized through "initialize_keyboard()".')
        hold_seconds = self.hold_seconds if hold_seconds is None else float(hold_seconds)
        if hold_seconds <= 0:
            raise ValueError("hold_seconds must be > 0")
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0 if provided")

        target_keys = list(target_keys)
        target_codes = self._to_keycodes(target_keys)
        if len(target_codes) != 2:
            raise ValueError("wait_keys_light_press_visual requires exactly two target keys")
        explicit_left_pressure_label = left_pressure_label is not None
        explicit_right_pressure_label = right_pressure_label is not None
        left_pressure_label = left_pressure_label or str(target_keys[0]).upper()
        right_pressure_label = right_pressure_label or str(target_keys[1]).upper()

        if widget is not None:
            conflicting_widget_args = []
            for name, value in (
                ("fixation_cross", fixation_cross),
                ("center", center),
                ("half_width", half_width),
                ("half_height", half_height),
                ("thickness", thickness),
                ("initial_color", initial_color),
                ("target_color", target_color),
                ("vertical_color", vertical_color),
                ("show_pressure_text", show_pressure_text),
            ):
                if value is not None and value is not _UNSET:
                    conflicting_widget_args.append(name)
            if explicit_left_pressure_label:
                conflicting_widget_args.append("left_pressure_label")
            if explicit_right_pressure_label:
                conflicting_widget_args.append("right_pressure_label")
            if conflicting_widget_args:
                names = ", ".join(conflicting_widget_args)
                raise ValueError(
                    "Do not pass auto-widget configuration arguments when `widget` is provided: "
                    f"{names}. Configure the widget directly instead."
                )

        exit_key_set = {str(key).lower() for key in exit_keys}
        if response_handler is not None and hasattr(response_handler, "keys_to_listen"):
            response_handler.keys_to_listen = sorted(exit_key_set)

        if widget is None:
            try:
                from wooting_package.feedback.tachypy_widget import TachyPyInteractiveFixationCross
            except ImportError as exc:
                raise RuntimeError('Install TachyPy support with: pip install ".[tachypy]"') from exc
            widget = TachyPyInteractiveFixationCross(
                screen=screen,
                fixation_cross=fixation_cross,
                center=center,
                half_width=8.0 if half_width is _UNSET else half_width,
                half_height=8.0 if half_height is _UNSET else half_height,
                thickness=1.0 if thickness is _UNSET else thickness,
                background_color=background_color,
                initial_color=(100, 100, 100) if initial_color is _UNSET else initial_color,
                target_color=(0, 0, 0) if target_color is _UNSET else target_color,
                vertical_color=vertical_color,
                acquisition=self,
                show_pressure_text=True if show_pressure_text is _UNSET else show_pressure_text,
                left_pressure_label=left_pressure_label,
                right_pressure_label=right_pressure_label,
            )

        state = PressureFeedbackState(
            PressureFeedbackConfig(
                min_pressure_start=self.min_pressure_start,
                max_pressure_start=self.max_pressure_start,
                threshold=self.threshold,
                hold_seconds=hold_seconds,
            )
        )

        interval = 1.0 / 1000.0
        next_t = time.perf_counter()
        deadline = None if timeout_seconds is None else next_t + timeout_seconds

        while True:
            now = time.perf_counter()
            if deadline is not None and now >= deadline:
                raise TimeoutError("wait_keys_light_press_visual: timeout exceeded")
            if self._visual_exit_requested(response_handler, exit_key_set):
                return False

            frame_background_color = background_color() if callable(background_color) else background_color
            if hasattr(screen, "fill"):
                screen.fill(frame_background_color)

            pos_map = self._read_positions_for_targets(target_codes)
            state.update(
                left_pressure=float(pos_map.get(int(target_codes[0]), 0.0)),
                right_pressure=float(pos_map.get(int(target_codes[1]), 0.0)),
                now=now,
            )

            widget.update(state)
            widget.draw()

            if not hasattr(screen, "flip"):
                raise AttributeError("screen must expose flip()")
            screen.flip()

            if state.is_ready:
                if verbose:
                    print("[wait_keys_light_press_visual] condition satisfied.")
                return True

            next_t += interval
            now2 = time.perf_counter()
            if next_t < (now2 - 0.10):
                next_t = now2 + interval

            self._wait_until_next_tick(next_t)

    @staticmethod
    def _visual_exit_requested(response_handler, exit_keys: set[str]) -> bool:
        if response_handler is None:
            return False
        if hasattr(response_handler, "get_events"):
            response_handler.get_events()
        if hasattr(response_handler, "should_quit") and response_handler.should_quit():
            return True
        if not hasattr(response_handler, "get_key_presses"):
            return False
        for event in response_handler.get_key_presses():
            if event.get("type") == "keydown" and str(event.get("key", "")).lower() in exit_keys:
                return True
        return False


    def wait_keys_released(
        self,
        target_keys,
        hold_seconds: float = 0.30,
        timeout_seconds: float | None = None,
        release_max: float = 0.01,
        response_handler=None,
        exit_keys=("escape", "esc", "enter", "return", "space", "q"),
        on_tick=None,
        verbose: bool = False,
    ) -> float | None:
        """
        Wait for all target keys to be released.

        Parameters
        ----------
        target_keys : sequence of str or int
            Keys that must all remain at or below ``release_max``.
        hold_seconds : float, default=0.30
            Required continuous release duration.
        timeout_seconds : float, optional
            Maximum time to wait before raising ``TimeoutError``.
        release_max : float, default=0.01
            Maximum pressure considered released. This tolerance helps absorb
            small sensor noise.
        response_handler : object, optional
            TachyPy ``ResponseHandler``-like object used to detect exit keys.
        exit_keys : sequence of str, default=("escape", "esc", "enter", "return", "space", "q")
            Keys that stop the wait early when ``response_handler`` is provided.
        on_tick : callable, optional
            Function called once per polling iteration. Useful for drawing a
            visual display while waiting for release.
        verbose : bool, default=False
            Print state transitions and reset reasons.

        Returns
        -------
        float or None
            ``time.perf_counter()`` timestamp when release is satisfied. Returns
            ``None`` when an exit key is detected through ``response_handler``.

        Raises
        ------
        ValueError
            If the keyboard is not initialized or parameters are invalid.
        TimeoutError
            If ``timeout_seconds`` is reached.

        Notes
        -----
        Sampling is scheduled at 1000 Hz. Timing precision follows the instance
        ``timing_mode``.
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
        exit_key_set = {str(key).lower() for key in exit_keys}
        if response_handler is not None and hasattr(response_handler, "keys_to_listen"):
            response_handler.keys_to_listen = sorted(exit_key_set)

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
            if self._visual_exit_requested(response_handler, exit_key_set):
                return None

            pos_map = self._read_positions_for_targets(target_codes)

            all_released = True
            offenders_pressed: list[tuple[int, float]] = []

            for code in target_codes:
                v = float(pos_map.get(int(code), 0.0))
                if v > RELEASE_MAX:
                    all_released = False
                    offenders_pressed.append((int(code), v))

            if on_tick is not None:
                on_tick()

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

def delete_interface(file: Optional[str] = None):
    """Remove compiled CFFI artifacts and common build leftovers.

    Parameters
    ----------
    file : str, optional
        Reserved for backward compatibility. The current implementation removes
        generated interface artifacts from the package interface directory.

    Returns
    -------
    None
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

