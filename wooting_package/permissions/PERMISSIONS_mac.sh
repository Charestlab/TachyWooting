#!/bin/bash
set -euo pipefail

# Detect architecture (arm64 or x86_64)
ARCH="$(uname -m)"

# BASE_DIR = script directory (script is in permissions/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Go up one level to access the package root
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Path to libraries
LIB_DIR="$BASE_DIR/libraries/darwin/$ARCH"

echo "Removing quarantine from: $LIB_DIR"
if [ -d "$LIB_DIR" ]; then
  xattr -dr com.apple.quarantine "$LIB_DIR" || true
else
  echo "Directory not found: $LIB_DIR"
  exit 0
fi

# Sign .dylib files only if present
SDK="$LIB_DIR/libwooting_analog_sdk.dylib"
WRAPPER="$LIB_DIR/libwooting_analog_wrapper.dylib"

echo "Signing .dylib files (best-effort)…"
if [ -f "$SDK" ]; then
  codesign --force --sign - "$SDK" || echo "codesign failed for $SDK (non-fatal)"
else
  echo "Missing: $SDK"
fi

if [ -f "$WRAPPER" ]; then
  codesign --force --sign - "$WRAPPER" || echo "codesign failed for $WRAPPER (non-fatal)"
else
  echo "Missing: $WRAPPER"
fi

echo "Gatekeeper permissions applied for $ARCH."
