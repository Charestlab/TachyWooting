from __future__ import annotations

import argparse
import os
import time

from wooting_package import WOOTING_ACQUISITION
from wooting_package.feedback.tachypy_widget import TachyPyInteractiveFixationCross


BACKGROUND_COLOR = (128, 128, 128)
HIT_BACKGROUND_COLOR = (120, 190, 120)
INITIAL_HORIZONTAL_COLOR = (80, 80, 80)
CROSS_COLOR = (0, 0, 0)
QUIT_KEYS = {"escape", "esc", "enter", "return", "space", "q"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TachyPy demo for the interactive Wooting fixation cross.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--screen-number", type=int, default=0)
    parser.add_argument("--refresh-rate", type=int, default=240)
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--left-key", default="z")
    parser.add_argument("--right-key", default="c")
    parser.add_argument("--hold-seconds", type=float, default=5.00)
    parser.add_argument("--min-pressure", type=float, default=0.33)
    parser.add_argument("--max-pressure", type=float, default=0.66)
    parser.add_argument("--threshold", type=float, default=0.80)
    parser.add_argument("--release-hold-seconds", type=float, default=0.15)
    parser.add_argument("--half-width", type=float, default=80.0)
    parser.add_argument("--half-height", type=float, default=80.0)
    parser.add_argument("--thickness", type=float, default=10.0)
    return parser


class GamifiedFixationWidget:
    """Heads-up display wrapper for the visual fixation demo.

    Parameters
    ----------
    screen : object
        TachyPy ``Screen``-like object used for sizing HUD rectangles.
    fixation_widget : object
        Widget that draws the interactive fixation cross.
    text_cls : type
        TachyPy ``Text`` class or compatible replacement.
    started_at : float
        ``time.perf_counter()`` timestamp used as the timer origin.
    hold_seconds : float
        Hold duration used to compute theoretical hit rate and efficiency.
    """

    def __init__(self, screen, fixation_widget, text_cls, started_at: float, hold_seconds: float, font_name: str = "Helvetica"):
        self.screen = screen
        self.fixation_widget = fixation_widget
        self.text_cls = text_cls
        self.started_at = float(started_at)
        self.hold_seconds = float(hold_seconds)
        self.font_name = font_name
        self.hits = 0
        self.flash_until = 0.0
        self._timer_text = None
        self._hits_text = None
        self._efficiency_text = None
        self._exit_text = None

    def update(self, state) -> None:
        self.fixation_widget.update(state)

    def draw(self) -> None:
        self.fixation_widget.draw()
        self._draw_hud()

    def register_hit(self) -> None:
        self.hits += 1
        self.flash_until = time.perf_counter() + 0.30

    def background_color(self):
        if time.perf_counter() < self.flash_until:
            return HIT_BACKGROUND_COLOR
        return BACKGROUND_COLOR

    def _draw_hud(self) -> None:
        width, height = self._screen_size()
        margin = max(16, int(min(width, height) * 0.025))
        font_size = max(16, int(min(width, height) * 0.026))
        small_font_size = max(14, int(font_size * 0.78))

        elapsed = max(0.0, time.perf_counter() - self.started_at)
        timer_rect = self._rect_centered(width / 2, margin + font_size, 220, font_size * 1.8)
        hits_rect = self._rect(margin, margin, 180, font_size * 1.8)
        efficiency_rect = self._rect(width - margin - 220, margin, 220, font_size * 1.8)
        exit_rect = self._rect(width - margin - 180, height - margin - small_font_size * 7, 180, small_font_size * 7)

        self._timer_text = self._draw_text(
            self._timer_text,
            f"Time  {elapsed:05.1f}s",
            timer_rect,
            font_size,
        )
        self._hits_text = self._draw_text(
            self._hits_text,
            f"Hits  {self.hits}",
            hits_rect,
            font_size,
        )
        self._efficiency_text = self._draw_text(
            self._efficiency_text,
            f"Efficiency  {self._efficiency_percent(elapsed):05.1f}%",
            efficiency_rect,
            font_size,
        )
        self._exit_text = self._draw_text(
            self._exit_text,
            "Quit:\n• Esc\n• Enter\n• Space\n• Q",
            exit_rect,
            small_font_size,
        )

    def _draw_text(self, text_obj, text: str, dest_rect, font_size: int):
        dest_rect = self._clamp_rect(dest_rect)
        if text_obj is None:
            text_obj = self.text_cls(
                text=text,
                font_size=font_size,
                color=CROSS_COLOR,
                dest_rect=dest_rect,
                font_name=self.font_name,
            )
        else:
            text_obj.set_dest_rect(dest_rect)
            if text_obj.text != text:
                text_obj.set_text(text)
        text_obj.draw()
        return text_obj

    def _efficiency_percent(self, elapsed: float) -> float:
        if elapsed <= 0 or self.hold_seconds <= 0:
            return 0.0
        theoretical_hits = elapsed / self.hold_seconds
        if theoretical_hits <= 0:
            return 0.0
        return min(999.9, max(0.0, (self.hits / theoretical_hits) * 100.0))

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
            fullscreen=not args.windowed,
            desired_refresh_rate=args.refresh_rate,
        )
        if hasattr(screen, "hide_mouse"):
            screen.hide_mouse()

        response_handler = ResponseHandler(screen=screen)
        response_handler.keys_to_listen = sorted(QUIT_KEYS)

        fixation_widget = TachyPyInteractiveFixationCross(
            screen=screen,
            acquisition=acq,
            center=(screen.width // 2, screen.height // 2),
            half_width=args.half_width,
            half_height=args.half_height,
            thickness=args.thickness,
            background_color=BACKGROUND_COLOR,
            initial_color=INITIAL_HORIZONTAL_COLOR,
            target_color=CROSS_COLOR,
            vertical_color=CROSS_COLOR,
            show_pressure_text=True,
            left_pressure_label=args.left_key.upper(),
            right_pressure_label=args.right_key.upper(),
            pressure_text_font_name="Helvetica",
        )
        widget = GamifiedFixationWidget(
            screen=screen,
            fixation_widget=fixation_widget,
            text_cls=Text,
            started_at=time.perf_counter(),
            hold_seconds=args.hold_seconds,
            font_name="Helvetica",
        )

        print("Press Escape, Enter, Space, or q to quit.")
        print(f"Use {args.left_key!r} for left and {args.right_key!r} for right.")

        def draw_release_frame() -> None:
            screen.fill(widget.background_color())
            widget.draw()
            screen.flip()

        while True:
            ready = acq.wait_keys_light_press_visual(
                screen=screen,
                target_keys=[args.left_key, args.right_key],
                widget=widget,
                background_color=widget.background_color,
                response_handler=response_handler,
                exit_keys=QUIT_KEYS,
            )
            if not ready:
                print(f"Final hits: {widget.hits}")
                return 0
            widget.register_hit()
            released_at = acq.wait_keys_released(
                target_keys=[args.left_key, args.right_key],
                hold_seconds=args.release_hold_seconds,
                response_handler=response_handler,
                exit_keys=QUIT_KEYS,
                on_tick=draw_release_frame,
            )
            if released_at is None:
                print(f"Final hits: {widget.hits}")
                return 0

        return 0

    finally:
        acq.uninitialize_keyboard()
        if screen is not None and hasattr(screen, "close"):
            screen.close()


if __name__ == "__main__":
    raise SystemExit(main())
