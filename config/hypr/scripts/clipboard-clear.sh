#!/usr/bin/env bash
set -euo pipefail

notify_ok() {
  # Visual-only: hyprctl bypasses swaync, so the receive hook never fires.
  hyprctl notify 1 2500 'rgb(a6e3a1)' 'Clipboard history cleared'
}

notify_error() {
  # Visual-only: hyprctl bypasses swaync, so the receive hook never fires.
  hyprctl notify 1 3500 'rgb(ff6666)' 'cliphist is not installed'
}

if ! command -v cliphist >/dev/null 2>&1; then
  notify_error
  exit 1
fi

cliphist wipe >/dev/null 2>&1
notify_ok
