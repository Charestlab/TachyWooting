"""Python interface for Wooting analog keyboards.

The package exposes acquisition, logging, readiness checks, and optional visual
pressure feedback for Wooting keyboards.

See Also
--------
WOOTING_ACQUISITION
    Main acquisition class.
wooting_package.feedback
    Pure pressure-feedback state and rendering widget interfaces.
"""
# Keep package import side-effect free: building permissions/native CFFI is done explicitly
# with `wooting-build-interface` so imports stay safe in tests, docs, and CI.
from .interface import lib, ffi
from .wooting_interface_builder import build_interface
from .wooting_utils import WOOTING_ACQUISITION, convert_char_to_keycode
from .package_setup import delete_interface

__all__ = [
    "WOOTING_ACQUISITION",
    "build_interface",
    "convert_char_to_keycode",
    "delete_interface",
    "lib",
    "ffi",
]
