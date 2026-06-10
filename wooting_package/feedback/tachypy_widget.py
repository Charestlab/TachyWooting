from __future__ import annotations

from .state import PressureFeedbackState
from .widgets import PressureFeedbackWidget


class TachyPyInteractiveFixationCross(PressureFeedbackWidget):
    def __init__(
        self,
        # Required TachyPy context
        screen,
        # Manual fixation-cross geometry 
        center=None,
        half_width: float = 8.0,
        half_height: float = 8.0,
        thickness: float = 1.0,
        # Visual colors
        initial_color=(100, 100, 100),
        target_color=(0, 0, 0),
        vertical_color=None,
        background_color=(128, 128, 128),
        # Optional objects used to simplify setup
        fixation_cross=None,
        acquisition=None,
        # Optional goal markers (thin vertical ticks at ±half_width)
        show_goal_markers: bool | float = False,
        # Optional real-time pressure text
        show_pressure_text: bool = False,
        left_pressure_label: str = "",
        right_pressure_label: str = "",
        pressure_text_color=None,
        pressure_text_font_size: int | None = None,
        pressure_text_width: float | None = None,
        pressure_text_height: float | None = None,
        pressure_text_gap: float = 10.0,
        pressure_text_decimals: int = 2,
        pressure_text_font_name: str | None = None,
    ):
        """
        Create an interactive TachyPy fixation cross for visual pressure feedback.

        This widget can be configured manually, or it can reuse values from
        existing objects to reduce duplicated setup in experiments.

        Values taken from `screen`
        --------------------------
        `screen` is required because TachyPy drawing needs an active screen.
        If `center` is not provided and no `fixation_cross` is provided, the
        widget centers itself from `screen.width` / `screen.height` (or `w` / `h`
        if those names are used by the screen object).

        Values taken from `fixation_cross`
        ----------------------------------
        Pass an existing TachyPy `FixationCross` when you already created one
        for the experiment and want this widget to match it. The widget copies:

        - `center` -> widget center
        - `half_width` -> horizontal half-size
        - `half_height` -> vertical half-size
        - `thickness` -> line thickness
        - `color` -> `target_color`

        These copied values override the constructor defaults. Manual values are
        used only when the existing fixation cross does not expose the matching
        attribute.

        Values taken from `acquisition`
        -------------------------------
        Pass a `WOOTING_ACQUISITION` instance when the widget should be tied to
        the same object that owns the pressure configuration. The widget stores:

        - `min_pressure_start`
        - `max_pressure_start`
        - `threshold`
        - `hold_seconds`

        These values are kept on the widget for inspection and consistency with
        `wait_keys_light_press_visual()`. The actual real-time pressure state is
        still provided through `update(state)`.

        Pressure text
        -------------
        If `show_pressure_text=True`, TachyPy `Text` objects are shown above the
        cross only for keys currently outside the acceptable pressure interval.
        Text size and box dimensions scale from the fixation cross size unless
        `pressure_text_font_size`, `pressure_text_width`, or
        `pressure_text_height` are provided explicitly.
        """
        if fixation_cross is not None:
            center = self._as_tuple(getattr(fixation_cross, "center", center))
            half_width = getattr(fixation_cross, "half_width", half_width)
            half_height = getattr(fixation_cross, "half_height", half_height)
            thickness = getattr(fixation_cross, "thickness", thickness)
            target_color = getattr(fixation_cross, "color", target_color)

        initial_color = self._as_rgb_color(initial_color, "initial_color")
        target_color = self._as_rgb_color(target_color, "target_color")
        background_color = self._as_rgb_color(background_color, "background_color")
        vertical_color = target_color if vertical_color is None else self._as_rgb_color(vertical_color, "vertical_color")
        pressure_text_color = (
            None if pressure_text_color is None else self._as_rgb_color(pressure_text_color, "pressure_text_color")
        )

        if initial_color == background_color:
            raise ValueError("initial_color must differ from background_color")
        if half_width <= 0 or half_height <= 0 or thickness <= 0:
            raise ValueError("half_width, half_height, and thickness must be positive")
        try:
            from tachypy import Line
            if show_pressure_text:
                from tachypy import Text
            else:
                Text = None
        except ImportError as exc:
            raise RuntimeError('Install TachyPy support with: pip install ".[tachypy]"') from exc

        self._set_tachypy_context(screen=screen, line_cls=Line, text_cls=Text)
        self._set_acquisition_context(acquisition)
        self._set_geometry(center=center, half_width=half_width, half_height=half_height, thickness=thickness)
        self._set_colors(
            initial_color=initial_color,
            target_color=target_color,
            vertical_color=vertical_color,
            background_color=background_color,
        )
        self._set_pressure_text(
            show_pressure_text=show_pressure_text,
            left_pressure_label=left_pressure_label,
            right_pressure_label=right_pressure_label,
            pressure_text_color=pressure_text_color,
            pressure_text_font_size=pressure_text_font_size,
            pressure_text_width=pressure_text_width,
            pressure_text_height=pressure_text_height,
            pressure_text_gap=pressure_text_gap,
            pressure_text_decimals=pressure_text_decimals,
            pressure_text_font_name=pressure_text_font_name,
        )
        self.show_goal_markers = bool(show_goal_markers)
        self._reset_runtime_state()

    def _set_tachypy_context(self, screen, line_cls, text_cls) -> None:
        self.screen = screen
        self._line_cls = line_cls
        self._text_cls = text_cls

    def _set_acquisition_context(self, acquisition) -> None:
        self.acquisition = acquisition
        self.min_pressure_start = getattr(acquisition, "min_pressure_start", None)
        self.max_pressure_start = getattr(acquisition, "max_pressure_start", None)
        self.threshold = getattr(acquisition, "threshold", None)
        self.hold_seconds = getattr(acquisition, "hold_seconds", None)

    def _set_geometry(self, center, half_width: float, half_height: float, thickness: float) -> None:
        self.center = center
        self.half_width = float(half_width)
        self.half_height = float(half_height)
        self.thickness = float(thickness)

    def _set_colors(self, initial_color, target_color, vertical_color, background_color) -> None:
        self.initial_color = initial_color
        self.target_color = target_color
        self.vertical_color = vertical_color
        self.background_color = background_color

    def _set_pressure_text(
        self,
        show_pressure_text: bool,
        left_pressure_label: str,
        right_pressure_label: str,
        pressure_text_color,
        pressure_text_font_size: int | None,
        pressure_text_width: float | None,
        pressure_text_height: float | None,
        pressure_text_gap: float,
        pressure_text_decimals: int,
        pressure_text_font_name: str | None = None,
    ) -> None:
        self.show_pressure_text = bool(show_pressure_text)
        self.left_pressure_label = str(left_pressure_label)
        self.right_pressure_label = str(right_pressure_label)
        self.pressure_text_color = tuple(pressure_text_color or self.target_color)
        self.pressure_text_font_size = int(pressure_text_font_size or self._auto_text_font_size())
        self.pressure_text_width = float(pressure_text_width or self._auto_text_width())
        self.pressure_text_height = float(pressure_text_height or self._auto_text_height())
        self.pressure_text_gap = float(pressure_text_gap)
        self.pressure_text_decimals = int(pressure_text_decimals)
        self.pressure_text_font_name = pressure_text_font_name or "Helvetica"

    def _reset_runtime_state(self) -> None:
        self.left_pressure = 0.0
        self.right_pressure = 0.0
        self.left_status = "too_weak"
        self.right_status = "too_weak"
        self.left_scale = 1.0
        self.right_scale = 1.0
        self.color = self.initial_color
        self._left_line = None
        self._right_line = None
        self._vertical_line = None
        self._left_marker = None
        self._right_marker = None
        self._left_text = None
        self._right_text = None
    def update(self, state: PressureFeedbackState) -> None:
        """Update the widget from a pressure feedback state.

        Parameters
        ----------
        state : PressureFeedbackState
            Latest pressure feedback state. The widget copies pressure values,
            statuses, scales, and hold progress from this object.

        Returns
        -------
        None
            The widget state is updated in place.
        """
        self.left_pressure = state.left_pressure
        self.right_pressure = state.right_pressure
        self.left_status = state.left_status
        self.right_status = state.right_status
        self.left_scale = state.left_scale
        self.right_scale = state.right_scale
        self.color = self._lerp_color(self.initial_color, self.target_color, state.hold_progress)

    def draw(self) -> None:
        """Draw the interactive fixation cross and optional pressure text.

        Notes
        -----
        The vertical line is always drawn. A horizontal side with scale ``0`` is
        hidden, which corresponds to no detected pressure on that side.
        """
        center_x, center_y = self._center()
        left_x = center_x - self.half_width * self.left_scale
        right_x = center_x + self.half_width * self.right_scale
        top_y = center_y + self.half_height
        bottom_y = center_y - self.half_height

        if self.show_goal_markers:
            marker_h = self.thickness / 2
            self._draw_line("_left_marker", (center_x - self.half_width - 1, center_y - marker_h), (center_x - self.half_width - 1, center_y + marker_h), self.target_color, thickness=2)
            self._draw_line("_right_marker", (center_x + self.half_width + 1, center_y - marker_h), (center_x + self.half_width + 1, center_y + marker_h), self.target_color, thickness=2)

        if self.left_scale > 0.0:
            self._draw_line("_left_line", (left_x, center_y), (center_x, center_y), self.color)
        if self.right_scale > 0.0:
            self._draw_line("_right_line", (center_x, center_y), (right_x, center_y), self.color)
        self._draw_line(
            "_vertical_line",
            (center_x, bottom_y),
            (center_x, top_y),
            self.vertical_color or self.color,
        )
        if self.show_pressure_text and (self.left_status != "ideal" or self.right_status != "ideal"):
            self._draw_pressure_text(center_x, top_y)

    def _center(self):
        if self.center is not None:
            return self.center
        width = getattr(self.screen, "width", getattr(self.screen, "w", 0))
        height = getattr(self.screen, "height", getattr(self.screen, "h", 0))
        return width / 2, height / 2

    def _draw_line(self, attr_name: str, start, end, color, thickness: float | None = None) -> None:
        t = self.thickness if thickness is None else thickness
        line = getattr(self, attr_name)
        if line is None:
            line = self._line_cls(start_point=start, end_point=end, thickness=t, color=color)
            setattr(self, attr_name, line)
        else:
            line.set_start_point(start)
            line.set_end_point(end)
            line.set_color(color)
            line.set_thickness(t)
        line.draw()

    def _draw_pressure_text(self, center_x: float, top_y: float) -> None:
        text_y1 = top_y + self.pressure_text_gap
        text_y2 = text_y1 + self.pressure_text_height
        left_rect = (
            center_x - self.half_width - self.pressure_text_width,
            text_y1,
            center_x - self.half_width,
            text_y2,
        )
        right_rect = (
            center_x + self.half_width,
            text_y1,
            center_x + self.half_width + self.pressure_text_width,
            text_y2,
        )

        if self.left_status != "ideal":
            left_text = self._format_pressure(self.left_pressure_label, self.left_pressure)
            self._left_text = self._draw_text(self._left_text, left_text, left_rect)
        if self.right_status != "ideal":
            right_text = self._format_pressure(self.right_pressure_label, self.right_pressure)
            self._right_text = self._draw_text(self._right_text, right_text, right_rect)

    def _draw_text(self, text_obj, text: str, dest_rect):
        if text_obj is None:
            text_obj = self._text_cls(
                text=text,
                font_size=self.pressure_text_font_size,
                color=self.pressure_text_color,
                dest_rect=dest_rect,
                font_name=self.pressure_text_font_name,
            )
        else:
            text_obj.set_dest_rect(dest_rect)
            if text_obj.text != text:
                text_obj.set_text(text)
        text_obj.draw()
        return text_obj

    def _format_pressure(self, label: str, pressure: float) -> str:
        prefix = f"{label}: " if label else ""
        return f"{prefix}{pressure:.{self.pressure_text_decimals}f}"

    def _screen_min(self) -> float:
        width = float(getattr(self.screen, "width", getattr(self.screen, "w", 1024)))
        height = float(getattr(self.screen, "height", getattr(self.screen, "h", 768)))
        return min(width, height)

    def _auto_text_font_size(self) -> int:
        return max(12, int(round(self._screen_min() * 0.012)))

    def _auto_text_width(self) -> float:
        return max(48.0, self._screen_min() * 0.055)

    def _auto_text_height(self) -> float:
        return max(20.0, self.pressure_text_font_size * 1.5)

    @staticmethod
    def _lerp_color(start, end, progress: float):
        progress = max(0.0, min(1.0, float(progress)))
        return tuple(
            int(round(float(s) + (float(e) - float(s)) * progress))
            for s, e in zip(start, end)
        )

    @staticmethod
    def _as_tuple(value):
        if value is None:
            return None
        return tuple(float(item) for item in value)

    @staticmethod
    def _as_rgb_color(value, name: str):
        try:
            color = tuple(int(round(float(channel))) for channel in value)
        except TypeError as exc:
            raise ValueError(f"{name} must be an RGB sequence") from exc
        if len(color) != 3:
            raise ValueError(f"{name} must contain exactly 3 RGB channels")
        if any(channel < 0 or channel > 255 for channel in color):
            raise ValueError(f"{name} RGB channels must be between 0 and 255")
        return color
