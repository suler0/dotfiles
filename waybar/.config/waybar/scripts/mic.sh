#!/bin/bash
MUTED=$(pactl get-source-mute @DEFAULT_SOURCE@ 2>/dev/null | awk '{print $2}')
if [ "$MUTED" = "yes" ]; then
    echo '{"text": "", "class": "muted", "tooltip": "Mic muted - click to unmute"}'
else
    echo '{"text": "", "class": "unmuted", "tooltip": "Mic on - click to mute"}'
fi
