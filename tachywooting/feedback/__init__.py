"""Pressure-feedback logic and widget interfaces.

This subpackage contains the backend-independent pressure-feedback state machine
and visual widget contracts. TachyPy-specific rendering lives in
``tachywooting.feedback.tachypy_widget``.
"""

from .mapping import PressureScaleMapper
from .state import PressureFeedbackConfig, PressureFeedbackState
from .widgets import PressureFeedbackWidget

__all__ = [
    "PressureFeedbackConfig",
    "PressureFeedbackState",
    "PressureFeedbackWidget",
    "PressureScaleMapper",
]
