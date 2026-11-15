-- <Space>ff: floating fuzzy file finder with preview.

local fzf = require('plugins.fzf')

local M = {}

local function file_list()
	local cmd = table.concat({
		'(command -v rg >/dev/null 2>&1 && rg --files --color never) ||',
		'(command -v fd >/dev/null 2>&1 && fd --type f --color never) ||',
		"find . -type f -not -path './.git/*'",
	}, ' ')
	local status, out = fzf.run('', cmd)
	if status ~= 0 or not out or out == '' then return nil end
	return out
end

function M.pick()
	local list = file_list()
	if not list then
		vis:info('no files found')
		return
	end

	local args = {
		'fzf',
		'--height=85%',
		'--min-height=12',
		'--scheme=path',
		'--prompt=> ',
		'--border-label= Files ',
		'--header=Enter: open  ·  C-/: preview',
		'--preview=if command -v bat >/dev/null 2>&1; then bat --color=always --style=numbers --line-range=:300 -- {}; else sed -n "1,300p" {}; fi',
		'--preview-window=right,60%,border-left,wrap',
		'--bind=ctrl-/:toggle-preview',
	}
	for _, opt in ipairs(fzf.chrome) do args[#args + 1] = opt end

	local quoted = {}
	for _, arg in ipairs(args) do quoted[#quoted + 1] = fzf.quote(arg) end
	local cmd = table.concat(quoted, ' ')
	local status, out = fzf.run(list, cmd)
	if status ~= 0 or not out or out == '' then return end

	local path = out:gsub('\n$', '')
	if path == '' then return end
	vis:command('e ' .. fzf.ex(path))
end

return M
