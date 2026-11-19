#!/usr/bin/env bash
# Capture the focused monitor with flameshot without a monitor prompt.
# Falls back to interactive gui when detection fails.
set -euo pipefail

fallback() {
  exec flameshot gui
}

command -v hyprctl >/dev/null 2>&1 || fallback
command -v jq >/dev/null 2>&1 || fallback
command -v flameshot >/dev/null 2>&1 || fallback

monitors_json="$(hyprctl monitors -j 2>/dev/null)" || fallback

# Index of the focused monitor sorted by x then y, matching Qt screen order.
num="$(printf '%s' "$monitors_json" | jq -r '[sort_by(.x, .y) | to_entries[] | select(.value.focused == true) | .key][0] // empty' 2>/dev/null)" || fallback

if [ -z "${num:-}" ] || [ "$num" = "null" ]; then
  fallback
fi

if ! [[ "$num" =~ ^[0-9]+$ ]]; then
  fallback
fi

exec flameshot screen -n "$num" --edit || fallback
