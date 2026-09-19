import os
from pathlib import Path

APP_ID = "dev.ritch.ControlCenter"
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
PID_FILE = RUNTIME_DIR / "lnx-df-control-center.pid"
CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
CACHE_HOME = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
BASE = CONFIG_HOME
AUDIO_PREF_FILE = CONFIG_HOME / "waybar" / "audio-preferences.env"
STEP = 2
PANEL_WIDTH = 420
PANEL_HEIGHT = 285
PANEL_FALLBACK_X = 1470
PANEL_TOP_MARGIN = 42
PANEL_RIGHT_MARGIN = 18
PANEL_HORIZONTAL_DECORATION = 34
PANEL_ANIMATION_MS = 180
LAYER_NAMESPACE = "control-center-panel"
