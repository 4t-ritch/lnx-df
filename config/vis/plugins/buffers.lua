-- <Tab>: floating buffer manager for vis.
-- vis has no hidden buffers: the list is every file currently shown in a window.

local fzf = require('plugins.fzf')

local M = {}

local function relpath(name)
	local cwd = os.getenv('PWD') or ''
	if cwd ~= '' and name:sub(1, #cwd + 1) == cwd .. '/' then
		return name:sub(#cwd + 2)
	end
	return name
end

local function collect()
	local current = vis.win and vis.win.file
	local lines = {}
	for file in vis:files() do
		local name = file.name
		if name and name ~= '' then
			local marker = (file == current) and '● ' or '  '
			local modified = file.modified and ' [+]' or ''
			lines[#lines + 1] = marker .. relpath(name) .. modified .. '\t' .. name
		end
	end
	table.sort(lines, function(a, b) return a:lower() < b:lower() end)
	return lines, current
end

local function window_count()
	local n = 0
	for _ in vis:windows() do n = n + 1 end
	return n
end

-- vis has no hidden buffers and no command to close a window by file, so only
-- the focused window can be closed. The selected entry must be the current file.
-- Returns an error string for the panel, or nil on success.
local function close_file(path)
	local win = vis.win
	if not win then return 'no window' end
	if win.file.name ~= path then
		return 'not the current window — open it first (<CR>)'
	end
	if win.file.modified then
		return 'unsaved changes: ' .. relpath(path)
	end
	if window_count() <= 1 then
		return 'cannot close the last window'
	end
	vis:command('q')
	return nil
end

function M.toggle()
	local notice = nil
	local last_path = nil
	while true do
		local lines, current = collect()
		if #lines == 0 then return end

		local pos = 1
		if last_path then
			for i, entry in ipairs(lines) do
				if entry:match('\t([^\t]+)$') == last_path then pos = i break end
			end
		end

		local header = 'current: ' .. relpath(current and current.name or '[No Name]')
		if notice then header = header .. '\n' .. notice end

		local args = {
			'fzf',
			'--height=70%',
			'--min-height=10',
			'--prompt=» ',
			'--border-label= Buffer Manager ',
			'--footer= <CR>: Open · C-d: Close · C-r: Refresh · Esc: Quit ',
			'--delimiter=\t',
			'--with-nth=1',
			'--nth=1',
			'--no-sort',
			'--expect=ctrl-d,ctrl-r',
			'--header=' .. header,
			'--bind=load:pos(' .. pos .. ')',
		}
		for _, opt in ipairs(fzf.chrome) do args[#args + 1] = opt end

		local quoted = {}
		for _, arg in ipairs(args) do quoted[#quoted + 1] = fzf.quote(arg) end

		local status, out = fzf.run(table.concat(lines, '\n') .. '\n', table.concat(quoted, ' '))
		if status ~= 0 or not out or out == '' then return end

		local key, line = out:match('^([^\n]*)\n?([^\n]*)')
		local path = line and line:match('\t([^\t]+)$')
		if not path then return end
		last_path = path

		if key == 'ctrl-d' then
			notice = close_file(path)
		elseif key == 'ctrl-r' then
			notice = nil
		else
			vis:command('e ' .. fzf.ex(path))
			return
		end
	end
end

function M.close_current()
	local win = vis.win
	if not win then return end
	if win.file.modified then
		vis:info('unsaved changes: ' .. (win.file.name or '[No Name]'))
		return
	end
	vis:command('q')
end

return M
