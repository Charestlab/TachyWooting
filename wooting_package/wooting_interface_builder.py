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
from text_extraction import extract_header_code

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INTERFACE_DIR = os.path.join(CURRENT_DIR, 'interface')
LIBRARIES_DIR = os.path.join(CURRENT_DIR, 'libraries')

system = platform.system()
if system == 'Windows':
    SUBLIBRARY_PATH = os.path.join(LIBRARIES_DIR, 'windows')
    SDK_LIBRARY_NAME = "wooting_analog_sdk"
    WRAPPER_LIBRARY_NAME = "wooting_analog_wrapper"  # Necessary on Windows
elif system == 'Darwin':
    SUBLIBRARY_PATH = os.path.join(LIBRARIES_DIR, 'darwin')
    SDK_LIBRARY_NAME = "wooting_analog_sdk" # Necessary on macOS
    WRAPPER_LIBRARY_NAME = "wooting_analog_wrapper"

elif system == 'Linux':
    SUBLIBRARY_PATH = os.path.join(LIBRARIES_DIR, 'linux')
    SDK_LIBRARY_NAME = "wooting_analog_sdk"
    WRAPPER_LIBRARY_NAME = "wooting_analog_wrapper"

else:
    raise NotImplementedError(f"Unsupported platform: {system}")

COMMON_HEADER_FILENAME = "wooting-analog-common.h"
WRAPPER_HEADER_FILENAME = "wooting-analog-wrapper.h"

def get_platform_config():
    """Returns platform-specific configuration."""
    if system == 'Darwin':  # macOS
        #machine = platfcorm.machine()
        #if machine == 'arm64':
        #    arch_flags = ['-arch', 'arm64']
        #elif machine == 'x86_64':
        #    arch_flags = ['-arch', 'x86_64']
        #else:
        #    arch_flags = ['-arch', 'arm64', '-arch', 'x86_64']

        # Simplified compile arguments for macOS
        compile_args = [
            #*arch_flags,
            #'-v',                  # Verbose mode — tells the compiler to print detailed information during compilation
            #'-Wall',                # Enable most common compiler warnings
            #'-Wextra',              # Extra warnings
            #'-g',                   # debug infos 
            #'-O0',                  # Turn off compiler optimizations
            f'-I{SUBLIBRARY_PATH}', # ACTUALLY NECESSARY
            #'-target', 'arm64-apple-darwin',
            #'-march=armv8-a',
            #'-mtune=native'
        ]

        system_libs = []

    elif system == 'Windows':
        compile_args = [
            '/W4', # Warning level for debugging
            '/Zi', # More debugging info
            '/Od', # A ENLEVER POUR VERSION FINAL, MIEUX POUR DEBUGGER
        ]

        system_libs = [
            'ws2_32',      # Windows Socket API
            'kernel32',    # Windows Kernel API
            'advapi32',    # Windows Advanced API
            'ntdll',       # Windows NT API
            'bcrypt',      # Windows Cryptography API
            'userenv'      # Windows User Environment API
        ]
 
    elif system == 'Linux':
        compile_args = [
            '-Wall',
            '-Wextra',
            '-g',
            '-O0',
            f'-I{SUBLIBRARY_PATH}'
            ]

        system_libs = []

    else:
        raise NotImplementedError(f"Unsupported platform: {system}")

    return {
        'compile_args': compile_args,
        'system_libs': system_libs
    }

def build_interface():
    """Builds the Python interface for the Wooting Analog SDK."""

    print("Building Wooting interface...")
    print(f"Using libraries from: {SUBLIBRARY_PATH}")

    # Check if header files exist
    common_header_path = os.path.join(SUBLIBRARY_PATH, COMMON_HEADER_FILENAME)
    wrapper_header_path = os.path.join(SUBLIBRARY_PATH, WRAPPER_HEADER_FILENAME)

    # Extract code from header files
    common_header_code, wrapper_header_code = extract_header_code(
        common_header_path,
        wrapper_header_path
    )
    
    # Create CFFI builder
    ffi_builder = FFI()

    # Define C declarations for headers
    ffi_builder.cdef(common_header_code)
    ffi_builder.cdef(wrapper_header_code)

    # Get platform-specific configuration
    platform_config = get_platform_config()

    # Configure source and libraries
    ffi_builder.set_source('wooting_interface',
        f"""#include <{WRAPPER_HEADER_FILENAME}>
""",
        libraries=[SDK_LIBRARY_NAME, WRAPPER_LIBRARY_NAME] + platform_config['system_libs'], # Necessary run utils
        library_dirs=[SUBLIBRARY_PATH], # Necessary interface
        extra_compile_args=platform_config['compile_args'], # Necessary to run utils after (darwin)
        extra_link_args=['-Wl,-rpath,' + SUBLIBRARY_PATH] if system in ('Darwin', 'Linux') else [] # Necessary to build interface (darwin)
        )

    try:
        ffi_builder.compile(verbose=True, tmpdir=INTERFACE_DIR)
        print("\nInterface compiled successfully!")

    except Exception as e:
        print(f"\nCompilation error: {str(e)}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Command output: {e.output.decode() if e.output else 'No output'}")
        raise

if __name__ == "__main__":
    build_interface()
    
    
    