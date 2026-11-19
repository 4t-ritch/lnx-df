# vis editor port: zenwritten theme + floating fzf UI

## Objective
Make `vis` a usable daily editor with the user's Neovim look and workflow:
zenwritten dark theme, a floating open-buffers panel, a floating file tree
with full filesystem actions, and a floating fuzzy finder on `<Space>ff`.

## Problem / why
The user installed `vis` and asked for a port of their Neovim setup. `vis` has
no floating windows, no resizable splits, no buffer list and no prompt API, so
the Neovim experience cannot be reproduced natively. Live test (2026-11-14)
proved `vis:pipe()` + `fzf` renders a rounded floating box over the vis screen
and vis repaints correctly afterwards. That is the chosen UI layer.

## Scope
- `config/vis/visrc.lua`
- `config/vis/themes/zenwritten.lua`
- `config/vis/plugins/fzf_files.lua`
- `config/vis/plugins/buffers.lua`
- `config/vis/plugins/tree.lua`
- `config/vis/bin/vis-tree` (bash helper owning the tree UI)
- `config/vis/README.md`
- symlink `~/.config/vis` -> `~/dotfiles/config/vis`

Out of scope: LSP, completions, statusline changes, tabs as real editor tabs.

## Constraints (verified)
- `vis` layout is tiling-only and windows are equally sized; no floating, no
  resizing, no Lua drawing API (`research: man 1194-1195`, binary probes).
- No prompt API; text input must come from a child process (`fzf --print-query`).
- No hidden buffers: closing the last window of a file discards it.
- `vis:pipe()` is blocking and vis repaints after the child exits.
- fzf 0.74.5 supports `--border-label`, `--footer`, `--preview-window`,
  `--print-query`, `--phony`, `--expect`, `--bind` with `transform`/`execute`.
- Theme attrs: `bold`, `italics`, `underlined`, `reverse`, `dim`.
- No tmux dependency for any feature.

## Tasks

- [x] T1 Port zenwritten dark palette to `themes/zenwritten.lua` (all 114
      STYLE_* keys + 14 UI style ids). Source: Neovim resolved highlights.
- [x] T2 `visrc.lua`: `require('vis')`, set theme, register plugins, keymaps.
- [x] T3 `<Space>ff` fuzzy file finder: `rg --files`/`fd` + `bat` preview,
      rounded border, height 85%, always visible.
- [x] T4 `<Tab>` Buffer Manager: floating list of open files, current marker
      and `[+]` modified flag, `<CR>` open, `d` close file, `q` quit.
- [x] T5 `<Space>e` / `<C-n>` file tree: floating fzf tree with expand/collapse,
      create file/dir (nested paths), copy/paste, duplicate, rename, delete,
      per-entry hide/unhide, open file. Implemented as `bin/vis-tree`.
- [x] T6 Symlink `~/.config/vis`, README, end-to-end tmux verification.

## Acceptance criteria
- `vis file` starts with zenwritten colors and no errors.
- `<Space>ff` opens a bordered floating finder with preview; Enter opens the
  file in vis.
- `<Tab>` lists named open files, marks the current one and modified ones,
  Enter switches, `C-d` closes the selected file only when it is current.
- Tree: directories toggle with Enter/Right/Left, files open with Enter; each
  requested action works on the selected entry; hidden entries disappear
  immediately and survive restarts; nested dir creation works.
- Every float is visible at default font size (height in terminal cells, not
  tied to font size).

## Checks
- `bash -n config/vis/bin/vis-tree`
- `luac -p` on every Lua file (Lua 5.5 parser available via `lua`).
- Interactive harness: detached tmux session running `VIS_PATH=<config> vis`,
  `send-keys`, `capture-pane` assertions. Recorded per task in Progress.

## Delivery
- Branch: `feat/vis-port` (dotfiles repo).
- Commit per task; branch point is the current HEAD of
  `feat/codex-usage-sidebar`, only `config/vis/**` and this file are staged.

## Progress
- 2026-11-14: exploration + capability research done; fzf overlay proven live.
- Decision: fzf floating tree (user-chosen) over native 50% split.
- 2026-11-14: implemented theme, finder, Buffer Manager, file tree, README,
  and `~/.config/vis` symlink. Verified Lua/Bash syntax, `git diff --check`,
  theme rendering with the temporary `vis-lexers` extraction, finder open,
  buffer list/open/close/modified protection, and tree expand/collapse,
  nested file/directory creation, copy/paste, duplicate, rename, delete,
  hide/unhide. Full syntax highlighting still needs the system `vis-lexers`
  package; no sudo installation was performed.
- Current tested buffer behavior: closing a non-current entry reports the
  limitation in-panel; closing a modified file and the last window is refused.
- Pending: install `vis-lexers` (`sudo pacman -S vis-lexers`) and re-check
  highlighting in the installed runtime. Temporary package extraction used
  for tests is under `/tmp/opencode/vispath`.
- Route: delegated exploration preceded implementation; one direct implementation
  route for the coordinated config set. Checks: `bash -n`, Lua loadfile syntax,
  `git diff --check`, tmux/fzf interactive smoke tests.
