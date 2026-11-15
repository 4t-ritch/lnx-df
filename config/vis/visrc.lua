-- vis configuration: zenwritten theme + floating fzf UI
-- https://github.com/martanne/vis

-- load standard vis module, providing parts of the Lua API
require('vis')

local fzf_files = require('plugins.fzf_files')
local buffers = require('plugins.buffers')
local tree = require('plugins.tree')

vis.events.subscribe(vis.events.INIT, function()
	vis:command('set theme zenwritten')
end)

-- file finder
vis:map(vis.modes.NORMAL, ' ff', fzf_files.pick, 'Fuzzy find files')

-- open buffers
vis:map(vis.modes.NORMAL, '<Tab>', buffers.toggle, 'Buffer manager')
vis:map(vis.modes.NORMAL, ' bx', buffers.close_current, 'Close current file')

-- file tree
vis:map(vis.modes.NORMAL, ' e', tree.open, 'File tree')
vis:map(vis.modes.NORMAL, '<C-n>', tree.open, 'File tree')
