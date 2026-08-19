#!/usr/bin/env bash
# Lightweight daemon: decides refresh cadence for custom/prayer-times module
# Sleeps most of the time (near-zero CPU), only ticks every second
# during the final minute before the next prayer.
CACHE_FILE="$HOME/.cache/prayer-times/timings.json"

while true; do
    if [[ -f "$CACHE_FILE" ]]; then
        NOW_SEC=$(date +%s)
        NEXT_SEC=999999999999

        for T in $(jq -r '.Fajr, .Dhuhr, .Asr, .Maghrib, .Isha' "$CACHE_FILE" 2>/dev/null); do
            T_SEC=$(date -d "$T" +%s 2>/dev/null)
            if [[ -n "$T_SEC" ]] && [[ "$T_SEC" -gt "$NOW_SEC" ]] && [[ "$T_SEC" -lt "$NEXT_SEC" ]]; then
                NEXT_SEC="$T_SEC"
            fi
        done

        if [[ "$NEXT_SEC" == "999999999999" ]]; then
            DIFF=99999
        else
            DIFF=$(( NEXT_SEC - NOW_SEC ))
        fi
    else
        DIFF=99999
    fi

    pkill -RTMIN+9 waybar 2>/dev/null

    if [[ "$DIFF" -le 65 ]]; then
        sleep 1
    else
        sleep 30
    fi
done
