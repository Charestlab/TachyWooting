"""
Wooting Keyboard Utilities

This module provides utilities for working with Wooting analog keyboards:
- Analog value acquisition and processing
- Keyboard initialization and management
- Keycode conversion and handling
"""

import time
from interface import lib, ffi
import pandas as pd
import os
import numpy as np

"""
Character to Keycode Converter Module

This module provides functionality to convert between keyboard characters and their
corresponding keycodes for Wooting keyboards. It supports both character-to-keycode
and keycode-to-character conversions, including special keys and modifiers.

The module maintains a comprehensive mapping of all supported keys and their
corresponding HID keycodes used by Wooting keyboards.
"""

def convert_char_to_keycode(input_values):
    """
    Convert between characters and keycodes for Wooting keyboards.

    This function performs bidirectional conversion between keyboard characters
    and their corresponding HID keycodes. It supports both individual characters
    and lists of characters/keycodes.

    Args:
        input_values (str or int or list): A single character/keycode or a list of
            characters/keycodes to convert.

    Returns:
        list: A list of converted values. If converting from characters to keycodes,
            returns a list of keycodes. If converting from keycodes to characters,
            returns a list of characters.

    Note:
        The function will print an error message and return None if:
        - A character is not found in the mapping
        - A keycode is not found in the mapping
        - The input type is neither string nor integer
    """
    # Comprehensive mapping of keys to their HID keycodes
    # Format: [key_name, keycode, width, height]
    key_mapping = [
        ['Esc', 41, 1, 1],
        ['', 0, 1, 1],
        ['F1', 58, 1, 1],
        ['F2', 59, 1, 1],
        ['F3', 60, 1, 1],
        ['F4', 61, 1, 1],
        ['F5', 62, 1, 1],
        ['F6', 63, 1, 1],
        ['F7', 64, 1, 1],
        ['F8', 65, 1, 1],
        ['F9', 66, 1, 1],
        ['F10', 67, 1, 1],
        ['F11', 68, 1, 1],
        ['F12', 69, 1, 1],
        ['Prnt', 70, 1, 1],
        ['Pse', 72, 1, 1],
        ['Scrl', 71, 1, 1],
        ['A1', 0, 1, 1],
        ['A2', 0, 1, 1],
        ['A3', 0, 1, 1],
        ['Mode', 0, 1, 1],
        ['`', 53, 1, 1],
        ['1', 30, 1, 1],
        ['2', 31, 1, 1],
        ['3', 32, 1, 1],
        ['4', 33, 1, 1],
        ['5', 34, 1, 1],
        ['6', 35, 1, 1],
        ['7', 36, 1, 1],
        ['8', 37, 1, 1],
        ['9', 38, 1, 1],
        ['0', 39, 1, 1],
        ['-', 45, 1, 1],
        ['=', 46, 1, 1],
        ['<-', 42, 1, 1],
        ['Ins', 73, 1, 1],
        ['Hme', 74, 1, 1],
        ['PgUp', 75, 1, 1],
        ['NumLck', 83, 1, 1],
        ['/', 84, 1, 1],
        ['*', 85, 1, 1],
        ['-', 86, 1, 1],
        ['Tab', 43, 1, 1],
        ['Q', 20, 1, 1],
        ['W', 26, 1, 1],
        ['E', 8, 1, 1],
        ['R', 21, 1, 1],
        ['T', 23, 1, 1],
        ['Y', 28, 1, 1],
        ['U', 24, 1, 1],
        ['I', 12, 1, 1],
        ['O', 18, 1, 1],
        ['P', 19, 1, 1],
        ['[', 47, 1, 1],
        [']', 48, 1, 1],
        ['#', 49, 1, 1],
        ['Del', 76, 1, 1],
        ['End', 77, 1, 1],
        ['PgDn', 78, 1, 1],
        ['7', 95, 1, 1],
        ['8', 96, 1, 1],
        ['9', 97, 1, 1],
        ['+', 87, 1, 2],
        ['Caps', 57, 1, 1],
        ['A', 4, 1, 1],
        ['S', 22, 1, 1],
        ['D', 7, 1, 1],
        ['F', 9, 1, 1],
        ['G', 10, 1, 1],
        ['H', 11, 1, 1],
        ['J', 13, 1, 1],
        ['K', 14, 1, 1],
        ['L', 15, 1, 1],
        [';', 51, 1, 1],
        ['\'', 52, 1, 1],
        ['Enter', 40, 2, 1],
        ['', 0, 1, 1],
        ['', 0, 1, 1],
        ['', 0, 1, 1],
        ['4', 92, 1, 1],
        ['5', 93, 1, 1],
        ['6', 94, 1, 1],
        ['Shift', 225, 1, 1],
        ['Z', 29, 1, 1],
        ['X', 27, 1, 1],
        ['C', 6, 1, 1],
        ['V', 25, 1, 1],
        ['B', 5, 1, 1],
        ['N', 17, 1, 1],
        ['M', 16, 1, 1],
        ['', 54, 1, 1],
        ['.', 55, 1, 1],
        ['/', 56, 1, 1],
        ['Shift', 229, 3, 1],
        ['', 0, 1, 1],
        ['^', 82, 1, 1],
        ['', 0, 1, 1],
        ['1', 89, 1, 1],
        ['', 0, 1, 1],
        ['2', 90, 1, 1],
        ['3', 91, 1, 1],
        ['Enter', 88, 1, 2],
        ['Ctrl', 224, 1, 1],
        ['Win', 227, 1, 1],
        ['Alt', 226, 1, 1],
        ['Space', 44, 7, 1],
        ['Alt', 230, 1, 1],
        ['Win', 231, 1, 1],
        ['Fn', 0, 1, 1],
        ['Ctrl', 228, 1, 1],
        ['<', 80, 1, 1],
        ['v', 81, 1, 1],
        ['>', 79, 1, 1],
        ['0', 98, 2, 1],
        ['.', 99, 1, 1]
    ]
    
    if type(input_values) != list :
        if type(input_values) == str or type(input_values) == int:
            input_values = [input_values]
        else:
            raise TypeError("Input must be a string, integer, or list of strings/integers.")
    
    # Transpose the list for easier access to columns
    key_names, keycodes, widths, heights = zip(*key_mapping)
    converted_values = [None] * len(input_values)

    # Process each input value
    for index, value in enumerate(input_values):
        # Handle string input (character to keycode conversion)
        if isinstance(value, str):
            value_found = False
            for key_index, key_name in enumerate(key_names):
                if key_name.lower() == value.lower():
                    converted_values[index] = keycodes[key_index]
                    value_found = True
                    break

            if not value_found:
                print("Problem, not finding the input value in the key codes list.")
                return

        # Handle integer input (keycode to character conversion)
        elif isinstance(value, int):
            value_found = False
            for key_index, keycode in enumerate(keycodes):
                if keycode == value:
                    converted_values[index] = key_names[key_index]
                    value_found = True
                    break

            if not value_found:
                print("Problem, not finding the input value in the key codes list.")
                return

        # Handle invalid input type
        else:
            print('Please use input_values of type char/string or integer')
            return

    return converted_values

def get_data_directory():
    """
    Get the data directory path based on the operating system.
    Creates the directory if it doesn't exist.
    
    Returns:
        str: Path to the data directory
    """
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(base_path, exist_ok=True)
    return base_path

class WOOTING_ACQUISITION():

    def __init__(self):
        self.trial = 0
        self.parquet_tracking = False
        self.int_analog = False

    def parquet_acquisition(self, name, path, int_analog=1):
        """
        Initialize parquet file for data logging.
        
        Args:
            name (str): Name of the parquet file
            path (str, optional): Full path to the directory where the file will be stored.
                                 If None, uses a 'data' directory in the same folder as the script.
            int_analog (int): 1 for integer mode, 2 for analog mode
        """
        self.parquet_tracking = True
            
        self.parquet_full_path = os.path.join(path, name)

        if int_analog not in [1, 2]:
            raise ValueError("int_analog options for position logging must be either 1 (int) or 2 (analog)")
        self.int_analog = int_analog
    
    def _parquet_logs_(self, collected_data):
        # Convert to DataFrame and append to parquet file
        df = pd.DataFrame(collected_data, columns=['trial', 'key', 'position', 'time_to_threshold'])
       
        # Append mode using fast row group writing
        if os.path.exists(self.parquet_full_path):
            existing_df = pd.read_parquet(self.parquet_full_path)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
        else:
            combined_df = df

        combined_df.to_parquet(self.parquet_full_path, index=False)
            
    def _acquire_raw_values(
        self,
        target_keys,
        threshold=0.1,
        duration_after_threshold=0.5,
        duration_before_threshold=None,
        sampling_interval=1/8000, # Tachyon mode on best Wooting (60HE v2) has a 8000Hz polling 
        verbose=False
    ):
        if isinstance(target_keys, list):
            if any(isinstance(k, str) for k in target_keys):
                target_keys = convert_char_to_keycode(target_keys)
        else:
            raise TypeError("target_keys must be a list of character(s) or integer(s)")

        if threshold <= 0 or threshold > 1:
            raise ValueError("Threshold must be between 0 and 1")
        if duration_after_threshold <= 0:
            raise ValueError("Duration after threshold must be positive")
        if sampling_interval <= 0:
            raise ValueError("Sampling interval must be positive")
        if duration_before_threshold is not None and duration_before_threshold <= 0:
            raise ValueError("Duration before threshold must be positive")

        buffer_pre_threshold = []
        collected_data = []
        triggered = False
        trigger_time_ns = None

        if verbose:
            print(f"Waiting for any key in {target_keys} to exceed threshold {threshold}...")

        while True:
            current_time_ns = time.time_ns()
            snapshot = []

            for code in target_keys:
                value = lib.wooting_analog_read_analog(code)
                snapshot.append({'time_ns': current_time_ns, 'key': code, 'position': value})

            if not triggered:
                for s in snapshot:
                    if s['position'] >= threshold:
                        trigger_time_ns = current_time_ns
                        triggered = True
                        if verbose:
                            char = convert_char_to_keycode([s['key']])[0]
                            print(f"\nThreshold reached on key {s['key']} ({char}) at t = {trigger_time_ns / 1e9:.6f}s")
                        break
                buffer_pre_threshold.extend(snapshot)

            if triggered:
                for s in snapshot:
                    collected_data.append({
                        'trial': self.trial,
                        'key': s['key'],
                        'position': s['position'],
                        'time_to_threshold': (s['time_ns'] - trigger_time_ns) / 1e9
                    })

                if (current_time_ns - trigger_time_ns) / 1e9 >= duration_after_threshold:
                    break

            time.sleep(sampling_interval)

        for s in buffer_pre_threshold:
            time_to_threshold = (s['time_ns'] - trigger_time_ns) / 1e9
            if duration_before_threshold is None or abs(time_to_threshold) <= duration_before_threshold:
                collected_data.append({
                    'trial': self.trial,
                    'key': s['key'],
                    'position': s['position'],
                    'time_to_threshold': time_to_threshold
                })

        collected_data.sort(key=lambda x: x['time_to_threshold'])

        if verbose:
            print(f"\nAcquisition complete ({len(collected_data)} samples captured).")

        return collected_data

    def acquire_analog_values(
        self,
        target_keys,
        threshold=0.1,
        duration_after_threshold=0.5,
        duration_before_threshold=None,
        sampling_interval=1/8000,
        verbose=False
    ):
        if self.parquet_tracking and self.int_analog == 1:
            raise ValueError("Cannot use acquire_analog_values when logging in integer mode (int_analog=1). Use acquire_integer_values instead.")

        collected_data = self._acquire_raw_values(
            target_keys=target_keys,
            threshold=threshold,
            duration_after_threshold=duration_after_threshold,
            duration_before_threshold=duration_before_threshold,
            sampling_interval=sampling_interval,
            verbose=verbose
        )

        if self.parquet_tracking and self.int_analog == 2:
            self._parquet_logs_(collected_data)

        self.trial += 1
        return collected_data

    def acquire_integer_values(
        self,
        target_keys,
        threshold=26,
        duration_after_threshold=0.5,
        duration_before_threshold=None,
        sampling_interval=1/8000,
        verbose=False
    ):
        if self.parquet_tracking and self.int_analog == 2:
            raise ValueError("Cannot use acquire_integer_values when logging in analog mode (int_analog=2). Use acquire_analog_values instead.")

        collected_data = self._acquire_raw_values(
            target_keys=target_keys,
            threshold=threshold/255,
            duration_after_threshold=duration_after_threshold,
            duration_before_threshold=duration_before_threshold,
            sampling_interval=sampling_interval,
            verbose=verbose
        )

        for d in collected_data:
            d['position'] = round(d['position'] * 255)

        if self.parquet_tracking and self.int_analog == 1:
            self._parquet_logs_(collected_data)

        self.trial += 1
        return collected_data
        
def initialize_keyboard(verbose = False):
    """
    Initialize the Wooting keyboard interface.
    
    Args:
        verbose: Enable verbose output with device information
        
    Returns:
        True if initialization successful, False otherwise
    """
    if not lib.wooting_analog_initialise():
        raise ValueError("Error: Failed to initialize Wooting interface")
    
    if not lib.wooting_analog_is_initialised():
        raise ValueError("Error: Interface not properly initialized")

    device_count = lib.wooting_analog_initialise()
    if device_count <= 0:
        raise RuntimeError("No Wooting devices found.")

    buffer = ffi.new("WootingAnalog_DeviceInfo_FFI *[]", device_count)
    lib.wooting_analog_get_connected_devices_info(buffer, device_count)

    if verbose:
        device = buffer[0]
        vendor = f"0x{device.vendor_id:04x}"
        product = f"0x{device.product_id:04x}"
        manufacturer = ffi.string(device.manufacturer_name).decode() if device.manufacturer_name else "Unknown"
        device_name = ffi.string(device.device_name).decode() if device.device_name else "Unknown"
        
        print(f"""
Detected Wooting keyboard:
    - Vendor ID       : {vendor}
    - Product ID      : {product}
    - Device ID       : {device.device_id}
    - Device Type     : {device.device_type}
    - Manufacturer    : {manufacturer}
    - Device Name     : {device_name}
    """)

    return True

def uninitialize_keyboard():
    """Uninitialize the Wooting keyboard interface."""
    lib.wooting_analog_uninitialise()


def wooting_plotting_response_test(target_key, reps=10):
    """Plots the position of time for a key in a certain number of repetitions
    Args:
        target_key (list of one character or int): key being tested
        reps (int, optional): number of repetitions. Defaults to 10.
    """
    import matplotlib.pyplot as plt

    if type(target_key) != list or len(target_key) > 1:
        raise ValueError("target_key must be a list of single character or integer for the test")

    acqui = WOOTING_ACQUISITION()
    acqui.parquet_acquisition(path = os.getcwd(), name="tracking.parquet", int_analog=1)
    
    for i in range(reps):
        print(f"\r{i+1} : Press {target_key}")
        data = acqui.acquire_integer_values(duration_before_threshold=0.5, target_keys=target_key)
        times = [d['time_to_threshold'] for d in data]
        positions = [d['position'] for d in data]
        plt.plot(times, positions, label=f'Trial {i+1}')

    plt.xlabel('Time to Threshold (s)')
    plt.ylabel('Position')
    plt.title('Key Response Over Time')
    plt.legend()
    plt.savefig("plot.png")
    
# Test

#2) Initialize the keyboard    
initialize_keyboard(verbose=True)
acqui = WOOTING_ACQUISITION()
#acqui.parquet_acquisition(path = os.getcwd(), name = "tracking.parquet", int_analog=2)    

wooting_plotting_response_test(target_key=['z'])
#acqui.acquire_analog_values(target_keys=['z'])
uninitialize_keyboard()

