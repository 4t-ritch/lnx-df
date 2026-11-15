-- <Space>e / <C-n>: floating file tree.
-- The UI lives in bin/vis-tree (bash + fzf); this module only launches it and
-- opens the selected file.

local fzf = require('plugins.fzf')

local M = {}

function M.open()
	local root = os.getenv('PWD') or os.getenv('HOME') or '.'
	local helper = fzf.helper('vis-tree')

	local cmd = table.concat({
		'VIS_TREE_ROOT=' .. fzf.quote(root),
		fzf.quote(helper), 'ui', fzf.quote(root),
	}, ' ')

	local status, out, err = fzf.run('', cmd)
	if status ~= 0 then
		fzf.report(status, out, err)
		return
	end

	local path = (out or ''):gsub('\n$', '')
	if path ~= '' then
		vis:command('e ' .. fzf.ex(path))
	end
end

return M
