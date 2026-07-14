import sys

path = "/home/bo7afes/.config/waybar-ycal/popup.py"
with open(path, encoding='utf-8') as f:
    src = f.read()

def apply(label, old, new):
    global src
    if old not in src:
        sys.exit(f"ABORT at step '{label}': anchor not found.")
    src = src.replace(old, new, 1)

apply(
    "button-label",
    'add_btn = Gtk.Button(label="+ Add task")',
    'add_btn = Gtk.Button(label="+ Add")'
)

apply(
    "mode-toggle-and-time-fields",
    '''        self.add_title_entry = Gtk.Entry()
        self.add_title_entry.set_placeholder_text("Task title")
        self.add_title_entry.connect("activate", self._on_save_event_clicked)
        form_box.append(self.add_title_entry)

        self.add_status_label = Gtk.Label(label="")''',
    '''        self.add_mode = 'task'

        mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add_mode_task_btn = Gtk.ToggleButton(label="Task")
        self.add_mode_task_btn.add_css_class('add-btn')
        self.add_mode_task_btn.set_active(True)
        self.add_mode_task_btn.connect("toggled", self._on_add_mode_toggled, 'task')
        self.add_mode_event_btn = Gtk.ToggleButton(label="Event")
        self.add_mode_event_btn.add_css_class('add-btn')
        self.add_mode_event_btn.set_group(self.add_mode_task_btn)
        self.add_mode_event_btn.connect("toggled", self._on_add_mode_toggled, 'event')
        mode_row.append(self.add_mode_task_btn)
        mode_row.append(self.add_mode_event_btn)
        form_box.append(mode_row)

        self.add_title_entry = Gtk.Entry()
        self.add_title_entry.set_placeholder_text("Task title")
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
        self.add_time_row.append(Gtk.Label(label="\u2013"))
        self.add_time_row.append(self.add_end_entry)
        self.add_time_row.set_visible(False)
        form_box.append(self.add_time_row)

        self.add_status_label = Gtk.Label(label="")'''
)

apply(
    "add-mode-toggled-handler",
    '''    def _on_add_clicked(self, _):
        self.add_title_entry.set_text("")
        self.add_status_label.set_text("")
        self.add_revealer.set_reveal_child(not self.add_revealer.get_reveal_child())
        if self.add_revealer.get_reveal_child():
            self.add_title_entry.grab_focus()''',
    '''    def _on_add_mode_toggled(self, btn, mode):
        if not btn.get_active():
            return
        self.add_mode = mode
        self.add_time_row.set_visible(mode == 'event')
        self.add_title_entry.set_placeholder_text("Event title" if mode == 'event' else "Task title")

    def _on_add_clicked(self, _):
        self.add_title_entry.set_text("")
        self.add_start_entry.set_text("")
        self.add_end_entry.set_text("")
        self.add_status_label.set_text("")
        self.add_revealer.set_reveal_child(not self.add_revealer.get_reveal_child())
        if self.add_revealer.get_reveal_child():
            self.add_title_entry.grab_focus()'''
)

apply(
    "save-handler-branch",
    '''    def _on_save_event_clicked(self, _):
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
        threading.Thread(target=do_save, daemon=True).start()''',
    '''    def _on_save_event_clicked(self, _):
        title = self.add_title_entry.get_text().strip()

        if not title:
            self.add_status_label.set_text("Title required")
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
                self.add_status_label.set_text("Use HH:MM format")
                return

        self.add_status_label.set_text("Saving...")
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
                else:
                    service = build('calendar', 'v3', credentials=creds)
                    tz = datetime.datetime.now().astimezone().tzinfo
                    start_dt = datetime.datetime.combine(d, start_time, tzinfo=tz)
                    end_dt = datetime.datetime.combine(d, end_time, tzinfo=tz)
                    body = {
                        'summary': title,
                        'start': {'dateTime': start_dt.isoformat()},
                        'end': {'dateTime': end_dt.isoformat()},
                    }
                    result = service.events().insert(calendarId='primary', body=body).execute()

                    label = f"{title} {start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
                    self.events.setdefault(d.isoformat(), []).append({
                        'type': 'event',
                        'id': result['id'],
                        'cal_id': 'primary',
                        'title': label,
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
                    self.add_status_label.set_text("Failed to save")
                    return False
                GLib.idle_add(after_err)
        threading.Thread(target=do_save, daemon=True).start()'''
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print("Task/Event mode toggle patch applied successfully.")
