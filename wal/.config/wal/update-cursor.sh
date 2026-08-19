#!/bin/bash

# Path to the bibata_cursor repo
REPO_DIR="$HOME/bibata_cursor"
THEME_NAME="Bibata-Modern-Pywal"

# Lock file to prevent multiple runs
LOCKFILE="/tmp/wal-cursor.lock"

# Check if already running
if [ -f "$LOCKFILE" ]; then
    echo "Cursor update already running, skipping"
    exit 0
fi

# Create lock file
touch "$LOCKFILE"

# Clean up lock on exit
trap 'rm -f "$LOCKFILE"' EXIT

# Read pywal colors
color1=$(cat ~/.cache/wal/colors.json | grep -o '"color1": "[^"]*"' | cut -d'"' -f4)
foreground=$(cat ~/.cache/wal/colors.json | grep -o '"foreground": "[^"]*"' | cut -d'"' -f4)
background=$(cat ~/.cache/wal/colors.json | grep -o '"background": "[^"]*"' | cut -d'"' -f4)

echo "Updating cursor with colors: $color1, $foreground, $background"

cd "$REPO_DIR" || exit 1

# Remove old build directory
rm -rf ./pywal-cursor

# Restore original render.json
cp config/render.json.backup config/render.json

# Update render.json with current pywal colors
python3 -c "
import json

with open('config/render.json', 'r') as f:
    data = json.load(f)

data['$THEME_NAME'] = {
    'desc': 'pywal-colored modern Bibata cursors',
    'dir': 'svg/modern',
    'colors': [
        {'match': '#00FF00', 'replace': '$color1'},
        {'match': '#0000FF', 'replace': '$foreground'},
        {'match': '#FF0000', 'replace': '$background'}
    ]
}

with open('config/render.json', 'w') as f:
    json.dump(data, f, indent=4)
"

# Build the theme
python src/cursor_utils.py --hypr --theme "$THEME_NAME" --out-dir ./pywal-cursor

# Install the theme
cp -r "./pywal-cursor/$THEME_NAME" ~/.local/share/icons/

# Apply the theme
hyprctl setcursor "$THEME_NAME" 24
gsettings set org.gnome.desktop.interface cursor-theme "$THEME_NAME" 2>/dev/null

echo "Cursor updated to $THEME_NAME"
