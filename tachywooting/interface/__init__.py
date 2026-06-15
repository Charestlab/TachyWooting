import importlib
import os
from pathlib import Path

# The Wooting SDK's background device-watcher thread periodically tries to
# re-open the HID device that is already held open by the main connection.
# On macOS this always fails (exclusive access) and floods stderr with ERROR
# logs. RUST_LOG silences only that plugin's logger; functionality is unchanged.
# Users can override by setting RUST_LOG themselves before importing the package.
#os.environ.setdefault("RUST_LOG", "off")

MISSING_INTERFACE_MESSAGE = """
══════════════════════════════════════════════════════════════════════
 Wooting keyboard support is not ready yet
══════════════════════════════════════════════════════════════════════

The native Wooting interface could not be loaded. The package tried to
build it automatically and could not finish the one-time setup — this
usually means the build needs a C compiler, or the SDK plugins and the
permissions required to read analog key input are not installed yet.

▶ Run this once from your terminal:

      wooting-build-interface

  It compiles the native interface, installs the Wooting SDK + analog
  plugins (this part needs admin / sudo), and grants the input
  permissions. Then re-run your script.

  To undo it later:  wooting-delete-interface
══════════════════════════════════════════════════════════════════════
""".strip()

NO_DEVICE_MESSAGE = """
══════════════════════════════════════════════════════════════════════
 No Wooting device detected
══════════════════════════════════════════════════════════════════════

The native interface loaded, but the SDK found no analog keyboard.

  1. Make sure a Wooting keyboard is plugged in (try another cable/port).
  2. If it is connected, the SDK plugins or input permissions are likely
     missing. Run this once from your terminal:

         wooting-build-interface

     (installs the SDK + analog plugins and the required permissions;
      needs admin / sudo). Then re-run your script.
══════════════════════════════════════════════════════════════════════
""".strip()

try:
    if os.name == "nt" and hasattr(os, "add_dll_directory"):
        dll_dir = Path(__file__).resolve().parents[1] / "libraries" / "windows" / "release"
        if dll_dir.is_dir():
            os.add_dll_directory(str(dll_dir))

    # The compiled CFFI module is generated locally by `wooting-build-interface`.
    # It is intentionally optional at import time so pure-Python utilities remain usable.
    _wooting_interface = importlib.import_module("tachywooting.interface.wooting_interface")
    lib = _wooting_interface.lib
    ffi = _wooting_interface.ffi
except (ModuleNotFoundError, ImportError, OSError):
    lib = None
    ffi = None

__all__ = ["MISSING_INTERFACE_MESSAGE", "NO_DEVICE_MESSAGE", "lib", "ffi"]
