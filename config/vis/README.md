# vis configuration

This configuration ports the `zenwritten` dark palette and several Neovim-style
file workflows to [vis](https://github.com/martanne/vis).

## Requirements

- `vis` and its Lua runtime
- `vis-lexers` for syntax highlighting
- `fzf` for the floating interfaces
- `rg` (preferred), `fd`, or `find` for file discovery
- `bat` for fuzzy-finder previews (optional; fzf remains usable without it)
- Bash for the file-tree helper

On Arch Linux, install `vis-lexers` separately from `vis`:

```sh
sudo pacman -S vis-lexers
```

## Install

Link this directory as the user configuration:

```sh
ln -s ~/dotfiles/config/vis ~/.config/vis
```

`visrc.lua` loads the theme and mappings automatically. The file tree stores
per-entry hidden state, expanded directories, and its copy buffer under
`$XDG_CACHE_HOME/vis/` (or `~/.cache/vis/` when `XDG_CACHE_HOME` is unset).

## Key bindings

| Key | Action |
| --- | --- |
| `<Space>ff` | Floating fuzzy file finder with preview |
| `<Tab>` | Floating open-files manager |
| `<Space>bx` | Close the current window, if unmodified and not the last window |
| `<Space>e` or `<C-n>` | Floating file tree |

The Buffer Manager opens the selected file with vis's `:e` command. Closing
another window is deliberately limited: vis does not expose a command to close
an arbitrary non-focused window, so select that file first. Unsaved buffers
and the final window are never closed by the manager.

The tree uses Enter or Right to expand a directory, Left to collapse it, and
Enter on a file to open it. Its footer lists the available actions: create
files/directories (including nested paths), copy/paste, duplicate, rename,
delete with confirmation, hide/unhide individual entries, and toggle dotfiles.

## Floating UI implementation

vis itself uses equal-size tiled windows and does not provide floating windows
or a Lua drawing API. These panels are therefore rendered by `fzf` while vis
temporarily yields the terminal through `vis:pipe()`. They do not depend on
tmux and use terminal-cell dimensions, not editor font size.
