#!/usr/bin/python3
import json
import datetime
import os
from hijridate import Gregorian

CACHE_FILE = os.path.expanduser('~/.cache/waybar-ycal/events.json')
MODE_FILE = os.path.expanduser('~/.cache/waybar-ycal/date_mode')

def load_events():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_mode():
    if os.path.exists(MODE_FILE):
        try:
            with open(MODE_FILE) as f:
                return f.read().strip()
        except Exception:
            pass
    return "gregorian"

now = datetime.datetime.now()
today = now.date()
events = load_events()
today_events = events.get(today.isoformat(), [])
mode = get_mode()

ARABIC_DAYS = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
ARABIC_MONTHS = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
                  "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
def to_arabic_digits(n):
    western = "0123456789"
    eastern = "٠١٢٣٤٥٦٧٨٩"
    return str(n).translate(str.maketrans(western, eastern))

if mode == "hijri":
    h = Gregorian(now.year, now.month, now.day).to_hijri()
    date_str = f"{to_arabic_digits(h.day)} {h.month_name('ar')} {to_arabic_digits(h.year)}"
else:
    date_str = f"{ARABIC_DAYS[now.weekday()]} {str(now.day)} {ARABIC_MONTHS[now.month - 1]}"

output = {
    "text": f"\U000f00ed  {date_str}",
    "tooltip": "",
    "class": "has-events" if today_events else ""
}

print(json.dumps(output))
