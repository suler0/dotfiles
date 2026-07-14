#!/bin/bash
WALLPAPER_DIR="$HOME/myfiles/Pictures/Wallpapers"
CURRENT=$(grep "^wallpaper = " ~/.config/waypaper/config.ini | head -1 | cut -d'=' -f2- | xargs)
CURRENT="${CURRENT/#\~/$HOME}"

mapfile -t WALLPAPERS < <(find "$WALLPAPER_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" \) | sort)

TOTAL=${#WALLPAPERS[@]}
CURRENT_INDEX=0

for i in "${!WALLPAPERS[@]}"; do
    if [ "${WALLPAPERS[$i]}" = "$CURRENT" ]; then
        CURRENT_INDEX=$i
        break
    fi
done

NEXT_INDEX=$(( (CURRENT_INDEX + 1) % TOTAL ))
NEXT="${WALLPAPERS[$NEXT_INDEX]}"

~/.config/wal/apply.sh "$NEXT"

sed -i "s|^wallpaper = .*|wallpaper = $NEXT|" ~/.config/waypaper/config.ini
