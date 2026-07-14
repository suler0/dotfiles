import sys

path = "/home/bo7afes/.config/waybar-ycal/popup.py"
with open(path, encoding='utf-8') as f:
    src = f.read()

def apply(label, old, new):
    global src
    if old not in src:
        sys.exit(f"ABORT at step '{label}': anchor not found.")
    src = src.replace(old, new, 1)

# 1. Enter key in the title entry triggers save
apply(
    "enter-to-save",
    '''        self.add_title_entry = Gtk.Entry()
        self.add_title_entry.set_placeholder_text("Task title")
        form_box.append(self.add_title_entry)

        self.add_status_label = Gtk.Label(label="")''',
    '''        self.add_title_entry = Gtk.Entry()
        self.add_title_entry.set_placeholder_text("Task title")
        self.add_title_entry.connect("activate", self._on_save_event_clicked)
        form_box.append(self.add_title_entry)

        self.add_status_label = Gtk.Label(label="")'''
)

# 2. Store calendar events as dicts with id/cal_id (needed for deletion) instead of plain strings
apply(
    "event-dict-format",
    '''            for item in result.get('items', []):
                start = item['start']
                end = item['end']
                title = item.get('summary', '(no title)')
                if 'dateTime' in start:
                    # Timed event: show on start date with time range
                    dt = datetime.datetime.fromisoformat(start['dateTime'])
                    dt_end = datetime.datetime.fromisoformat(end['dateTime'])
                    label = f"{title} {dt.strftime('%H:%M')}-{dt_end.strftime('%H:%M')}"
                    events_by_date.setdefault(dt.date().isoformat(), []).append(label)
                else:
                    # All-day event: Google end date is exclusive, so expand across all days
                    d = datetime.date.fromisoformat(start['date'])
                    d_end = datetime.date.fromisoformat(end['date'])
                    while d < d_end:
                        events_by_date.setdefault(d.isoformat(), []).append(title)
                        d += datetime.timedelta(days=1)''',
    '''            for item in result.get('items', []):
                start = item['start']
                end = item['end']
                title = item.get('summary', '(no title)')
                event_id = item.get('id')
                if 'dateTime' in start:
                    # Timed event: show on start date with time range
                    dt = datetime.datetime.fromisoformat(start['dateTime'])
                    dt_end = datetime.datetime.fromisoformat(end['dateTime'])
                    label = f"{title} {dt.strftime('%H:%M')}-{dt_end.strftime('%H:%M')}"
                    events_by_date.setdefault(dt.date().isoformat(), []).append({
                        'type': 'event',
                        'id': event_id,
                        'cal_id': cal_id,
                        'title': label,
                    })
                else:
                    # All-day event: Google end date is exclusive, so expand across all days
                    d = datetime.date.fromisoformat(start['date'])
                    d_end = datetime.date.fromisoformat(end['date'])
                    while d < d_end:
                        events_by_date.setdefault(d.isoformat(), []).append({
                            'type': 'event',
                            'id': event_id,
                            'cal_id': cal_id,
                            'title': title,
                        })
                        d += datetime.timedelta(days=1)'''
)

# 3. Update month-grid dot detection to recognize the new event dict format (keeps legacy string fallback)
apply(
    "grid-dot-detection",
    '''            has_events = any(isinstance(e, str) for e in day_events)
            has_tasks = any(isinstance(e, dict) and not e.get('done') for e in day_events)''',
    '''            has_events = any(isinstance(e, str) for e in day_events) or any(isinstance(e, dict) and e.get('type') == 'event' for e in day_events)
            has_tasks = any(isinstance(e, dict) and e.get('type') == 'task' and not e.get('done') for e in day_events)'''
)

# 4. Fix sort order now that events are dicts too (tasks first, then events)
apply(
    "sort-order",
    '''        day_events = sorted(
            self.events.get(date.isoformat(), []),
            key=lambda e: 0 if (isinstance(e, dict) and not e.get('done')) else (1 if isinstance(e, dict) else 2)
        )''',
    '''        def _sort_key(e):
            if isinstance(e, dict):
                if e.get('type') == 'task':
                    return 0 if not e.get('done') else 1
                return 2
            return 2
        day_events = sorted(
            self.events.get(date.isoformat(), []),
            key=_sort_key
        )'''
)

# 5. Rebuild _make_event_row to add delete buttons for both tasks and events
apply(
    "make-event-row",
    '''    def _make_event_row(self, ev):
        """Build a single event or task row for the day panel."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        if isinstance(ev, dict):
            # Task row: colored dot, title, done toggle button
            done = ev.get('done', False)
            dot = Gtk.Label(label="\u2022")
            dot.add_css_class('done-dot' if done else 'task-dot')
            name = Gtk.Label(label=ev['title'])
            name.set_hexpand(True)
            name.set_ellipsize(Pango.EllipsizeMode.END)
            name.set_tooltip_text(ev['title'])
            name.add_css_class('event-name')
            toggle = Gtk.Button(label="\u2713")
            toggle.add_css_class('done-toggle')
            toggle.add_css_class('done-toggle-active' if done else 'done-toggle-inactive')
            toggle.connect("clicked", self._on_task_toggle, ev)
            row.append(dot)
            row.append(name)
            row.append(toggle)
        else:
            # Event row: accent dot + title
            dot = Gtk.Label(label="\u2022")
            dot.add_css_class('event-dot')
            name = Gtk.Label(label=ev)
            name.set_ellipsize(Pango.EllipsizeMode.END)
            name.set_tooltip_text(ev)
            name.add_css_class('event-name')
            row.append(dot)
            row.append(name)

        return row''',
    '''    def _make_event_row(self, ev, date):
        """Build a single event or task row for the day panel."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        if isinstance(ev, dict) and ev.get('type') == 'task':
            done = ev.get('done', False)
            dot = Gtk.Label(label="\u2022")
            dot.add_css_class('done-dot' if done else 'task-dot')
            name = Gtk.Label(label=ev['title'])
            name.set_hexpand(True)
            name.set_ellipsize(Pango.EllipsizeMode.END)
            name.set_tooltip_text(ev['title'])
            name.add_css_class('event-name')
            toggle = Gtk.Button(label="\u2713")
            toggle.add_css_class('done-toggle')
            toggle.add_css_class('done-toggle-active' if done else 'done-toggle-inactive')
            toggle.connect("clicked", self._on_task_toggle, ev)
            delete = Gtk.Button(label="\u00d7")
            delete.add_css_class('done-toggle')
            delete.connect("clicked", self._on_delete_clicked, ev, date)
            row.append(dot)
            row.append(name)
            row.append(toggle)
            row.append(delete)
        elif isinstance(ev, dict) and ev.get('type') == 'event':
            dot = Gtk.Label(label="\u2022")
            dot.add_css_class('event-dot')
            name = Gtk.Label(label=ev['title'])
            name.set_hexpand(True)
            name.set_ellipsize(Pango.EllipsizeMode.END)
            name.set_tooltip_text(ev['title'])
            name.add_css_class('event-name')
            delete = Gtk.Button(label="\u00d7")
            delete.add_css_class('done-toggle')
            delete.connect("clicked", self._on_delete_clicked, ev, date)
            row.append(dot)
            row.append(name)
            row.append(delete)
        else:
            # Legacy plain-string event from a cache written before this patch.
            # No delete button until the next sync refreshes it into dict form.
            dot = Gtk.Label(label="\u2022")
            dot.add_css_class('event-dot')
            name = Gtk.Label(label=ev)
            name.set_ellipsize(Pango.EllipsizeMode.END)
            name.set_tooltip_text(ev)
            name.add_css_class('event-name')
            row.append(dot)
            row.append(name)

        return row'''
)

# 6. Pass `date` through to _make_event_row so the delete handler knows which day's list to update
apply(
    "call-site-date",
    '''        if day_events:
            for ev in day_events:
                self.events_box.append(self._make_event_row(ev))''',
    '''        if day_events:
            for ev in day_events:
                self.events_box.append(self._make_event_row(ev, date))'''
)

# 7. Add the delete handler itself
apply(
    "delete-handler",
    '''    def _on_edit_clicked(self, _):
        d = self.selected_date
        url = f"https://calendar.google.com/calendar/r/day/{d.year}/{d.month}/{d.day}"
        subprocess.Popen(['xdg-open', url])
        self._hide()''',
    '''    def _on_edit_clicked(self, _):
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
        threading.Thread(target=do_delete, daemon=True).start()'''
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print("Delete + enter-key patch applied successfully.")
