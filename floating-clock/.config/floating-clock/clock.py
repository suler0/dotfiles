#!/usr/bin/python3
from ctypes import CDLL
CDLL('libgtk4-layer-shell.so')
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, GLib, Gtk4LayerShell, Gdk, Pango, PangoCairo
import datetime
import json
import os
import subprocess
import signal
import math
import itertools

CACHE_FILE = os.path.expanduser('~/.cache/prayer-times/timings.json')
ACCENT = (0.878, 0.341, 0.333)
ACCENT_HEX = "#E05755"
NAMES_AR = {"Fajr": "الفجر", "Dhuhr": "الظهر", "Asr": "العصر", "Maghrib": "المغرب", "Isha": "العشاء"}
SOUND_CANDIDATES = [
    "/usr/share/sounds/freedesktop/stereo/complete.oga",
    "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga",
]


def play_sound():
    for path in SOUND_CANDIDATES:
        if os.path.exists(path):
            try:
                subprocess.Popen(["paplay", path])
            except Exception:
                pass
            return


def load_prayer_times():
    try:
        with open(CACHE_FILE) as f:
            data = json.load(f)
        return {k: data[k] for k in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]}
    except Exception:
        return {}


def next_prayer():
    prayers = load_prayer_times()
    now = datetime.datetime.now()
    today = now.date()
    best_name, best_dt = None, None
    for name, t in prayers.items():
        h, m = map(int, t.split(":"))
        dt = datetime.datetime.combine(today, datetime.time(h, m))
        if dt > now and (best_dt is None or dt < best_dt):
            best_name, best_dt = name, dt
    if best_name is None:
        h, m = map(int, prayers.get("Fajr", "04:00").split(":"))
        best_dt = datetime.datetime.combine(today + datetime.timedelta(days=1), datetime.time(h, m))
        best_name = "Fajr"
    diff = best_dt - now
    total_sec = int(diff.total_seconds())
    hrs, rem = divmod(total_sec, 3600)
    mins, secs = divmod(rem, 60)
    countdown = f"{hrs}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins}:{secs:02d}"
    return NAMES_AR.get(best_name, best_name), countdown


def fmt_seconds(total):
    total = max(0, int(total))
    mins, secs = divmod(total, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins}:{secs:02d}"


_timer_id_counter = itertools.count(1)


class Timer:
    def __init__(self, label, duration_sec):
        self.id = next(_timer_id_counter)
        self.label = label
        self.duration = duration_sec
        self.remaining_at_pause = duration_sec
        self.end_time = datetime.datetime.now() + datetime.timedelta(seconds=duration_sec)
        self.paused = False
        self.done = False

    def remaining(self):
        if self.paused:
            return self.remaining_at_pause
        return (self.end_time - datetime.datetime.now()).total_seconds()

    def fraction_remaining(self):
        if self.duration <= 0:
            return 0
        return max(0.0, min(1.0, self.remaining() / self.duration))

    def pause(self):
        if not self.paused:
            self.remaining_at_pause = max(0, self.remaining())
            self.paused = True

    def resume(self):
        if self.paused:
            self.end_time = datetime.datetime.now() + datetime.timedelta(seconds=self.remaining_at_pause)
            self.paused = False


class ClockWidget(Gtk.DrawingArea):
    def __init__(self, on_click):
        super().__init__()
        self.set_content_width(200)
        self.set_content_height(80)
        self.set_draw_func(self.draw, None)
        self.opacity_level = 0.55
        self.target_opacity = 0.55

        self.mode = "clock"
        self.timers = []  # list of Timer
        self.stopwatch_start = None
        self.stopwatch_running = False
        self.stopwatch_elapsed = 0.0
        self.laps = []

        GLib.timeout_add(1000, self.tick)
        GLib.timeout_add(50, self.animate_opacity)

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", self.on_enter)
        motion.connect("leave", self.on_leave)
        self.add_controller(motion)

        click = Gtk.GestureClick()
        click.set_button(1)  # left click only
        click.connect("released", lambda g, n, x, y: on_click())
        self.add_controller(click)

    def on_enter(self, controller, x, y):
        self.target_opacity = 1.0

    def on_leave(self, controller):
        self.target_opacity = 0.55

    def animate_opacity(self):
        diff = self.target_opacity - self.opacity_level
        if abs(diff) > 0.01:
            self.opacity_level += diff * 0.2
            self.queue_draw()
        return True

    def tick(self):
        for t in list(self.timers):
            if not t.done and not t.paused and t.remaining() <= 0:
                t.done = True
                GLib.idle_add(self.notify_timer_done, t.label)
        self.queue_draw()
        return True

    def active_timer(self):
        undone = [t for t in self.timers if not t.done]
        if undone:
            return min(undone, key=lambda t: t.remaining())
        if self.timers:
            return self.timers[-1]
        return None

    def rounded_rect(self, cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -1.5708, 0)
        cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
        cr.arc(x + r, y + h - r, r, 1.5708, 3.14159)
        cr.arc(x + r, y + r, r, 3.14159, 4.71239)
        cr.close_path()

    def draw_glow_text(self, cr, layout, x, y, color, op, glow_strength=1.0):
        for offset, alpha in [(2, 0.025), (1, 0.04)]:
            cr.set_source_rgba(color[0], color[1], color[2], alpha * op * glow_strength)
            for dx in (-offset, 0, offset):
                for dy in (-offset, 0, offset):
                    if dx == 0 and dy == 0:
                        continue
                    cr.move_to(x + dx, y + dy)
                    PangoCairo.show_layout(cr, layout)
        cr.set_source_rgba(color[0], color[1], color[2], 0.95 * op)
        cr.move_to(x, y)
        PangoCairo.show_layout(cr, layout)

    def draw_centered(self, cr, width, text, font_desc, y, color, op, glow=0.4):
        layout = PangoCairo.create_layout(cr)
        layout.set_text(text, -1)
        layout.set_font_description(Pango.FontDescription(font_desc))
        ink, logical = layout.get_pixel_extents()
        tx = (width - logical.width) / 2
        self.draw_glow_text(cr, layout, tx, y, color, op, glow_strength=glow)
        return logical.height

    def draw_progress_ring(self, cr, cx, cy, radius, fraction, op):
        cr.set_line_width(3)
        cr.set_source_rgba(1, 1, 1, 0.12 * op)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.stroke()

        cr.set_source_rgba(*ACCENT, 0.9 * op)
        start = -math.pi / 2
        end = start + fraction * 2 * math.pi
        cr.arc(cx, cy, radius, start, end)
        cr.stroke()

    def draw(self, area, cr, width, height, data):
        now = datetime.datetime.now()
        op = self.opacity_level

        radius_corner = 16
        cr.set_source_rgba(0.08, 0.08, 0.1, 0.55 * op)
        self.rounded_rect(cr, 4, 4, width - 8, height - 8, radius_corner)
        cr.fill()
        cr.set_source_rgba(*ACCENT, 0.25 * op)
        cr.set_line_width(1.5)
        self.rounded_rect(cr, 4, 4, width - 8, height - 8, radius_corner)
        cr.stroke()

        if self.mode == "clock":
            time_str = now.strftime("%H:%M:%S")
            h1 = self.draw_centered(cr, width, time_str, "Target 2000 18", 12, (1, 1, 1), op, glow=0.35)
            name, countdown = next_prayer()
            sub_text = f"{name}  ‎-{countdown}"
            self.draw_centered(cr, width, sub_text, "Ubuntu Arabic Bold 11", 12 + h1 + 6, ACCENT, op, glow=0.6)

        elif self.mode == "timer":
            t = self.active_timer()
            if t is None:
                self.draw_centered(cr, width, "TIMER", "Target 2000 16", 12, (1, 1, 1), op, glow=0.35)
                self.draw_centered(cr, width, "set below", "Ubuntu Arabic Bold 10", 42, ACCENT, op, glow=0.5)
            else:
                self.draw_progress_ring(cr, width - 22, 22, 12, t.fraction_remaining(), op)
                disp = fmt_seconds(t.remaining())
                color = ACCENT if t.done else (1, 1, 1)
                self.draw_centered(cr, width, disp, "Target 2000 18", 10, color, op, glow=0.5 if t.done else 0.35)
                extra = len(self.timers) - 1
                if t.done:
                    label = "TIME'S UP"
                elif t.paused:
                    label = "PAUSED"
                else:
                    label = t.label or "TIMER"
                if extra > 0:
                    label += f"  +{extra}"
                self.draw_centered(cr, width, label, "Ubuntu Arabic Bold 9", 44, ACCENT, op, glow=0.5)

        elif self.mode == "stopwatch":
            if self.stopwatch_running:
                elapsed = self.stopwatch_elapsed + (now - self.stopwatch_start).total_seconds()
            else:
                elapsed = self.stopwatch_elapsed
            disp = fmt_seconds(elapsed)
            self.draw_centered(cr, width, disp, "Target 2000 18", 12, (1, 1, 1), op, glow=0.35)
            label = "RUNNING" if self.stopwatch_running else "PAUSED"
            if self.laps:
                label += f"  \u00b7 {len(self.laps)} laps"
            self.draw_centered(cr, width, label, "Ubuntu Arabic Bold 9", 44, ACCENT, op, glow=0.5)

    def notify_timer_done(self, label):
        try:
            subprocess.Popen(["notify-send", "-u", "critical", "Timer", f"{label or 'Timer'} — Time's up!"])
        except Exception:
            pass
        play_sound()
        return False


class PlacementController:
    """Right-click the clock to enter placement mode: a full-screen
    transparent overlay appears, and the next click instantly moves
    the clock there. Escape cancels."""
    def __init__(self, app, win, clock_width, clock_height):
        self.app = app
        self.win = win
        self.clock_width = clock_width
        self.clock_height = clock_height
        self.overlay_win = None

        click = Gtk.GestureClick()
        click.set_button(3)  # right click
        click.connect("released", lambda g, n, x, y: self.enter_placement_mode())
        win.add_controller(click)

    def enter_placement_mode(self):
        if self.overlay_win is not None:
            return

        display = Gdk.Display.get_default()
        monitor = display.get_monitors().get_item(0)
        geometry = monitor.get_geometry()
        screen_w = geometry.width
        screen_h = geometry.height

        overlay = Gtk.ApplicationWindow(application=self.app)
        Gtk4LayerShell.init_for_window(overlay)
        Gtk4LayerShell.set_layer(overlay, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_anchor(overlay, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(overlay, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(overlay, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_anchor(overlay, Gtk4LayerShell.Edge.RIGHT, True)
        Gtk4LayerShell.set_exclusive_zone(overlay, -1)
        Gtk4LayerShell.set_keyboard_mode(overlay, Gtk4LayerShell.KeyboardMode.EXCLUSIVE)
        overlay.set_decorated(False)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"window.placement-overlay { background: alpha(#000000, 0.15); }")
        Gtk.StyleContext.add_provider_for_display(
            display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        overlay.add_css_class("placement-overlay")

        click = Gtk.GestureClick()
        click.set_button(1)
        click.connect("released", lambda g, n, x, y: self.place_at(x, y, screen_w, screen_h))
        overlay.add_controller(click)

        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self.on_key)
        overlay.add_controller(key)

        overlay.present()
        self.overlay_win = overlay

    def on_key(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close_overlay()
            return True
        return False

    def place_at(self, x, y, screen_w, screen_h):
        new_right = max(0, screen_w - x - self.clock_width / 2)
        new_bottom = max(0, screen_h - y - self.clock_height / 2)
        Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.RIGHT, int(new_right))
        Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.BOTTOM, int(new_bottom))
        self.close_overlay()

    def close_overlay(self):
        if self.overlay_win is not None:
            self.overlay_win.close()
            self.overlay_win = None


class MenuController:
    def __init__(self, clock):
        self.clock = clock
        self.container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.container.set_visible(False)
        self.container.set_margin_top(4)
        self.container.set_margin_bottom(4)
        self.container.set_margin_start(4)
        self.container.set_margin_end(4)
        self.rebuild()

    def toggle(self):
        self.container.set_visible(not self.container.get_visible())
        if self.container.get_visible():
            self.rebuild()

    def open(self):
        self.container.set_visible(True)
        self.rebuild()

    def clear(self):
        child = self.container.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.container.remove(child)
            child = nxt

    def styled_button(self, label):
        btn = Gtk.Button(label=label)
        btn.add_css_class("clockbtn")
        return btn

    def hrow(self):
        return Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

    def rebuild(self):
        self.clear()
        c = self.clock

        if c.mode == "clock":
            row = self.hrow()
            b1 = self.styled_button("Timer")
            b1.connect("clicked", lambda b: self.enter_timer_setup())
            b2 = self.styled_button("Stopwatch")
            b2.connect("clicked", lambda b: self.start_stopwatch())
            row.append(b1)
            row.append(b2)
            self.container.append(row)

        elif c.mode == "timer":
            for t in c.timers:
                trow = self.hrow()
                lbl = Gtk.Label(label=f"{t.label or 'timer'}: {fmt_seconds(t.remaining())}")
                lbl.set_xalign(0)
                lbl.add_css_class("clocklabel")
                trow.append(lbl)
                if not t.done:
                    pr_btn = self.styled_button("Resume" if t.paused else "Pause")

                    def make_pause_handler(timer_obj, button):
                        def handler(_b):
                            if timer_obj.paused:
                                timer_obj.resume()
                            else:
                                timer_obj.pause()
                            self.rebuild()
                            self.clock.queue_draw()
                        return handler

                    pr_btn.connect("clicked", make_pause_handler(t, pr_btn))
                    trow.append(pr_btn)

                cancel_btn = self.styled_button("x")

                def make_cancel_handler(timer_obj):
                    def handler(_b):
                        c.timers.remove(timer_obj)
                        self.rebuild()
                        self.clock.queue_draw()
                    return handler

                cancel_btn.connect("clicked", make_cancel_handler(t))
                trow.append(cancel_btn)
                self.container.append(trow)

            preset_row = self.hrow()
            for mins in (5, 10, 25):
                pb = self.styled_button(f"{mins}m")

                def make_preset_handler(m):
                    def handler(_b):
                        c.timers.append(Timer(f"{m}m", m * 60))
                        self.rebuild()
                        self.clock.queue_draw()
                    return handler

                pb.connect("clicked", make_preset_handler(mins))
                preset_row.append(pb)
            self.container.append(preset_row)

            entry_row = self.hrow()
            entry = Gtk.Entry()
            entry.set_placeholder_text("minutes")
            entry.set_max_width_chars(6)
            start_btn = self.styled_button("Add")

            def do_start(_b):
                txt = entry.get_text().strip()
                try:
                    mins = float(txt)
                except ValueError:
                    return
                c.timers.append(Timer("", mins * 60))
                entry.set_text("")
                self.rebuild()
                c.queue_draw()

            start_btn.connect("clicked", do_start)
            entry.connect("activate", do_start)
            entry_row.append(entry)
            entry_row.append(start_btn)
            self.container.append(entry_row)

            back = self.styled_button("Back")
            back.connect("clicked", lambda b: self.back_to_clock())
            self.container.append(back)

        elif c.mode == "stopwatch":
            row = self.hrow()
            toggle_btn = self.styled_button("Pause" if c.stopwatch_running else "Start")

            def do_toggle(_b):
                now = datetime.datetime.now()
                if c.stopwatch_running:
                    c.stopwatch_elapsed += (now - c.stopwatch_start).total_seconds()
                    c.stopwatch_running = False
                else:
                    c.stopwatch_start = now
                    c.stopwatch_running = True
                self.rebuild()
                c.queue_draw()

            toggle_btn.connect("clicked", do_toggle)

            lap_btn = self.styled_button("Lap")

            def do_lap(_b):
                if c.stopwatch_running:
                    elapsed = c.stopwatch_elapsed + (datetime.datetime.now() - c.stopwatch_start).total_seconds()
                else:
                    elapsed = c.stopwatch_elapsed
                c.laps.append(elapsed)
                self.rebuild()
                c.queue_draw()

            lap_btn.connect("clicked", do_lap)

            reset_btn = self.styled_button("Reset")

            def do_reset(_b):
                c.stopwatch_running = False
                c.stopwatch_elapsed = 0.0
                c.stopwatch_start = None
                c.laps = []
                self.rebuild()
                c.queue_draw()

            reset_btn.connect("clicked", do_reset)

            back = self.styled_button("Back")
            back.connect("clicked", lambda b: self.back_to_clock())

            row.append(toggle_btn)
            row.append(lap_btn)
            row.append(reset_btn)
            row.append(back)
            self.container.append(row)

            if c.laps:
                laps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                for i, lap in enumerate(reversed(c.laps[-4:])):
                    idx = len(c.laps) - i
                    lbl = Gtk.Label(label=f"#{idx}  {fmt_seconds(lap)}")
                    lbl.set_xalign(0)
                    lbl.add_css_class("clocklabel")
                    laps_box.append(lbl)
                self.container.append(laps_box)

    def enter_timer_setup(self):
        self.clock.mode = "timer"
        self.rebuild()
        self.clock.queue_draw()

    def start_stopwatch(self):
        self.clock.mode = "stopwatch"
        self.clock.stopwatch_elapsed = 0.0
        self.clock.stopwatch_start = datetime.datetime.now()
        self.clock.stopwatch_running = True
        self.clock.laps = []
        self.container.set_visible(False)
        self.clock.queue_draw()

    def back_to_clock(self):
        c = self.clock
        c.mode = "clock"
        c.timers = []
        c.stopwatch_running = False
        c.stopwatch_elapsed = 0.0
        c.laps = []
        self.container.set_visible(False)
        c.queue_draw()


def on_activate(app):
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(f"""
        window {{ background: transparent; }}
        .clockbtn {{
            background: alpha(#ffffff, 0.08);
            color: #ffffff;
            border-radius: 8px;
            padding: 3px 8px;
            font-size: 11px;
            border: 1px solid alpha({ACCENT_HEX}, 0.4);
        }}
        .clockbtn:hover {{
            background: alpha({ACCENT_HEX}, 0.3);
        }}
        .clocklabel {{
            color: #ffffff;
            font-size: 11px;
        }}
        entry {{
            background: alpha(#ffffff, 0.08);
            color: #ffffff;
            border-radius: 8px;
            padding: 3px 6px;
            font-size: 11px;
            border: 1px solid alpha({ACCENT_HEX}, 0.4);
        }}
    """.encode())
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    win = Gtk.ApplicationWindow(application=app)
    Gtk4LayerShell.init_for_window(win)
    Gtk4LayerShell.set_layer(win, Gtk4LayerShell.Layer.OVERLAY)
    Gtk4LayerShell.set_anchor(win, Gtk4LayerShell.Edge.BOTTOM, True)
    Gtk4LayerShell.set_anchor(win, Gtk4LayerShell.Edge.RIGHT, True)
    Gtk4LayerShell.set_margin(win, Gtk4LayerShell.Edge.BOTTOM, 20)
    Gtk4LayerShell.set_margin(win, Gtk4LayerShell.Edge.RIGHT, 20)
    Gtk4LayerShell.set_exclusive_zone(win, -1)
    Gtk4LayerShell.set_keyboard_mode(win, Gtk4LayerShell.KeyboardMode.ON_DEMAND)

    win.set_decorated(False)

    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    menu = {}

    def on_click():
        menu["controller"].toggle()

    clock = ClockWidget(on_click)
    menu["controller"] = MenuController(clock)

    outer.append(clock)
    outer.append(menu["controller"].container)

    win.set_child(outer)
    PlacementController(app, win, 200, 80)

    def on_sigusr2():
        menu["controller"].open()
        return GLib.SOURCE_CONTINUE

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR2, on_sigusr2)

    win.present()


app = Gtk.Application(application_id="com.b7s.floatingclock")
app.connect("activate", on_activate)
app.run(None)
