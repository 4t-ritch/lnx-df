#!/usr/bin/env python3
"""Claude Code status line.

Layout:  <branch>  <dir>  <model> (<effort>)  5h <bar>%  7d <bar>%

Claude Code sends session JSON on stdin. The `rate_limits` object is only
present after the first API response and is dropped once a window resets, so
every observed snapshot is persisted to a cache file and reused when the
current payload has no fresh value. Within one reset window usage only grows,
so a stale snapshot from another concurrent session never overwrites a newer
cached value.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import time

# Both entry points are installed as symlinks into this config tree.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from statusline_git import STATUS_ARGS, branch_label
finally:
    sys.path.pop(0)

BAR_WIDTH = 10
BAR_FILLED = "\u25b0"
BAR_EMPTY = "\u25b1"

RESET = "\033[0m"
DIM = "\033[2m"
CYAN = "\033[38;2;143;176;182m"  # ritch-rose branch cyan #8FB0B6
BLUE = "\033[38;2;147;169;196m"  # ritch-rose path blue #93A9C4
PINK = "\033[38;2;209;133;171m"  # ritch-rose accent #D185AB

GIT_ICON = "\uf418"    # nf-oct-git_branch
TREE_ICON = "\U000f0645"  # nf-md-file_tree
STAR_ICON = "\uf51b"   # nf-oct-sparkle_fill

CACHE_DIR = os.path.join(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
    "claude-statusline",
)
CACHE_FILE = os.path.join(CACHE_DIR, "usage.json")


def load_cache():
    try:
        with open(CACHE_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(cache):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = "{}.{}.tmp".format(CACHE_FILE, os.getpid())
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(cache, handle)
        os.replace(tmp, CACHE_FILE)
    except OSError:
        pass


def record_usage(cache, window, entry, now):
    """Persist the freshest snapshot of one rate-limit window."""
    if not isinstance(entry, dict):
        return
    pct = entry.get("used_percentage")
    resets_at = entry.get("resets_at")
    if pct is None:
        return
    if resets_at is not None and resets_at <= now:
        return
    cached = cache.get(window) if isinstance(cache.get(window), dict) else {}
    cached_pct = cached.get("used_percentage")
    cached_resets = cached.get("resets_at")
    if cached_pct is not None:
        same_window = cached_resets == resets_at
        if same_window and pct < cached_pct:
            return
        if (
            not same_window
            and resets_at is not None
            and cached_resets is not None
            and resets_at < cached_resets
        ):
            return
    cache[window] = {
        "used_percentage": pct,
        "resets_at": resets_at,
        "updated_at": int(now),
    }


def resolve_usage(cache, window, incoming, now):
    """Freshest live value: newest reset window wins, then the highest value.

    Usage is cumulative inside one window, so a lower number for the same
    window is an older observation (for example from a concurrent session).
    """
    candidates = []
    entry = incoming if isinstance(incoming, dict) else {}
    pct = entry.get("used_percentage")
    resets_at = entry.get("resets_at")
    if pct is not None and (resets_at is None or resets_at > now):
        candidates.append((resets_at, float(pct)))
    cached = cache.get(window)
    if isinstance(cached, dict):
        cached_pct = cached.get("used_percentage")
        cached_resets = cached.get("resets_at")
        if cached_pct is not None and (cached_resets is None or cached_resets > now):
            candidates.append((cached_resets, float(cached_pct)))
    if not candidates:
        return None
    newest = max((resets or 0) for resets, _ in candidates)
    return max(pct for resets, pct in candidates if (resets or 0) == newest)


def render_bar(pct):
    pct = max(0.0, min(100.0, pct))
    filled = int(round(pct * BAR_WIDTH / 100))
    color = PINK
    return "{}{}{}{}{} {}{:.0f}%{}".format(
        color,
        BAR_FILLED * filled,
        RESET,
        DIM,
        BAR_EMPTY * (BAR_WIDTH - filled),
        color,
        pct,
        RESET,
    )


def git_output(cwd, *args):
    try:
        result = subprocess.run(
            ["git", "-C", cwd] + list(args),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def git_branch(cwd):
    return branch_label(git_output(cwd, *STATUS_ARGS))


def repo_root(cwd):
    """Main repository root, even when cwd is a linked worktree."""
    common = git_output(cwd, "rev-parse", "--git-common-dir")
    if common:
        if not os.path.isabs(common):
            common = os.path.join(cwd, common)
        common = os.path.abspath(common)
        if os.path.basename(common) == ".git":
            return os.path.dirname(common)
        return common
    return git_output(cwd, "rev-parse", "--show-toplevel")


def repo_tail(cwd):
    """Last two path components of the repository root, e.g. dev/my-repo."""
    root = repo_root(cwd) or os.path.normpath(cwd)
    parts = [part for part in root.split(os.sep) if part]
    tail = parts[-2:] if len(parts) >= 2 else parts
    return "/".join(tail) if tail else "/"


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    now = time.time()
    workspace = data.get("workspace") if isinstance(data.get("workspace"), dict) else {}
    cwd = workspace.get("current_dir") or data.get("cwd") or os.getcwd()

    cache = load_cache()
    rate_limits = data.get("rate_limits") if isinstance(data.get("rate_limits"), dict) else {}
    before = json.dumps(cache, sort_keys=True)
    for window in ("five_hour", "seven_day"):
        record_usage(cache, window, rate_limits.get(window), now)
    if json.dumps(cache, sort_keys=True) != before:
        save_cache(cache)

    parts = []

    branch = git_branch(cwd)
    if branch:
        parts.append("{}{} {}{}".format(CYAN, GIT_ICON, branch, RESET))
    else:
        parts.append("{}{} -{}".format(DIM, GIT_ICON, RESET))

    worktree_meta = data.get("worktree") if isinstance(data.get("worktree"), dict) else {}
    worktree = workspace.get("git_worktree") or worktree_meta.get("name")
    if not worktree:
        worktree = "main" if repo_root(cwd) else "-"
    tail = repo_tail(cwd)
    parts.append(
        "{}{} {}{} {}({}){}".format(
            BLUE, TREE_ICON, tail, RESET, DIM, worktree, RESET
        )
    )

    model = (data.get("model") or {}).get("display_name") or "unknown"
    effort = (data.get("effort") or {}).get("level")
    model_part = "{}{} {}{}".format(PINK, STAR_ICON, model, RESET)
    if effort:
        model_part += " {}({}){}".format(DIM, effort, RESET)
    parts.append(model_part)

    for label, window in (("5h", "five_hour"), ("7d", "seven_day")):
        pct = resolve_usage(cache, window, rate_limits.get(window), now)
        if pct is None:
            parts.append("{}{} -{}".format(DIM, label, RESET))
        else:
            parts.append("{}{} {}{}".format(DIM, label, RESET, render_bar(pct)))

    separator = " {}{}{} ".format(DIM, "|", RESET)
    sys.stdout.write("{}\n".format(separator.join(parts)))


if __name__ == "__main__":
    main()
