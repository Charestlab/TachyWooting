"""
Wooting Plugin Management Example

This script demonstrates how to install, verify, and uninstall
system plugins required by the Wooting SDK.
"""

from wooting_package.post_install import install_plugins, uninstall_plugins
from wooting_package.wooting_utils import delete_interface
from wooting_package.interface import lib
import os

def check_installation():
    """Check if plugins are installed."""
    print("\n=== Installation Status ===\n")
    
    # Linux paths
    sdk_path = "/usr/local/lib/libwooting_analog_sdk.so"
    plugin_dir = "/usr/local/share/WootingAnalogPlugins"
    
    sdk_exists = os.path.exists(sdk_path)
    plugin_exists = os.path.exists(plugin_dir)
    
    print(f"SDK installed: {'✓' if sdk_exists else '✗'} ({sdk_path})")
    print(f"Plugins installed: {'✓' if plugin_exists else '✗'} ({plugin_dir})")
    
    if sdk_exists and plugin_exists:
        # Test initialization
        try:
            result = lib.wooting_analog_initialise()
            is_init = lib.wooting_analog_is_initialised()
            
            if result >= 0 and is_init:
                print(f"\n✓ SDK functional - {result} device(s) detected")
                lib.wooting_analog_uninitialise()
            else:
                print(f"\n✗ Initialization problem (code: {result})")
        except Exception as e:
            print(f"\n✗ Test error: {e}")
    else:
        print("\n⚠ Incomplete installation")
    
    return sdk_exists and plugin_exists

def example_install():
    """Example plugin installation."""
    print("\n=== Installing Plugins ===\n")
    install_plugins()
    check_installation()

def example_uninstall():
    """Example plugin uninstallation."""
    print("\n=== Uninstalling Plugins ===\n")
    uninstall_plugins()
    check_installation()

def example_full_cleanup():
    """Example complete cleanup (interface + plugins)."""
    print("\n=== Complete Cleanup ===\n")
    print("Removing compiled interface AND system plugins...")
    delete_interface(cleanup_plugins=True)
    check_installation()

def example_interface_only_cleanup():
    """Example interface-only cleanup."""
    print("\n=== Interface Cleanup Only ===\n")
    print("Removing compiled interface (keeping plugins)...")
    delete_interface(cleanup_plugins=False)
    # Plugins remain installed
    check_installation()

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Wooting Plugin Management")
    print("=" * 60)
    
    # Current state
    is_installed = check_installation()
    
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        
        if action == "install":
            example_install()
        elif action == "uninstall":
            example_uninstall()
        elif action == "cleanup-all":
            example_full_cleanup()
        elif action == "cleanup-interface":
            example_interface_only_cleanup()
        else:
            print(f"\nUnknown action: {action}")
            print("\nAvailable actions:")
            print("  install            - Install plugins")
            print("  uninstall          - Uninstall plugins")
            print("  cleanup-all        - Cleanup interface + plugins")
            print("  cleanup-interface  - Cleanup interface only")
    else:
        print("\nUsage:")
        print(f"  python {sys.argv[0]} <action>")
        print("\nAvailable actions:")
        print("  install            - Install plugins")
        print("  uninstall          - Uninstall plugins")
        print("  cleanup-all        - Cleanup interface + plugins")
        print("  cleanup-interface  - Cleanup interface only")
        print("\nExample:")
        print(f"  python {sys.argv[0]} install")
