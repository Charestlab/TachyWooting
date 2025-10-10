"""
Wooting Interface Builder

This scripts build the Python interface for the SDK Wooting Analog using CFFI.
Components:
-----------
wooting-analog-sdk: The core Analog SDK which handles loading of plugins. This is installed systemwide and is updated separately.
wooting-analog-common: This library contains all common Analog SDK definitions which are used by every part.
wooting-analog-plugin-dev: This library contains all common elements needed for designing plugins. This re-exports wooting-analog-common, so it is not required for plugins to separately depend on wooting-analog-common.
wooting-analog-wrapper: This is the SDK wrapper which is what Applications should use to communicate with the SDK. The linked dll should be shipped with the application using it.
wooting-analog-test-plugin: Dummy plugin which uses shared memory so other processes can control the output of the plugin. This is used for unit testing of the SDK and allows the wooting-analog-virtual-kb to work.
wooting-analog-virtual-kb: Virtual Keyboard using GTK which allows to set the analog value of all the keys through the dummy plugin. This allows you to test an Analog SDK implementation without an analog device.
wooting-analog-sdk-updater: Updater tool to update the Analog SDK from Github releases.

Headers:
--------
wooting-analog-wrapper.h: This is the header which includes everything that you need to use the SDK. (This uses wooting-analog-common.h which defines all relevant enums & structs)
wooting-analog-common.h: This defines all common enums, headers & structs which are needed by plugins & SDK users
wooting-analog-plugin-dev.h: This includes wooting-analog-common.h & additional functions which are obtained from statically linking to the analog-sdk-common library. (FOR USE WITH PLUGINS)
plugin.h: This is the header which plugins should use to define all functions that need to be exported for a plugin to work

Dependencies:
------------
- CFFI: For building the Python interface
- Platform-specific SDK libraries (dll/dylib/so)
- Platform-specific header files

Usage:
------
Run this script to build the Python interface for the Wooting Analog SDK.
The script will automatically detect the platform and use the appropriate build settings.
"""

import os
import platform
import subprocess
from cffi import FFI
from wooting_package.text_extraction import extract_header_code

CURRENT_DIR   = os.path.dirname(os.path.abspath(__file__))
INTERFACE_DIR = os.path.join(CURRENT_DIR, 'interface')
LIBRARIES_DIR = os.path.join(CURRENT_DIR, 'libraries')

system = platform.system()
if system == 'Windows':
    SUBLIBRARY_PATH = os.path.join(LIBRARIES_DIR, 'windows')
    SDK_LIBRARY_NAME = "wooting_analog_sdk"
    WRAPPER_LIBRARY_NAME = "wooting_analog_wrapper"
elif system == 'Darwin':
    SUBLIBRARY_PATH = os.path.join(LIBRARIES_DIR, 'darwin')
    SDK_LIBRARY_NAME = "wooting_analog_sdk"
    WRAPPER_LIBRARY_NAME = "wooting_analog_wrapper"
elif system == 'Linux':
    SUBLIBRARY_PATH = os.path.join(LIBRARIES_DIR, 'linux')
    SDK_LIBRARY_NAME = "wooting_analog_sdk"
    WRAPPER_LIBRARY_NAME = "wooting_analog_wrapper"
else:
    raise NotImplementedError(f"Unsupported platform: {system}")

COMMON_HEADER_FILENAME  = "wooting-analog-common.h"
WRAPPER_HEADER_FILENAME = "wooting-analog-wrapper.h"


def get_platform_config():
    """Returns platform-specific compile/link configuration."""
    if system == 'Darwin':  # macOS
        # Optionnel : verrouiller l’architecture (décommente si utile)
        # machine = platform.machine()
        # if machine == 'arm64':
        #     arch_flags = ['-arch', 'arm64']
        # elif machine == 'x86_64':
        #     arch_flags = ['-arch', 'x86_64']
        # else:
        #     arch_flags = ['-arch', 'arm64', '-arch', 'x86_64']

        compile_args = [
            # *arch_flags,
            f'-I{SUBLIBRARY_PATH}',  # headers
        ]
        # RPATH relatif : la .so chargera la dylib depuis ../libraries/darwin
        extra_link_args = [ '-Wl,-rpath,@loader_path/../libraries/darwin' ]
        system_libs = []

    elif system == 'Linux':
        compile_args = [
            '-Wall', '-Wextra', '-g', '-O0',
            f'-I{SUBLIBRARY_PATH}',
        ]
        # ELF: $ORIGIN ≈ emplacement du binaire chargé
        extra_link_args = [ '-Wl,-rpath,$ORIGIN/../libraries/linux' ]
        system_libs = []

    else:  # Windows
        compile_args = [
            '/W4',  # warnings
            '/Zi',  # debug info
            '/Od',  # no opt (dev)
        ]
        extra_link_args = []  # RPATH non utilisé sous Windows
        system_libs = [
            'ws2_32', 'kernel32', 'advapi32', 'ntdll', 'bcrypt', 'userenv'
        ]

    return {
        'compile_args': compile_args,
        'extra_link_args': extra_link_args,
        'system_libs': system_libs,
    }


def build_interface():
    """Builds the Python interface for the Wooting Analog SDK."""
    print("Building Wooting interface...")
    print(f"Using libraries from: {SUBLIBRARY_PATH}")

    # Ensure folders
    os.makedirs(INTERFACE_DIR, exist_ok=True)

    # Headers presence
    common_header_path  = os.path.join(SUBLIBRARY_PATH, COMMON_HEADER_FILENAME)
    wrapper_header_path = os.path.join(SUBLIBRARY_PATH, WRAPPER_HEADER_FILENAME)
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

    cfg = get_platform_config()

    # Module name kept as 'wooting_interface' (import via: from interface import lib, ffi)
    ffib.set_source(
        'wooting_interface',
        f'#include <{WRAPPER_HEADER_FILENAME}>\n',
        libraries=[SDK_LIBRARY_NAME, WRAPPER_LIBRARY_NAME] + cfg['system_libs'],
        library_dirs=[SUBLIBRARY_PATH],
        extra_compile_args=cfg['compile_args'],
        extra_link_args=cfg['extra_link_args'],
    )

    # Compile into the interface/ directory so import path stays the same
    # cffi place le .so dans le CWD: on se place donc dans INTERFACE_DIR.
    old_cwd = os.getcwd()
    try:
        os.chdir(INTERFACE_DIR)
        ffib.compile(verbose=True)
        print("\nInterface compiled successfully!")
    except Exception as e:
        print(f"\nCompilation error: {e}")
        if isinstance(e, subprocess.CalledProcessError) and e.output:
            print(f"Command output:\n{e.output.decode(errors='ignore')}")
        raise
    finally:
        os.chdir(old_cwd)

    if system == 'Darwin':
        print(
            "\n[macOS] Si vous voyez encore 'Library not loaded' ou 'library load disallowed by system policy', "
            "supprimez la quarantaine et signez ad-hoc la dylib :\n"
            f'  xattr -dr com.apple.quarantine "{SUBLIBRARY_PATH}"\n'
            f'  codesign --force --sign - "{os.path.join(SUBLIBRARY_PATH, "libwooting_analog_sdk.dylib")}"\n'
            "Puis relancez Python."
        )


if __name__ == "__main__":
    build_interface()
