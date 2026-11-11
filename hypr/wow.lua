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

	-- hyper's left mods leak into wine as held keys (wow would see ALT-CTRL-SHIFT-1):
	-- shift/ctrl hide [mod:rshift] / [mod:rctrl], alt is wow's self-cast key
	local function release_left_mods(target)
		for _, left in ipairs({ "Shift_L", "Control_L", "Alt_L", "Super_L" }) do
			hl.dispatch(hl.dsp.send_key_state({ mods = "", key = left, state = "up", window = target }))
		end
	end

	-- presses are serialized: while a switch is in flight the next press waits (only the
	-- latest is kept, enough for spamming) and is sent while the target still has focus;
	-- `home` stays the window we came from, so focus can't get stuck on the target
	local busy, pending, home, home_follow_mouse = false, nil, nil, nil

	local function run(job)
		-- release hyper's left mods, then re-press the right ones so wine sees rshift / rctrl
		release_left_mods(job.target)
		for _, m in ipairs(job.held) do
			hl.dispatch(hl.dsp.send_key_state({ mods = "", key = m.right, state = "up", window = job.target }))
			hl.dispatch(hl.dsp.send_key_state({ mods = "", key = m.right, state = "down", window = job.target }))
		end
		hl.dispatch(hl.dsp.send_shortcut({ mods = job.mods, key = job.key, window = job.target }))
		for _, m in ipairs(job.held) do
			hl.dispatch(hl.dsp.send_key_state({ mods = job.mods, key = m.right, state = "up", window = job.target }))
		end
		hl.timer(function()
			if pending then
				local next_job = pending
				pending = nil
				run(next_job)
				return
			end
			hl.dispatch(hl.dsp.focus({ window = home }))
			hl.config({ cursor = { no_warps = false }, input = { follow_mouse = home_follow_mouse } })
			busy = false
		end, { timeout = delay, type = "oneshot" })
	end

	local function send_to_wow(key)
		return function()
			local target, prev = find_windows()
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
			hl.dispatch(hl.dsp.focus({ window = target }))
			hl.timer(function()
				run(job)
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
			hl.dispatch(hl.dsp.focus({ window = target }))
			hl.timer(function()
				release_left_mods(target)
				hl.dispatch(hl.dsp.send_key_state({ mods = "", key = key, state = "down", window = target }))
				local watch
				watch = hl.timer(function()
					if not hl.is_key_down(key:lower()) then
						watch:set_enabled(false)
						hl.dispatch(hl.dsp.send_key_state({ mods = "", key = key, state = "up", window = target }))
						hl.dispatch(hl.dsp.focus({ window = prev }))
						hl.config({ cursor = { no_warps = false }, input = { follow_mouse = follow_mouse } })
						busy = false
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
