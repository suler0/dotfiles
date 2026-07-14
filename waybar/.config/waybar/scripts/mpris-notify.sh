#!/bin/bash
playerctl --follow metadata --format '{{status}} {{title}}' | while read line; do
    status=$(echo "$line" | awk '{print $1}')
    title=$(echo "$line" | cut -d' ' -f2-)
    
    if [ "$status" = "Playing" ]; then
        notify-send -i media-playback-start "Now Playing" "$title" -t 3000
    elif [ "$status" = "Paused" ]; then
        notify-send -i media-playback-pause "Paused" "$title" -t 2000
    fi
done
