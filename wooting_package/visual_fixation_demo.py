"""Backward-compatible wrapper for the visual fixation demo module."""

from wooting_package.demos.visual_fixation_demo import main

__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
