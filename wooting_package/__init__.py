# wooting_package/__init__.py
"""
Top-level package initializer.

- If the compiled CFFI extension is missing, build it once on first import.
- On macOS, try to remove Gatekeeper quarantine and ad-hoc sign the shipped
  .dylib files (best-effort, non-fatal).
- Then expose the public API: WOOTING_ACQUISITION, convert_char_to_keycode, lib, ffi, build_interface.
"""

import os
import glob
import stat
import platform
import subprocess
from pathlib import Path

# --- Paths ---
_PKG_DIR        = os.path.dirname(os.path.abspath(__file__))
_INTERFACE_DIR  = os.path.join(_PKG_DIR, "interface")
_PERM_MAC_SH    = os.path.join(_PKG_DIR, "permissions", "PERMISSIONS_mac.sh")
_PERM_LINUX_SH  = os.path.join(_PKG_DIR, "permissions", "PERMISSIONS_linux.sh")

# Any file produced by cffi will match this pattern
_COMPILED_GLOB  = os.path.join(_INTERFACE_DIR, "wooting_interface*")

def _compiled_interface_present() -> bool:
    """Return True if any compiled CFFI module is already present."""
    return len(glob.glob(_COMPILED_GLOB)) > 0

def _make_executable(path: str) -> None:
    """Ensure the .sh script is executable (no-op if it already is)."""
    try:
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IXUSR)  # add user-exec bit
    except Exception:
        # Soft-fail: permissions will be tried by /bin/bash anyway.
        pass

def _apply_macos_gatekeeper():
    """
    Best-effort: remove quarantine and ad-hoc sign dylibs shipped in:
        <pkg>/libraries/darwin/<arch>/
    Runs only on macOS, no-op otherwise. Never raises.
    """
    if platform.system() != "Darwin":
        return

    arch = platform.machine()  # 'arm64' or 'x86_64'
    dylib_dir = Path(_PKG_DIR) / "libraries" / "darwin" / arch
    sdk_path = dylib_dir / "libwooting_analog_sdk.dylib"
    wrapper_path = dylib_dir / "libwooting_analog_wrapper.dylib"

    try:
        if dylib_dir.is_dir():
            # Remove quarantine on the folder (recursive)
            subprocess.run(
                ["xattr", "-dr", "com.apple.quarantine", str(dylib_dir)],
                check=False
            )
        else:
            # Nothing to do if the folder is not present yet (e.g., sdist)
            return

        # Sign only if files exist (first install/build may not have copied them yet)
        if sdk_path.exists():
            subprocess.run(["codesign", "--force", "--sign", "-", str(sdk_path)], check=False)
        if wrapper_path.exists():
            subprocess.run(["codesign", "--force", "--sign", "-", str(wrapper_path)], check=False)
        print("\n")
    except Exception as e:
        # Never hard-fail here; keep import working and just inform.
        print(f"[Wooting][macOS] Gatekeeper step skipped: {e}")

def _run_permissions_if_needed() -> None:
    """
    Run platform-specific permission script only if the interface
    is not yet compiled. No-op if compiled or on unsupported OS.
    """
    if _compiled_interface_present():
        return  # already compiled ⇒ do nothing

    system = platform.system()
    if system == "Darwin" and os.path.isfile(_PERM_MAC_SH):
        _make_executable(_PERM_MAC_SH)
        try:
            subprocess.run(["/bin/bash", _PERM_MAC_SH], check=True, cwd=_PKG_DIR)
        except Exception as e:
            print(f"[Wooting] macOS permission setup skipped (script error): {e}")

    elif system == "Linux" and os.path.isfile(_PERM_LINUX_SH):
        _make_executable(_PERM_LINUX_SH)
        try:
            subprocess.run(["/bin/bash", _PERM_LINUX_SH], check=True, cwd=_PKG_DIR)
        except Exception as e:
            print(f"[Wooting] Linux permission setup skipped (script error): {e}")
    print("\n")
    # Windows or missing script: silently skip

# 1) Run permissions (only if not compiled yet)
_run_permissions_if_needed()

# 2) Build interface on first import if missing
if not _compiled_interface_present():
    from .wooting_interface_builder import build_interface
    try:
        build_interface()
    except Exception as e:
        # Surface a clear error so users know why the import failed
        raise RuntimeError(f"[Wooting] Failed to build CFFI interface: {e}") from e

# 2b) Apply macOS Gatekeeper fixups (best-effort), now that files likely exist
_apply_macos_gatekeeper()

# 3) Import public API (now that interface exists)
from .wooting_utils import WOOTING_ACQUISITION, convert_char_to_keycode, delete_interface
from .interface import lib, ffi
from .wooting_interface_builder import build_interface  # ensure symbol is exported

__all__ = [
    "WOOTING_ACQUISITION",
    "convert_char_to_keycode",
    "lib",
    "ffi",
    "build_interface",
    "delete_interface",
]
