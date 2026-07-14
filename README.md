# Dotfiles

My personal Hyprland rice configs, managed with GNU Stow.

## Included

- `hypr` — Hyprland window manager config
- `waybar` / `waybar-ycal` — status bar + calendar widget
- `rofi` — app launcher
- `alacritty` — terminal emulator
- `swaync` — notification daemon
- `wal` — pywal color scheme templates
- `waypaper` — wallpaper manager
- `wlogout` — logout menu
- `skripts` / `scritps` — helper scripts

## Setup on a new machine

**1. Install git and stow**
```bash
sudo pacman -S git stow
```

**2. Clone this repo**
```bash
git clone https://github.com/suler0/dotfiles.git ~/dotfiles
```

**3. Go into the folder**
```bash
cd ~/dotfiles
```

**4. Link everything with stow**
```bash
stow hypr waybar waybar-ycal rofi alacritty swaync wal waypaper wlogout skripts scritps
```

This creates symlinks from `~/.config/*` back into `~/dotfiles/*`, so your configs are instantly active.

**If stow complains about existing files** (e.g. "existing target is not a symlink"), it means the app already created a default config on the new machine. Delete it first, then re-run stow:
```bash
rm -rf ~/.config/hypr   # replace 'hypr' with whichever package failed
```

**5. Restore Google Calendar credentials (not included in repo)**
Copy your `credentials.json` back manually, or generate a new one from Google Cloud Console, and place it at:## Dependencies (install separately)

- [qylock](https://github.com/Darkkal44/qylock) — lockscreen theme switcher
