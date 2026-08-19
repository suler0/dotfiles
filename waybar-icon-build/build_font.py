import fontforge

font = fontforge.font()
font.encoding = "UnicodeFull"
font.fontname = "WaybarIcons"
font.familyname = "Waybar Icons"
font.fullname = "Waybar Icons"
font.em = 1000
font.ascent = 800
font.descent = 200

icons = {
    0x100000: "svgs/alacritty.svg",
    0x100001: "svgs/discord.svg",
    0x100002: "svgs/helium.svg",
    0x100003: "svgs/telegram.svg",
    0x100004: "svgs/brave.svg",
    0x100005: "svgs/steam.svg",
    0x100006: "svgs/heroic.svg",
    0x100007: "svgs/obs.svg",
    0x100008: "svgs/obsidian.svg",
    0x100009: "svgs/localsend.svg",
    0x10000A: "svgs/gimp.svg",
    0x10000B: "svgs/chrome.svg",
    0x10000C: "svgs/nvim.svg",
    0x10000D: "svgs/thunar.svg",
    0x10000E: "svgs/mpv.svg",
}

for codepoint, path in icons.items():
    glyph = font.createChar(codepoint)
    glyph.importOutlines(path)
    glyph.removeOverlap()
    bbox = glyph.boundingBox()
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    scale = 700.0 / max(w, h) if max(w, h) > 0 else 1
    glyph.transform((scale, 0, 0, scale, -bbox[0]*scale, -bbox[1]*scale))
    glyph.width = 1000

font.generate("waybar_icon_font.ttf")
print("Font built:", len(icons), "glyphs")
