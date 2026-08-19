#!/bin/bash

WALLPAPER="${1/#\~/$HOME}"

wal -i "$WALLPAPER" -n
wpg -s "$WALLPAPER"
source ~/.cache/wal/colors.sh
COLOR1=$(echo $color1 | tr -d '#')
COLOR2=$(echo $color2 | tr -d '#')
hyprctl eval "hl.config({ general = { col = { active_border = '0xff${COLOR1}', inactive_border = '0x99${COLOR2}' } } })"

awww img "$WALLPAPER" --transition-type wipe --transition-duration 1.3 --transition-angle 45 --transition-fps 120

sed -i "0,/path = .*/s|path = .*|path = $WALLPAPER|" ~/.config/hypr/hyprlock.conf

killall waybar && waybar &disown

killall swaync && swaync &disown

~/skripts/wal-to-omarchy-ycal.sh
systemctl --user restart waybar-ycal.service
nohup ~/.config/wal/update-cursor.sh > /tmp/wal-cursor.log 2>&1 & disown
echo "✓ Done"
