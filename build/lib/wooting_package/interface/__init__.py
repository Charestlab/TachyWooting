import importlib

try:
    # Import the compiled CFFI module (the .so/.pyd file)
    _wooting_interface = importlib.import_module("wooting_package.interface.wooting_interface")
    lib = _wooting_interface.lib
    ffi = _wooting_interface.ffi
except ModuleNotFoundError:
    lib = None
    ffi = None

__all__ = ["lib", "ffi"]