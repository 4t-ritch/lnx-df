#!/usr/bin/env python3
"""Codex CLI status line provider (MCP over stdio).

Mirrors the Claude Code status line:

    <branch> | <repo tail> (<worktree>) | <model> (<effort>) | 5h <bar> <pct> | 7d <bar> <pct>

Codex polls the advertised resource about once per second and sends the
displayed thread snapshot in ``params._meta``. The rate-limit windows are only
present while the account reports them, so every observation is persisted to a
cache file and reused afterwards. Inside one reset window usage only grows, so
an older snapshot from another session never overwrites a newer cached value.

Colors are the muted ``ritch-rose`` palette: desaturated rose, warm gray,
soft cyan and slate blue.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

# Both entry points are installed as symlinks into this config tree.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from statusline_git import STATUS_ARGS, branch_label
finally:
    sys.path.pop(0)

URI = "ui://codex-statusline/footer"
STATE_KEY = "com.openai/codex-statusline-state"

BAR_WIDTH = 10
BAR_FILLED = "\u25b0"
BAR_EMPTY = "\u25b1"

PINK = "#D185AB"        # ritch-rose muted rose
CYAN = "#8FB0B6"        # muted cyan
BLUE = "#93A9C4"        # muted blue
SUBTLE = "#6F636B"      # separators, labels
EMPTY_BAR = "#574D53"   # unfilled bar

GIT_ICON = "\uf418"       # nf-oct-git_branch
TREE_ICON = "\U000f0645"  # nf-md-file_tree
STAR_ICON = "\uf51b"      # nf-oct-sparkle_fill

CACHE_DIR = os.path.join(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
    "codex-statusline",
)
CACHE_FILE = os.path.join(CACHE_DIR, "usage.json")

TOOL = {
    "name": "statusline",
    "title": "Gentleman Cute",
    "description": "Branch, repository, model and usage limits in the Codex footer.",
    "inputSchema": {"type": "object", "properties": {}},
    "_meta": {
        "openai/ui": {"entrypoints": [{"type": "statusline", "resourceUri": URI}]}
    },
}


def text(value, color=None):
    props = {"color": color} if color else {}
    return {"type": "text", "props": props, "children": [value]}


def row(children, gap=1):
    return {"type": "row", "props": {"gap": gap, "wrap": "nowrap"}, "children": children}


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
    pct = entry.get("used_percent")
    resets_at = entry.get("resets_at")
    if pct is None:
        return
    if resets_at is not None and resets_at <= now:
        return
    cached = cache.get(window) if isinstance(cache.get(window), dict) else {}
    cached_pct = cached.get("used_percent")
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
        "used_percent": pct,
        "resets_at": resets_at,
        "updated_at": int(now),
    }


def resolve_usage(cache, window, incoming, now):
    """Freshest live value: newest reset window wins, then the highest value."""
    candidates = []
    entry = incoming if isinstance(incoming, dict) else {}
    pct = entry.get("used_percent")
    resets_at = entry.get("resets_at")
    if pct is not None and (resets_at is None or resets_at > now):
        candidates.append((resets_at, float(pct)))
    cached = cache.get(window)
    if isinstance(cached, dict):
        cached_pct = cached.get("used_percent")
        cached_resets = cached.get("resets_at")
        if cached_pct is not None and (cached_resets is None or cached_resets > now):
            candidates.append((cached_resets, float(cached_pct)))
    if not candidates:
        return None
    newest = max((resets or 0) for resets, _ in candidates)
    return max(pct for resets, pct in candidates if (resets or 0) == newest)


def remaining_percent(used_percent):
    """Convert the API's consumed percentage to the remaining quota."""
    return 100.0 - max(0.0, min(100.0, float(used_percent)))


def bar(pct):
    pct = max(0.0, min(100.0, float(pct)))
    filled = int(round(pct * BAR_WIDTH / 100.0))
    segments = []
    if filled:
        segments.append(text(BAR_FILLED * filled, PINK))
    if BAR_WIDTH - filled:
        segments.append(text(BAR_EMPTY * (BAR_WIDTH - filled), EMPTY_BAR))
    return row(segments, gap=0)


def git(cwd, args):
    try:
        result = subprocess.run(
            ["git", "-C", cwd] + list(args),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=0.35,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def git_branch(cwd):
    return branch_label(git(cwd, STATUS_ARGS))


def repo_paths(cwd):
    """Main repository root and current worktree top level."""
    output = git(cwd, ["rev-parse", "--show-toplevel", "--git-common-dir"])
    if not output:
        return None, None
    lines = output.splitlines()
    toplevel = lines[0] if lines else None
    common = lines[1] if len(lines) > 1 else None
    if not common:
        return toplevel, toplevel
    if not os.path.isabs(common):
        common = os.path.join(cwd, common)
    common = os.path.abspath(common)
    root = os.path.dirname(common) if os.path.basename(common) == ".git" else common
    return root, toplevel


def repo_tail(root, cwd):
    """Last two path components of the repository root, e.g. dev/my-repo."""
    base = root or os.path.normpath(cwd)
    parts = [part for part in base.split(os.sep) if part]
    tail = parts[-2:] if len(parts) >= 2 else parts
    return "/".join(tail) if tail else "/"


def worktree_name(root, toplevel):
    if not root:
        return "-"
    if not toplevel or os.path.realpath(root) == os.path.realpath(toplevel):
        return "main"
    return os.path.basename(toplevel.rstrip(os.sep)) or "main"


def pick_snapshot(rate_limits):
    if not isinstance(rate_limits, list):
        return None
    for item in rate_limits:
        if isinstance(item, dict) and item.get("limit_id") == "codex":
            return item
    for item in rate_limits:
        if isinstance(item, dict) and (
            item.get("primary_limit") or item.get("secondary_limit")
        ):
            return item
    return None


def render(state):
    thread = state.get("thread") if isinstance(state.get("thread"), dict) else {}
    workspace = thread.get("workspace") if isinstance(thread.get("workspace"), dict) else {}
    model_data = thread.get("model") if isinstance(thread.get("model"), dict) else {}
    cwd = workspace.get("cwd") or os.getcwd()
    model = model_data.get("display_name") or "unknown"
    effort = model_data.get("reasoning_level")
    now = time.time()

    snapshot = pick_snapshot(
        (state.get("account") or {}).get("rate_limits")
        if isinstance(state.get("account"), dict)
        else None
    )
    incoming = {
        "five_hour": snapshot.get("primary_limit") if snapshot else None,
        "seven_day": snapshot.get("secondary_limit") if snapshot else None,
    }

    cache = load_cache()
    before = json.dumps(cache, sort_keys=True)
    for window, entry in incoming.items():
        record_usage(cache, window, entry, now)
    if json.dumps(cache, sort_keys=True) != before:
        save_cache(cache)

    root, toplevel = repo_paths(cwd)
    branch = git_branch(cwd) if root else None

    children = []
    if branch:
        children.append(text(GIT_ICON + " " + branch, CYAN))
    else:
        children.append(text(GIT_ICON + " -", SUBTLE))

    children.append(text("|", SUBTLE))
    children.append(text(TREE_ICON + " " + repo_tail(root, cwd), BLUE))
    children.append(text("(" + worktree_name(root, toplevel) + ")", SUBTLE))
    children.append(text("|", SUBTLE))
    children.append(text(STAR_ICON + " " + model, PINK))
    if effort:
        children.append(text("(" + effort + ")", SUBTLE))

    for label, window in (("5h", "five_hour"), ("7d", "seven_day")):
        pct = resolve_usage(cache, window, incoming[window], now)
        children.append(text("|", SUBTLE))
        if pct is None:
            children.append(text(label + " -", SUBTLE))
        else:
            remaining = remaining_percent(pct)
            children.append(
                row(
                    [
                        text(label, SUBTLE),
                        bar(remaining),
                        text("{:.0f}%".format(remaining), PINK),
                    ],
                    gap=1,
                )
            )

    return row(children, gap=1)


def respond(method, params):
    if method == "initialize":
        return {
            "protocolVersion": params.get("protocolVersion") or "2025-06-18",
            "capabilities": {"tools": {}, "resources": {}},
            "serverInfo": {"name": "codex-statusline", "version": "1.0.0"},
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": [TOOL]}
    if method == "tools/call":
        if params.get("name") != TOOL["name"]:
            raise ValueError("Unknown tool name")
        return {
            "content": [
                {"type": "text", "text": "The status line resource is " + URI + "."}
            ]
        }
    if method == "resources/list":
        return {
            "resources": [{"name": "footer", "uri": URI, "mimeType": "application/json"}]
        }
    if method == "resources/templates/list":
        return {"resourceTemplates": []}
    if method == "resources/read":
        if params.get("uri") != URI:
            raise ValueError("Unknown resource URI")
        state = (params.get("_meta") or {}).get(STATE_KEY) or {}
        if not isinstance(state, dict):
            state = {}
        try:
            tree = render(state)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            tree = text("statusline unavailable", SUBTLE)
        return {
            "contents": [
                {
                    "uri": URI,
                    "mimeType": "application/json",
                    "text": json.dumps(tree),
                }
            ]
        }
    raise KeyError(method)


def main():
    for line in sys.stdin.buffer:
        if not line.strip():
            continue
        reply = {"jsonrpc": "2.0", "id": None}
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or not isinstance(
                request.get("method"), str
            ):
                reply["error"] = {"code": -32600, "message": "Invalid request"}
            elif "id" not in request:
                continue
            else:
                reply["id"] = request["id"]
                reply["result"] = respond(request["method"], request.get("params") or {})
        except json.JSONDecodeError:
            reply["error"] = {"code": -32700, "message": "Parse error"}
        except KeyError:
            reply["error"] = {"code": -32601, "message": "Method not found"}
        except (TypeError, ValueError, AttributeError):
            reply["error"] = {"code": -32602, "message": "Invalid parameters"}
        print(json.dumps(reply), flush=True)


if __name__ == "__main__":
    main()
