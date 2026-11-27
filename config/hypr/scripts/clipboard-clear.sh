#!/usr/bin/env bash
set -euo pipefail

notify_ok() {
  if command -v notify-send >/dev/null 2>&1; then
    notify-send \
      --app-name=Clipboard \
      --expire-time=2500 \
      --hint=boolean:suppress-sound:true \
      --hint=boolean:transient:true \
      'Clipboard history cleared'
  else
    hyprctl notify 1 2500 'rgb(a6e3a1)' 'Clipboard history cleared'
  fi
}

notify_error() {
  if command -v notify-send >/dev/null 2>&1; then
    notify-send \
      --app-name=Clipboard \
      --expire-time=3500 \
      --hint=boolean:suppress-sound:true \
      --hint=boolean:transient:true \
      'cliphist is not installed'
  else
    hyprctl notify 1 3500 'rgb(ff6666)' 'cliphist is not installed'
  fi
}

if ! command -v cliphist >/dev/null 2>&1; then
  notify_error
  exit 1
fi

cliphist wipe >/dev/null 2>&1
notify_ok
