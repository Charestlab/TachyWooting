from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .mapping import PressureScaleMapper

PressureStatus = Literal["too_weak", "ideal", "too_strong"]


@dataclass(frozen=True)
class PressureFeedbackConfig:
    """Configuration for pressure-readiness feedback.

    Parameters
    ----------
    min_pressure_start : float, default=0.01
        Lower bound for the accepted light-press interval.
    max_pressure_start : float, default=0.35
        Upper bound for the accepted light-press interval.
    threshold : float, default=0.8
        Response threshold used by the acquisition task. Must be greater than
        ``max_pressure_start``.
    hold_seconds : float, default=0.30
        Duration for which both pressures must remain inside the accepted
        interval before readiness is reached.
    mapper : PressureScaleMapper, optional
        Object used to convert pressure values to visual scale factors.
    """

    min_pressure_start: float = 0.01
    max_pressure_start: float = 0.35
    threshold: float = 0.8
    hold_seconds: float = 0.30
    mapper: PressureScaleMapper = field(default_factory=PressureScaleMapper)

    def __post_init__(self) -> None:
        if not (0 <= self.min_pressure_start < self.max_pressure_start < self.threshold <= 1):
            raise ValueError("Require 0 <= min_pressure_start < max_pressure_start < threshold <= 1")
        if self.hold_seconds <= 0:
            raise ValueError("hold_seconds must be positive")


@dataclass
class PressureFeedbackState:
    """State machine for real-time pressure feedback.

    Parameters
    ----------
    config : PressureFeedbackConfig
        Feedback thresholds, hold duration, and pressure-to-scale mapper.

    Attributes
    ----------
    left_pressure, right_pressure : float
        Most recent pressure values.
    left_scale, right_scale : float
        Current visual scale values for the left and right horizontal segments.
    left_status, right_status : {"too_weak", "ideal", "too_strong"}
        Pressure classification for each side.
    hold_progress : float
        Fraction of the hold duration completed, clamped to ``[0, 1]``.
    elapsed_hold_time : float
        Seconds spent continuously inside the accepted interval.
    is_ready : bool
        ``True`` once both pressures have remained ideal for ``hold_seconds``.

    Notes
    -----
    This class contains no TachyPy, OpenGL, or drawing code. It is pure logic and
    can be unit-tested independently.
    """

    config: PressureFeedbackConfig
    left_pressure: float = 0.0
    right_pressure: float = 0.0
    left_scale: float = 1.0
    right_scale: float = 1.0
    left_status: PressureStatus = "too_weak"
    right_status: PressureStatus = "too_weak"
    hold_progress: float = 0.0
    elapsed_hold_time: float = 0.0
    is_ready: bool = False
    _hold_started_at: float | None = None

    def update(self, left_pressure: float, right_pressure: float, now: float) -> None:
        """Update pressure status, scale, hold timer, and readiness.

        Parameters
        ----------
        left_pressure : float
            Current pressure for the left monitored key.
        right_pressure : float
            Current pressure for the right monitored key.
        now : float
            Current monotonic timestamp, usually from ``time.perf_counter()``.

        Returns
        -------
        None
            The object is updated in place.
        """
        self.left_pressure = float(left_pressure)
        self.right_pressure = float(right_pressure)
        self.left_status = self._status(self.left_pressure)
        self.right_status = self._status(self.right_pressure)
        self.left_scale = self.config.mapper.map(
            self.left_pressure,
            self.config.min_pressure_start,
            self.config.max_pressure_start,
        )
        self.right_scale = self.config.mapper.map(
            self.right_pressure,
            self.config.min_pressure_start,
            self.config.max_pressure_start,
        )

        if self.left_status == "ideal" and self.right_status == "ideal":
            if self._hold_started_at is None:
                self._hold_started_at = float(now)
            self.elapsed_hold_time = max(0.0, float(now) - self._hold_started_at)
            self.hold_progress = min(1.0, self.elapsed_hold_time / self.config.hold_seconds)
            self.is_ready = self.hold_progress >= 1.0
            return

        self._hold_started_at = None
        self.elapsed_hold_time = 0.0
        self.hold_progress = 0.0
        self.is_ready = False

    def _status(self, pressure: float) -> PressureStatus:
        if pressure < self.config.min_pressure_start:
            return "too_weak"
        if pressure > self.config.max_pressure_start:
            return "too_strong"
        return "ideal"
