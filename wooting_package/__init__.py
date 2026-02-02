"""
Wooting Analog Keyboard Python Interface

This package provides a Python interface for Wooting analog keyboards,
enabling reading of analog key values and managing keyboard events.

The package automatically handles post-installation setup (permissions,
interface building) on first import if needed.
"""
import time
import os
import glob

# --- Paths ---
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_INTERFACE_DIR = os.path.join(_PKG_DIR, "interface")

# Any file produced by cffi will match this pattern
_COMPILED_GLOB = os.path.join(_INTERFACE_DIR, "wooting_interface*")


def _compiled_interface_present() -> bool:
    """Return True if any compiled CFFI module is already present."""
    return len(glob.glob(_COMPILED_GLOB)) > 0


def _ensure_setup_complete() -> None:
    """
    Ensure post-installation setup is complete.
    This runs automatically on first import if the interface is not yet built.
    
    Can be skipped by setting WOOTING_SKIP_SETUP environment variable.
    """
    # Allow skipping setup (useful for cleanup operations)
    if os.environ.get('WOOTING_SKIP_SETUP'):
        return
    
    if _compiled_interface_present():
        return  # already set up

    # Run post-installation setup
    from .post_install import run_post_install
    run_post_install()



# Run setup if needed (only once, on first import)
_ensure_setup_complete()

# Import public API (now that interface exists)
from .wooting_utils import WOOTING_ACQUISITION, convert_char_to_keycode, delete_interface
from .wooting_interface_builder import build_interface
from .interface import lib, ffi

__all__ = [
    "WOOTING_ACQUISITION",
    "convert_char_to_keycode",
    "lib",
    "ffi"
]
