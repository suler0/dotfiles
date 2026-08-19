#!/usr/bin/python3
from ctypes import CDLL
CDLL('libgtk4-layer-shell.so')
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, GLib, Gtk4LayerShell, Pango, PangoCairo
import calendar
import datetime
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import threading
import tomllib

CONFIG_DIR = os.path.expanduser('~/.config/waybar-ycal')
CACHE_DIR = os.path.expanduser('~/.cache/waybar-ycal')
CACHE_FILE = os.path.join(CACHE_DIR, 'events.json')
PID_FILE = os.path.join(CACHE_DIR, 'popup.pid')
CREDENTIALS_FILE = os.path.join(CONFIG_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(CACHE_DIR, 'token.json')
SETTINGS_FILE = os.path.join(CONFIG_DIR, 'settings.json')
THEME_CONFIG_FILE = os.path.join(CONFIG_DIR, 'theme.toml')

OMARCHY_THEME_FILE = os.path.expanduser('~/.config/omarchy/current/theme/colors.toml')
MATUGEN_CACHE_FILE = os.path.join(CACHE_DIR, 'matugen.toml')
PYWAL_FILE = os.path.expanduser('~/.cache/wal/colors.json')

SYNC_INTERVAL_SEC = 15 * 60  # 15 minutes

NERD_FONT = "JetBrainsMonoNL Nerd Font, JetBrainsMono Nerd Font, Symbols Nerd Font,Ubuntu Arabic"
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks',
]

DEFAULT_COLORS = {
    'foreground': '#ffcead',
    'background': '#060B1E',
    'accent': '#7d82d9',
    'accent2': '#e0c1a3',
    'error': '#ff5555',
}
DEFAULT_APPEARANCE = {'opacity': 0.92, 'popover_opacity': 0.98, 'radius': 12}

DEFAULT_SETTINGS = {
    'lang': 'en',
    'week_start': 'monday',        # 'monday' or 'sunday'
    'notifications_enabled': True,
    'timezone': '',                # IANA name, e.g. 'Africa/Algiers'; '' = system local
    'date_format': '',             # strftime pattern; '' = built-in per-language format
    'time_format': '24h',          # '24h' or '12h'
    'font_family': '',             # '' = default UI font
    'font_size': 11,
    'window_scale': 1.0,
    'custom_languages': {},        # {'fr': {'today': 'Aujourd\\'hui', ...}, ...}
    'colors': {},                  # final override, wins over theme.toml
}


# ── Settings ────────────────────────────────────────────────────────
def load_settings():
    s = json.loads(json.dumps(DEFAULT_SETTINGS))
    try:
        with open(SETTINGS_FILE) as f:
            loaded = json.load(f)
        for k in s:
            if k not in loaded:
                continue
            if isinstance(s[k], dict) and isinstance(loaded[k], dict):
                s[k].update(loaded[k])
            else:
                s[k] = loaded[k]
    except Exception:
        pass
    return s


def save_settings(s):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = SETTINGS_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SETTINGS_FILE)


# ── Theme sourcing (theme.toml: auto / matugen / omarchy / pywal / manual / file) ──
def load_theme_config():
    cfg = {'source': 'auto', 'path': '', 'colors': {}, 'appearance': dict(DEFAULT_APPEARANCE)}
    try:
        with open(THEME_CONFIG_FILE, 'rb') as f:
            d = tomllib.load(f)
        cfg['source'] = d.get('source', cfg['source'])
        cfg['path'] = d.get('path', cfg['path'])
        cfg['colors'].update(d.get('colors', {}))
        cfg['appearance'].update(d.get('appearance', {}))
    except Exception:
        pass
    return cfg


def _read_toml_colors(path):
    try:
        with open(os.path.expanduser(path), 'rb') as f:
            d = tomllib.load(f)
        colors = d.get('colors', d)
        return {k: colors[k] for k in DEFAULT_COLORS if colors.get(k)}
    except Exception:
        return {}


def _read_pywal_colors():
    try:
        with open(PYWAL_FILE) as f:
            d = json.load(f)
        sp = d.get('special', {})
        cols = d.get('colors', {})
        out = {}
        if sp.get('foreground'):
            out['foreground'] = sp['foreground']
        if sp.get('background'):
            out['background'] = sp['background']
        if cols.get('color4'):
            out['accent'] = cols['color4']
        if cols.get('color5'):
            out['accent2'] = cols['color5']
        if cols.get('color1'):
            out['error'] = cols['color1']
        return out
    except Exception:
        return {}


def load_colors(settings):
    cfg = load_theme_config()
    source = cfg.get('source', 'auto')
    base = {}
    if source == 'manual':
        base = {}
    elif source == 'file' and cfg.get('path'):
        base = _read_toml_colors(cfg['path'])
    elif source == 'matugen':
        base = _read_toml_colors(MATUGEN_CACHE_FILE)
    elif source == 'omarchy':
        base = _read_toml_colors(OMARCHY_THEME_FILE)
    elif source == 'pywal':
        base = _read_pywal_colors()
    else:  # auto: matugen -> omarchy -> pywal -> defaults
        for loader in (lambda: _read_toml_colors(MATUGEN_CACHE_FILE),
                       lambda: _read_toml_colors(OMARCHY_THEME_FILE),
                       _read_pywal_colors):
            base = loader()
            if base:
                break

    merged = {**DEFAULT_COLORS, **base, **{k: v for k, v in cfg.get('colors', {}).items() if v}}
    settings_colors = settings.get('colors') or {}
    merged.update({k: v for k, v in settings_colors.items() if v})
    return merged, cfg.get('appearance', DEFAULT_APPEARANCE)


def hex_to_rgb_float(hex_color):
    h = hex_color.lstrip('#')
    return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255


def hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r}, {g}, {b}, {alpha})'


# ── Translations ────────────────────────────────────────────────────
STRINGS = {
    'en': {
        'today': 'Today', 'add': '+ Add', 'task': 'Task', 'event': 'Event',
        'task_title_ph': 'Task title', 'event_title_ph': 'Event title',
        'title_required': 'Title required', 'saving': 'Saving...',
        'failed_save': 'Failed to save', 'use_hhmm': 'Use HH:MM format',
        'save': 'Save', 'cancel': 'Cancel', 'no_events': 'No events',
        'connect_cal_title': 'Connect Google Calendar',
        'connect_cal_msg': 'Place your OAuth credentials at:\n{path}\n\nWaiting for file...',
        'open_console': 'Open Google Cloud Console',
        'console_opened': 'Opened — place credentials.json and wait...',
        'connect_acct_title': 'Connect Google Account',
        'connect_acct_msg': 'Click below to open a browser and\nauthenticate with Google.',
        'authenticate': 'Authenticate', 'opening_browser': 'Opening browser...',
        'auth_failed': 'Failed — try again',
        'settings_title': 'Settings', 'language_label': 'Language', 'size_label': 'Size',
        'size_small': 'Small', 'size_normal': 'Normal', 'size_large': 'Large',
        'theme_label': 'Theme override (leave blank to use theme.toml source)',
        'bg_ph': 'Background #hex', 'fg_ph': 'Foreground #hex', 'accent_ph': 'Accent #hex',
        'settings_saved': 'Saved',
    },
    'ar': {
        'today': 'اليوم', 'add': '+ إضافة', 'task': 'مهمة', 'event': 'حدث',
        'task_title_ph': 'عنوان المهمة', 'event_title_ph': 'عنوان الحدث',
        'title_required': 'العنوان مطلوب', 'saving': 'جارٍ الحفظ...',
        'failed_save': 'فشل الحفظ', 'use_hhmm': 'استخدم صيغة HH:MM',
        'save': 'حفظ', 'cancel': 'إلغاء', 'no_events': 'لا توجد أحداث',
        'connect_cal_title': 'ربط تقويم جوجل',
        'connect_cal_msg': 'ضع ملف اعتماد OAuth في:\n{path}\n\nبانتظار الملف...',
        'open_console': 'فتح Google Cloud Console',
        'console_opened': 'تم الفتح — ضع credentials.json وانتظر...',
        'connect_acct_title': 'ربط حساب جوجل',
        'connect_acct_msg': 'اضغط أدناه لفتح المتصفح\nوتسجيل الدخول إلى جوجل.',
        'authenticate': 'تسجيل الدخول', 'opening_browser': 'جارٍ فتح المتصفح...',
        'auth_failed': 'فشل — حاول مرة أخرى',
        'settings_title': 'الإعدادات', 'language_label': 'اللغة', 'size_label': 'الحجم',
        'size_small': 'صغير', 'size_normal': 'عادي', 'size_large': 'كبير',
        'theme_label': 'تخصيص الألوان (اتركه فارغًا لاستخدام theme.toml)',
        'bg_ph': 'لون الخلفية #hex', 'fg_ph': 'لون النص #hex', 'accent_ph': 'اللون المميز #hex',
        'settings_saved': 'تم الحفظ',
    },
}

ARABIC_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                 "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
ARABIC_WEEKDAYS_FULL = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
ARABIC_WEEKDAYS_SHORT_MON = ["إث", "ثل", "أر", "خم", "جم", "سب", "أح"]
ARABIC_WEEKDAYS_SHORT_SUN = ["أح", "إث", "ثل", "أر", "خم", "جم", "سب"]
ARABIC_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _localize_num(n, lang):
    s = str(n)
    return s.translate(ARABIC_DIGITS) if lang == 'ar' else s


def get_strings(settings):
    strings = json.loads(json.dumps(STRINGS))
    for lang_code, translations in (settings.get('custom_languages') or {}).items():
        strings.setdefault(lang_code, {})
        strings[lang_code].update(translations)
    return strings


def _get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    return creds


def _fmt_time(dt, time_format):
    if time_format == '12h':
        return dt.strftime('%I:%M %p').lstrip('0')
    return dt.strftime('%H:%M')


def _maybe_notify(events_by_date, settings):
    if not settings.get('notifications_enabled'):
        return
    if not shutil.which('notify-send'):
        return
    today_key = datetime.date.today().isoformat()
    pending = [e for e in events_by_date.get(today_key, [])
               if isinstance(e, dict) and e.get('type') == 'task' and not e.get('done')]
    if not pending:
        return
    lang = settings.get('lang', 'en')
    title = 'ycal' if lang != 'ar' else 'التقويم'
    body = f"{len(pending)} task(s) due today" if lang != 'ar' else f"{len(pending)} مهمة مستحقة اليوم"
    try:
        subprocess.Popen(['notify-send', title, body])
    except Exception:
        pass


def _run_sync():
    """Fetch events from Google Calendar and write to cache. Runs in a thread."""
    try:
        from googleapiclient.discovery import build

        if not os.path.exists(TOKEN_FILE):
            return

        creds = _get_credentials()
        if creds is None:
            return

        settings = load_settings()
        time_format = settings.get('time_format', '24h')

        service = build('calendar', 'v3', credentials=creds)
        today = datetime.date.today()
        time_min = (today - datetime.timedelta(days=60)).isoformat() + 'T00:00:00Z'
        time_max = (today + datetime.timedelta(days=365)).isoformat() + 'T23:59:59Z'

        cal_list = service.calendarList().list().execute()
        calendar_ids = [c['id'] for c in cal_list.get('items', [])]

        events_by_date = {}
        for cal_id in calendar_ids:
            try:
                result = service.events().list(
                    calendarId=cal_id, timeMin=time_min, timeMax=time_max,
                    singleEvents=True, orderBy='startTime', maxResults=500,
                ).execute()
            except Exception:
                continue
            for item in result.get('items', []):
                start = item['start']
                end = item['end']
                title = item.get('summary', '(no title)')
                event_id = item.get('id')
                if 'dateTime' in start:
                    dt = datetime.datetime.fromisoformat(start['dateTime'])
                    dt_end = datetime.datetime.fromisoformat(end['dateTime'])
                    label = f"{title} {_fmt_time(dt, time_format)}-{_fmt_time(dt_end, time_format)}"
                    events_by_date.setdefault(dt.date().isoformat(), []).append({
                        'type': 'event', 'id': event_id, 'cal_id': cal_id, 'title': label,
                    })
                else:
                    d = datetime.date.fromisoformat(start['date'])
                    d_end = datetime.date.fromisoformat(end['date'])
                    while d < d_end:
                        events_by_date.setdefault(d.isoformat(), []).append({
                            'type': 'event', 'id': event_id, 'cal_id': cal_id, 'title': title,
                        })
                        d += datetime.timedelta(days=1)

        tasks_service = build('tasks', 'v1', credentials=creds)
        task_lists = tasks_service.tasklists().list().execute()
        for tl in task_lists.get('items', []):
            try:
                tasks = tasks_service.tasks().list(
                    tasklist=tl['id'], showCompleted=True, showHidden=True, maxResults=100,
                ).execute()
            except Exception:
                continue
            for task in tasks.get('items', []):
                due = task.get('due')
                title = task.get('title', '(no title)')
                completed = task.get('status') == 'completed'
                if due:
                    date_key = due[:10]
                    events_by_date.setdefault(date_key, []).append({
                        'type': 'task', 'id': task['id'], 'lid': tl['id'],
                        'title': title, 'done': completed,
                    })

        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = CACHE_FILE + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(events_by_date, f)
        os.replace(tmp, CACHE_FILE)

        _maybe_notify(events_by_date, settings)

    except Exception as e:
        print(f'[gcal sync error] {e}', file=sys.stderr)


def sync_in_background():
    threading.Thread(target=_run_sync, daemon=True).start()
    return True


def load_events():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


class ClickShield(Gtk.Window):
    def __init__(self, app, on_click):
        super().__init__(application=app)
        self.set_decorated(False)
        self.add_css_class('click-shield')
        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.TOP)
        for edge in [Gtk4LayerShell.Edge.TOP, Gtk4LayerShell.Edge.BOTTOM,
                     Gtk4LayerShell.Edge.LEFT, Gtk4LayerShell.Edge.RIGHT]:
            Gtk4LayerShell.set_anchor(self, edge, True)
        Gtk4LayerShell.set_exclusive_zone(self, -1)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
        box = Gtk.Box()
        box.set_hexpand(True)
        box.set_vexpand(True)
        self.set_child(box)
        gesture = Gtk.GestureClick()
        gesture.connect('pressed', lambda *_: on_click())
        box.add_controller(gesture)
        self.set_visible(False)


class CalendarPopup(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("waybar-ycal")
        self.set_default_size(-1, -1)

        self.settings = load_settings()
        self.strings = get_strings(self.settings)
        self.lang = self.settings['lang']
        self.window_scale = self.settings.get('window_scale', 1.0)
        self.font_size = self.settings.get('font_size', 11)
        self.week_start = self.settings.get('week_start', 'monday')
        self.time_format = self.settings.get('time_format', '24h')
        self.date_format = self.settings.get('date_format', '')
        self.timezone_name = self.settings.get('timezone', '')

        self.today = datetime.date.today()
        self.year = self.today.year
        self.month = self.today.month
        self.selected_date = self.today
        self.events = load_events()
        self._selected_btn = None
        self._cred_poll_timer = None
        self._shield = ClickShield(app, self._hide)

        self._setup_window()
        self.set_direction(Gtk.TextDirection.RTL if self.lang == 'ar' else Gtk.TextDirection.LTR)
        self._apply_css()
        self._build_ui()

    # ── i18n / scale helpers ────────────────────────────────────
    def t(self, key):
        return self.strings.get(self.lang, self.strings['en']).get(key, key)

    def s(self, px):
        """Scale a widget pixel dimension by window_scale."""
        return max(1, round(px * self.window_scale))

    def fs(self, px):
        """Scale a font-related pixel size by font_size (baseline 11)."""
        return max(1, round(px * (self.font_size / 11.0)))

    def _get_tz(self):
        if self.timezone_name:
            try:
                from zoneinfo import ZoneInfo
                return ZoneInfo(self.timezone_name)
            except Exception:
                pass
        return datetime.datetime.now().astimezone().tzinfo

    def _month_year_label(self):
        d = datetime.date(self.year, self.month, 1)
        if self.date_format:
            return d.strftime(self.date_format)
        if self.lang == 'ar':
            return f"{ARABIC_MONTHS[self.month - 1]} {self.year}"
        return d.strftime('%B %Y').upper()

    def _weekday_full(self, date):
        if self.lang == 'ar':
            return ARABIC_WEEKDAYS_FULL[date.weekday()]
        return date.strftime('%A')

    def _day_short_label(self, date):
        if self.date_format:
            return date.strftime(self.date_format)
        if self.lang == 'ar':
            return f"{date.day} {ARABIC_MONTHS[date.month - 1][:3]}"
        return date.strftime('%d %b').lstrip('0')

    def _setup_window(self):
        self.set_decorated(False)
        self.set_resizable(False)
        self.connect("close-request", lambda *_: self._hide())

        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, False)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.TOP, 4)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.ON_DEMAND)

        self.set_visible(False)

    def toggle(self):
        if self.get_visible():
            self._hide()
        else:
            self._show()

    def _show(self):
        self._apply_css()
        self._shield.present()
        if not os.path.exists(CREDENTIALS_FILE):
            self._show_setup_screen('no_credentials')
            self.present()
            return
        if not os.path.exists(TOKEN_FILE):
            self._show_setup_screen('no_token')
            self.present()
            return
        self._reset_to_today()
        self._show_calendar()
        self.present()

    def _reset_to_today(self):
        self.today = datetime.date.today()
        self.year = self.today.year
        self.month = self.today.month
        self.selected_date = self.today
        self.events = load_events()

    def _show_calendar(self):
        self.set_child(self.main_box)
        self._build_grid()
        self.month_label.set_markup(f"<b>{self._month_year_label()}</b>")
        self._update_day_panel(self.today)

    def _make_setup_card(self, title_text, msg_text):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.add_css_class('popup-bg')
        box.set_size_request(self.s(360), -1)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)

        title = Gtk.Label(label=title_text)
        title.add_css_class('setup-title')

        msg = Gtk.Label(label=msg_text)
        msg.add_css_class('setup-msg')
        msg.set_justify(Gtk.Justification.CENTER)

        box.append(title)
        box.append(msg)
        return box

    def _show_setup_screen(self, state):
        self.set_default_size(-1, -1)

        if self._cred_poll_timer is not None:
            GLib.source_remove(self._cred_poll_timer)
            self._cred_poll_timer = None

        if state == 'no_credentials':
            short_path = CREDENTIALS_FILE.replace(os.path.expanduser('~'), '~')
            box = self._make_setup_card(
                self.t('connect_cal_title'),
                self.t('connect_cal_msg').format(path=short_path),
            )
            open_btn = Gtk.Button(label=self.t('open_console'))
            open_btn.add_css_class('add-btn')
            open_btn.connect("clicked", self._on_open_console_clicked)
            box.append(open_btn)

            def poll_for_credentials():
                if os.path.exists(CREDENTIALS_FILE):
                    self._cred_poll_timer = None
                    self._show_setup_screen('no_token')
                    return False
                return True
            self._cred_poll_timer = GLib.timeout_add(2000, poll_for_credentials)

        elif state == 'no_token':
            box = self._make_setup_card(self.t('connect_acct_title'), self.t('connect_acct_msg'))
            auth_btn = Gtk.Button(label=self.t('authenticate'))
            auth_btn.add_css_class('add-btn')
            auth_btn.connect("clicked", self._on_auth_clicked)
            box.append(auth_btn)

        self.set_child(box)

    def _on_open_console_clicked(self, btn):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        btn.set_sensitive(False)
        btn.set_label(self.t('console_opened'))
        subprocess.Popen(['xdg-open', 'https://console.cloud.google.com/apis/credentials'])

    def _on_auth_clicked(self, btn):
        btn.set_sensitive(False)
        btn.set_label(self.t('opening_browser'))

        def do_auth():
            try:
                _get_credentials()
                _run_sync()

                def after():
                    self._reset_to_today()
                    self._show_calendar()
                    return False
                GLib.idle_add(after)
            except Exception:
                def after_err():
                    btn.set_label(self.t('auth_failed'))
                    btn.set_sensitive(True)
                    return False
                GLib.idle_add(after_err)
        threading.Thread(target=do_auth, daemon=True).start()

    def _hide(self):
        self._shield.set_visible(False)
        if self._cred_poll_timer is not None:
            GLib.source_remove(self._cred_poll_timer)
            self._cred_poll_timer = None
        self.set_visible(False)

    def _build_ui(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.main_box.add_css_class('popup-bg')
        self.set_child(self.main_box)

        self.left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.left_box.set_size_request(self.s(220), -1)
        self.main_box.append(self.left_box)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        header.set_size_request(-1, self.s(32))
        prev_btn = Gtk.Button(label="‹")
        prev_btn.connect("clicked", lambda _: self._navigate(-1))

        self.month_label = Gtk.Label()
        self.month_label.set_markup(f"<b>{self._month_year_label()}</b>")
        self.month_label.set_hexpand(True)

        next_btn = Gtk.Button(label="›")
        next_btn.connect("clicked", lambda _: self._navigate(1))

        self._refresh_angle = 0.0
        self._refresh_spin_timer = None
        self._refresh_da = Gtk.DrawingArea()
        self._refresh_da.set_size_request(self.s(20), self.s(20))
        self._refresh_da.set_draw_func(self._draw_refresh_icon)

        self.refresh_btn = Gtk.Button()
        self.refresh_btn.set_child(self._refresh_da)
        self.refresh_btn.set_size_request(self.s(28), self.s(28))
        self.refresh_btn.set_valign(Gtk.Align.CENTER)
        self.refresh_btn.add_css_class('refresh-btn')
        self.refresh_btn.connect("clicked", self._on_refresh_clicked)

        settings_btn = Gtk.Button()
        settings_lbl = Gtk.Label(label="\uf013")
        settings_lbl.add_css_class('nerd-label')
        settings_btn.set_child(settings_lbl)
        settings_btn.set_size_request(self.s(28), self.s(28))
        settings_btn.set_valign(Gtk.Align.CENTER)
        settings_btn.add_css_class('refresh-btn')
        settings_btn.connect("clicked", self._on_settings_clicked)

        header.append(prev_btn)
        header.append(self.month_label)
        header.append(next_btn)
        header.append(self.refresh_btn)
        header.append(settings_btn)
        self.left_box.append(header)

        self.grid = None
        self._build_grid()

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.add_css_class('panel-divider')
        self.main_box.append(sep)

        self.right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.right_box.set_size_request(self.s(180), -1)
        self.right_box.add_css_class('day-panel')
        self.main_box.append(self.right_box)

        self.day_label = Gtk.Label()
        self.day_label.set_halign(Gtk.Align.START)
        self.day_label.add_css_class('day-heading')
        self.right_box.append(self.day_label)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        self.right_box.append(scroll)

        self.events_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll.set_child(self.events_box)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_row.set_size_request(-1, self.s(32))
        add_btn = Gtk.Button(label=self.t('add'))
        add_btn.add_css_class('add-btn')
        add_btn.set_hexpand(True)
        add_btn.connect("clicked", self._on_add_clicked)
        edit_btn = Gtk.Button()
        edit_lbl = Gtk.Label(label="\uf044")
        edit_lbl.set_halign(Gtk.Align.CENTER)
        edit_lbl.set_valign(Gtk.Align.CENTER)
        edit_btn.set_child(edit_lbl)
        edit_btn.set_size_request(self.s(36), -1)
        edit_btn.set_hexpand(False)
        edit_btn.add_css_class('add-btn')
        edit_btn.add_css_class('nerd')
        edit_btn.connect("clicked", self._on_edit_clicked)
        btn_row.append(add_btn)
        btn_row.append(edit_btn)
        self.right_box.append(btn_row)

        self.add_revealer = Gtk.Revealer()
        self.add_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        form_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        form_box.add_css_class('add-form')
        form_box.add_css_class('panel-bg')

        self.add_mode = 'task'

        mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add_mode_task_btn = Gtk.ToggleButton(label=self.t('task'))
        self.add_mode_task_btn.add_css_class('add-btn')
        self.add_mode_task_btn.set_active(True)
        self.add_mode_task_btn.connect("toggled", self._on_add_mode_toggled, 'task')
        self.add_mode_event_btn = Gtk.ToggleButton(label=self.t('event'))
        self.add_mode_event_btn.add_css_class('add-btn')
        self.add_mode_event_btn.set_group(self.add_mode_task_btn)
        self.add_mode_event_btn.connect("toggled", self._on_add_mode_toggled, 'event')
        mode_row.append(self.add_mode_task_btn)
        mode_row.append(self.add_mode_event_btn)
        form_box.append(mode_row)

        self.add_title_entry = Gtk.Entry()
        self.add_title_entry.set_placeholder_text(self.t('task_title_ph'))
        self.add_title_entry.connect("activate", self._on_save_event_clicked)
        form_box.append(self.add_title_entry)

        self.add_time_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add_start_entry = Gtk.Entry()
        self.add_start_entry.set_placeholder_text("09:00")
        self.add_start_entry.set_max_length(5)
        self.add_start_entry.set_width_chars(6)
        self.add_end_entry = Gtk.Entry()
        self.add_end_entry.set_placeholder_text("10:00")
        self.add_end_entry.set_max_length(5)
        self.add_end_entry.set_width_chars(6)
        self.add_time_row.append(self.add_start_entry)
        self.add_time_row.append(Gtk.Label(label="–"))
        self.add_time_row.append(self.add_end_entry)
        self.add_time_row.set_visible(False)
        form_box.append(self.add_time_row)

        self.add_status_label = Gtk.Label(label="")
        self.add_status_label.add_css_class('add-status')
        self.add_status_label.set_halign(Gtk.Align.START)
        form_box.append(self.add_status_label)

        form_btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        save_btn = Gtk.Button(label=self.t('save'))
        save_btn.add_css_class('add-btn')
        save_btn.connect("clicked", self._on_save_event_clicked)
        cancel_btn = Gtk.Button(label=self.t('cancel'))
        cancel_btn.add_css_class('add-btn')
        cancel_btn.connect("clicked", lambda _: self.add_revealer.set_reveal_child(False))
        form_btn_row.append(save_btn)
        form_btn_row.append(cancel_btn)
        form_box.append(form_btn_row)

        self.add_revealer.set_child(form_box)
        self.right_box.append(self.add_revealer)

        # ── Settings revealer ──────────────────────────────────
        self.settings_revealer = Gtk.Revealer()
        self.settings_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        s_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        s_box.add_css_class('add-form')
        s_box.add_css_class('panel-bg')

        s_title = Gtk.Label(label=self.t('settings_title'))
        s_title.add_css_class('setup-title')
        s_title.set_halign(Gtk.Align.START)
        s_box.append(s_title)

        lang_lbl = Gtk.Label(label=self.t('language_label'))
        lang_lbl.set_halign(Gtk.Align.START)
        lang_lbl.add_css_class('add-status')
        s_box.append(lang_lbl)
        lang_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.lang_en_btn = Gtk.ToggleButton(label="English")
        self.lang_en_btn.add_css_class('add-btn')
        self.lang_ar_btn = Gtk.ToggleButton(label="العربية")
        self.lang_ar_btn.add_css_class('add-btn')
        self.lang_ar_btn.set_group(self.lang_en_btn)
        (self.lang_ar_btn if self.lang == 'ar' else self.lang_en_btn).set_active(True)
        self.lang_en_btn.connect("toggled", self._on_lang_toggled, 'en')
        self.lang_ar_btn.connect("toggled", self._on_lang_toggled, 'ar')
        lang_row.append(self.lang_en_btn)
        lang_row.append(self.lang_ar_btn)
        s_box.append(lang_row)

        size_lbl = Gtk.Label(label=self.t('size_label'))
        size_lbl.set_halign(Gtk.Align.START)
        size_lbl.add_css_class('add-status')
        s_box.append(size_lbl)
        size_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.size_small_btn = Gtk.ToggleButton(label=self.t('size_small'))
        self.size_small_btn.add_css_class('add-btn')
        self.size_normal_btn = Gtk.ToggleButton(label=self.t('size_normal'))
        self.size_normal_btn.add_css_class('add-btn')
        self.size_normal_btn.set_group(self.size_small_btn)
        self.size_large_btn = Gtk.ToggleButton(label=self.t('size_large'))
        self.size_large_btn.add_css_class('add-btn')
        self.size_large_btn.set_group(self.size_small_btn)
        if self.window_scale <= 0.9:
            self.size_small_btn.set_active(True)
        elif self.window_scale >= 1.15:
            self.size_large_btn.set_active(True)
        else:
            self.size_normal_btn.set_active(True)
        self.size_small_btn.connect("toggled", self._on_size_toggled, 0.85)
        self.size_normal_btn.connect("toggled", self._on_size_toggled, 1.0)
        self.size_large_btn.connect("toggled", self._on_size_toggled, 1.2)
        size_row.append(self.size_small_btn)
        size_row.append(self.size_normal_btn)
        size_row.append(self.size_large_btn)
        s_box.append(size_row)

        theme_lbl = Gtk.Label(label=self.t('theme_label'))
        theme_lbl.set_halign(Gtk.Align.START)
        theme_lbl.add_css_class('add-status')
        theme_lbl.set_wrap(True)
        s_box.append(theme_lbl)

        ov = self.settings.get('colors', {})
        self.bg_entry = Gtk.Entry()
        self.bg_entry.set_placeholder_text(self.t('bg_ph'))
        if ov.get('background'):
            self.bg_entry.set_text(ov['background'])
        self.fg_entry = Gtk.Entry()
        self.fg_entry.set_placeholder_text(self.t('fg_ph'))
        if ov.get('foreground'):
            self.fg_entry.set_text(ov['foreground'])
        self.accent_entry = Gtk.Entry()
        self.accent_entry.set_placeholder_text(self.t('accent_ph'))
        if ov.get('accent'):
            self.accent_entry.set_text(ov['accent'])
        s_box.append(self.bg_entry)
        s_box.append(self.fg_entry)
        s_box.append(self.accent_entry)

        self.settings_status_label = Gtk.Label(label="")
        self.settings_status_label.add_css_class('add-status')
        self.settings_status_label.set_halign(Gtk.Align.START)
        s_box.append(self.settings_status_label)

        s_btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        s_save_btn = Gtk.Button(label=self.t('save'))
        s_save_btn.add_css_class('add-btn')
        s_save_btn.connect("clicked", self._on_settings_save_clicked)
        s_cancel_btn = Gtk.Button(label=self.t('cancel'))
        s_cancel_btn.add_css_class('add-btn')
        s_cancel_btn.connect("clicked", lambda _: self.settings_revealer.set_reveal_child(False))
        s_btn_row.append(s_save_btn)
        s_btn_row.append(s_cancel_btn)
        s_box.append(s_btn_row)

        self.settings_revealer.set_child(s_box)
        self.right_box.append(self.settings_revealer)

        self._update_day_panel(self.selected_date)

    def _on_settings_clicked(self, _):
        self.add_revealer.set_reveal_child(False)
        self.settings_revealer.set_reveal_child(not self.settings_revealer.get_reveal_child())

    def _on_lang_toggled(self, btn, lang_code):
        if not btn.get_active() or self.lang == lang_code:
            return
        self.lang = lang_code
        self.settings['lang'] = lang_code
        save_settings(self.settings)
        self._apply_settings_live()

    def _on_size_toggled(self, btn, scale_value):
        if not btn.get_active() or abs(self.window_scale - scale_value) < 1e-6:
            return
        self.window_scale = scale_value
        self.settings['window_scale'] = scale_value
        save_settings(self.settings)
        self._apply_settings_live()

    def _apply_settings_live(self):
        """Re-apply language/size/theme instantly, no restart needed."""
        # Preserve state that a full UI rebuild would otherwise wipe out.
        bg_text = self.bg_entry.get_text()
        fg_text = self.fg_entry.get_text()
        accent_text = self.accent_entry.get_text()
        settings_was_open = self.settings_revealer.get_reveal_child()
        add_was_open = self.add_revealer.get_reveal_child()

        self.set_direction(Gtk.TextDirection.RTL if self.lang == 'ar' else Gtk.TextDirection.LTR)
        self._apply_css()
        self._build_ui()  # rebuilds every widget using the new self.lang / self.window_scale

        self.bg_entry.set_text(bg_text)
        self.fg_entry.set_text(fg_text)
        self.accent_entry.set_text(accent_text)
        self.settings_revealer.set_reveal_child(settings_was_open)
        self.add_revealer.set_reveal_child(add_was_open)

    def _on_settings_save_clicked(self, _):
        self.settings['colors'] = {
            'background': self.bg_entry.get_text().strip() or None,
            'foreground': self.fg_entry.get_text().strip() or None,
            'accent': self.accent_entry.get_text().strip() or None,
        }
        save_settings(self.settings)
        self._apply_settings_live()
        self.settings_status_label.set_text(self.t('settings_saved'))

    def _week_layout(self):
        """Returns (day_names, offset_fn, weekend_idx) for the configured week_start."""
        if self.week_start == 'sunday':
            day_names = ARABIC_WEEKDAYS_SHORT_SUN if self.lang == 'ar' else ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
            weekend_idx = {0, 6}
            offset = lambda first: (first.weekday() + 1) % 7
        else:
            day_names = ARABIC_WEEKDAYS_SHORT_MON if self.lang == 'ar' else ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
            weekend_idx = {5, 6}
            offset = lambda first: first.weekday()
        return day_names, offset, weekend_idx

    def _build_grid(self):
        if self.grid is not None:
            self.left_box.remove(self.grid)
        self._selected_btn = None

        self.grid = Gtk.Grid()
        self.grid.set_row_spacing(4)
        self.grid.set_column_spacing(0)
        self.grid.set_column_homogeneous(True)

        day_names, offset_fn, weekend_idx = self._week_layout()
        for col, name in enumerate(day_names):
            lbl = Gtk.Label(label=name)
            lbl.add_css_class('weekday')
            if col in weekend_idx:
                lbl.add_css_class('weekend-label')
            lbl.set_size_request(self.s(28), self.s(18))
            self.grid.attach(lbl, col, 0, 1, 1)

        first = datetime.date(self.year, self.month, 1)
        offset = offset_fn(first)
        start = first - datetime.timedelta(days=offset)
        last = datetime.date(self.year, self.month, calendar.monthrange(self.year, self.month)[1])
        weeks = math.ceil((offset + last.day) / 7)
        total_days = weeks * 7

        for i in range(total_days):
            date = start + datetime.timedelta(days=i)
            day_events = self.events.get(date.isoformat(), [])

            overlay = Gtk.Overlay()
            overlay.set_size_request(self.s(28), self.s(28))

            number = Gtk.Label(label=_localize_num(date.day, self.lang))
            number.add_css_class('day-number')
            number.set_halign(Gtk.Align.CENTER)
            number.set_valign(Gtk.Align.CENTER)
            overlay.set_child(number)

            has_events = any(isinstance(e, str) for e in day_events) or any(isinstance(e, dict) and e.get('type') == 'event' for e in day_events)
            has_tasks = any(isinstance(e, dict) and e.get('type') == 'task' and not e.get('done') for e in day_events)

            if has_events or has_tasks:
                bar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                bar_box.set_halign(Gtk.Align.CENTER)
                bar_box.set_valign(Gtk.Align.END)
                bar_box.set_margin_bottom(4)
                w = self.s(8) if (has_events and has_tasks) else self.s(18)
                if has_tasks:
                    task_bar = Gtk.Box()
                    task_bar.add_css_class('task-bar')
                    task_bar.set_size_request(w, 2)
                    bar_box.append(task_bar)
                if has_events:
                    bar = Gtk.Box()
                    bar.add_css_class('event-bar')
                    bar.set_size_request(w, 2)
                    bar_box.append(bar)
                overlay.add_overlay(bar_box)

            btn = Gtk.Button()
            btn.set_child(overlay)
            btn.set_size_request(self.s(28), self.s(28))
            btn.date = date
            btn.connect("clicked", self._on_day_clicked)

            col = i % 7
            if date.month != self.month:
                btn.add_css_class("other-month")
            if col in weekend_idx:
                btn.add_css_class("weekend")
            if date == self.today:
                btn.add_css_class("today")
            if date == self.selected_date:
                btn.add_css_class("selected")
                self._selected_btn = btn

            row = i // 7 + 1
            self.grid.attach(btn, col, row, 1, 1)

        self.left_box.append(self.grid)

    def _on_day_clicked(self, btn):
        if self._selected_btn is not None:
            self._selected_btn.remove_css_class('selected')
        self._selected_btn = btn
        btn.add_css_class('selected')
        self.selected_date = btn.date
        self._update_day_panel(btn.date)

    def _make_event_row(self, ev, date):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        if isinstance(ev, dict) and ev.get('type') == 'task':
            done = ev.get('done', False)
            dot = Gtk.Label(label="•")
            dot.add_css_class('done-dot' if done else 'task-dot')
            name = Gtk.Label(label=ev['title'])
            name.set_hexpand(True)
            name.set_ellipsize(Pango.EllipsizeMode.END)
            name.set_tooltip_text(ev['title'])
            name.add_css_class('event-name')
            toggle = Gtk.Button(label="✓")
            toggle.add_css_class('done-toggle')
            toggle.add_css_class('check-toggle')
            toggle.add_css_class('done-toggle-active' if done else 'done-toggle-inactive')
            toggle.connect("clicked", self._on_task_toggle, ev)
            delete = Gtk.Button(label="×")
            delete.add_css_class('done-toggle')
            delete.connect("clicked", self._on_delete_clicked, ev, date)
            row.append(dot)
            row.append(name)
            row.append(toggle)
            row.append(delete)
        elif isinstance(ev, dict) and ev.get('type') == 'event':
            dot = Gtk.Label(label="•")
            dot.add_css_class('event-dot')
            name = Gtk.Label(label=ev['title'])
            name.set_hexpand(True)
            name.set_ellipsize(Pango.EllipsizeMode.END)
            name.set_tooltip_text(ev['title'])
            name.add_css_class('event-name')
            delete = Gtk.Button(label="×")
            delete.add_css_class('done-toggle')
            delete.connect("clicked", self._on_delete_clicked, ev, date)
            row.append(dot)
            row.append(name)
            row.append(delete)
        else:
            dot = Gtk.Label(label="•")
            dot.add_css_class('event-dot')
            name = Gtk.Label(label=ev)
            name.set_ellipsize(Pango.EllipsizeMode.END)
            name.set_tooltip_text(ev)
            name.add_css_class('event-name')
            row.append(dot)
            row.append(name)

        return row

    def _update_day_panel(self, date):
        if date == self.today:
            heading = f"<b>{self.t('today')}</b>  <span alpha='60%'>{self._day_short_label(date)}</span>"
        else:
            heading = f"<b>{self._weekday_full(date)}</b>  <span alpha='60%'>{self._day_short_label(date)}</span>"
        self.day_label.set_markup(heading)

        while True:
            child = self.events_box.get_first_child()
            if child is None:
                break
            self.events_box.remove(child)

        def _sort_key(e):
            if isinstance(e, dict):
                if e.get('type') == 'task':
                    return 0 if not e.get('done') else 1
                return 2
            return 2
        day_events = sorted(self.events.get(date.isoformat(), []), key=_sort_key)
        if day_events:
            for ev in day_events:
                self.events_box.append(self._make_event_row(ev, date))
        else:
            empty = Gtk.Label(label=self.t('no_events'))
            empty.add_css_class('no-events')
            empty.set_halign(Gtk.Align.START)
            self.events_box.append(empty)

    def _on_add_mode_toggled(self, btn, mode):
        if not btn.get_active():
            return
        self.add_mode = mode
        self.add_time_row.set_visible(mode == 'event')
        self.add_title_entry.set_placeholder_text(self.t('event_title_ph') if mode == 'event' else self.t('task_title_ph'))

    def _on_add_clicked(self, _):
        self.settings_revealer.set_reveal_child(False)
        self.add_title_entry.set_text("")
        self.add_start_entry.set_text("")
        self.add_end_entry.set_text("")
        self.add_status_label.set_text("")
        self.add_revealer.set_reveal_child(not self.add_revealer.get_reveal_child())
        if self.add_revealer.get_reveal_child():
            self.add_title_entry.grab_focus()

    def _on_save_event_clicked(self, _):
        title = self.add_title_entry.get_text().strip()

        if not title:
            self.add_status_label.set_text(self.t('title_required'))
            return

        mode = self.add_mode
        d = self.selected_date

        start_time = end_time = None
        if mode == 'event':
            start_text = self.add_start_entry.get_text().strip() or "09:00"
            end_text = self.add_end_entry.get_text().strip() or "10:00"
            try:
                start_time = datetime.datetime.strptime(start_text, '%H:%M').time()
                end_time = datetime.datetime.strptime(end_text, '%H:%M').time()
            except ValueError:
                self.add_status_label.set_text(self.t('use_hhmm'))
                return

        self.add_status_label.set_text(self.t('saving'))
        self.add_title_entry.set_sensitive(False)

        def do_save():
            try:
                from googleapiclient.discovery import build
                creds = _get_credentials()
                if creds is None:
                    raise RuntimeError("Not authenticated")

                if mode == 'task':
                    tasks_service = build('tasks', 'v1', credentials=creds)
                    task_lists = tasks_service.tasklists().list().execute()
                    items = task_lists.get('items', [])
                    tasklist_id = items[0]['id'] if items else '@default'

                    due_dt = datetime.datetime.combine(d, datetime.time(0, 0), tzinfo=datetime.timezone.utc)
                    due_str = due_dt.isoformat().replace('+00:00', 'Z')

                    result = tasks_service.tasks().insert(
                        tasklist=tasklist_id, body={'title': title, 'due': due_str},
                    ).execute()

                    self.events.setdefault(d.isoformat(), []).append({
                        'type': 'task', 'id': result['id'], 'lid': tasklist_id,
                        'title': title, 'done': False,
                    })
                else:
                    service = build('calendar', 'v3', credentials=creds)
                    tz = self._get_tz()
                    start_dt = datetime.datetime.combine(d, start_time, tzinfo=tz)
                    end_dt = datetime.datetime.combine(d, end_time, tzinfo=tz)
                    body = {
                        'summary': title,
                        'start': {'dateTime': start_dt.isoformat()},
                        'end': {'dateTime': end_dt.isoformat()},
                    }
                    result = service.events().insert(calendarId='primary', body=body).execute()

                    label = f"{title} {_fmt_time(start_dt, self.time_format)}-{_fmt_time(end_dt, self.time_format)}"
                    self.events.setdefault(d.isoformat(), []).append({
                        'type': 'event', 'id': result['id'], 'cal_id': 'primary', 'title': label,
                    })

                def after():
                    self.add_title_entry.set_sensitive(True)
                    self.add_revealer.set_reveal_child(False)
                    self._update_day_panel(d)
                    self._build_grid()
                    return False
                GLib.idle_add(after)
            except Exception as e:
                print(f'[add error] {e}', file=sys.stderr)
                def after_err():
                    self.add_title_entry.set_sensitive(True)
                    self.add_status_label.set_text(self.t('failed_save'))
                    return False
                GLib.idle_add(after_err)
        threading.Thread(target=do_save, daemon=True).start()

    def _on_edit_clicked(self, _):
        d = self.selected_date
        url = f"https://calendar.google.com/calendar/r/day/{d.year}/{d.month}/{d.day}"
        subprocess.Popen(['xdg-open', url])
        self._hide()

    def _on_delete_clicked(self, btn, ev, date):
        btn.set_sensitive(False)

        def do_delete():
            try:
                from googleapiclient.discovery import build
                creds = _get_credentials()
                if creds is None:
                    raise RuntimeError("Not authenticated")
                if ev.get('type') == 'task':
                    tasks_service = build('tasks', 'v1', credentials=creds)
                    tasks_service.tasks().delete(tasklist=ev['lid'], task=ev['id']).execute()
                else:
                    service = build('calendar', 'v3', credentials=creds)
                    service.events().delete(calendarId=ev['cal_id'], eventId=ev['id']).execute()

                day_list = self.events.get(date.isoformat(), [])
                if ev in day_list:
                    day_list.remove(ev)

                def after():
                    self._update_day_panel(date)
                    self._build_grid()
                    return False
                GLib.idle_add(after)
            except Exception as e:
                print(f'[delete error] {e}', file=sys.stderr)
                def after_err():
                    btn.set_sensitive(True)
                    return False
                GLib.idle_add(after_err)
        threading.Thread(target=do_delete, daemon=True).start()

    def _on_task_toggle(self, btn, task):
        # Flip instantly — no set_sensitive(False)/dimming, so the click
        # never looks delayed. The network call runs in the background;
        # only a genuine failure reverts the visual state.
        new_done = not task.get('done', False)
        task['done'] = new_done
        btn.remove_css_class('done-toggle-inactive' if new_done else 'done-toggle-active')
        btn.add_css_class('done-toggle-active' if new_done else 'done-toggle-inactive')

        def do_toggle():
            try:
                from googleapiclient.discovery import build
                creds = _get_credentials()
                if creds is None:
                    return
                service = build('tasks', 'v1', credentials=creds)
                new_status = 'completed' if new_done else 'needsAction'
                service.tasks().patch(
                    tasklist=task['lid'], task=task['id'], body={'status': new_status},
                ).execute()
                _run_sync()
                def after():
                    self.events = load_events()
                    self._build_grid()
                    self._update_day_panel(self.selected_date)
                    return False
                GLib.idle_add(after)
            except Exception as e:
                print(f'[task toggle error] {e}', file=sys.stderr)
                def after_err():
                    task['done'] = not new_done
                    self._update_day_panel(self.selected_date)
                    return False
                GLib.idle_add(after_err)
        threading.Thread(target=do_toggle, daemon=True).start()

    def _draw_refresh_icon(self, da, ctx, width, height):
        r, g, b = self._refresh_fg

        if not hasattr(self, '_refresh_layout'):
            self._refresh_layout = PangoCairo.create_layout(ctx)
            font_name = NERD_FONT.split(',')[0].strip()
            self._refresh_layout.set_font_description(
                Pango.FontDescription.from_string(f"{font_name} {self.fs(12)}"))
            self._refresh_layout.set_text("\uf021")
            ink, _ = self._refresh_layout.get_pixel_extents()
            self._refresh_ink = ink
        else:
            PangoCairo.update_layout(ctx, self._refresh_layout)

        ink = self._refresh_ink
        x = (width - ink.width) / 2 - ink.x
        y = (height - ink.height) / 2 - ink.y

        if self._refresh_angle != 0.0:
            ctx.translate(width / 2, height / 2)
            ctx.rotate(self._refresh_angle)
            ctx.translate(-width / 2, -height / 2)

        ctx.set_source_rgba(r, g, b, 1.0)
        ctx.move_to(x, y)
        PangoCairo.show_layout(ctx, self._refresh_layout)

    def _on_refresh_clicked(self, _):
        self.refresh_btn.set_sensitive(False)

        def tick():
            self._refresh_angle += 0.15
            self._refresh_da.queue_draw()
            return not self.refresh_btn.get_sensitive()
        self._refresh_spin_timer = GLib.timeout_add(16, tick)

        def do_sync():
            _run_sync()
            def after():
                if self._refresh_spin_timer:
                    GLib.source_remove(self._refresh_spin_timer)
                    self._refresh_spin_timer = None
                self._refresh_angle = 0.0
                self._refresh_da.queue_draw()
                self.events = load_events()
                self._build_grid()
                self._update_day_panel(self.selected_date)
                self.refresh_btn.set_sensitive(True)
                return False
            GLib.idle_add(after)
        threading.Thread(target=do_sync, daemon=True).start()

    def _navigate(self, delta):
        self.month += delta
        if self.month < 1:
            self.month = 12
            self.year -= 1
        elif self.month > 12:
            self.month = 1
            self.year += 1
        self.month_label.set_markup(f"<b>{self._month_year_label()}</b>")
        self._build_grid()

    def _apply_css(self):
        colors, appearance = load_colors(self.settings if hasattr(self, 'settings') else {})
        fg = colors['foreground']
        bg = colors['background']
        accent = colors['accent']
        accent2 = colors.get('accent2', accent)
        error = colors.get('error', '#ff5555')
        self._refresh_fg = hex_to_rgb_float(fg)

        opacity = appearance.get('opacity', 0.92)
        popover_opacity = appearance.get('popover_opacity', 0.98)
        radius = appearance.get('radius', 12)
        btn_radius = max(4, radius - 2)

        font_family = self.settings.get('font_family', '') if hasattr(self, 'settings') else ''
        font_family_css = f'font-family: "{font_family}";' if font_family else ''

        def fs(px):
            return self.fs(px)

        css = f"""
      window {{
          background: transparent;
      }}
      .click-shield {{
          background: rgba(0, 0, 0, 0.01);
      }}
      .popup-bg {{
          background: {hex_to_rgba(bg, opacity)};
          border-radius: {radius}px;
          border: 1px solid {hex_to_rgba(accent, 0.35)};
          padding: 10px;
      }}
      .panel-bg {{
          background: {hex_to_rgba(bg, popover_opacity)};
          border-radius: {btn_radius}px;
      }}
      button {{
          background: transparent;
          border: 1px solid transparent;
          border-radius: {btn_radius}px;
          color: {fg};
          font-size: {fs(11)}px;
          font-weight: 500;
          {font_family_css}
      }}
      button:hover {{
          background: rgba(255, 255, 255, 0.07);
      }}
      button:active {{
          background: rgba(255, 255, 255, 0.18);
          transition: background 50ms;
      }}
      button:focus,
      button:focus-visible {{
          outline: none;
          box-shadow: none;
      }}
      label {{
          color: {fg};
          font-size: {fs(11)}px;
          font-weight: 500;
          {font_family_css}
      }}
      .weekday {{
          color: {hex_to_rgba(fg, 0.4)};
          font-size: {fs(11)}px;
      }}
      .day-number {{
          font-weight: 600;
      }}
      .other-month {{
          opacity: 0.2;
      }}
      .other-month:hover {{
          background: transparent;
      }}
      .weekend {{
          background: {hex_to_rgba(fg, 0.04)};
          border-radius: {btn_radius}px;
      }}
      .weekend-label {{
          color: {hex_to_rgba(accent2, 0.8)};
      }}
      .today {{
          background: {hex_to_rgba(accent, 0.5)};
          border-radius: {btn_radius}px;
          font-weight: bold;
      }}
      .today:hover {{
          background: {hex_to_rgba(accent, 0.65)};
      }}
      .selected {{
          border: 1px solid {hex_to_rgba(accent, 0.8)};
          border-radius: {btn_radius}px;
      }}
      .today.selected {{
          border: 1px solid {fg};
      }}
      .event-bar {{
          background: {hex_to_rgba(accent, 0.9)};
          border-radius: 2px;
          min-height: 2px;
      }}
      .today .event-bar {{
          background: {fg};
      }}
      .panel-divider {{
          background: {hex_to_rgba(accent, 0.2)};
          min-width: 1px;
          margin: 0 8px;
      }}
      .day-panel {{
          padding: 2px 4px 2px 0;
      }}
      .day-heading {{
          font-size: {fs(11)}px;
          margin-bottom: 4px;
      }}
      .event-dot {{
          color: {hex_to_rgba(accent, 0.9)};
          font-size: {fs(10)}px;
      }}
      .event-name {{
          font-size: {fs(11)}px;
          color: {fg};
      }}
      .task-bar {{
          background: {hex_to_rgba(error, 0.9)};
          border-radius: 2px;
          min-height: 2px;
      }}
      .task-dot {{
          color: {hex_to_rgba(error, 0.9)};
          font-size: {fs(10)}px;
      }}
      .done-dot {{
          color: {hex_to_rgba('#50fa7b', 0.9)};
          font-size: {fs(10)}px;
      }}
      .done-toggle {{
          font-size: {fs(10)}px;
          min-width: {self.s(18)}px;
          min-height: {self.s(18)}px;
          padding: 0;
          border-radius: 4px;
      }}
      .check-toggle {{
          font-size: {fs(15)}px;
          min-width: {self.s(26)}px;
          min-height: {self.s(26)}px;
      }}
      button:disabled {{
          opacity: 1;
      }}
      .done-toggle-inactive {{
          border: 1px solid {hex_to_rgba(fg, 0.2)};
          color: transparent;
      }}
      .done-toggle-inactive:hover {{
          border-color: {hex_to_rgba('#50fa7b', 0.6)};
          color: {hex_to_rgba('#50fa7b', 0.6)};
      }}
      .done-toggle-active {{
          border: 1px solid {hex_to_rgba('#50fa7b', 0.6)};
          color: {hex_to_rgba('#50fa7b', 0.9)};
          background: {hex_to_rgba('#50fa7b', 0.15)};
      }}
      .no-events {{
          font-size: {fs(11)}px;
          color: {hex_to_rgba(fg, 0.35)};
          font-style: italic;
      }}
      .add-status {{
          color: {hex_to_rgba(fg, 0.6)};
      }}
      .add-status-error {{
          color: {hex_to_rgba(error, 0.9)};
      }}
      .add-btn {{
          background: {hex_to_rgba(accent, 0.15)};
          border: 1px solid {hex_to_rgba(accent, 0.35)};
          border-radius: {btn_radius}px;
          color: {fg};
          font-size: {fs(11)}px;
          padding: 4px 0;
          margin-top: 4px;
      }}
      .add-btn:hover {{
          background: {hex_to_rgba(accent, 0.28)};
      }}
      .refresh-btn {{
          background: {hex_to_rgba(accent, 0.15)};
          border: 1px solid {hex_to_rgba(accent, 0.35)};
          color: {fg};
          font-size: {fs(15)}px;
          padding: 0;
      }}
      .refresh-btn:hover {{
          background: {hex_to_rgba(accent, 0.28)};
      }}
      .nerd-label {{
          font-family: "{NERD_FONT}";
          font-size: {fs(13)}px;
      }}
      .add-btn.nerd {{
          font-family: "{NERD_FONT}";
          font-size: {fs(13)}px;
          padding: 0;
      }}
      .add-btn.nerd label {{
          all: unset;
          font-family: "{NERD_FONT}";
          font-size: {fs(13)}px;
          color: {fg};
          margin-left: -2px;
      }}
      .setup-title {{
          font-size: {fs(14)}px;
          font-weight: bold;
          color: {fg};
          margin-top: 8px;
          margin-bottom: 6px;
      }}
      .setup-msg {{
          font-size: {fs(11)}px;
          color: {hex_to_rgba(fg, 0.6)};
          margin-bottom: 12px;
      }}
      """.encode()
        if not hasattr(self, '_css_provider'):
            self._css_provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_display(
                self.get_display(), self._css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        with open('/tmp/ycal_debug.css', 'wb') as _dbg:
            _dbg.write(css)
        self._css_provider.load_from_data(css)


win = None

def on_activate(app):
    global win
    _settings = load_settings()
    Gtk.Widget.set_default_direction(
        Gtk.TextDirection.RTL if _settings.get('lang') == 'ar' else Gtk.TextDirection.LTR
    )
    win = CalendarPopup(app)
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, lambda: win.toggle() or True)
    sync_in_background()
    GLib.timeout_add_seconds(SYNC_INTERVAL_SEC, sync_in_background)


app = Gtk.Application(application_id="com.waybar.ycal")
app.connect("activate", on_activate)

try:
    app.run(None)
finally:
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
