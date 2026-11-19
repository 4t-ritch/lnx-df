status is-interactive; or return

alias g 'git'
alias tre 'eza -T'
alias .. 'cd ..'
alias opc 'opencode'
alias cc 'clear'
alias cls 'clear'
alias mk 'mkdir'
alias vi 'nvim'
alias ee 'exit'
alias fr 'rm -rf'
alias fc 'cp -rf'
alias fm 'mv -rf'
alias gl 'pwd'
alias zed 'zeditor'
alias zz 'zeditor'

function dd --description 'guard against accidental raw disk writes'
  set -l escaped_args (string escape -- $argv)
  printf 'dd is blocked in fish to avoid accidental disk writes.\n' >&2
  printf 'If you really need it, run: command dd %s\n' (string join ' ' $escaped_args) >&2
  return 1
end

function codex --description 'run Codex in unrestrict mode'
  command codex -s danger-full-access -a never $argv
end

function cdx --description 'short alias for Codex in unrestrict mode'
  codex $argv
end

function claude --description 'run Claude with permission prompts disabled'
  command claude --dangerously-skip-permissions $argv
end

function cld --description 'short alias for Claude with permission prompts disabled'
  claude $argv
end

if test -d $DFL
  function df --description 'cd into dotfiles root'
    cd $DFL
  end
end

if test -d $DFL/config/nvim
  function nvc --description 'cd into nvim config'
    cd $DFL/config/nvim
  end
end

if test -d $DEVD
  function gg --description 'cd into development directory'
    cd $DEVD
  end
end

function xx --description 'open current directory in default file explorer'
  if command -sq nautilus
    nautilus . >/dev/null 2>&1 &
  else if command -sq xdg-open
    xdg-open . >/dev/null 2>&1 &
  else if command -sq open
    open . >/dev/null 2>&1 &
  else if command -sq explorer.exe
    explorer.exe . >/dev/null 2>&1 &
  else
    printf 'No default file opener found\n' >&2
    return 1
  end
end

function jj --description 'open todo directory in file explorer'
  if command -sq nautilus
    nautilus /mnt/todo/ >/dev/null 2>&1 &
  else if command -sq xdg-open
    xdg-open /mnt/todo/ >/dev/null 2>&1 &
  else if command -sq open
    open /mnt/todo/ >/dev/null 2>&1 &
  else if command -sq explorer.exe
    explorer.exe /mnt/todo/ >/dev/null 2>&1 &
  else
    printf 'No default file opener found\n' >&2
    return 1
  end
end
