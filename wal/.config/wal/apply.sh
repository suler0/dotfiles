#!/bin/bash

# حوّل ~ لمسار كامل
WALLPAPER="${1/#\~/$HOME}"

# تطبيق pywal
wal -i "$WALLPAPER" -n
source ~/.cache/wal/colors.sh
COLOR1=$(echo $color1 | tr -d '#')
COLOR2=$(echo $color2 | tr -d '#')
hyprctl eval "hl.config({ general = { col = { active_border = '0xff${COLOR1}', inactive_border = '0x99${COLOR2}' } } })"

# تغيير wallpaper الـ desktop
awww img "$WALLPAPER" --transition-type grow --transition-pos center

# تحديث hyprlock
sed -i "0,/path = .*/s|path = .*|path = $WALLPAPER|" ~/.config/hypr/hyprlock.conf

# إعادة تشغيل waybar
killall waybar && waybar &disown

# إعادة تشغيل swaync
killall swaync && swaync &disown

~/skripts/wal-to-omarchy-ycal.sh
systemctl --user restart waybar-ycal.service
echo "✓ Done"
