from __future__ import annotations

from abc import ABC, abstractmethod

from .state import PressureFeedbackState


class PressureFeedbackWidget(ABC):
    """Abstract drawing interface for pressure feedback widgets.

    Notes
    -----
    Widgets consume a :class:`PressureFeedbackState` and render it using a
    specific backend. The acquisition code only depends on this interface, so
    new visual backends can be added without changing acquisition logic.
    """

    @abstractmethod
    def update(self, state: PressureFeedbackState) -> None:
        """Receive the latest pressure feedback state.

        Parameters
        ----------
        state : PressureFeedbackState
            Current pressure, scale, status, hold progress, and readiness state.
        """
        raise NotImplementedError

    @abstractmethod
    def draw(self) -> None:
        """Draw the widget using its rendering backend."""
        raise NotImplementedError
