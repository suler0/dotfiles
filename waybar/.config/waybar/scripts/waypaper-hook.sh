#!/bin/bash
sleep 0.5
WALLPAPER=$(grep "^wallpaper = " ~/.config/waypaper/config.ini | head -1 | cut -d'=' -f2- | xargs)
WALLPAPER="${WALLPAPER/#\~/$HOME}"
~/.config/wal/apply.sh "$WALLPAPER"
