#!/bin/bash
count=$(swaync-client -c 2>/dev/null)
if [ -n "$count" ] && [ "$count" -gt 0 ]; then
    echo "{\"text\": \"\udb80\udc99\", \"class\": \"has-notif\", \"tooltip\": \"$count notification(s)\"}"
else
    echo "{\"text\": \"\udb80\udc9a\", \"class\": \"\", \"tooltip\": \"no notifications\"}"
fi
