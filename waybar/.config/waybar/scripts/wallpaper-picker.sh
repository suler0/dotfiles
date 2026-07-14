#!/bin/bash

WALLPAPER_DIR="$HOME/Pictures/Wallpapers"

selected=$(find "$WALLPAPER_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" \) -printf "%f\n" | \
    rofi -dmenu -p "🖼 Wallpaper")

if [ -n "$selected" ]; then
    ~/.config/wal/apply.sh "$WALLPAPER_DIR/$selected"
fi
