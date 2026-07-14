#!/bin/bash
chosen=$(printf "⏮ Previous\n⏯ Play/Pause\n⏭ Next\n⏹ Stop" | rofi -dmenu -p "  Media")
case "$chosen" in
  "⏮ Previous") playerctl previous ;;
  "⏯ Play/Pause") playerctl play-pause ;;
  "⏭ Next") playerctl next ;;
  "⏹ Stop") playerctl stop ;;
esac
