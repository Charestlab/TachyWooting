"""Regression tests for WOOTING_ACQUISITION.get_response_key() and the
"_attrs" entry it reads from hier[trial].

get_response_key() previously read a "threshold_key"/"threshold_time" pair
out of hier[trial]["_attrs"], but the live hier dict returned directly by
acquire_analog_values()/acquire_integer_values() never had an "_attrs" key
(that key used to only be added by the separate, offline load_trial()
function when reading a trial back from a saved HDF5 file). As a result,
get_response_key() always returned (None, nan) regardless of whether a key
actually crossed the threshold during acquisition -- silently discarding
every response.

_acquire_raw_values() now also writes an "_attrs" entry onto the live hier,
mirroring the same metadata persisted as HDF5 trial attributes (see
_write_trial_file), so hier[trial]["_attrs"] and a trial dict reloaded via
load_trial() now have the same shape. get_response_key() still falls back to
the threshold crossing tracked internally on the instance for hier that
doesn't carry "_attrs" (a hand-built or older-format hier, or when hier is
omitted entirely).

These tests build a WOOTING_ACQUISITION instance without the native SDK
interface (bypassing __init__/hardware requirements via __new__, matching
the minimum state acquire_analog_values() actually reads) and monkeypatch
the low-level position reader so a threshold crossing can be produced
deterministically, with no physical keyboard required.
"""
from tachywooting.wooting_utils import WOOTING_ACQUISITION


def _make_acquisition(threshold=0.9, trial=1):
    acq = WOOTING_ACQUISITION.__new__(WOOTING_ACQUISITION)
    acq.threshold = threshold
    acq.finger_present_threshold = 0.01
    acq.count_post_threshold_removals = False
    acq.timing_mode = "busy"
    acq.trial = trial
    acq.logging_enabled = False
    acq.int_analog = 2
    acq.backend = "read_analog"
    acq.last_backend = ""
    acq.total_trials = 0
    acq.removal_trials = 0
    acq.removal_trial_indices = []
    acq._removal_trial_index_set = set()
    acq.current_removal_streak = 0
    acq.max_removal_streak = 0
    acq.last_trial_had_removal = False
    acq._pending_trial_had_removal = False
    acq.initialized = True
    acq._target_codes_cache = None
    acq._target_set_cache = None
    return acq


def test_get_response_key_detects_real_threshold_crossing():
    acq = _make_acquisition(threshold=0.9)
    acq._read_positions_for_targets = lambda codes: {29: 0.95, 6: 0.1}  # Z crosses, C stays low

    hier = acq.acquire_analog_values(
        target_keys=[6, 29],
        duration_after_threshold=0.02,
        duration_before_threshold=None,
        sampling_interval=1 / 1000,
    )

    pressed_code, rt = acq.get_response_key(hier)

    assert pressed_code == 29
    assert rt == acq._last_threshold_time
    assert rt >= 0.0


def test_acquire_analog_values_writes_attrs_onto_live_hier():
    # The live hier now mirrors what gets persisted as HDF5 trial attributes,
    # so callers (and get_response_key) don't need a round trip through disk.
    acq = _make_acquisition(threshold=0.9)
    acq._read_positions_for_targets = lambda codes: {29: 0.95, 6: 0.1}

    hier = acq.acquire_analog_values(
        target_keys=[6, 29],
        duration_after_threshold=0.02,
        duration_before_threshold=None,
        sampling_interval=1 / 1000,
    )

    attrs = hier["1"]["_attrs"]
    assert attrs["threshold_key"] == 29
    assert attrs["threshold_time"] == acq._last_threshold_time
    assert attrs["threshold"] == 0.9
    assert attrs["backend"] == acq.last_backend

    # keycode keys are unaffected and still only carry position/time series
    assert set(hier["1"]["6"].keys()) == {"position", "time_from_onset", "time_abs"}


def test_get_response_key_prefers_attrs_from_hier_when_present():
    # Simulate a load_trial()-style (or any future) hier that does carry
    # "_attrs" -- it should win over whatever the instance happens to be
    # tracking internally.
    acq = _make_acquisition(threshold=0.9, trial=3)
    acq._last_threshold_key = 6
    acq._last_threshold_time = 0.5

    hier = {"2": {"_attrs": {"threshold_key": 29, "threshold_time": 0.123}}}

    pressed_code, rt = acq.get_response_key(hier)

    assert pressed_code == 29
    assert rt == 0.123


def test_get_response_key_falls_back_to_instance_state_when_hier_lacks_attrs():
    # A non-empty hier with no "_attrs" (e.g. a hand-built dict, or the shape
    # acquire_analog_values() used to return before it started writing
    # "_attrs" onto the live hier) must still fall back correctly.
    acq = _make_acquisition(threshold=0.9, trial=2)
    acq._last_threshold_key = 6
    acq._last_threshold_time = 0.25

    hier = {"1": {"0006": {"position": [0.95], "time_from_onset": [0.25], "time_abs": [1000.0]}}}

    pressed_code, rt = acq.get_response_key(hier)

    assert pressed_code == 6
    assert rt == 0.25


def test_get_response_key_returns_none_before_any_crossing_is_recorded():
    # acquire_analog_values() blocks until a key crosses threshold (no timeout
    # path), so "no response" can only be observed before any acquisition has
    # completed -- exactly the state __init__ sets these instance attributes
    # to, and what get_response_key() must fall back to.
    acq = _make_acquisition(threshold=0.9)
    acq._last_threshold_key = None
    acq._last_threshold_time = None

    pressed_code, rt = acq.get_response_key({})

    assert pressed_code is None
    import math
    assert math.isnan(rt)
