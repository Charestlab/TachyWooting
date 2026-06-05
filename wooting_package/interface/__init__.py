import importlib
import os

# The Wooting SDK's background device-watcher thread periodically tries to
# re-open the HID device that is already held open by the main connection.
# On macOS this always fails (exclusive access) and floods stderr with ERROR
# logs. RUST_LOG silences only that plugin's logger; functionality is unchanged.
# Users can override by setting RUST_LOG themselves before importing the package.
#os.environ.setdefault("RUST_LOG", "off")

MISSING_INTERFACE_MESSAGE = """
The Wooting native interface has not been built yet.

Run this command once from your terminal:

    wooting-build-interface

Then run your Python script again.
""".strip()

try:
    # The compiled CFFI module is generated locally by `wooting-build-interface`.
    # It is intentionally optional at import time so pure-Python utilities remain usable.
    _wooting_interface = importlib.import_module("wooting_package.interface.wooting_interface")
    lib = _wooting_interface.lib
    ffi = _wooting_interface.ffi
except ModuleNotFoundError:
    lib = None
    ffi = None

__all__ = ["MISSING_INTERFACE_MESSAGE", "lib", "ffi"]
