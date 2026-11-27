# Waybar layout

Both bars show the date and time without a calendar popup or tooltip.
Control center and power buttons are omitted; their existing keyboard shortcuts
remain available. The workspace, window, keyboard, and primary-output tray
modules are unchanged.

## Checks

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s config/waybar/tests
```

These checks validate both bar layouts without opening windows or invoking
power actions.
