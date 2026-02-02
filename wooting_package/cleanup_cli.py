"""
CLI script for cleanup operations that need to avoid auto-setup.

This module is separate from wooting_utils to prevent triggering
automatic post-installation setup when we're trying to clean up.
"""

import os
import sys


def main_delete_interface():
    """CLI entry point for delete_interface command."""
    import argparse
    
    # Parse args first to check if we need to skip setup
    parser = argparse.ArgumentParser(
        description='Clean up Wooting interface and optionally remove system plugins',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  wooting-delete-interface                 # Remove interface only
  wooting-delete-interface --cleanup-plugins  # Remove interface + plugins
        """
    )
    parser.add_argument(
        '--cleanup-plugins',
        action='store_true',
        help='Also remove system-wide installed plugins (requires sudo/admin)'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Additional file to delete'
    )
    
    args = parser.parse_args()
    
    # If cleaning up plugins, skip auto-setup to avoid reinstalling
    if args.cleanup_plugins:
        os.environ['WOOTING_SKIP_SETUP'] = '1'
    
    try:
        # Now safe to import
        from wooting_package.wooting_utils import delete_interface
        
        print("\n[Wooting] Cleaning up interface...")
        if args.cleanup_plugins:
            print("[Wooting] Plugins will also be removed...")
        
        delete_interface(file=args.file, cleanup_plugins=args.cleanup_plugins)
        
        print("[Wooting] Cleanup completed successfully.\n")
    except KeyboardInterrupt:
        print("\n[Wooting] Cleanup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[Wooting] Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up environment variable
        os.environ.pop('WOOTING_SKIP_SETUP', None)


if __name__ == "__main__":
    main_delete_interface()
