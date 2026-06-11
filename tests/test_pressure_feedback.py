import pytest
import sys
import types

from tachywooting.feedback import PressureFeedbackConfig, PressureFeedbackState, PressureScaleMapper
from tachywooting.feedback.tachypy_widget import TachyPyInteractiveFixationCross
from tachywooting.wooting_utils import WOOTING_ACQUISITION


def test_pressure_scale_mapper():
    mapper = PressureScaleMapper(min_scale=0.25, normal_scale=1.0, max_scale=2.0)

    assert mapper.map(0.0, 0.1, 0.4) == 0.0
    assert mapper.map(0.001, 0.1, 0.4) > 0.25
    assert mapper.map(0.1, 0.1, 0.4) == 1.0
    assert mapper.map(0.3, 0.1, 0.4) == 1.0
    assert mapper.map(1.0, 0.1, 0.4) == 2.0


def test_pressure_feedback_state_hold_timer():
    state = PressureFeedbackState(
        PressureFeedbackConfig(
            min_pressure_start=0.1,
            max_pressure_start=0.4,
            threshold=0.8,
            hold_seconds=0.5,
        )
    )

    state.update(0.2, 0.2, now=1.0)
    assert state.hold_progress == 0.0
    assert not state.is_ready

    state.update(0.2, 0.2, now=1.25)
    assert state.hold_progress == 0.5
    assert not state.is_ready

    state.update(0.2, 0.2, now=1.5)
    assert state.hold_progress == 1.0
    assert state.is_ready


def test_pressure_feedback_state_resets_when_out_of_range():
    state = PressureFeedbackState(
        PressureFeedbackConfig(
            min_pressure_start=0.1,
            max_pressure_start=0.4,
            threshold=0.8,
            hold_seconds=0.5,
        )
    )

    state.update(0.2, 0.2, now=1.0)
    state.update(0.2, 0.5, now=1.25)

    assert state.right_status == "too_strong"
    assert state.hold_progress == 0.0
    assert not state.is_ready


def test_tachypy_widget_updates_and_draws_lines(monkeypatch):
    class FakeScreen:
        width = 100
        height = 80

    class FakeLine:
        created = []

        def __init__(self, start_point, end_point, thickness, color):
            self.start_point = start_point
            self.end_point = end_point
            self.thickness = thickness
            self.color = color
            self.draw_count = 0
            self.created.append(self)

        def set_start_point(self, start_point):
            self.start_point = start_point

        def set_end_point(self, end_point):
            self.end_point = end_point

        def set_thickness(self, thickness):
            self.thickness = thickness

        def set_color(self, color):
            self.color = color

        def draw(self):
            self.draw_count += 1

    screen = FakeScreen()
    monkeypatch.setitem(sys.modules, "tachypy", types.SimpleNamespace(Line=FakeLine))
    widget = TachyPyInteractiveFixationCross(
        screen=screen,
        half_width=10,
        half_height=5,
        initial_color=(100, 100, 100),
        target_color=(0, 0, 0),
        background_color=(255, 255, 255),
    )
    state = PressureFeedbackState(
        PressureFeedbackConfig(
            min_pressure_start=0.1,
            max_pressure_start=0.4,
            threshold=0.8,
            hold_seconds=0.5,
        )
    )
    state.update(0.0, 1.0, now=1.0)

    widget.update(state)
    widget.draw()

    assert widget.left_scale == 0.0
    assert widget.right_scale == 2.0
    assert len(FakeLine.created) == 2
    assert all(line.draw_count == 1 for line in FakeLine.created)


def test_tachypy_widget_rejects_invisible_initial_color():
    with pytest.raises(ValueError, match="initial_color"):
        TachyPyInteractiveFixationCross(
            screen=object(),
            initial_color=(128, 128, 128),
            background_color=(128, 128, 128),
        )


def test_tachypy_widget_can_copy_existing_fixation_cross(monkeypatch):
    class FakeLine:
        def __init__(self, start_point, end_point, thickness, color):
            pass

    fixation = types.SimpleNamespace(
        center=(12, 34),
        half_width=7,
        half_height=9,
        thickness=3,
        color=(10, 20, 30),
    )
    monkeypatch.setitem(sys.modules, "tachypy", types.SimpleNamespace(Line=FakeLine))

    widget = TachyPyInteractiveFixationCross(
        screen=object(),
        fixation_cross=fixation,
        initial_color=(100, 100, 100),
        background_color=(128, 128, 128),
    )

    assert widget.center == (12.0, 34.0)
    assert widget.half_width == 7.0
    assert widget.half_height == 9.0
    assert widget.thickness == 3.0
    assert widget.target_color == (10, 20, 30)


@pytest.mark.parametrize("thickness", [3, 4, 5, 6])
def test_goal_markers_touch_ideal_pressure_bar_edges(monkeypatch, thickness):
    class FakeLine:
        created = []

        def __init__(self, start_point, end_point, thickness, color):
            self.start_point = start_point
            self.end_point = end_point
            self.thickness = thickness
            self.color = color
            self.created.append(self)

        def set_start_point(self, start_point):
            self.start_point = start_point

        def set_end_point(self, end_point):
            self.end_point = end_point

        def set_thickness(self, thickness):
            self.thickness = thickness

        def set_color(self, color):
            self.color = color

        def draw(self):
            pass

    monkeypatch.setitem(sys.modules, "tachypy", types.SimpleNamespace(Line=FakeLine))
    widget = TachyPyInteractiveFixationCross(
        screen=object(),
        center=(50, 40),
        half_width=10,
        half_height=5,
        thickness=thickness,
        show_goal_markers=True,
    )
    state = PressureFeedbackState(
        PressureFeedbackConfig(
            min_pressure_start=0.1,
            max_pressure_start=0.4,
            threshold=0.8,
            hold_seconds=0.5,
        )
    )
    state.update(0.2, 0.2, now=1.0)

    widget.update(state)
    widget.draw()

    assert widget.left_scale == 1.0
    assert widget.right_scale == 1.0
    expected_marker_width = max(1.0, widget.thickness * 0.25)
    left_edge_x = widget._left_line.start_point[0]
    right_edge_x = widget._right_line.end_point[0]
    center_y = widget._left_line.start_point[1]
    assert widget._left_marker.start_point == (left_edge_x - expected_marker_width, center_y)
    assert widget._left_marker.end_point == (left_edge_x, center_y)
    assert widget._right_marker.start_point == (right_edge_x, center_y)
    assert widget._right_marker.end_point == (right_edge_x + expected_marker_width, center_y)
    assert widget._left_marker.thickness == widget.thickness
    assert widget._right_marker.thickness == widget.thickness
    assert widget._left_marker.thickness == widget._left_line.thickness
    assert widget._right_marker.thickness == widget._right_line.thickness
    assert FakeLine.created == [
        widget._left_marker,
        widget._right_marker,
        widget._left_line,
        widget._right_line,
        widget._vertical_line,
    ]


def test_tachypy_widget_accepts_acquisition_settings(monkeypatch):
    class FakeLine:
        def __init__(self, start_point, end_point, thickness, color):
            pass

    acquisition = types.SimpleNamespace(
        min_pressure_start=0.33,
        max_pressure_start=0.66,
        threshold=0.8,
        hold_seconds=0.3,
    )
    monkeypatch.setitem(sys.modules, "tachypy", types.SimpleNamespace(Line=FakeLine))

    widget = TachyPyInteractiveFixationCross(
        screen=object(),
        acquisition=acquisition,
        initial_color=(100, 100, 100),
        background_color=(128, 128, 128),
    )

    assert widget.acquisition is acquisition
    assert widget.min_pressure_start == 0.33
    assert widget.max_pressure_start == 0.66
    assert widget.threshold == 0.8
    assert widget.hold_seconds == 0.3


def test_tachypy_widget_lerps_any_rgb_channels():
    assert TachyPyInteractiveFixationCross._lerp_color((10, 200, 30), (110, 20, 230), 0.0) == (10, 200, 30)
    assert TachyPyInteractiveFixationCross._lerp_color((10, 200, 30), (110, 20, 230), 0.5) == (60, 110, 130)
    assert TachyPyInteractiveFixationCross._lerp_color((10, 200, 30), (110, 20, 230), 1.0) == (110, 20, 230)
    assert TachyPyInteractiveFixationCross._lerp_color((0, 0, 255), (255, 128, 0), 2.0) == (255, 128, 0)
    assert TachyPyInteractiveFixationCross._lerp_color((0, 0, 255), (255, 128, 0), -1.0) == (0, 0, 255)


def test_tachypy_widget_draws_pressure_text(monkeypatch):
    class FakeScreen:
        width = 100
        height = 80

    class FakeLine:
        def __init__(self, start_point, end_point, thickness, color):
            pass

        def draw(self):
            pass

    class FakeText:
        created = []

        def __init__(self, text, font_size, color, dest_rect):
            self.text = text
            self.font_size = font_size
            self.color = color
            self.dest_rect = dest_rect
            self.draw_count = 0
            self.created.append(self)

        def set_text(self, text):
            self.text = text

        def set_dest_rect(self, dest_rect):
            self.dest_rect = dest_rect

        def draw(self):
            self.draw_count += 1

    monkeypatch.setitem(sys.modules, "tachypy", types.SimpleNamespace(Line=FakeLine, Text=FakeText))
    widget = TachyPyInteractiveFixationCross(
        screen=FakeScreen(),
        center=(50, 40),
        half_width=10,
        half_height=5,
        show_pressure_text=True,
        left_pressure_label="C",
        right_pressure_label="Z",
        pressure_text_width=40,
        pressure_text_height=20,
        pressure_text_gap=6,
    )
    state = PressureFeedbackState(
        PressureFeedbackConfig(
            min_pressure_start=0.1,
            max_pressure_start=0.4,
            threshold=0.8,
        )
    )
    state.update(0.0, 1.0, now=1.0)

    widget.update(state)
    widget.draw()

    assert [text.text for text in FakeText.created] == ["C: 0.00", "Z: 1.00"]
    assert FakeText.created[0].dest_rect == (0.0, 51.0, 40.0, 71.0)
    assert FakeText.created[1].dest_rect == (60.0, 51.0, 100.0, 71.0)
    assert all(text.draw_count == 1 for text in FakeText.created)


def test_tachypy_widget_hides_pressure_text_when_pressure_is_ideal(monkeypatch):
    class FakeScreen:
        width = 100
        height = 80

    class FakeLine:
        def __init__(self, start_point, end_point, thickness, color):
            pass

        def draw(self):
            pass

    class FakeText:
        created = []

        def __init__(self, text, font_size, color, dest_rect):
            self.created.append(self)

    monkeypatch.setitem(sys.modules, "tachypy", types.SimpleNamespace(Line=FakeLine, Text=FakeText))
    widget = TachyPyInteractiveFixationCross(
        screen=FakeScreen(),
        center=(50, 40),
        half_width=10,
        half_height=5,
        show_pressure_text=True,
    )
    state = PressureFeedbackState(
        PressureFeedbackConfig(
            min_pressure_start=0.1,
            max_pressure_start=0.4,
            threshold=0.8,
        )
    )
    state.update(0.2, 0.3, now=1.0)

    widget.update(state)
    widget.draw()

    assert FakeText.created == []


def test_visual_wait_does_not_show_pressure_text_by_default(monkeypatch):
    class FakeScreen:
        width = 100
        height = 80

        def fill(self, color):
            pass

        def flip(self):
            pass

    class FakeLine:
        def __init__(self, start_point, end_point, thickness, color):
            pass

        def set_start_point(self, value):
            pass

        def set_end_point(self, value):
            pass

        def set_thickness(self, value):
            pass

        def set_color(self, value):
            pass

        def draw(self):
            pass

    class FakeText:
        created = []

        def __init__(self, text, font_size, color, dest_rect):
            self.text = text
            self.created.append(self)

        def set_dest_rect(self, dest_rect):
            pass

        def set_text(self, text):
            self.text = text

        def draw(self):
            pass

    monkeypatch.setitem(sys.modules, "tachypy", types.SimpleNamespace(Line=FakeLine, Text=FakeText))

    acq = WOOTING_ACQUISITION.__new__(WOOTING_ACQUISITION)
    acq.initialized = True
    acq.min_pressure_start = 0.33
    acq.max_pressure_start = 0.66
    acq.threshold = 0.8
    acq.hold_seconds = 0.001
    acq._to_keycodes = lambda keys: [1, 2]
    acq._wait_until_next_tick = lambda next_t: None

    reads = {"count": 0}

    def read_positions(codes):
        reads["count"] += 1
        if reads["count"] == 1:
            return {1: 0.0, 2: 1.0}
        return {1: 0.5, 2: 0.5}

    acq._read_positions_for_targets = read_positions

    assert acq.wait_keys_light_press_visual(screen=FakeScreen(), target_keys=["c", "z"])
    assert FakeText.created == []


def test_visual_wait_rejects_auto_widget_args_when_widget_is_provided():
    class FakeScreen:
        def fill(self, color):
            pass

        def flip(self):
            pass

    class FakeWidget:
        def update(self, state):
            pass

        def draw(self):
            pass

    acq = WOOTING_ACQUISITION.__new__(WOOTING_ACQUISITION)
    acq.initialized = True
    acq.min_pressure_start = 0.33
    acq.max_pressure_start = 0.66
    acq.threshold = 0.8
    acq.hold_seconds = 0.001
    acq._to_keycodes = lambda keys: [1, 2]

    fixation_cross = object()

    with pytest.raises(ValueError, match="fixation_cross"):
        acq.wait_keys_light_press_visual(
            screen=FakeScreen(),
            target_keys=["c", "z"],
            widget=FakeWidget(),
            fixation_cross=fixation_cross,
        )


def test_visual_wait_rejects_non_drawable_overlay():
    class FakeScreen:
        def fill(self, color):
            pass

        def flip(self):
            pass

    class FakeWidget:
        def update(self, state):
            pass

        def draw(self):
            pass

    acq = WOOTING_ACQUISITION.__new__(WOOTING_ACQUISITION)
    acq.initialized = True
    acq.min_pressure_start = 0.33
    acq.max_pressure_start = 0.66
    acq.threshold = 0.8
    acq.hold_seconds = 0.001
    acq._to_keycodes = lambda keys: [1, 2]
    acq._read_positions_for_targets = lambda codes: {1: 0.5, 2: 0.5}

    with pytest.raises(AttributeError, match="draw"):
        acq.wait_keys_light_press_visual(
            screen=FakeScreen(),
            target_keys=["c", "z"],
            widget=FakeWidget(),
            overlay_drawables=[object()],
        )
