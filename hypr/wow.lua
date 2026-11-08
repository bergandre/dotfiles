-- WoW multibox: send keys to the WoW on a given monitor
-- both WoWs share one wineserver, which only takes keys for its active window,
-- so: focus target -> send key -> focus back
-- one keypress -> one client (no broadcasting)

local delay = 30 -- ms for wine to notice the focus change

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

	-- hyper's left mods leak into wine as held keys (wow would see ALT-CTRL-SHIFT-1)
	local function release_left_mods(target)
		for _, left in ipairs({ "Shift_L", "Control_L", "Alt_L", "Super_L" }) do
			hl.dispatch(hl.dsp.send_key_state({ mods = "", key = left, state = "up", window = target }))
		end
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
			mods = table.concat(mods, " + ")

			-- no cursor warp while switching, so the mouse stays put
			hl.config({ cursor = { no_warps = true } })
			hl.dispatch(hl.dsp.focus({ window = target }))
			hl.timer(function()
				-- release hyper's left mods, then re-press the right ones so wine sees rshift / rctrl
				release_left_mods(target)
				for _, m in ipairs(held) do
					hl.dispatch(hl.dsp.send_key_state({ mods = "", key = m.right, state = "up", window = target }))
					hl.dispatch(hl.dsp.send_key_state({ mods = "", key = m.right, state = "down", window = target }))
				end
				hl.dispatch(hl.dsp.send_shortcut({ mods = mods, key = key, window = target }))
				for _, m in ipairs(held) do
					hl.dispatch(hl.dsp.send_key_state({ mods = mods, key = m.right, state = "up", window = target }))
				end
				hl.timer(function()
					hl.dispatch(hl.dsp.focus({ window = prev }))
					hl.config({ cursor = { no_warps = false } })
				end, { timeout = delay, type = "oneshot" })
			end, { timeout = delay, type = "oneshot" })
		end
	end

	-- movement keys are held instead of tapped: the top wow keeps focus while the key is down,
	-- the key is polled so it works whether hyper or the key is released first
	local function hold_in_wow(key)
		return function()
			local target, prev = find_windows()
			if not target then
				return
			end
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
					end
				end, { timeout = delay, type = "repeat" })
			end, { timeout = delay, type = "oneshot" })
		end
	end

	local keys = {
		"1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "minus", "equal",
		"Q", "E", "R", "T", "Y", "F", "G", "H", "Z", "X", "C", "V", "B",
		"F7", "F8", "F9", "F10",
		"mouse:275", "mouse:276", -- mouse back / forward
	}

	for _, key in ipairs(keys) do
		hl.bind(hyper .. " + " .. key, send_to_wow(key))
	end
	for _, key in ipairs({ "W", "A", "S", "D" }) do
		hl.bind(hyper .. " + " .. key, hold_in_wow(key))
	end
end
