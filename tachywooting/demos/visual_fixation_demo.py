from __future__ import annotations

import argparse
import time

from tachywooting import WOOTING_ACQUISITION
from tachywooting.feedback.tachypy_widget import TachyPyInteractiveFixationCross


BACKGROUND_COLOR = (128, 128, 128)
HIT_BACKGROUND_COLOR = (120, 190, 120)
INITIAL_HORIZONTAL_COLOR = (80, 80, 80)
CROSS_COLOR = (0, 0, 0)
QUIT_KEYS = {"escape", "esc", "enter", "return", "space", "q"}
RUN_KEY = "x"
RUN_DURATION = 15.0
WINDOWED_WIDTH = 1502
WINDOWED_HEIGHT = 750
FIX_CROSS_LINE = 3
FIX_CROSS_RATIO = 3
FIX_CROSS_HALF = FIX_CROSS_LINE * (FIX_CROSS_RATIO + 1)  # = 12  (run cross)
FIX_CROSS_IDLE_LINE = 5
FIX_CROSS_IDLE_HALF = 24  # idle cross (bigger)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TachyPy demo for the interactive Wooting fixation cross.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--screen-number", type=int, default=0)
    parser.add_argument("--refresh-rate", type=int, default=240)
    parser.add_argument("--fullscreen", action="store_true", help="Use TachyPy fullscreen mode. By default the demo opens in a 1502x750 window.")
    parser.add_argument("--left-key", default="z")
    parser.add_argument("--right-key", default="c")
    parser.add_argument("--hold-seconds", type=float, default=1.00)
    parser.add_argument("--min-pressure", type=float, default=0.33)
    parser.add_argument("--max-pressure", type=float, default=0.66)
    parser.add_argument("--threshold", type=float, default=0.80)

    parser.add_argument("--half-width", type=float, default=FIX_CROSS_IDLE_HALF)
    parser.add_argument("--half-height", type=float, default=FIX_CROSS_IDLE_HALF)
    parser.add_argument("--thickness", type=float, default=FIX_CROSS_IDLE_LINE)
    parser.add_argument("--run-half-width", type=float, default=FIX_CROSS_HALF)
    parser.add_argument("--run-half-height", type=float, default=FIX_CROSS_HALF)
    parser.add_argument("--run-thickness", type=float, default=FIX_CROSS_LINE)
    return parser


class _ExitKeyTracker:
    """Wraps a ResponseHandler to record which exit key triggered the last exit."""

    def __init__(self, rh) -> None:
        self._rh = rh
        self.last_key: str | None = None
        self._seen_event_count = 0

    def get_events(self) -> None:
        if hasattr(self._rh, "get_events"):
            self._rh.get_events()

    def should_quit(self) -> bool:
        return bool(getattr(self._rh, "should_quit", lambda: False)())

    def get_key_presses(self) -> list:
        all_events = self._rh.get_key_presses() if hasattr(self._rh, "get_key_presses") else []
        new_events = all_events[self._seen_event_count:]
        self._seen_event_count = len(all_events)
        for e in new_events:
            if e.get("type") == "keydown":
                self.last_key = str(e.get("key", "")).lower()
        return all_events

    def clear_events(self) -> None:
        if hasattr(self._rh, "clear_events"):
            self._rh.clear_events()
        self._seen_event_count = 0
        self.last_key = None

    @property
    def keys_to_listen(self):
        return self._rh.keys_to_listen

    @keys_to_listen.setter
    def keys_to_listen(self, value) -> None:
        self._rh.keys_to_listen = value
        if value is not None:
            if hasattr(self._rh, "_probed_keys"):
                self._rh._probed_keys.update(value)
            if getattr(self._rh, "backend", None) == "glfw":
                screen = getattr(self._rh, "screen", None)
                if screen is not None and hasattr(screen, "track_keys"):
                    screen.track_keys(value)


class GamifiedFixationWidget:
    """Heads-up display wrapper for the visual fixation demo.

    Parameters
    ----------
    screen : object
        TachyPy ``Screen``-like object used for sizing HUD rectangles.
    fixation_widget : object
        Widget that draws the interactive fixation cross in idle mode (bigger).
    run_fixation_widget : object
        Widget that draws the interactive fixation cross during a run (smaller).
    text_cls : type
        TachyPy ``Text`` class or compatible replacement.
    started_at : float
        ``time.perf_counter()`` timestamp used as the timer origin.
    hold_seconds : float
        Hold duration used to compute theoretical hit rate and efficiency.
    """

    def __init__(
        self,
        screen,
        fixation_widget,
        run_fixation_widget,
        text_cls,
        started_at: float,
        hold_seconds: float,
        font_name: str = "Helvetica",
        compact_layout: bool = False,
    ):
        self.screen = screen
        self.fixation_widget = fixation_widget
        self.run_fixation_widget = run_fixation_widget
        self.text_cls = text_cls
        self.started_at = float(started_at)
        self.hold_seconds = float(hold_seconds)
        self.font_name = font_name
        self.compact_layout = bool(compact_layout)
        self.hits = 0
        self.flash_until = 0.0
        # Run state
        self._run_active = False
        self._run_start_time = 0.0
        self._run_duration = RUN_DURATION
        self._run_start_hits = 0
        # Best score
        self._has_best = False
        self.best_hits = 0
        self.best_efficiency = 0.0
        # Text objects
        self._timer_text = None
        self._hits_text = None
        self._efficiency_text = None
        self._controls_text = None
        self._best_label_text = None
        self._best_value_text = None

    @property
    def _active_cross(self):
        return self.run_fixation_widget if self._run_active else self.fixation_widget

    # ── run lifecycle ────────────────────────────────────────────────────────

    def start_run(self, duration: float = RUN_DURATION) -> None:
        self._run_active = True
        self._run_start_time = time.perf_counter()
        self._run_duration = float(duration)
        self._run_start_hits = self.hits

    def end_run(self) -> None:
        if not self._run_active:
            return
        self._run_active = False
        run_hits = self._run_hits()
        run_eff = self._run_efficiency_percent()
        if not self._has_best or run_hits > self.best_hits or (run_hits == self.best_hits and run_eff > self.best_efficiency):
            self.best_hits = run_hits
            self.best_efficiency = run_eff
            self._has_best = True

    def _run_elapsed(self) -> float:
        return min(self._run_duration, time.perf_counter() - self._run_start_time)

    def _run_remaining(self) -> float:
        return max(0.0, self._run_duration - (time.perf_counter() - self._run_start_time))

    def _run_hits(self) -> int:
        return self.hits - self._run_start_hits

    def _run_efficiency_percent(self) -> float:
        elapsed = self._run_elapsed()
        if elapsed <= 0 or self.hold_seconds <= 0:
            return 0.0
        theoretical = elapsed / self.hold_seconds
        return min(999.9, max(0.0, (self._run_hits() / theoretical) * 100.0))

    # ── widget protocol ──────────────────────────────────────────────────────

    def update(self, state) -> None:
        self._active_cross.update(state)

    def draw(self) -> None:
        self._active_cross.draw()
        self._draw_hud()

    def register_hit(self) -> None:
        self.hits += 1
        self.flash_until = time.perf_counter() + 0.30

    def background_color(self):
        if time.perf_counter() < self.flash_until:
            return HIT_BACKGROUND_COLOR
        return BACKGROUND_COLOR

    # ── HUD ─────────────────────────────────────────────────────────────────

    def _draw_hud(self) -> None:
        width, height = self._screen_size()
        margin = max(16, int(min(width, height) * 0.025))
        font_size = max(16, int(min(width, height) * 0.026))
        small_font_size = max(14, int(font_size * 0.78))

        if self.compact_layout:
            font_size = max(22, int(min(width, height) * 0.032))
            small_font_size = max(16, int(font_size * 0.76))
            hud_y = margin
            line_h = font_size * 2.1
            timer_w = 260
            hits_w = 220
            efficiency_w = 330
            timer_rect = self._rect_centered(width / 2, hud_y + line_h / 2, timer_w, line_h)
            hits_rect = self._rect(margin, hud_y, hits_w, line_h)
            efficiency_rect = self._rect(width - margin - efficiency_w, hud_y, efficiency_w, line_h)
        else:
            timer_rect = self._rect_centered(width / 2, margin + font_size, 220, font_size * 1.8)
            hits_rect = self._rect(margin, margin, 180, font_size * 1.8)
            efficiency_rect = self._rect(width - margin - 220, margin, 220, font_size * 1.8)

        if self._run_active:
            remaining = self._run_remaining()
            self._timer_text = self._draw_text(self._timer_text, f"RUN  {remaining:04.1f}s", timer_rect, font_size)
            self._hits_text = self._draw_text(self._hits_text, f"Hits  {self._run_hits()}", hits_rect, font_size)
            self._efficiency_text = self._draw_text(self._efficiency_text, f"Efficiency  {self._run_efficiency_percent():05.1f}%", efficiency_rect, font_size)
        else:
            elapsed = max(0.0, time.perf_counter() - self.started_at)
            if self.compact_layout:
                controls_rect = self._rect_centered(width / 2, height - margin - small_font_size * 2.6, 220, small_font_size * 4.0)
            else:
                controls_rect = self._rect(width - margin - 180, height - margin - small_font_size * 5, 180, small_font_size * 5)
            self._timer_text = self._draw_text(self._timer_text, f"Time  {elapsed:05.1f}s", timer_rect, font_size)
            self._hits_text = self._draw_text(self._hits_text, f"Hits  {self.hits}", hits_rect, font_size)
            self._efficiency_text = self._draw_text(self._efficiency_text, f"Efficiency  {self._efficiency_percent(elapsed):05.1f}%", efficiency_rect, font_size)
            self._controls_text = self._draw_text(self._controls_text, f"{RUN_KEY.upper()}: run\nEsc: quit", controls_rect, small_font_size)

        if self._has_best:
            label_h = small_font_size * 1.6
            value_h = font_size * 2.0
            if self.compact_layout:
                label_rect = self._rect(margin, height - margin - label_h - value_h, 360, label_h)
                value_rect = self._rect(margin, height - margin - value_h, 360, value_h)
            else:
                label_rect = self._rect(margin, height - margin - label_h - value_h, 300, label_h)
                value_rect = self._rect(margin, height - margin - value_h, 300, value_h)
            self._best_label_text = self._draw_text(self._best_label_text, "BEST SCORE", label_rect, small_font_size, color=(70, 70, 70))
            self._best_value_text = self._draw_text(self._best_value_text, f"{self.best_hits} hits   {self.best_efficiency:.1f}%", value_rect, font_size)

    def _efficiency_percent(self, elapsed: float) -> float:
        if elapsed <= 0 or self.hold_seconds <= 0:
            return 0.0
        theoretical_hits = elapsed / self.hold_seconds
        if theoretical_hits <= 0:
            return 0.0
        return min(999.9, max(0.0, (self.hits / theoretical_hits) * 100.0))

    def _draw_text(self, text_obj, text: str, dest_rect, font_size: int, color=None):
        dest_rect = self._snap_rect(self._clamp_rect(dest_rect))
        draw_color = color if color is not None else CROSS_COLOR
        if text_obj is None:
            text_obj = self.text_cls(
                text=text,
                font_size=font_size,
                color=draw_color,
                dest_rect=dest_rect,
                font_name=self.font_name,
            )
        else:
            text_obj.set_dest_rect(dest_rect)
            if text_obj.text != text:
                text_obj.set_text(text)
        text_obj.draw()
        return text_obj

    def _screen_size(self):
        return (
            float(getattr(self.screen, "width", getattr(self.screen, "w", 1024))),
            float(getattr(self.screen, "height", getattr(self.screen, "h", 768))),
        )

    def _rect(self, x, y, width, height):
        return (float(x), float(y), float(x + width), float(y + height))

    def _rect_centered(self, center_x, center_y, width, height):
        return self._rect(center_x - width / 2, center_y - height / 2, width, height)

    def _clamp_rect(self, rect):
        screen_width, screen_height = self._screen_size()
        x1, y1, x2, y2 = rect
        width = min(max(1.0, x2 - x1), screen_width)
        height = min(max(1.0, y2 - y1), screen_height)
        x1 = min(max(0.0, x1), screen_width - width)
        y1 = min(max(0.0, y1), screen_height - height)
        return (x1, y1, x1 + width, y1 + height)

    @staticmethod
    def _snap_rect(rect):
        x1, y1, x2, y2 = rect
        return (round(x1), round(y1), round(x2), round(y2))


def _draw_countdown(screen, widget, text_cls, background_color_fn, font_name: str) -> None:
    """Show a 3-2-1 countdown in the center of the screen."""
    width = float(getattr(screen, "width", getattr(screen, "w", 1024)))
    height = float(getattr(screen, "height", getattr(screen, "h", 768)))
    font_size = max(80, int(min(width, height) * 0.14))
    box = min(width, height) * 0.22
    center_rect = (width / 2 - box / 2, height / 2 - box / 2, width / 2 + box / 2, height / 2 + box / 2)

    countdown_text = None
    for count in range(3, 0, -1):
        deadline = time.perf_counter() + 1.0
        label = str(count)
        while time.perf_counter() < deadline:
            screen.fill(background_color_fn())
            widget.draw()
            if countdown_text is None:
                countdown_text = text_cls(
                    text=label,
                    font_size=font_size,
                    color=(220, 220, 220),
                    dest_rect=center_rect,
                    font_name=font_name,
                )
            elif countdown_text.text != label:
                countdown_text.set_text(label)
            countdown_text.draw()
            screen.flip()


def main() -> int:
    args = _build_parser().parse_args()

    try:
        from tachypy import ResponseHandler, Screen, Text
    except ImportError as exc:
        raise RuntimeError('Install TachyPy support with: pip install ".[tachypy]"') from exc

    acq = WOOTING_ACQUISITION(
        threshold=args.threshold,
        min_pressure_start=args.min_pressure,
        max_pressure_start=args.max_pressure,
        light_press_hold_seconds=args.hold_seconds,
        backend="auto",
        timing_mode="hybrid",
    )
    acq.initialize_keyboard(verbose=True)

    screen = None
    try:
        screen = Screen(
            screen_number=args.screen_number,
            width=None if args.fullscreen else WINDOWED_WIDTH,
            height=None if args.fullscreen else WINDOWED_HEIGHT,
            fullscreen=args.fullscreen,
            desired_refresh_rate=args.refresh_rate,
        )
        if hasattr(screen, "hide_mouse"):
            screen.hide_mouse()

        response_handler = ResponseHandler(screen=screen)
        key_tracker = _ExitKeyTracker(response_handler)

        center = (screen.width // 2, screen.height // 2)
        shared_cross_kwargs = dict(
            screen=screen,
            acquisition=acq,
            center=center,
            background_color=BACKGROUND_COLOR,
            initial_color=INITIAL_HORIZONTAL_COLOR,
            target_color=CROSS_COLOR,
            vertical_color=CROSS_COLOR,
            show_pressure_text=True,
            show_goal_markers=True,
            pressure_text_font_name="Helvetica",
        )

        idle_cross = TachyPyInteractiveFixationCross(
            half_width=args.half_width,
            half_height=args.half_height,
            thickness=args.thickness,
            **shared_cross_kwargs,
        )
        run_cross = TachyPyInteractiveFixationCross(
            half_width=args.run_half_width,
            half_height=args.run_half_height,
            thickness=args.run_thickness,
            **shared_cross_kwargs,
        )

        widget = GamifiedFixationWidget(
            screen=screen,
            fixation_widget=idle_cross,
            run_fixation_widget=run_cross,
            text_cls=Text,
            started_at=time.perf_counter(),
            hold_seconds=args.hold_seconds,
            font_name="Helvetica",
            compact_layout=not args.fullscreen,
        )

        def draw_release_frame() -> None:
            screen.fill(widget.background_color())
            widget.draw()
            screen.flip()

        print("Press Escape, Enter, Space, or q to quit.")
        print(f"Use {args.left_key!r} for left and {args.right_key!r} for right.")
        print(f"Press {RUN_KEY!r} to start a {RUN_DURATION:.0f}s run.")

        while True:
            in_run = widget._run_active
            current_exit_keys = QUIT_KEYS if in_run else (QUIT_KEYS | {RUN_KEY})
            timeout = max(0.01, widget._run_remaining()) if in_run else None
            key_tracker.last_key = None

            try:
                ready = acq.wait_keys_light_press_visual(
                    screen=screen,
                    target_keys=[args.left_key, args.right_key],
                    widget=widget,
                    background_color=widget.background_color,
                    response_handler=key_tracker,
                    exit_keys=current_exit_keys,
                    timeout_seconds=timeout,
                )
            except TimeoutError:
                widget.end_run()
                key_tracker.clear_events()
                continue

            if not ready:
                if in_run:
                    widget.end_run()
                    key_tracker.clear_events()
                    continue
                if key_tracker.last_key == RUN_KEY:
                    _draw_countdown(screen, widget, Text, widget.background_color, "Helvetica")
                    widget.start_run(RUN_DURATION)
                    continue
                print(f"Final hits: {widget.hits}")
                return 0

            widget.register_hit()

            release_timeout = max(0.01, widget._run_remaining()) if widget._run_active else None
            try:
                released_at = acq.wait_keys_released(
                    target_keys=[args.left_key, args.right_key],
                    hold_seconds=0.01,
                    response_handler=key_tracker,
                    exit_keys=QUIT_KEYS,
                    on_tick=draw_release_frame,
                    timeout_seconds=release_timeout,
                )
            except TimeoutError:
                widget.end_run()
                key_tracker.clear_events()
                continue

            if released_at is None:
                if widget._run_active:
                    widget.end_run()
                print(f"Final hits: {widget.hits}")
                return 0

        return 0

    finally:
        acq.uninitialize_keyboard()
        if screen is not None and hasattr(screen, "close"):
            screen.close()


if __name__ == "__main__":
    raise SystemExit(main())
