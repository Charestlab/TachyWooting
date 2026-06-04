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
import platform
import subprocess
import sysconfig

from cffi import FFI

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INTERFACE_DIR = os.path.join(CURRENT_DIR, "interface")
LIBRARIES_DIR = os.path.join(CURRENT_DIR, "libraries")

SDK_LIBRARY_NAME = "wooting_analog_sdk"
WRAPPER_LIBRARY_NAME = "wooting_analog_wrapper"
COMMON_HEADER_FILENAME = "wooting-analog-common.h"
WRAPPER_HEADER_FILENAME = "wooting-analog-wrapper.h"

SYSTEM = platform.system().lower()


def extract_header_code(common_header_path, wrapper_header_path):
    comment_chars = ("#", "/", "*")

    with open(common_header_path, encoding="utf-8") as file:
        common_header_content = file.readlines()
    with open(wrapper_header_path, encoding="utf-8") as file:
        wrapper_header_content = file.readlines()

    extracted_code_common = []
    for line in common_header_content:
        stripped_line = line.lstrip()
        if stripped_line and stripped_line[0] not in comment_chars and "extern" not in stripped_line:
            extracted_code_common.append(line)

    extracted_code_wrapper = []
    for line in wrapper_header_content:
        stripped_line = line.lstrip()
        if stripped_line and stripped_line[0] not in comment_chars and "extern" not in stripped_line:
            extracted_code_wrapper.append(line)

    return "".join(extracted_code_common), "".join(extracted_code_wrapper)


def _norm_arch():
    """Normalize architecture names we care about."""
    arch = platform.machine().lower()
    if arch in ("arm64", "aarch64", "arm64e"):
        return "arm64"
    if arch in ("x86_64", "amd64"):
        return "x86_64"
    raise RuntimeError(f"Unsupported CPU architecture: {arch}")


def get_library_dir():
    """Return the correct library directory based on platform and architecture."""
    if SYSTEM not in {"darwin", "linux", "windows"}:
        raise RuntimeError(f"Unsupported platform: {SYSTEM}")

    # macOS ships separate SDK binaries per architecture; Linux/Windows use one folder.
    base_dir = os.path.join(LIBRARIES_DIR, SYSTEM)
    if SYSTEM == "darwin":
        arch = _norm_arch()
        return os.path.join(base_dir, arch)
    return base_dir


def get_platform_config(library_dir):
    """Return platform-specific compile/link configuration."""
    arch = _norm_arch()
    # CFFI compiles a Python extension, so the Python C headers must be discoverable.
    py_inc = sysconfig.get_config_var("INCLUDEPY") or sysconfig.get_paths()["include"]

    if SYSTEM == "darwin":
        compile_args = [
            f"-I{library_dir}",
        ]
        # @loader_path resolves relative to the compiled extension at runtime.
        extra_link_args = [
            f"-Wl,-rpath,@loader_path/../libraries/darwin/{arch}",
        ]
        system_libs = []

    elif SYSTEM == "linux":
        compile_args = [
            "-Wall",
            "-Wextra",
            "-O2",
            f"-I{library_dir}",
            f"-I{py_inc}",
        ]
        # $ORIGIN resolves relative to the compiled extension on ELF platforms.
        extra_link_args = [
            "-Wl,-rpath,$ORIGIN/../libraries/linux",
        ]
        system_libs = []

    else:
        compile_args = [
            "/W4",
            "/O2",
        ]
        extra_link_args = []
        system_libs = [
            "ws2_32",
            "kernel32",
            "advapi32",
            "ntdll",
            "bcrypt",
            "userenv",
        ]

    return {
        "compile_args": compile_args,
        "extra_link_args": extra_link_args,
        "system_libs": system_libs,
    }


def create_ffibuilder(module_name: str = "wooting_interface") -> FFI:
    """Create a CFFI builder for the Wooting Analog SDK wrapper.

    Parameters
    ----------
    module_name : str, default="wooting_interface"
        Name of the generated Python extension module.

    Returns
    -------
    cffi.FFI
        Configured CFFI builder.

    Raises
    ------
    FileNotFoundError
        If required Wooting SDK headers are missing for the current platform.
    """
    library_dir = get_library_dir()

    # Verify header presence
    common_header_path = os.path.join(library_dir, COMMON_HEADER_FILENAME)
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

    # Keep the generated module name stable: interface/__init__.py imports this exact name.
    ffib.set_source(
        module_name,
        f"#include <{WRAPPER_HEADER_FILENAME}>\n",
        libraries=[SDK_LIBRARY_NAME, WRAPPER_LIBRARY_NAME] + cfg["system_libs"],
        library_dirs=[library_dir],
        extra_compile_args=cfg["compile_args"],
        extra_link_args=cfg["extra_link_args"],
    )
    return ffib


ffibuilder = create_ffibuilder("wooting_package.interface.wooting_interface")


def build_interface():
    """Compile the Wooting CFFI extension in the package interface directory.

    Returns
    -------
    None

    Raises
    ------
    Exception
        Propagates compiler, linker, or CFFI errors so callers can present a
        clear installation failure.
    """
    print("\n\nBuilding Wooting interface...")
    print(f"\n\tUsing libraries from: {get_library_dir()}")
    os.makedirs(INTERFACE_DIR, exist_ok=True)
    ffib = create_ffibuilder("wooting_interface")

    old_cwd = os.getcwd()
    try:
        # CFFI writes generated .c/.o/.so artifacts to the current working directory.
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
