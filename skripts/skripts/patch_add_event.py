import sys

path = "/home/bo7afes/.config/waybar-ycal/popup.py"
with open(path) as f:
    src = f.read()

# 1. Widen calendar scope from read-only to full access (needed to create events)
old_scopes = """SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/tasks',
]"""
new_scopes = """SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks',
]"""
if old_scopes not in src:
    sys.exit("ABORT: SCOPES block not found — file may already be patched or differs from expected.")
src = src.replace(old_scopes, new_scopes, 1)

# 2. Insert inline quick-add form after btn_row is appended to right_box
old_btnrow_end = """        btn_row.append(add_btn)
        btn_row.append(edit_btn)
        self.right_box.append(btn_row)

        self._update_day_panel(self.today)"""
new_btnrow_end = '''        btn_row.append(add_btn)
        btn_row.append(edit_btn)
        self.right_box.append(btn_row)

        self.add_revealer = Gtk.Revealer()
        self.add_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        form_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        form_box.add_css_class('add-form')

        self.add_title_entry = Gtk.Entry()
        self.add_title_entry.set_placeholder_text("Event title")
        form_box.append(self.add_title_entry)

        time_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add_start_entry = Gtk.Entry()
        self.add_start_entry.set_placeholder_text("09:00")
        self.add_start_entry.set_max_length(5)
        self.add_start_entry.set_width_chars(6)
        self.add_end_entry = Gtk.Entry()
        self.add_end_entry.set_placeholder_text("10:00")
        self.add_end_entry.set_max_length(5)
        self.add_end_entry.set_width_chars(6)
        time_row.append(self.add_start_entry)
        time_row.append(Gtk.Label(label="\u2013"))
        time_row.append(self.add_end_entry)
        form_box.append(time_row)

        self.add_status_label = Gtk.Label(label="")
        self.add_status_label.add_css_class('add-status')
        self.add_status_label.set_halign(Gtk.Align.START)
        form_box.append(self.add_status_label)

        form_btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class('add-btn')
        save_btn.connect("clicked", self._on_save_event_clicked)
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.add_css_class('add-btn')
        cancel_btn.connect("clicked", lambda _: self.add_revealer.set_reveal_child(False))
        form_btn_row.append(save_btn)
        form_btn_row.append(cancel_btn)
        form_box.append(form_btn_row)

        self.add_revealer.set_child(form_box)
        self.right_box.append(self.add_revealer)

        self._update_day_panel(self.today)'''
if old_btnrow_end not in src:
    sys.exit("ABORT: btn_row anchor not found.")
src = src.replace(old_btnrow_end, new_btnrow_end, 1)

# 3. Replace _on_add_clicked (browser-open) with form-toggle + add _on_save_event_clicked
old_add_clicked = '''    def _on_add_clicked(self, _):
        d = self.selected_date
        url = (f"https://calendar.google.com/calendar/r/eventedit"
               f"?dates={d.strftime('%Y%m%d')}/{d.strftime('%Y%m%d')}")
        subprocess.Popen(['xdg-open', url])
        self._hide()'''
new_add_clicked = '''    def _on_add_clicked(self, _):
        self.add_title_entry.set_text("")
        self.add_start_entry.set_text("")
        self.add_end_entry.set_text("")
        self.add_status_label.set_text("")
        self.add_revealer.set_reveal_child(not self.add_revealer.get_reveal_child())
        if self.add_revealer.get_reveal_child():
            self.add_title_entry.grab_focus()

    def _on_save_event_clicked(self, _):
        title = self.add_title_entry.get_text().strip()
        start_text = self.add_start_entry.get_text().strip() or "09:00"
        end_text = self.add_end_entry.get_text().strip() or "10:00"

        if not title:
            self.add_status_label.set_text("Title required")
            return

        try:
            start_time = datetime.datetime.strptime(start_text, '%H:%M').time()
            end_time = datetime.datetime.strptime(end_text, '%H:%M').time()
        except ValueError:
            self.add_status_label.set_text("Use HH:MM format")
            return

        d = self.selected_date
        self.add_status_label.set_text("Saving...")
        self.add_title_entry.set_sensitive(False)

        def do_save():
            try:
                from googleapiclient.discovery import build
                creds = _get_credentials()
                if creds is None:
                    raise RuntimeError("Not authenticated")
                service = build('calendar', 'v3', credentials=creds)
                tz = datetime.datetime.now().astimezone().tzinfo
                start_dt = datetime.datetime.combine(d, start_time, tzinfo=tz)
                end_dt = datetime.datetime.combine(d, end_time, tzinfo=tz)
                body = {
                    'summary': title,
                    'start': {'dateTime': start_dt.isoformat()},
                    'end': {'dateTime': end_dt.isoformat()},
                }
                service.events().insert(calendarId='primary', body=body).execute()

                label = f"{title} {start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
                self.events.setdefault(d.isoformat(), []).append(label)

                def after():
                    self.add_title_entry.set_sensitive(True)
                    self.add_revealer.set_reveal_child(False)
                    self._update_day_panel(d)
                    self._build_grid()
                    return False
                GLib.idle_add(after)
            except Exception as e:
                print(f'[add event error] {e}', file=sys.stderr)
                def after_err():
                    self.add_title_entry.set_sensitive(True)
                    self.add_status_label.set_text("Failed to save")
                    return False
                GLib.idle_add(after_err)
        threading.Thread(target=do_save, daemon=True).start()'''
if old_add_clicked not in src:
    sys.exit("ABORT: _on_add_clicked anchor not found.")
src = src.replace(old_add_clicked, new_add_clicked, 1)

with open(path, 'w') as f:
    f.write(src)

print("Patch applied successfully.")
