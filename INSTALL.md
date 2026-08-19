# Full reinstall guide

Follow these steps in order on a fresh Arch install to get back to the current setup.

## 1. Base packages

```bash
sudo pacman -S --needed git stow paru --noconfirm
git clone https://github.com/suler0/dotfiles.git ~/dotfiles
cd ~/dotfiles/package-lists
./restore-packages.sh
```

## 2. Link configs with Stow

```bash
cd ~/dotfiles
stow hypr waybar waybar-ycal rofi alacritty swaync wal waypaper wlogout \
     skripts scritps floating-clock wpg
```

If stow complains about an existing file/folder (e.g. `~/.config/hypr` already
has default content), delete it first, then re-run stow for that package:
```bash
rm -rf ~/.config/hypr
```

## 3. Fonts

```bash
# DSEG (digital clock font, used by floating-clock)
paru -S ttf-dseg --noconfirm

# Target 2000 (used by floating-clock's main display)
curl -sL "https://www.fontspace.com/get/family/4wx70" -o /tmp/target2000.zip
mkdir -p /tmp/target2000 && unzip -o /tmp/target2000.zip -d /tmp/target2000
mkdir -p ~/.local/share/fonts
cp /tmp/target2000/*.otf ~/.local/share/fonts/

# Custom Waybar workspace-icon font (rebuild from source SVGs)
sudo pacman -S --needed fontforge python-fonttools --noconfirm
cd ~/dotfiles/waybar-icon-build
fontforge -script build_font.py
cp waybar_icon_font.ttf ~/.local/share/fonts/

fc-cache -f
```

## 4. Cursor theme

```bash
paru -S bibata-cursor-theme-bin --noconfirm
hyprpm add https://github.com/virtcode/hypr-dynamic-cursors
hyprpm enable dynamic-cursors
```

## 5. Lockscreen (qylock)

```bash
sudo pacman -S --needed sddm quickshell qt6-declarative qt6-5compat qt6-svg \
     qt6-multimedia qt6-multimedia-ffmpeg gst-plugins-base gst-plugins-good \
     gst-plugins-bad gst-plugins-ugly fzf --noconfirm

git clone https://github.com/Darkkal44/qylock.git ~/qylock
cd ~/qylock
chmod +x sddm.sh quickshell.sh
./sddm.sh
./quickshell.sh
```

Bind your lock keybind (already set in `hyprland.lua`) to:

Note: some qylock themes need copyrighted fonts dropped manually into
`themes/<theme_name>/font/` — see qylock's own README for the list.

## 6. Pywal / GTK theming (wpgtk)

```bash
sudo pacman -S --needed python-pywal python-gobject python-pillow libxslt --noconfirm
paru -S wpgtk-git --noconfirm

# Config is already restored by stow (step 2). Just generate + apply:
wpg -a ~/myfiles/Pictures/Wallpapers/<your-wallpaper>
wpg -s ~/myfiles/Pictures/Wallpapers/<your-wallpaper>
```

## 7. Manual steps (not automated, do these yourself)

- Restore Google Calendar `credentials.json` to
  `~/.config/waybar-ycal/credentials.json` (excluded from git on purpose)
- Re-add browser bookmarks (Helium, Brave) — not backed up by this repo
- Re-add wallpaper collection to `~/myfiles/Pictures/Wallpapers`
- Developer toolchains not covered by pacman/AUR: `rustup`, .NET SDK, Java,
  npm globals, Python venvs, Flutter/Dart — reinstall these separately
