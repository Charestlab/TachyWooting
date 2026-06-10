from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PressureScaleMapper:
    """Map analog pressure values to visual scale factors.

    Parameters
    ----------
    min_scale : float, default=0.25
        Scale used for the weakest non-zero pressure.
    normal_scale : float, default=1.0
        Scale used when pressure is inside the accepted range.
    max_scale : float, default=2.0
        Maximum scale used for strong over-pressure.

    Notes
    -----
    A pressure value of exactly ``0.0`` maps to ``0.0`` so the corresponding
    horizontal line segment can be hidden entirely.
    """

    min_scale: float = 0.25
    normal_scale: float = 1.0
    max_scale: float = 2.0

    def __post_init__(self) -> None:
        if not (0 < self.min_scale <= self.normal_scale <= self.max_scale):
            raise ValueError("Require 0 < min_scale <= normal_scale <= max_scale")

    def map(
        self,
        pressure: float,
        min_pressure_start: float,
        max_pressure_start: float,
    ) -> float:
        """Return the visual scale for one pressure value.

        Parameters
        ----------
        pressure : float
            Analog pressure in the ``[0, 1]`` range.
        min_pressure_start : float
            Lower bound of the accepted light-press range.
        max_pressure_start : float
            Upper bound of the accepted light-press range.

        Returns
        -------
        float
            Visual scale factor. Returns ``0.0`` when ``pressure`` is exactly
            zero, ``normal_scale`` inside the accepted interval, and a clamped
            continuous scale outside it.
        """
        pressure = max(0.0, min(1.0, float(pressure)))
        if pressure == 0.0:
            return 0.0

        if pressure < min_pressure_start:
            if min_pressure_start <= 0:
                return self.normal_scale
            ratio = pressure / min_pressure_start
            return self._clamp(self.min_scale + ratio * (self.normal_scale - self.min_scale))

        if pressure <= max_pressure_start:
            return self.normal_scale

        if max_pressure_start >= 1.0:
            return self.max_scale
        ratio = (pressure - max_pressure_start) / (1.0 - max_pressure_start)
        return self._clamp(self.normal_scale + ratio * (self.max_scale - self.normal_scale))

    def _clamp(self, value: float) -> float:
        return max(self.min_scale, min(self.max_scale, float(value)))
