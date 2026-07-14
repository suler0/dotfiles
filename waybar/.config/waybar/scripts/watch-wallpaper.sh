#!/bin/bash
while inotifywait -e modify ~/.config/waypaper/config.ini 2>/dev/null; do
    sleep 0.5
    WALLPAPER=$(grep "^wallpaper" ~/.config/waypaper/config.ini | cut -d'=' -f2 | xargs)
    WALLPAPER="${WALLPAPER/#\~/$HOME}"
    if [ -f "$WALLPAPER" ]; then
        ~/.config/wal/apply.sh "$WALLPAPER"
    fi
done
