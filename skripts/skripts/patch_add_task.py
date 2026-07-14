import sys

path = "/home/bo7afes/.config/waybar-ycal/popup.py"
with open(path) as f:
    src = f.read()

old_label = 'add_btn = Gtk.Button(label="+ Add event")'
new_label = 'add_btn = Gtk.Button(label="+ Add task")'
if old_label not in src:
    sys.exit("ABORT: add_btn label not found.")
src = src.replace(old_label, new_label, 1)

old_form_middle = '''        self.add_title_entry = Gtk.Entry()
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

        self.add_status_label = Gtk.Label(label="")'''
new_form_middle = '''        self.add_title_entry = Gtk.Entry()
        self.add_title_entry.set_placeholder_text("Task title")
        form_box.append(self.add_title_entry)

        self.add_status_label = Gtk.Label(label="")'''
if old_form_middle not in src:
    sys.exit("ABORT: form middle anchor not found.")
src = src.replace(old_form_middle, new_form_middle, 1)

old_add_clicked = '''    def _on_add_clicked(self, _):
        self.add_title_entry.set_text("")
        self.add_start_entry.set_text("")
        self.add_end_entry.set_text("")
        self.add_status_label.set_text("")
        self.add_revealer.set_reveal_child(not self.add_revealer.get_reveal_child())
        if self.add_revealer.get_reveal_child():
            self.add_title_entry.grab_focus()'''
new_add_clicked = '''    def _on_add_clicked(self, _):
        self.add_title_entry.set_text("")
        self.add_status_label.set_text("")
        self.add_revealer.set_reveal_child(not self.add_revealer.get_reveal_child())
        if self.add_revealer.get_reveal_child():
            self.add_title_entry.grab_focus()'''
if old_add_clicked not in src:
    sys.exit("ABORT: _on_add_clicked anchor not found.")
src = src.replace(old_add_clicked, new_add_clicked, 1)

old_save = '''    def _on_save_event_clicked(self, _):
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

new_save = '''    def _on_save_event_clicked(self, _):
        title = self.add_title_entry.get_text().strip()

        if not title:
            self.add_status_label.set_text("Title required")
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
                tasks_service = build('tasks', 'v1', credentials=creds)

                task_lists = tasks_service.tasklists().list().execute()
                items = task_lists.get('items', [])
                tasklist_id = items[0]['id'] if items else '@default'

                due_dt = datetime.datetime.combine(d, datetime.time(0, 0), tzinfo=datetime.timezone.utc)
                due_str = due_dt.isoformat().replace('+00:00', 'Z')

                result = tasks_service.tasks().insert(
                    tasklist=tasklist_id,
                    body={'title': title, 'due': due_str},
                ).execute()

                self.events.setdefault(d.isoformat(), []).append({
                    'type': 'task',
                    'id': result['id'],
                    'lid': tasklist_id,
                    'title': title,
                    'done': False,
                })

                def after():
                    self.add_title_entry.set_sensitive(True)
                    self.add_revealer.set_reveal_child(False)
                    self._update_day_panel(d)
                    self._build_grid()
                    return False
                GLib.idle_add(after)
            except Exception as e:
                print(f'[add task error] {e}', file=sys.stderr)
                def after_err():
                    self.add_title_entry.set_sensitive(True)
                    self.add_status_label.set_text("Failed to save")
                    return False
                GLib.idle_add(after_err)
        threading.Thread(target=do_save, daemon=True).start()'''

if old_save not in src:
    sys.exit("ABORT: _on_save_event_clicked anchor not found.")
src = src.replace(old_save, new_save, 1)

with open(path, 'w') as f:
    f.write(src)

print("Task patch applied successfully.")
