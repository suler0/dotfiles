#!/bin/bash
player=$(playerctl -l 2>/dev/null | head -1)
if [ -n "$player" ]; then
    echo '{"text": "⏮", "class": "visible"}'
else
    echo '{"text": "", "class": "hidden"}'
fi
