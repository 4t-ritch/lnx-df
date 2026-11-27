-- Run from the repository root: lua config/hypr/tests/test_pip_scroll.lua
local file = assert(io.open("config/hypr/hyprland.lua"))
local source = file:read("*a")
file:close()
local block = assert(source:match("%-%- PiP scroll begin\n(.-)\n%-%- PiP scroll end"),
    "PiP scroll bindings are missing")
local bindings, dispatched = {}, {}
local window, cursor
local monitor = {
    x = 0, y = 0, width = 1920, height = 1080,
    reserved = { left = 0, right = 0, top = 30, bottom = 0 },
}
local function descriptor(kind)
    return function(args) return { kind = kind, args = args } end
end
local mock = {
    bind = function(key, callback) bindings[key] = callback end,
    get_active_window = function() return window end,
    get_cursor_pos = function() return cursor end,
    get_active_monitor = function() return monitor end,
    dispatch = function(action) dispatched[#dispatched + 1] = action end,
    dsp = {
        window = { resize = descriptor("resize"), move = descriptor("move") },
        exec_cmd = descriptor("exec"),
    },
}
assert(load(block, "pip-scroll", "t", setmetatable({ hl = mock, mainMod = "SUPER" }, { __index = _G })))()
local function reset(class, width, height)
    window = {
        class = class, title = "Picture in picture", address = "0x123",
        mapped = true, visible = true, floating = true,
        at = { x = 1424, y = 794 }, size = { x = width or 480, y = height or 270 },
    }
    cursor = { x = 1500, y = 820 }
    dispatched = {}
end
local function scroll(direction) bindings["SUPER + mouse_" .. direction]() end
local function check_resize(direction, width, height)
    reset("brave-browser")
    scroll(direction)
    assert(#dispatched == 2 and dispatched[1].kind == "resize" and dispatched[2].kind == "move")
    local size, position = dispatched[1].args, dispatched[2].args
    assert(size.window == "address:0x123" and size.relative == false)
    assert(size.x == width and size.y == height)
    assert(position.x + width == 1904 and position.y + height == 1064)
end
check_resize("up", 528, 297)
check_resize("down", 432, 243)
for _, case in ipairs({ { "up", "prev" }, { "down", "next" } }) do
    reset("kitty")
    scroll(case[1])
    assert(#dispatched == 1 and dispatched[1].kind == "exec")
    assert(dispatched[1].args == "~/.config/hypr/scripts/ws-cycle.sh " .. case[2])
end
reset("brave-browser", 240, 135)
scroll("down")
assert(#dispatched == 0, "Minimum-sized PiP must not trigger workspace scrolling")
reset("brave-browser", 1904, 1071)
scroll("up")
assert(dispatched[1].args.x <= 1904 and dispatched[1].args.y <= 1034)
print("PASS: PiP grows/shrinks proportionally, stays bounded, and preserves both workspace fallbacks")
