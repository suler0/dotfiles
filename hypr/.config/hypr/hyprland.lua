

local terminal    = "alacritty"
local fileManager = "Thunar"
local menu        = "rofi -show drun"
local mainMod     = "SUPER"

-- Monitor
hl.monitor({
    output   = "eDP-1",
    mode     = "1366x768@59.97300",
    position = "auto",
    scale    = 1,
})

-- Autostart
hl.on("hyprland.start", function()
    hl.exec_cmd("wl-paste --type text --watch cliphist store")
    hl.exec_cmd("/home/bo7afes/.local/share/quickshell-lockscreen/lock.sh")
    hl.exec_cmd("wl-paste --type image --watch cliphist store")
    hl.exec_cmd("awww-daemon")
    hl.exec_cmd("waybar")
    hl.exec_cmd("swaync")
    hl.exec_cmd("~/.config/waybar/scripts/update_workspace_icons.py")
    hl.exec_cmd("~/.config/waybar/scripts/hyprworkstyle.py")
    hl.exec_cmd("hyprctl setcursor Bibata-Modren-Amber 24")
end)

-- Environment variables
hl.env("XCURSOR_THEME", "Bibata-Modren-Amber")
hl.env("HYPRCURSOR_THEME", "Bibata-Modren-Amber")
hl.env("XCURSOR_SIZE", "24")
hl.env("HYPRCURSOR_SIZE", "24")

-- Look and feel
hl.config({
    general = {
        gaps_in  = 2,
        gaps_out = 4,
        border_size = 2,
        col = {
            active_border   = "rgba(B18F61ee)",
            inactive_border = "rgba(98602Eaa)",
        },
        resize_on_border = true,
        extend_border_grab_area = 20,
        allow_tearing = false,
        layout = "dwindle",
    },
    decoration = {
        rounding       = 10,
        rounding_power = 10,
        active_opacity   = 1.0,
        inactive_opacity = 0.95,
        shadow = {
            enabled      = true,
            range        = 20,
            render_power = 7,
            color        = 0xee1a1a1a,
        },
        blur = {
            enabled  = true,
            size     = 6,
            passes   = 3,
            vibrancy = 0.1696,
        },
    },
    animations = {
        enabled = true,
    },
})

-- Curves
hl.curve("easeOutQuint",   { type = "bezier", points = { {0.23, 1},    {0.32, 1}    } })
hl.curve("easeInOutCubic", { type = "bezier", points = { {0.65, 0.05}, {0.36, 1}    } })
hl.curve("linear",         { type = "bezier", points = { {0, 0},       {1, 1}       } })
hl.curve("almostLinear",   { type = "bezier", points = { {0.5, 0.5},   {0.75, 1}    } })
hl.curve("quick",          { type = "bezier", points = { {0.15, 0},    {0.1, 1}     } })

-- Animations
hl.animation({ leaf = "global",        enabled = true, speed = 1,    bezier = "default" })
hl.animation({ leaf = "border",        enabled = true, speed = 5.39, bezier = "easeOutQuint" })
hl.animation({ leaf = "windows",       enabled = true, speed = 4,    bezier = "easeOutQuint" })
hl.animation({ leaf = "windowsIn",     enabled = true, speed = 4,    bezier = "easeOutQuint", style = "slide bottom" })
hl.animation({ leaf = "windowsOut",    enabled = true, speed = 3,    bezier = "easeOutQuint", style = "slide bottom" })
hl.animation({ leaf = "fadeIn",        enabled = true, speed = 1,    bezier = "almostLinear" })
hl.animation({ leaf = "fadeOut",       enabled = true, speed = 1,    bezier = "almostLinear" })
hl.animation({ leaf = "fade",          enabled = true, speed = 1,    bezier = "quick" })
hl.animation({ leaf = "workspaces",    enabled = true, speed = 1,    bezier = "almostLinear", style = "fade" })
hl.animation({ leaf = "zoomFactor",    enabled = true, speed = 7,    bezier = "quick" })

-- Dwindle
hl.config({
    dwindle = {
        preserve_split = true,
    },
})

-- Master
hl.config({
    master = {
        new_status = "master",
    },
})

-- Misc
hl.config({
    misc = {
        force_default_wallpaper = 0,
        disable_hyprland_logo   = true,
    },
})

-- Input
hl.config({
    input = {
        kb_layout  = "us,ara",
        kb_options = "grp:alt_shift_toggle",
        follow_mouse = 1,
        sensitivity  = 0,
        touchpad = {
            natural_scroll = true,
        },
    },
})

-- Gesture
hl.gesture({
    fingers   = 3,
    direction = "horizontal",
    action    = "workspace",
})

-- Device
hl.device({
    name        = "epic-mouse-v1",
    sensitivity = -0.5,
})

-- Window rules
hl.window_rule({
    name  = "suppress-maximize",
    match = { class = ".*" },
    suppress_event = "maximize",
})

hl.window_rule({
    name  = "fix-xwayland-drags",
    match = { class = "^$", title = "^$", xwayland = true, float = true, fullscreen = false, pin = false },
    no_focus = true,
})

hl.window_rule({
    name  = "wlogout-float",
    match = { class = "wlogout" },
    float  = true,
    center = true,
    size   = "500 500",
    border_size = 0,
})

hl.window_rule({
    name  = "clock-popup",
    match = { class = "clock-popup" },
    float  = true,
    pin    = true,
    border_size = 0,
    no_focus = true,
    size   = "160 80",
    move   = "100%-180 20",
    opacity = 0.90,
})

-- Layer rules
hl.layer_rule({ match = { namespace = "wlogout" }, blur = true })
hl.layer_rule({ match = { namespace = "waybar" }, blur = true, ignore_alpha = 0.5 })
hl.layer_rule({ match = { namespace = "swaync-notification-window" }, blur = true, ignore_alpha = 0.5 })
hl.layer_rule({ match = { namespace = "swaync-control-center" }, blur = true, ignore_alpha = 0.3 })
hl.layer_rule({ match = { namespace = "rofi" }, blur = true, ignore_alpha = 0.5 })

-- Keybindings
hl.bind(mainMod .. " + Return", hl.dsp.exec_cmd(terminal))
hl.bind(mainMod .. " + E",      hl.dsp.exec_cmd(fileManager))
hl.bind(mainMod .. " + Space",  hl.dsp.exec_cmd("pkill rofi || rofi -show drun"))
hl.bind(mainMod .. " + B",      hl.dsp.exec_cmd("brave"))
hl.bind(mainMod .. " + F10",    hl.dsp.exec_cmd("obs"))
hl.bind(mainMod .. " + D",      hl.dsp.exec_cmd("discord"))
hl.bind("CTRL + SHIFT + Escape", hl.dsp.exec_cmd("alacritty -e btop"))
hl.bind(mainMod .. " + t", hl.dsp.exec_cmd("Telegram"))
hl.bind(mainMod .. " + C", hl.dsp.window.close())
hl.bind(mainMod .. " + M", hl.dsp.exit())
hl.bind(mainMod .. " + P", hl.dsp.window.pseudo())
hl.bind(mainMod .. " + J", hl.dsp.layout("togglesplit"))

-- Wallpaper and bar
hl.bind(mainMod .. " + SHIFT + P", hl.dsp.exec_cmd("waypaper --folder ~/myfiles/Pictures/Wallpapers"))
hl.bind(mainMod .. " + W",         hl.dsp.exec_cmd("~/.config/waybar/reload.sh"))
hl.bind(mainMod .. " + Z",         hl.dsp.exec_cmd("~/.config/floating-clock/toggle.sh"))

-- Session
hl.bind(mainMod .. " + SHIFT + X", hl.dsp.exec_cmd("loginctl poweroff"))
hl.bind(mainMod .. " + SHIFT + R", hl.dsp.exec_cmd("systemctl reboot"))
hl.bind(mainMod .. " +SHIFT + L", hl.dsp.exec_cmd("/home/bo7afes/.local/share/quickshell-lockscreen/lock.sh"))
-- Screenshots
--hl.bind("Print",         hl.dsp.exec_cmd("grim ~/myfiles/Pictures/screenshot-$(date +%F-%T).png"))
--hl.bind("SHIFT + Print", hl.dsp.exec_cmd("grim -g \"$(slurp)\" ~/myfiles/Pictures/area-$(date +%F-%T).png"))
--hl.bind(mainMod .. " + SHIFT + S", hl.dsp.exec_cmd("grim -g \"$(slurp)\" - | wl-copy --type image/png"))
-- Screenshots with rishot
hl.bind("Print", hl.dsp.exec_cmd("/home/bo7afes/.local/bin/rishot monitor"))
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.exec_cmd("/home/bo7afes/.local/bin/rishot"))
-- Focus movement
hl.bind(mainMod .. " + H", hl.dsp.focus({ direction = "left" }))
hl.bind(mainMod .. " + L", hl.dsp.focus({ direction = "right" }))
hl.bind(mainMod .. " + K", hl.dsp.focus({ direction = "up" }))
hl.bind(mainMod .. " + J", hl.dsp.focus({ direction = "down" }))
hl.bind(mainMod .. " + V", function()
    hl.dispatch(hl.dsp.window.float({ action = "toggle" }))
    local w = hl.get_active_window()
    if w ~= nil and w.floating then
        local monitor = hl.get_active_monitor()
        local winW, winH = 500, 500
        hl.dispatch(hl.dsp.window.resize({ x = winW, y = winH, relative = false }))
        hl.dispatch(hl.dsp.window.move({
            x = math.floor((monitor.width - winW) / 2),
            y = math.floor((monitor.height - winH) / 2),
            relative = false
        }))
    end
end)
-- Workspaces
for i = 1, 10 do
    local key = i % 10
    hl.bind(mainMod .. " + " .. key,         hl.dsp.focus({ workspace = i }))
    hl.bind(mainMod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }))
end

hl.bind(mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mainMod .. " + mouse_up",   hl.dsp.focus({ workspace = "e-1" }))

hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Media keys
hl.bind("XF86AudioRaiseVolume",  hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 1%+"),  { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume",  hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 1%-"),        { locked = true, repeating = true })
hl.bind("XF86AudioMute",         hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),       { locked = true, repeating = true })
hl.bind("XF86AudioMicMute",      hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"),     { locked = true, repeating = true })
hl.bind("XF86MonBrightnessUp",   hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%+"),                    { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%-"),                    { locked = true, repeating = true })

hl.bind("XF86AudioNext",  hl.dsp.exec_cmd("playerctl next"),        { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"),  { locked = true })
hl.bind("XF86AudioPlay",  hl.dsp.exec_cmd("playerctl play-pause"),  { locked = true })
hl.bind("XF86AudioPrev",  hl.dsp.exec_cmd("playerctl previous"),    { locked = true })

-- Wallpaper cycling
hl.bind(mainMod .. " + CTRL + Right", hl.dsp.exec_cmd("~/.config/waybar/scripts/wallpaper-next.sh"))
hl.bind(mainMod .. " + CTRL + Left",  hl.dsp.exec_cmd("~/.config/waybar/scripts/wallpaper-prev.sh"))

hl.bind(mainMod .. " + SHIFT + V", hl.dsp.exec_cmd("cliphist list | rofi -dmenu | cliphist decode | wl-copy"))

hl.bind(mainMod .. " + CTRL + H", hl.dsp.exec_cmd("~/scripts/hyprload.sh"))
hl.bind(mainMod .. " + SHIFT + Right", hl.dsp.exec_cmd("~/.config/qylock/next-theme.sh"))
hl.bind(mainMod .. " + SHIFT + Left",  hl.dsp.exec_cmd("~/.config/qylock/prev-theme.sh"))
hl.bind(mainMod .. " + SHIFT + H", hl.dsp.exec_cmd("helium-browser"))

hl.window_rule({
    name            = "xvb-hide",
    match           = { class = "xwaylandvideobridge" },
    opacity         = "0.0 override 0.0 override",
    no_anim         = true,
    no_focus        = true,
    no_initial_focus = true,
})

-- ========================================
-- DYNAMIC CURSORS PLUGIN
-- ========================================
if hl.plugin.dynamic_cursors then
    hl.config {
        plugin = {
            dynamic_cursors = {
                enabled = true,
                mode = "stretch",
                stretch = { limit = 800, activation = "quadratic", window = 100 },
                shake = { enabled = true, threshold = 6.0, base = 4.0, speed = 4.0, timeout = 2000 },
            }
        }
    }
end

-- Hyprland-run windowrule
hl.window_rule({
    name  = "move-hyprland-run",
    match = { class = "hyprland-run" },

    move  = "20 monitor_h-120",
    float = true,
})

local function zoom_screen(offset)
  local current = hl.get_config("cursor.zoom_factor")
  local new_zoom = math.max(1.0, math.min(3.0, current + offset))
  hl.config({ cursor = { zoom_factor = new_zoom } })
end
hl.bind("SUPER + SHIFT + mouse_down", function() zoom_screen(0.3) end)
hl.bind("SUPER + SHIFT + mouse_up", function() zoom_screen(-0.3) end)
