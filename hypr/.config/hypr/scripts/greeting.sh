#!/bin/bash
hour=$(date +%H)
if [ $hour -lt 12 ]; then
    echo "Good Morning"
else
    echo "Good Evening"
fi
