# Neovim DAP debugger

## Objective
Add a compact, manual debugger to the existing Neovim setup, preserving the
existing `<Space>d…` mappings and showing scopes/variables in a fixed left
panel while a debug session is active.

## Problem / why
`config/nvim/lua/mappings/dapmap.lua` already describes debugger commands but is
not loaded by `init.lua`, and no active DAP plugin or adapters are configured.
The user wants breakpoints, stepping, continue, and runtime variable inspection
without changing editors or adding unrelated UI.

## Scope
- `config/nvim/lua/plugins/dap.lua` (or equivalent focused plugin spec)
- `config/nvim/lua/mappings/dapmap.lua`
- `config/nvim/init.lua`
- `config/nvim/lua/config/debugger.lua` (if setup warrants a separate module)
- `odd/tasks/nvim-debugger.md`
- Per-user Mason DAP packages under Neovim's data directory; no sudo or global
  npm installs.

Out of scope: debugging static/config/document formats (Markdown, JSON, XML,
CSV, TOML, `.env`, HTML, CSS); changing language servers; replacing Neovim;
installing shell debuggers unless a supported adapter can be verified.

## Constraints and decisions
- User explicitly approved GitHub plugin downloads and Mason-local adapters.
- Keep existing `<Space>db`, `dc`, `dj`, `dk`, `dl`, `dd`, `de`, `dr` mappings.
- Use nvim-dap + nvim-dap-ui and a left scopes/watches layout; open on DAP
  session start and close on termination/exit.
- Configure runtime languages with supported adapters: Go, Rust, C/C++, C#,
  JavaScript/TypeScript, Python, Lua, Bash, and Godot/GDScript.
- Godot uses the running project's DAP endpoint; it is not an adapter binary
  that Mason installs.
- Static/local variable visibility depends on the adapter and build/debug info.
- Bash uses the Mason `bash-debug-adapter`; Fish has no DAP adapter verified.
- Lua uses Mason's `local-lua-debugger-vscode` package and the nvim-dap
  `local-lua` executable adapter configuration; install and runtime checks are
  still pending.
  Text/data/markup formats do not have runtime breakpoints.
- Current Neovim is 0.12.6; plugin manager is lazy.nvim. Existing indentation
  is already 2 spaces globally and per buffer.
- TDD mode: unresolved (no `sdd-init/dotfiles` testing-capabilities memory).
  Verification planned: headless Neovim config/plugin-load checks and focused
  adapter checks where a runnable sample/runtime is available.

## Tasks
- [ ] D1 Activate existing debugger mappings and integrate DAP UI/layout.
- [ ] D2 Configure and install supported debug adapters and Godot connection.
- [ ] D3 Verify mappings, startup, panel lifecycle, and representative adapter
      configuration; document unsupported targets and runtime prerequisites.

## Acceptance criteria
- Neovim loads without debugger-related errors.
- Existing `<Space>d…` keys invoke breakpoint, condition, step, continue,
  terminate, and rerun actions.
- Debug session opens a stable left panel with scopes/watches and closes when
  the session ends; floating window clutter is not added.
- Supported adapters are installed/configured locally and language configs
  identify the required runtime/server prerequisites.
- Unsupported/non-executable file types and any adapter gaps are stated
  honestly; static variables are shown only when the adapter exposes them.
- No unrelated dirty files are staged or modified.

## Verification
- Neovim headless startup with the user's config.
- Lua syntax/load check for changed Lua files.
- Focused DAP config check and interactive smoke test where runtime permits.
- Record exact commands/results and any unavailable language runtimes.

## Delivery
- Repository: `/home/ritch/dotfiles`, current branch `feat/vis-port`.
- Preserve unrelated dirty files. Each completed work unit gets its own
  Conventional Commit; do not push or open a PR.

## Progress
- 2026-11-15: inspected current config. Existing `dapmap.lua` is dormant;
  `init.lua` never requires it and no DAP plugin/adapter spec exists.
- User approved DAP scope for executable languages and GitHub/Mason downloads.
- 2026-11-15: verified Bash DAP support via Mason; Godot DAP uses the running
  editor's server at 127.0.0.1:6006; Fish remains unsupported by a verified DAP.
- 2026-11-15: configured Mason DAP source names and added the Mason-local Lua
  debugger adapter; package installation and runtime checks remain pending.
