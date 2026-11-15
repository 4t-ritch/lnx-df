-- Shared helpers for the fzf based floating UI.
-- vis has no floating windows: fzf draws its own box over the vis screen
-- through vis:pipe(), and vis repaints once the child exits.

local M = {}

-- zenwritten palette for fzf chrome
M.colors = table.concat({
	'fg:#BBBBBB',
	'bg:#191919',
	'hl:#B279A7',
	'fg+:#BBBBBB',
	'bg+:#444444',
	'hl+:#B279A7',
	'info:#6099C0',
	'prompt:#9E9E9E',
	'pointer:#DE6E7C',
	'marker:#819B69',
	'spinner:#66A5AD',
	'header:#939393',
	'label:#9E9E9E',
	'query:#BBBBBB',
	'border:#797979',
	'disabled:#555555',
}, ',')

-- border and layout shared by every popup
M.chrome = {
	'--layout=reverse',
	'--border=rounded',
	'--info=inline-right',
	'--pointer=▌',
	'--color=' .. M.colors,
}

-- Quote a string for a POSIX shell command line.
function M.quote(s)
	return "'" .. tostring(s):gsub("'", "'\\''") .. "'"
end

-- Quote a path for a vis ex command (spaces only; vis does not use sh).
function M.ex(s)
	return (tostring(s):gsub('[ \t]', '\\%0'))
end

-- Directory of this configuration, used to locate bin/ helpers.
-- Derived from the location of this file so it does not depend on VIS_PATH
-- (which may point at a lexer directory) being first.
function M.config_dir()
	local src = debug and debug.getinfo and debug.getinfo(1, 'S').source
	if src and src:sub(1, 1) == '@' then
		local dir = src:sub(2):match('^(.*)/plugins/[^/]+$')
		if dir then return dir end
	end
	local path = (os.getenv('VIS_PATH') or ''):match('^[^:]+') or ''
	if path ~= '' then
		local probe = io.open(path .. '/bin/vis-tree')
		if probe then
			probe:close()
			return path
		end
	end
	return (os.getenv('HOME') or '.') .. '/.config/vis'
end

function M.helper(name)
	return M.config_dir() .. '/bin/' .. name
end

-- Run a command through vis:pipe. Returns status, stdout, stderr.
-- vis:pipe goes through $SHELL, which may be fish; force a POSIX shell so the
-- command strings are interpreted consistently.
function M.run(input, cmd)
	local status, out, err = vis:pipe(input or '', 'sh -c ' .. M.quote(cmd))
	return status, out, err
end

-- Show stderr of a failed helper, if any.
function M.report(status, _, err)
	if status and status ~= 0 and err and err ~= '' then
		vis:info(err:gsub('%s+$', ''))
		return true
	end
	return false
end

return M
