"""
Post-installation setup script for Wooting keyboard interface.

This script handles:
- Platform-specific permission setup (macOS/Linux)
- Building the CFFI interface if needed
- macOS Gatekeeper quarantine removal and code signing

This should be run once after installing the package, or it will be
automatically called on first import if the interface is not yet built.
"""

import time
import os
import glob
import stat
import platform
import subprocess
from pathlib import Path


# --- Paths ---
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_INTERFACE_DIR = os.path.join(_PKG_DIR, "interface")
_PERM_MAC_SH = os.path.join(_PKG_DIR, "permissions", "PERMISSIONS_mac.sh")
_PERM_LINUX_SH = os.path.join(_PKG_DIR, "permissions", "PERMISSIONS_linux.sh")

# Any file produced by cffi will match this pattern
_COMPILED_GLOB = os.path.join(_INTERFACE_DIR, "wooting_interface*")


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


def setup_permissions() -> None:
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
            print("[Wooting] Setting up macOS permissions...")
            subprocess.run(["/bin/bash", _PERM_MAC_SH], check=True, cwd=_PKG_DIR)
            print("[Wooting] macOS permissions configured successfully.")
        except Exception as e:
            print(f"[Wooting] macOS permission setup skipped (script error): {e}")

    elif system == "Linux" and os.path.isfile(_PERM_LINUX_SH):
        _make_executable(_PERM_LINUX_SH)
        try:
            print("[Wooting] Setting up Linux permissions...")
            subprocess.run(["/bin/bash", _PERM_LINUX_SH], check=True, cwd=_PKG_DIR)
            print("[Wooting] Linux permissions configured successfully.")
        except Exception as e:
            print(f"[Wooting] Linux permission setup skipped (script error): {e}")
    # Windows or missing script: silently skip


def apply_macos_gatekeeper() -> None:
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
            print(f"[Wooting] Removing macOS quarantine from: {dylib_dir}")
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
        print("[Wooting] macOS Gatekeeper setup completed.")
    except Exception as e:
        # Never hard-fail here; keep import working and just inform.
        print(f"[Wooting] macOS Gatekeeper step skipped: {e}")


def build_interface_if_needed() -> None:
    """
    Build the CFFI interface if it doesn't exist yet.
    """
    if _compiled_interface_present():
        return  # already built

    try:
        from .wooting_interface_builder import build_interface
        print("[Wooting] Building CFFI interface...")
        build_interface()
        print("[Wooting] Interface built successfully.")
    except Exception as e:
        # Surface a clear error so users know why the build failed
        raise RuntimeError(f"[Wooting] Failed to build CFFI interface: {e}") from e


def run_post_install() -> None:
    """
    Main entry point for post-installation setup.
    Runs all setup steps in the correct order.
    """
    print("\n[Wooting] Running post-installation setup...\n")
    
    # 1) Setup permissions (only if not compiled yet)
    setup_permissions()
    
    # 2) Build interface on first import if missing
    build_interface_if_needed()
    
    # 3) Apply macOS Gatekeeper fixups (best-effort), now that files likely exist
    apply_macos_gatekeeper()

    print("\n[Wooting] Post-installation setup completed.\n")


if __name__ == "__main__":
    run_post_install()

