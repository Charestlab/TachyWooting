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
_LIBRARIES_DIR = os.path.join(_PKG_DIR, "libraries")

# Any file produced by cffi will match this pattern
_COMPILED_GLOB = os.path.join(_INTERFACE_DIR, "wooting_interface*")

# Plugin directory paths per platform
_PLUGIN_DIRS = {
    "Darwin": "/usr/local/share/WootingAnalogPlugins",
    "Linux": "/usr/local/share/WootingAnalogPlugins",
    "Windows": r"C:\Program Files\WootingAnalogPlugins"
}


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
    
    NOTE: This is called during post-installation, not on every import.
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


def install_plugins() -> None:
    r"""
    Install Wooting SDK and plugins to system directories.
    This is required for the SDK to detect and initialize devices.
    
    Installation structure:
    - SDK library: /usr/local/lib/ (Linux/macOS)
    - Plugins: /usr/local/share/WootingAnalogPlugins/ (Linux/macOS)
    - Windows: C:\Program Files\WootingAnalogPlugins\
    
    Requires sudo/admin privileges on Linux/macOS.
    """
    system = platform.system()
    
    if system not in _PLUGIN_DIRS:
        print(f"[Wooting] Plugin installation not supported on {system}")
        return
    
    plugin_dir = _PLUGIN_DIRS[system]
    
    # Determine source directories and files based on platform
    if system == "Darwin":
        arch = platform.machine()  # 'arm64' or 'x86_64'
        source_dir = os.path.join(_LIBRARIES_DIR, "darwin", arch)
        sdk_dest = "/usr/local/lib"
        plugin_files = ["libwooting_analog_plugin.dylib"]
        sdk_files = ["libwooting_analog_sdk.dylib"]
    elif system == "Linux":
        source_dir = os.path.join(_LIBRARIES_DIR, "linux")
        sdk_dest = "/usr/local/lib"
        plugin_files = ["libwooting_analog_plugin.so"]
        sdk_files = ["libwooting_analog_sdk.so"]
    elif system == "Windows":
        source_dir = os.path.join(_LIBRARIES_DIR, "windows")
        plugin_dir = r"C:\\Program Files\\WootingAnalogPlugins"
        sdk_dest = plugin_dir  # On Windows, everything goes in the same place
        plugin_files = ["wooting_analog_plugin.dll"]
        sdk_files = ["wooting_analog_sdk.dll"]
    else:
        return
    
    # Check if source files exist
    all_files = plugin_files + sdk_files
    missing_files = []
    for file_name in all_files:
        file_path = os.path.join(source_dir, file_name)
        if not os.path.exists(file_path):
            missing_files.append(file_name)
    
    if missing_files:
        print(f"[Wooting] Warning: Required files not found: {', '.join(missing_files)}")
        return
    
    try:
        # Install SDK to /usr/local/lib (or system lib directory)
        print(f"[Wooting] Installing SDK to {sdk_dest}...")
        
        if system in ["Linux", "Darwin"]:
            # Create lib directory if needed
            if not os.path.exists(sdk_dest):
                subprocess.run(["sudo", "mkdir", "-p", sdk_dest], check=True)
            
            # Copy SDK files
            for sdk_file in sdk_files:
                source_path = os.path.join(source_dir, sdk_file)
                dest_path = os.path.join(sdk_dest, sdk_file)
                subprocess.run(["sudo", "cp", source_path, dest_path], check=True)
                subprocess.run(["sudo", "chmod", "755", dest_path], check=True)
            
            # Run ldconfig to update library cache
            subprocess.run(["sudo", "ldconfig"], check=False)
        
        # Install plugins to plugin directory
        print(f"[Wooting] Installing plugins to {plugin_dir}...")
        
        if not os.path.exists(plugin_dir):
            if system in ["Linux", "Darwin"]:
                subprocess.run(["sudo", "mkdir", "-p", plugin_dir], check=True)
            else:
                os.makedirs(plugin_dir, exist_ok=True)
        
        # Copy plugin files
        for plugin_file in plugin_files:
            source_path = os.path.join(source_dir, plugin_file)
            dest_path = os.path.join(plugin_dir, plugin_file)
            
            if system in ["Linux", "Darwin"]:
                subprocess.run(["sudo", "cp", source_path, dest_path], check=True)
                subprocess.run(["sudo", "chmod", "755", dest_path], check=True)
            else:
                import shutil
                shutil.copy2(source_path, dest_path)
        
        print(f"[Wooting] SDK and plugins installed successfully.")
        
    except subprocess.CalledProcessError as e:
        print(f"[Wooting] Failed to install (may require sudo): {e}")
    except Exception as e:
        print(f"[Wooting] Installation error: {e}")


def uninstall_plugins() -> None:
    """
    Remove installed Wooting SDK and plugins from system directories.
    This is useful for cleanup and testing.
    
    Removes:
    - SDK library from /usr/local/lib/ (Linux/macOS)
    - Plugin directory /usr/local/share/WootingAnalogPlugins/
    - Udev rules /etc/udev/rules.d/70-wooting.rules (Linux)
    
    Requires sudo/admin privileges on Linux/macOS.
    """
    system = platform.system()
    
    if system not in _PLUGIN_DIRS:
        print(f"[Wooting] Plugin uninstallation not supported on {system}")
        return
    
    plugin_dir = _PLUGIN_DIRS[system]
    
    # Determine SDK location and files based on platform
    if system == "Darwin":
        sdk_dir = "/usr/local/lib"
        sdk_files = ["libwooting_analog_sdk.dylib"]
    elif system == "Linux":
        sdk_dir = "/usr/local/lib"
        sdk_files = ["libwooting_analog_sdk.so"]
    elif system == "Windows":
        sdk_dir = plugin_dir  # On Windows, everything is in the same place
        sdk_files = ["wooting_analog_sdk.dll"]
    else:
        return
    
    try:
        # Remove plugins directory
        if os.path.exists(plugin_dir):
            print(f"[Wooting] Removing plugins from {plugin_dir}...")
            if system in ["Linux", "Darwin"]:
                subprocess.run(["sudo", "rm", "-rf", plugin_dir], check=True)
            else:
                import shutil
                shutil.rmtree(plugin_dir, ignore_errors=True)
        
        # Remove SDK files from lib directory (Linux/macOS only)
        if system in ["Linux", "Darwin"]:
            print(f"[Wooting] Removing SDK from {sdk_dir}...")
            for sdk_file in sdk_files:
                sdk_path = os.path.join(sdk_dir, sdk_file)
                if os.path.exists(sdk_path):
                    subprocess.run(["sudo", "rm", sdk_path], check=True)
            
            # Update library cache
            subprocess.run(["sudo", "ldconfig"], check=False)
        
        # Remove udev rules on Linux
        if system == "Linux":
            udev_rules = "/etc/udev/rules.d/70-wooting.rules"
            if os.path.exists(udev_rules):
                print(f"[Wooting] Removing udev rules from {udev_rules}...")
                try:
                    subprocess.run(["sudo", "rm", udev_rules], check=True)
                    subprocess.run(["sudo", "udevadm", "control", "--reload-rules"], check=False)
                    print("[Wooting] Udev rules removed successfully.")
                except subprocess.CalledProcessError as e:
                    print(f"[Wooting] Failed to remove udev rules: {e}")
        
        print(f"[Wooting] SDK and plugins removed successfully.")
        
    except subprocess.CalledProcessError as e:
        print(f"[Wooting] Failed to remove (may require sudo): {e}")
    except Exception as e:
        print(f"[Wooting] Removal error: {e}")


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
    
    # 3) Install plugins (required for SDK to work)
    install_plugins()
    
    # 4) Apply macOS Gatekeeper fixups (best-effort), now that files likely exist
    apply_macos_gatekeeper()

    print("\n[Wooting] Post-installation setup completed.\n")


def main_install_plugins():
    """CLI entry point for installing plugins."""
    try:
        install_plugins()
    except KeyboardInterrupt:
        print("\n[Wooting] Installation cancelled by user.")
    except Exception as e:
        print(f"\n[Wooting] Installation failed: {e}")
        import sys
        sys.exit(1)


def main_uninstall_plugins():
    """CLI entry point for uninstalling plugins."""
    try:
        uninstall_plugins()
    except KeyboardInterrupt:
        print("\n[Wooting] Uninstallation cancelled by user.")
    except Exception as e:
        print(f"\n[Wooting] Uninstallation failed: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall_plugins()
    else:
        run_post_install()


