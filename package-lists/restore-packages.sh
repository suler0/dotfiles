#!/usr/bin/env bash
# Reinstall all packages from the saved lists.
# Run official packages first, then AUR (needs paru installed).
set -e
cd "$(dirname "$0")"

echo "Installing official packages..."
sudo pacman -S --needed - < official-packages.txt

echo "Installing AUR packages (requires paru)..."
paru -S --needed - < aur-packages.txt

echo "Done."
