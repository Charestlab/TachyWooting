#!/bin/bash

set -e  # Exit on first error

# Define rule target
RULES_FILE="/etc/udev/rules.d/99-wooting.rules"
VENDOR_ID="31e3"

echo "Looking for Wooting device with idVendor=$VENDOR_ID..."

# Try to find the first matching hidraw device
DEVICE_PATH=$(for dev in /dev/hidraw*; do
  udevadm info -a -n "$dev" | grep -q "ATTRS{idVendor}==\"$VENDOR_ID\"" && echo "$dev" && break
done)

if [[ -z "$DEVICE_PATH" ]]; then
  echo "No Wooting device found. Make sure the keyboard is connected."
  exit 1
fi

echo "Device found at $DEVICE_PATH"

# Get the product ID
ID_PRODUCT=$(udevadm info -a -n "$DEVICE_PATH" | grep 'ATTRS{idProduct}' | head -n1 | sed -E 's/.*"([0-9a-fA-F]+)".*/\1/')

echo "Detected idProduct: $ID_PRODUCT"

# Build the rule string
RULE="KERNEL==\"hidraw*\", SUBSYSTEM==\"hidraw\", ATTRS{idVendor}==\"$VENDOR_ID\", ATTRS{idProduct}==\"$ID_PRODUCT\", MODE=\"0666\""

# Check if rule already exists
if grep -Fq "$RULE" "$RULES_FILE" 2>/dev/null; then
    echo "Rule already exists in $RULES_FILE"
else
    echo "Adding new udev rule..."
    echo "$RULE" | sudo tee "$RULES_FILE" > /dev/null
fi

# Reload and apply rules
echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

sleep 1

# Show current permissions
echo "Current permissions for $DEVICE_PATH:"
ls -l "$DEVICE_PATH"

echo "Done. If the device is still not accessible, try unplugging and replugging the keyboard."