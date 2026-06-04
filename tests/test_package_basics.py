import pytest

import wooting_package
from wooting_package import WOOTING_ACQUISITION, convert_char_to_keycode


def test_import_does_not_require_built_native_interface():
    assert hasattr(wooting_package, "build_interface")
    assert hasattr(wooting_package, "delete_interface")


def test_convert_char_to_keycode_round_trip():
    assert convert_char_to_keycode(["A", "Esc", "Space"]) == [4, 41, 44]
    assert convert_char_to_keycode([4, 41, 44]) == ["A", "Esc", "Space"]


def test_acquisition_requires_native_interface_when_missing():
    if wooting_package.ffi is not None and wooting_package.lib is not None:
        pytest.skip("native interface is already built in this environment")

    with pytest.raises(RuntimeError, match="wooting-build-interface"):
        WOOTING_ACQUISITION()


def test_removal_tracking_statistics():
    tracker = WOOTING_ACQUISITION.__new__(WOOTING_ACQUISITION)
    tracker.total_trials = 0
    tracker.removal_trials = 0
    tracker.removal_trial_indices = []
    tracker._removal_trial_index_set = set()
    tracker.current_removal_streak = 0
    tracker.max_removal_streak = 0
    tracker.last_trial_had_removal = False

    tracker._record_trial_removal_status(1, True)
    tracker._record_trial_removal_status(2, True)
    tracker._record_trial_removal_status(3, False)
    tracker._record_trial_removal_status(4, True)

    assert tracker.total_trials == 4
    assert tracker.removal_trials == 3
    assert tracker.removal_trial_indices == [1, 2, 4]
    assert tracker.removal_trial_proportion == 0.75
    assert tracker.current_removal_streak == 1
    assert tracker.max_removal_streak == 2
    assert tracker.trial_contains_removal(2)
    assert not tracker.trial_contains_removal(3)


def test_removal_limit_helpers():
    tracker = WOOTING_ACQUISITION.__new__(WOOTING_ACQUISITION)
    tracker.total_trials = 0
    tracker.removal_trials = 0
    tracker.removal_trial_indices = []
    tracker._removal_trial_index_set = set()
    tracker.current_removal_streak = 2
    tracker.max_removal_streak = 2
    tracker.last_trial_had_removal = True

    assert tracker.reached_consecutive_removal_limit(2)
    assert not tracker.reached_consecutive_removal_limit(3)

    tracker.removal_trials = 5
    assert tracker.reached_total_removal_limit(5)
    assert not tracker.reached_total_removal_limit(3)

    with pytest.raises(ValueError, match="positive"):
        tracker.reached_consecutive_removal_limit(0)
    with pytest.raises(ValueError, match="positive"):
        tracker.reached_total_removal_limit(0)


def test_snapshot_finger_removal_detection():
    snapshot = [
        {"key": 4, "position": 0.8},
        {"key": 5, "position": 0.0},
    ]

    assert WOOTING_ACQUISITION._snapshot_has_finger_removal(snapshot, 0.01)
    assert not WOOTING_ACQUISITION._snapshot_has_finger_removal(snapshot, 0.0)


def test_pre_threshold_missing_contact_flags_trial_removal():
    tracker = WOOTING_ACQUISITION.__new__(WOOTING_ACQUISITION)
    tracker.threshold = 0.8
    tracker.finger_present_threshold = 0.01
    tracker.trial = 1
    tracker._to_keycodes = lambda keys: [1, 2]
    tracker._wait_until_next_tick = lambda next_t: None
    tracker._last_trial_start_perf_ns = None
    tracker._last_stim_on_clock = None

    samples = [
        {1: 0.0, 2: 0.5},  # pre-threshold missing contact
        {1: 0.9, 2: 0.5},  # trigger
        {1: 0.9, 2: 0.5},
    ]

    def read_positions(target_codes):
        if samples:
            return samples.pop(0)
        return {1: 0.9, 2: 0.5}

    tracker._read_positions_for_targets = read_positions

    tracker._acquire_raw_values(
        target_keys=["z", "c"],
        duration_after_threshold=0.000001,
        duration_before_threshold=0.1,
        sampling_interval=0.000001,
    )

    assert tracker._pending_trial_had_removal is True


def test_post_threshold_missing_contact_is_optional_for_trial_removal():
    def make_tracker(count_post_threshold_removals):
        tracker = WOOTING_ACQUISITION.__new__(WOOTING_ACQUISITION)
        tracker.threshold = 0.8
        tracker.finger_present_threshold = 0.01
        tracker.count_post_threshold_removals = count_post_threshold_removals
        tracker.trial = 1
        tracker._to_keycodes = lambda keys: [1, 2]
        tracker._wait_until_next_tick = lambda next_t: None
        tracker._last_trial_start_perf_ns = None
        tracker._last_stim_on_clock = None
        samples = [
            {1: 0.5, 2: 0.5},
            {1: 0.9, 2: 0.5},  # trigger, all fingers present
            {1: 0.9, 2: 0.0},  # post-threshold missing contact
        ]

        def read_positions(target_codes):
            if samples:
                return samples.pop(0)
            return {1: 0.9, 2: 0.5}

        tracker._read_positions_for_targets = read_positions
        return tracker

    default_tracker = make_tracker(False)
    default_tracker._acquire_raw_values(
        target_keys=["z", "c"],
        duration_after_threshold=0.000001,
        duration_before_threshold=0.1,
        sampling_interval=0.000001,
    )
    assert default_tracker._pending_trial_had_removal is False

    post_tracker = make_tracker(True)
    post_tracker._acquire_raw_values(
        target_keys=["z", "c"],
        duration_after_threshold=0.000001,
        duration_before_threshold=0.1,
        sampling_interval=0.000001,
    )
    assert post_tracker._pending_trial_had_removal is True
