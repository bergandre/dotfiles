-- WoW multibox: send keys to the WoW on a given monitor
-- both WoWs share one wineserver, which only takes keys for its active window,
-- so: focus target -> send key -> focus back
-- one keypress -> one client (no broadcasting)

local focus_delay = 30 -- ms after focusing the target before the key goes out (wine must notice the switch)
local delay = 10 -- ms after sending before focusing back / sending the next key

-- mouse buttons can't be sent like keys (they'd go to the window under the cursor),
-- so they reach the top wow as these keys instead
local send_as = {
	["mouse:275"] = "F11", -- mouse back
	["mouse:276"] = "F12", -- mouse forward
}

return function(hyper, monitor)
	-- target = the wow on `monitor`, prev = whatever has focus now
	local function find_windows()
		local target
		for _, w in ipairs(hl.get_windows({ class = "steam_proton", monitor = monitor })) do
			if w.title == "World of Warcraft" then
				target = "address:" .. w.address
			end
		end
		local prev = hl.get_active_window()
		if not target or not prev then
			return nil
		end
		return target, "address:" .. prev.address
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

	-- focus back + restore settings; always reached, even if something above threw
	local function finish(prev, follow_mouse)
		pending = nil
		dispatch(hl.dsp.focus({ window = prev }))
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
				dispatch(hl.dsp.focus({ window = job.target }))
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
			local target, prev = find_windows()
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
			local job = { target = target, key = key, held = held, mods = table.concat(mods, " + ") }

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
			local target, prev = find_windows()
			if not target or busy then
				return
			end
			busy = true
			-- no focus-follows-mouse while steering, or a mouse move would steal focus back
			local follow_mouse = hl.get_config("input:follow_mouse")
			hl.config({ cursor = { no_warps = true }, input = { follow_mouse = 0 } })
			dispatch(hl.dsp.focus({ window = target }))
			hl.timer(function()
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
			end, { timeout = focus_delay, type = "oneshot" })
		end
	end

	local keys = {
		"1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "minus", "equal",
		"Q", "E", "R", "T", "Y", "F", "G", "H", "Z", "X", "C", "V", "B",
		"F7", "F8", "F9", "F10",
		"mouse:275", "mouse:276", -- mouse back / forward
	}

	for _, key in ipairs(keys) do
		hl.bind(hyper .. " + " .. key, send_to_wow(send_as[key] or key))
	end
	for _, key in ipairs({ "W", "A", "S", "D" }) do
		hl.bind(hyper .. " + " .. key, hold_in_wow(key))
	end
end
