#!/usr/bin/env bash
# Waybar custom module: prayer times via Aladhan API
CITY="Djelfa"
COUNTRY="Algeria"
METHOD=3

CACHE_DIR="$HOME/.cache/prayer-times"
CACHE_FILE="$CACHE_DIR/timings.json"
TODAY=$(date +%F)

mkdir -p "$CACHE_DIR"

if [[ ! -f "$CACHE_FILE" ]] || [[ "$(jq -r '.date // empty' "$CACHE_FILE" 2>/dev/null)" != "$TODAY" ]]; then
    RESPONSE=$(curl -sL "https://api.aladhan.com/v1/timingsByCity?city=${CITY}&country=${COUNTRY}&method=${METHOD}")
    if [[ -n "$RESPONSE" ]] && echo "$RESPONSE" | jq -e '.data.timings' >/dev/null 2>&1; then
        echo "$RESPONSE" | jq --arg date "$TODAY" '.data.timings + {date: $date}' > "$CACHE_FILE"
    fi
fi

if [[ ! -f "$CACHE_FILE" ]]; then
    echo '{"text": "Prayer times unavailable", "tooltip": "Could not reach Aladhan API"}'
    exit 0
fi

FAJR=$(jq -r '.Fajr' "$CACHE_FILE")
DHUHR=$(jq -r '.Dhuhr' "$CACHE_FILE")
ASR=$(jq -r '.Asr' "$CACHE_FILE")
MAGHRIB=$(jq -r '.Maghrib' "$CACHE_FILE")
ISHA=$(jq -r '.Isha' "$CACHE_FILE")

NOW_SEC=$(date +%s)
NOW_HM=$(date +%H:%M)

declare -a NAMES=("الفجر" "الظهر" "العصر" "المغرب" "العشاء")
declare -a TIMES=("$FAJR" "$DHUHR" "$ASR" "$MAGHRIB" "$ISHA")

# Notification tracking
NOTIFIED_FILE="$CACHE_DIR/notified_$TODAY"
touch "$NOTIFIED_FILE"

# Check if it's time for any prayer and send notification with sound
for i in "${!NAMES[@]}"; do
    NAME="${NAMES[$i]}"
    T="${TIMES[$i]}"
    if [[ "$T" == "$NOW_HM" ]] && ! grep -qxF "$NAME" "$NOTIFIED_FILE"; then
        # Send notification
        notify-send -u critical "وقت الصلاة" "وقت صلاة ${NAME}"
        
        # Play sound - choose one of these methods:
        
        # Method 1: System bell (beep)
        echo -e "\a"
        
        # Method 2: Play a sound file (uncomment and set path)
        # aplay /usr/share/sounds/ubuntu/stereo/phone-incoming-call.ogg 2>/dev/null &
        # paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null &
        
        # Method 3: Play Adhan (if you have the file)
        mpv --no-video ~/.local/share/prayer-times/adhan.mp3 2>/dev/null &
        
        # Method 4: Use speaker-test for a simple tone
        # speaker-test -t sine -f 1000 -l 1 2>/dev/null &
        
        echo "$NAME" >> "$NOTIFIED_FILE"
    fi
done

NEXT_NAME=""
NEXT_SEC=0

for i in "${!NAMES[@]}"; do
    T="${TIMES[$i]}"
    T_SEC=$(date -d "$T" +%s 2>/dev/null)
    if [[ -n "$T_SEC" ]] && [[ "$T_SEC" -gt "$NOW_SEC" ]]; then
        NEXT_NAME="${NAMES[$i]}"
        NEXT_SEC="$T_SEC"
        break
    fi
done

if [[ -z "$NEXT_NAME" ]]; then
    NEXT_NAME="الفجر"
    NEXT_SEC=$(date -d "tomorrow $FAJR" +%s 2>/dev/null)
fi

DIFF=$(( NEXT_SEC - NOW_SEC ))
H=$(( DIFF / 3600 ))
M=$(( (DIFF % 3600) / 60 ))

# Show seconds when less than 1 minute remaining
if [[ "$H" -gt 0 ]]; then
    COUNTDOWN="${H}:$(printf '%02d' "$M")"
    UNIT="h"
elif [[ "$M" -gt 0 ]]; then
    COUNTDOWN="${M}"
    UNIT="m"
else
    COUNTDOWN="${DIFF}"
    UNIT="s"
fi

TEXT="${NEXT_NAME} ‎-${COUNTDOWN}${UNIT}"
TOOLTIP=$'مواقيت الصلاة\n\nالفجر:    '"${FAJR}"$'\nالظهر:    '"${DHUHR}"$'\nالعصر:    '"${ASR}"$'\nالمغرب:   '"${MAGHRIB}"$'\nالعشاء:   '"${ISHA}"

jq -cn --arg text "$TEXT" --arg tooltip "$TOOLTIP" '{text: $text, tooltip: $tooltip}'
