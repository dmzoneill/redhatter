#!/usr/bin/env python3
"""
Installation script for Chrome native messaging host on Linux.
This script automatically configures the native messaging manifest with the correct paths.
"""

import json
import sys
from pathlib import Path


def get_chrome_config_dirs():
    """Get Chrome configuration directories for Linux browsers."""
    home = Path.home()

    # Linux Chrome/Chromium config directories
    chrome_dirs = [
        home / ".config" / "google-chrome" / "NativeMessagingHosts",
        home / ".config" / "google-chrome-beta" / "NativeMessagingHosts",
        home / ".config" / "google-chrome-unstable" / "NativeMessagingHosts",
        home / ".config" / "chromium" / "NativeMessagingHosts",
        home / ".config" / "microsoft-edge" / "NativeMessagingHosts",
        home / ".config" / "brave-browser" / "NativeMessagingHosts",
    ]

    return chrome_dirs


def create_manifest(install_path, extension_id=None):
    """Create the native messaging manifest with the correct paths."""
    manifest = {
        "name": "com.redhat.rhotp",
        "description": "Native messaging host for RHOTP Chrome extension",
        "path": str(install_path / "rh-otp" / "native_host.py"),
        "type": "stdio",
        "allowed_origins": [],
    }

    if extension_id:
        manifest["allowed_origins"] = [f"chrome-extension://{extension_id}/"]
    else:
        # Add placeholder that user needs to replace
        manifest["allowed_origins"] = ["chrome-extension://YOUR_EXTENSION_ID_HERE/"]

    return manifest


def install_native_host(install_path=None, extension_id=None, browsers=None):
    """Install native messaging host for Chrome-based browsers on Linux."""

    # Check platform
    if not sys.platform.startswith("linux"):
        print(
            f"❌ Error: This script only supports Linux. "
            f"Detected platform: {sys.platform}"
        )
        return False

    # Use current directory if no install path provided
    if install_path is None:
        install_path = Path(__file__).parent.absolute()
    else:
        install_path = Path(install_path).absolute()

    print(f"📦 Installing native messaging host from: {install_path}")

    # Verify native_host.py exists
    native_host_path = install_path / "rh-otp" / "native_host.py"
    if not native_host_path.exists():
        print(f"❌ Error: {native_host_path} not found!")
        print("Make sure you're running this from the project root directory.")
        return False

    # Make native host executable
    native_host_path.chmod(0o755)

    # Create manifest
    manifest = create_manifest(install_path, extension_id)

    # Get Chrome directories
    chrome_dirs = get_chrome_config_dirs()
    if browsers:
        # Filter to only specified browsers
        chrome_dirs = [
            d for d in chrome_dirs if any(browser in str(d) for browser in browsers)
        ]

    installed_count = 0

    for chrome_dir in chrome_dirs:
        if chrome_dir.exists() or any(chrome_dir.parents):
            try:
                # Create directory if it doesn't exist
                chrome_dir.mkdir(parents=True, exist_ok=True)

                # Write manifest
                manifest_path = chrome_dir / "com.redhat.rhotp.json"
                with open(manifest_path, "w") as f:
                    json.dump(manifest, f, indent=2)

                print(f"✅ Installed to: {manifest_path}")
                installed_count += 1

            except Exception as e:
                print(f"⚠️  Failed to install to {chrome_dir}: {e}")

    if installed_count == 0:
        print("❌ No Chrome/Chromium installations found or accessible.")
        print("You may need to create the directories manually:")
        for chrome_dir in chrome_dirs[:3]:  # Show first few options
            print(f"   mkdir -p {chrome_dir}")
        return False

    print(f"\n🎉 Successfully installed to {installed_count} browser(s)!")

    if not extension_id:
        print("\n⚠️  IMPORTANT: You need to update the extension ID!")
        print("1. Load the extension in Chrome (Developer mode)")
        print("2. Copy the extension ID from chrome://extensions/")
        print("3. Run this script again with: --extension-id YOUR_EXTENSION_ID")
        print(
            "   OR manually edit the manifest files and replace YOUR_EXTENSION_ID_HERE"
        )

    return True


def uninstall_native_host():
    """Remove the native messaging host from all Chrome directories."""
    chrome_dirs = get_chrome_config_dirs()
    removed_count = 0

    for chrome_dir in chrome_dirs:
        manifest_path = chrome_dir / "com.redhat.rhotp.json"
        if manifest_path.exists():
            try:
                manifest_path.unlink()
                print(f"✅ Removed: {manifest_path}")
                removed_count += 1
            except Exception as e:
                print(f"⚠️  Failed to remove {manifest_path}: {e}")

    if removed_count == 0:
        print("ℹ️  No native messaging hosts found to remove.")
    else:
        print(f"\n🗑️  Removed from {removed_count} location(s).")

    return True


def main():
    """Main function with command line interface."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Install/uninstall Chrome native messaging host for RHOTP"
    )
    parser.add_argument("--path", help="Installation path (default: current directory)")
    parser.add_argument("--extension-id", help="Chrome extension ID")
    parser.add_argument(
        "--browsers",
        nargs="+",
        choices=["chrome", "chromium", "brave", "edge"],
        help="Specific browsers to install for",
    )
    parser.add_argument(
        "--uninstall", action="store_true", help="Uninstall native messaging host"
    )
    parser.add_argument(
        "--list", action="store_true", help="List Chrome configuration directories"
    )

    args = parser.parse_args()

    if args.list:
        print("Chrome configuration directories:")
        for chrome_dir in get_chrome_config_dirs():
            status = "✅ exists" if chrome_dir.exists() else "❌ not found"
            print(f"  {chrome_dir} ({status})")
        return

    if args.uninstall:
        uninstall_native_host()
        return

    success = install_native_host(
        install_path=args.path, extension_id=args.extension_id, browsers=args.browsers
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
