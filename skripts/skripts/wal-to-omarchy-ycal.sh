#!/bin/bash
WAL_JSON="$HOME/.cache/wal/colors.json"
OUT="$HOME/.config/omarchy/current/theme/colors.toml"
bg=$(python3 -c "import json;print(json.load(open('$WAL_JSON'))['special']['background'])")
fg=$(python3 -c "import json;print(json.load(open('$WAL_JSON'))['special']['foreground'])")
accent=$(python3 -c "import json;print(json.load(open('$WAL_JSON'))['colors']['color4'])")

cat > "$OUT" << TOML
foreground = "$fg"
background = "$bg"
accent = "$accent"
TOML
