#!/bin/bash
MODE_FILE="$HOME/.cache/waybar-ycal/date_mode"
mkdir -p "$(dirname "$MODE_FILE")"
CURRENT=$(cat "$MODE_FILE" 2>/dev/null || echo "gregorian")
if [[ "$CURRENT" == "hijri" ]]; then
    echo -n "gregorian" > "$MODE_FILE"
else
    echo -n "hijri" > "$MODE_FILE"
fi
pkill -RTMIN+8 waybar
