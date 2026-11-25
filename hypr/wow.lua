-- WoW multibox: send keys to the WoW on a given monitor
-- both WoWs share one wineserver, which only takes keys for its active window,
-- so: focus target -> send key -> focus back
-- one keypress -> one client (no broadcasting)

local focus_delay = 30 -- ms after focusing the target before the key goes out (wine must notice the switch)
local delay = 10 -- ms after sending before focusing back / sending the next key

-- mouse buttons / wheel can't be sent like keys (they'd go to the window under the cursor),
-- so they reach the top wow as these keys instead
local send_as = {
	["mouse:275"] = "F5", -- mouse back (F11 / F12 are the wheel tilt in wow)
	["mouse:276"] = "F6", -- mouse forward
	-- hyprland names the wheel backwards: mouse_down = wheel up
	["mouse_down"] = "Prior", -- wheel up -> PAGEUP in wow
	["mouse_up"] = "Next", -- wheel down -> PAGEDOWN in wow
}

return function(hyper, monitor)
	local last_target = nil -- single-monitor target, see find_windows

	-- target = the wow on `monitor`, prev = whatever has focus now
	local function find_windows()
		local target, center
		-- pcall: the monitor may be unplugged (playing on the tv only)
		local ok, on_monitor = pcall(hl.get_windows, { class = "steam_proton", monitor = monitor })
		for _, w in ipairs(ok and on_monitor or {}) do
			if w.title == "World of Warcraft" then
				target = "address:" .. w.address
				center = { x = w.at.x + w.size.x / 2, y = w.at.y + w.size.y / 2 }
			end
		end
		local prev = hl.get_active_window()
		-- single-monitor setup (both wows on the tv, see `stack` below): no wow on `monitor`,
		-- so the target is the other wow than the focused one; it is remembered, so a press
		-- from a non-wow window still goes to the same wow
		if not target and prev then
			local other, remembered
			for _, w in ipairs(hl.get_windows({ class = "steam_proton" })) do
				if w.title == "World of Warcraft" and w.address ~= prev.address then
					other = w
					if w.address == last_target then
						remembered = w
					end
				end
			end
			local is_wow = prev.class == "steam_proton" and prev.title == "World of Warcraft"
			local w = is_wow and other or remembered
			if w then
				last_target = w.address
				target = "address:" .. w.address
				center = { x = w.at.x + w.size.x / 2, y = w.at.y + w.size.y / 2 }
			end
		end
		if not target or not prev then
			return nil
		end
		return target, "address:" .. prev.address, center
	end

	-- a dispatch that throws (e.g. "send_key_state: key not found" after a monitor/keyboard
	-- re-plug, or a target window that just closed) must not abort the job halfway:
	-- that left `busy` stuck at true and every later hyper press was silently dropped
	-- debug: `touch /tmp/wow-trace.on` -> every press is logged to /tmp/wow-trace.log
	local function trace(...)
		local on = io.open("/tmp/wow-trace.on", "r")
		if not on then
			return
		end
		on:close()
		local f = io.open("/tmp/wow-trace.log", "a")
		if f then
			local parts = {}
			for _, v in ipairs({ ... }) do
				parts[#parts + 1] = tostring(v)
			end
			f:write(os.date("%H:%M:%S "), table.concat(parts, " "), "\n")
			f:close()
		end
	end

	local function dispatch(d)
		local ok, err = pcall(hl.dispatch, d)
		if not ok then
			trace("  dispatch error:", err)
		end
	end

	local function active_address()
		local a = hl.get_active_window()
		return a and ("address:" .. a.address) or "none"
	end

	-- hyper's left mods leak into wine as held keys (wow would see ALT-CTRL-SHIFT-1):
	-- shift/ctrl hide [mod:rshift] / [mod:rctrl], alt is wow's self-cast key
	local function release_left_mods(target)
		for _, left in ipairs({ "Shift_L", "Control_L", "Alt_L", "Super_L" }) do
			dispatch(hl.dsp.send_key_state({ mods = "", key = left, state = "up", window = target }))
		end
	end

	-- presses are serialized: while a switch is in flight the next press waits (only the
	-- latest is kept, enough for spamming) and is sent while the target still has focus;
	-- `home` stays the window we came from, so focus can't get stuck on the target
	local busy, pending, home, home_follow_mouse = false, nil, nil, 1

	-- sometimes the wow under the cursor (bottom one) grabs focus straight back, even with
	-- follow_mouse = 0 (likely wine holding a cursor clip; only a restart cleared it): then the
	-- cursor is moved onto the target too, and put back where it was when focus returns
	local cursor_home = nil

	local function pull_focus(target, center)
		if center and not cursor_home then
			local ok, pos = pcall(hl.get_cursor_pos)
			if ok and pos then
				cursor_home = { x = pos.x, y = pos.y }
				trace("  moving cursor to target", center.x, center.y)
				dispatch(hl.dsp.cursor.move({ x = center.x, y = center.y }))
			end
		end
		dispatch(hl.dsp.focus({ window = target }))
	end

	-- focus back + restore settings; always reached, even if something above threw
	local function finish(prev, follow_mouse)
		pending = nil
		dispatch(hl.dsp.focus({ window = prev }))
		if cursor_home then
			dispatch(hl.dsp.cursor.move(cursor_home))
			cursor_home = nil
		end
		pcall(hl.config, { cursor = { no_warps = false }, input = { follow_mouse = follow_mouse or 1 } })
		busy = false
	end

	local function run(job)
		-- focus can be taken back before the key goes out (seen with a fullscreen wow under the
		-- cursor: a tiny mouse move refocuses it), so re-focus and wait again, a few times at most
		local focused = active_address()
		if focused ~= job.target then
			job.tries = (job.tries or 0) + 1
			trace("  focus taken by", focused, "retry", job.tries)
			if job.tries <= 3 then
				-- also move the cursor onto the target: the wow under it may keep grabbing focus
				pull_focus(job.target, job.center)
				hl.timer(function()
					if not pcall(run, job) then
						finish(home, home_follow_mouse)
					end
				end, { timeout = focus_delay, type = "oneshot" })
				return
			end
		end
		trace("  run", job.key, "mods=" .. job.mods, focused == job.target and "focus ok" or ("FOCUS WRONG: " .. focused))
		-- release hyper's left mods, then re-press the right ones so wine sees rshift / rctrl
		release_left_mods(job.target)
		for _, m in ipairs(job.held) do
			dispatch(hl.dsp.send_key_state({ mods = "", key = m.right, state = "up", window = job.target }))
			dispatch(hl.dsp.send_key_state({ mods = "", key = m.right, state = "down", window = job.target }))
		end
		dispatch(hl.dsp.send_shortcut({ mods = job.mods, key = job.key, window = job.target }))
		for _, m in ipairs(job.held) do
			dispatch(hl.dsp.send_key_state({ mods = job.mods, key = m.right, state = "up", window = job.target }))
		end
		hl.timer(function()
			if pending then
				local next_job = pending
				pending = nil
				if pcall(run, next_job) then
					return
				end
			end
			finish(home, home_follow_mouse)
		end, { timeout = delay, type = "oneshot" })
	end

	local function send_to_wow(key)
		return function()
			local target, prev, center = find_windows()
			trace("press", key, "target=" .. tostring(target), "from=" .. tostring(prev), "busy=" .. tostring(busy))
			if not target then
				return
			end

			-- right shift / right ctrl (naga extra buttons, see keyd/naga.conf) are passed on
			-- as real right-side presses, so wow macros can use [mod:rshift] / [mod:rctrl]
			local held = {}
			for _, m in ipairs({
				{ right = "Shift_R", mod = "SHIFT" },
				{ right = "Control_R", mod = "CTRL" },
			}) do
				if hl.is_key_down(m.right) then
					table.insert(held, m)
				end
			end
			local mods = {}
			for _, m in ipairs(held) do
				table.insert(mods, m.mod)
			end
			local job = { target = target, center = center, key = key, held = held, mods = table.concat(mods, " + ") }

			if busy then
				pending = job
				return
			end
			busy, home = true, prev

			-- no cursor warp while switching, so the mouse stays put; no focus-follows-mouse,
			-- or the slightest mouse move (pressing a naga button) pulls focus straight back
			home_follow_mouse = hl.get_config("input:follow_mouse")
			hl.config({ cursor = { no_warps = true }, input = { follow_mouse = 0 } })
			dispatch(hl.dsp.focus({ window = target }))
			hl.timer(function()
				if not pcall(run, job) then
					finish(home, home_follow_mouse)
				end
			end, { timeout = focus_delay, type = "oneshot" })
		end
	end

	-- movement keys are held instead of tapped: the top wow keeps focus while the key is down,
	-- the key is polled so it works whether hyper or the key is released first
	local function hold_in_wow(key)
		return function()
			local target, prev, center = find_windows()
			if not target or busy then
				return
			end
			busy = true
			-- no focus-follows-mouse while steering, or a mouse move would steal focus back
			local follow_mouse = hl.get_config("input:follow_mouse")
			hl.config({ cursor = { no_warps = true }, input = { follow_mouse = 0 } })
			dispatch(hl.dsp.focus({ window = target }))
			local function start()
				release_left_mods(target)
				dispatch(hl.dsp.send_key_state({ mods = "", key = key, state = "down", window = target }))
				local watch
				watch = hl.timer(function()
					local ok, down = pcall(hl.is_key_down, key:lower())
					if not ok or not down then
						watch:set_enabled(false)
						dispatch(hl.dsp.send_key_state({ mods = "", key = key, state = "up", window = target }))
						finish(prev, follow_mouse)
					end
				end, { timeout = delay, type = "repeat" })
			end
			hl.timer(function()
				-- focus grabbed back by the wow under the cursor: move the cursor over too
				if active_address() ~= target then
					trace("hold", key, "focus taken by", active_address())
					pull_focus(target, center)
					hl.timer(function()
						if not pcall(start) then
							finish(prev, follow_mouse)
						end
					end, { timeout = focus_delay, type = "oneshot" })
					return
				end
				if not pcall(start) then
					finish(prev, follow_mouse)
				end
			end, { timeout = focus_delay, type = "oneshot" })
		end
	end

	local keys = {
		"1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "minus", "equal",
		"Q", "E", "R", "T", "Y", "F", "G", "H", "Z", "X", "C", "V", "B",
		"F7", "F8", "F9", "F10",
		"mouse:275", "mouse:276", -- mouse back / forward
		"mouse_down", "mouse_up", -- wheel up / down
	}

	for _, key in ipairs(keys) do
		hl.bind(hyper .. " + " .. key, send_to_wow(send_as[key] or key))
	end
	for _, key in ipairs({ "W", "A", "S", "D" }) do
		hl.bind(hyper .. " + " .. key, hold_in_wow(key))
	end

	-- hyper + F6 (pressed in a wow): stack every wow on this workspace as floating windows
	-- filling the monitor, the focused one on top. focusing a window on a hidden workspace
	-- would show that workspace on every keypress; focusing a floating window below another
	-- one doesn't raise it, so the screen stays on the wow being played
	hl.bind(hyper .. " + F6", function()
		local top = hl.get_active_window()
		if not top or top.class ~= "steam_proton" or top.title ~= "World of Warcraft" then
			return
		end
		local m, r = top.monitor, top.monitor.reserved
		local geo = { x = m.x + r.left, y = m.y + r.top, w = m.width - r.left - r.right, h = m.height - r.top - r.bottom }
		local top_addr = "address:" .. top.address
		for _, w in ipairs(hl.get_windows({ class = "steam_proton" })) do
			if w.title == "World of Warcraft" then
				local addr = "address:" .. w.address
				dispatch(hl.dsp.window.move({ workspace = top.workspace.id, follow = false, window = addr }))
				dispatch(hl.dsp.window.float({ action = "enable", window = addr }))
				dispatch(hl.dsp.window.resize({ x = geo.w, y = geo.h, window = addr }))
				dispatch(hl.dsp.window.move({ x = geo.x, y = geo.y, window = addr }))
			end
		end
		dispatch(hl.dsp.window.alter_zorder({ mode = "top", window = top_addr }))
		dispatch(hl.dsp.focus({ window = top_addr }))
	end)
end
