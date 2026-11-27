# Codex CLI theme and status line

Muted `ritch-rose` theme: warm dark background, gray-rose text, desaturated
rose accents. No bright white.

## Theme

`themes/ritch-rose.tmTheme` is a TextMate theme. The installer links it to
`~/.codex/themes/ritch-rose.tmTheme`; Codex discovers custom themes by file
stem. Select it with `/theme` or:

```toml
[tui]
theme = "ritch-rose"
```

| Element | Color |
| --- | --- |
| background | `#151316` |
| foreground | `#C9C0C5` |
| rose accent | `#D185AB` |
| branch cyan | `#8FB0B6` |
| path blue | `#93A9C4` |
| subtle gray | `#6F636B` |
| empty bar | `#574D53` |

The Claude Code theme in `config/claude/themes/ritch-rose.json` replicates this
same palette.

## Status line provider

`statusline.py` is an MCP server that renders the footer through the custom
status line provider. It mirrors the Claude Code status line:

```
 feat/vis-port |  ritch/dotfiles (main) |  GPT-6.1-Sol (medium) | 5h ▰▰▱▱▱▱▱▱▱▱ 24% | 7d ▰▰▰▰▰▰▰▱▱▱ 70%
```

The provider requires Codex `0.171.0-alpha.13` or newer; older releases ignore
the selection and keep the built-in status line.

### Wiring

The installer links `~/.codex/statusline.py` to this file. Register the MCP
server and enable the feature in `~/.codex/config.toml`:

```bash
codex mcp add codex-statusline -- /usr/bin/python3 -u "$HOME/.codex/statusline.py"
```

```toml
[features]
tui_extensions_statusline = true

[tui]
theme = "ritch-rose"
status_line_provider = { server = "codex-statusline", tool = "statusline" }
status_line = ["git-branch", "current-dir", "model-with-reasoning", "five-hour-limit", "weekly-limit"]
status_line_use_colors = true
```

Restart the TUI after changing the provider. The built-in `status_line` list
stays as the fallback.

### Usage cache

Codex sends rate-limit windows only while the account reports them. Every
observation is persisted to `${XDG_CACHE_HOME:-~/.cache}/codex-statusline/usage.json`
and reused afterwards. Inside one reset window usage only grows, so an older
snapshot never overwrites a newer cached value. The footer converts Codex's
consumed percentage to remaining quota, matching Claude's usage display.

### Customization

- Icons and colors: constants at the top of `statusline.py`.
- Bar width and glyphs: `BAR_WIDTH`, `BAR_FILLED`, `BAR_EMPTY`.
- Layout: `render()` builds a `row` of text leaves; see `statusline.d.ts` in the
  Codex `create-statusline` skill for the UI tree schema.

## Reverting

Install a stable release and drop the provider selection:

```bash
CODEX_RELEASE=0.170.0 CODEX_NON_INTERACTIVE=1 sh -c 's=$(curl -fsSL https://chatgpt.com/codex/install.sh) && eval "$s"'
```

Remove `tui.status_line_provider` (or set it to `"default"`). A background
daemon on a different version shows a startup warning; manage it with
`/daemon`.

The branch label matches the Fish prompt: `>` for commits ahead of upstream,
`<` for commits behind, and `!` for local changes, including untracked files.
Indicators combine in that order (for example, `main ><!`).
