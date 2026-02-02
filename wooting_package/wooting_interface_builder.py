"""
Wooting Interface Builder

This script builds the Python interface for the Wooting Analog SDK using CFFI.

Components:
-----------
wooting-analog-sdk: The core Analog SDK which handles loading of plugins. This is installed systemwide and is updated separately.
wooting-analog-common: Common Analog SDK definitions used by all parts.
wooting-analog-plugin-dev: Common elements needed for designing plugins. This re-exports wooting-analog-common, so plugins do not have to depend on it separately.
wooting-analog-wrapper: The SDK wrapper used by applications to communicate with the SDK. The linked DLL/dylib/so should be shipped with the application.
wooting-analog-test-plugin: Dummy plugin using shared memory so other processes can control output (used for unit testing and the virtual keyboard).
wooting-analog-virtual-kb: Virtual Keyboard (GTK) to set analog values for keys through the dummy plugin — useful for testing without an analog device.
wooting-analog-sdk-updater: Tool to update the Analog SDK from GitHub releases.

Headers:
--------
wooting-analog-wrapper.h: Includes everything needed to use the SDK (uses wooting-analog-common.h for enums/structs).
wooting-analog-common.h: Defines common enums/headers/structs needed by plugins and SDK users.
wooting-analog-plugin-dev.h: Includes wooting-analog-common.h and additional functions from the analog-sdk-common static library (for plugins).
plugin.h: Header plugins should use to define exported functions.

Dependencies:
------------
- CFFI: to build the Python interface
- Platform-specific SDK libraries (dll/dylib/so)
- Platform-specific header files

Usage:
------
Script is called in the __init__.py
The script detects the platform and uses the appropriate build settings.
"""
import os
import sysconfig
import platform
import subprocess
from cffi import FFI
from wooting_package.text_extraction import extract_header_code

CURRENT_DIR   = os.path.dirname(os.path.abspath(__file__))
INTERFACE_DIR = os.path.join(CURRENT_DIR, 'interface')
LIBRARIES_DIR = os.path.join(CURRENT_DIR, 'libraries')

SDK_LIBRARY_NAME = "wooting_analog_sdk"
WRAPPER_LIBRARY_NAME = "wooting_analog_wrapper"
COMMON_HEADER_FILENAME  = "wooting-analog-common.h"
WRAPPER_HEADER_FILENAME = "wooting-analog-wrapper.h"

system = platform.system().lower() # 'darwin', 'linux', 'windows'

def _norm_arch():
    """Normalize architecture names we care about."""
    arch = platform.machine().lower()
    if arch in ("arm64", "aarch64", "arm64e"):
        return "arm64"
    if arch in ("x86_64", "amd64"):
        return "x86_64"
    return "arm64" # Default

def get_library_dir():
    """Return the correct library directory based on platform and architecture."""
    base_dir = os.path.join(LIBRARIES_DIR, system)
    if system == "darwin": # .../libraries/darwin/arm64 or x86_64
        arch = _norm_arch()
        return os.path.join(base_dir, arch)
    else : # no arch subfolder
        return base_dir

def get_library_dir():
    """Return the correct library directory based on platform and architecture."""
    base_dir = os.path.join(LIBRARIES_DIR, system)
    if system == "darwin":  # .../libraries/darwin/arm64 or x86_64
        arch = _norm_arch()
        return os.path.join(base_dir, arch)
    else:
        # linux/windows: pas de sous-dossier d'archi dans ton layout actuel
        return base_dir
            
def get_platform_config(library_dir):
    """Return platform-specific compile/link configuration."""
    arch = _norm_arch()

    # This ensures that the compiler can find the Python C headers required to build the CFFI extension.
    py_inc = sysconfig.get_config_var("INCLUDEPY") or sysconfig.get_paths()["include"]

    if system == 'darwin':  # macOS
        compile_args = [
            f'-I{library_dir}',  # headers
        ]
        # rpath must include the arch subfolder so the .so finds the dylibs next to the package
        extra_link_args = [
            f'-Wl,-rpath,@loader_path/../libraries/darwin/{arch}'
        ]
        system_libs = []

    elif system == 'linux':
        compile_args = [
            '-Wall', '-Wextra', '-g', '-O0',
            f'-I{library_dir}',
            f'-I{py_inc}',
        ]
        # ELF: $ORIGIN resolves to the directory of the loaded binary
        # -Wl,-rpath-link allows the linker to find dependencies during compilation
        extra_link_args = [
            '-Wl,-rpath,$ORIGIN/../libraries/linux'
        ]
        system_libs = []

    else:  # Windows
        compile_args = [
            '/W4',  # warnings
            '/Zi',  # debug info
            '/Od',  # no optimization (dev)
        ]
        extra_link_args = []  # rpath is not used on Windows
        system_libs = [
            'ws2_32', 'kernel32', 'advapi32', 'ntdll', 'bcrypt', 'userenv'
        ]

    return {
        'compile_args': compile_args,
        'extra_link_args': extra_link_args,
        'system_libs': system_libs,
    }


def build_interface():
    """Build the Python interface for the Wooting Analog SDK.""" # OLD
    print("\n\nBuilding Wooting interface...")
    library_dir = get_library_dir()
    print(f"\n\tUsing libraries from: {library_dir}")
    os.makedirs(INTERFACE_DIR, exist_ok=True)

    # Verify header presence
    common_header_path  = os.path.join(library_dir, COMMON_HEADER_FILENAME)
    wrapper_header_path = os.path.join(library_dir, WRAPPER_HEADER_FILENAME)
    if not os.path.isfile(common_header_path):
        raise FileNotFoundError(f"Missing header: {common_header_path}")
    if not os.path.isfile(wrapper_header_path):
        raise FileNotFoundError(f"Missing header: {wrapper_header_path}")

    # Extract C declarations from headers
    common_header_code, wrapper_header_code = extract_header_code(
        common_header_path, wrapper_header_path
    )

    ffib = FFI()
    ffib.cdef(common_header_code)
    ffib.cdef(wrapper_header_code)
    cfg = get_platform_config(library_dir)


    # Keep the module name 'wooting_interface' (import via: from interface import lib, ffi)
    ffib.set_source(
        'wooting_interface',
        f'#include <{WRAPPER_HEADER_FILENAME}>\n',
        libraries=[SDK_LIBRARY_NAME, WRAPPER_LIBRARY_NAME] + cfg['system_libs'],
        library_dirs=[library_dir],
        extra_compile_args=cfg['compile_args'],
        extra_link_args=cfg['extra_link_args'],
    )

    old_cwd = os.getcwd()
    try:
        os.chdir(INTERFACE_DIR)
        ffib.compile(verbose=True)
        print("\n\tInterface compiled successfully!\n")
    except Exception as e:
        print(f"\n\tCompilation error: {e}")
        if isinstance(e, subprocess.CalledProcessError) and e.output:
            print(f"\tCommand output:\n{e.output.decode(errors='ignore')}")
        raise
    finally:
        os.chdir(old_cwd)


if __name__ == "__main__":
    build_interface()