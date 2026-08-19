#!/bin/bash
pkill -USR1 waybar

PIDFILE="$HOME/.cache/floating-clock.pid"
mkdir -p "$HOME/.cache"

if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    kill "$(cat "$PIDFILE")"
    rm -f "$PIDFILE"
else
    nohup python3 "$HOME/.config/floating-clock/clock.py" >/dev/null 2>&1 &
    echo $! > "$PIDFILE"
fi
