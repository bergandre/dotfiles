-- Neo-tree is a Neovim plugin to browse the file system
-- https://github.com/nvim-neo-tree/neo-tree.nvim

return {
	"nvim-neo-tree/neo-tree.nvim",
	version = "*",
	dependencies = {
		"nvim-lua/plenary.nvim",
		"nvim-tree/nvim-web-devicons", -- not strictly required, but recommended
		"MunifTanjim/nui.nvim",
	},
	lazy = false,
	keys = {
		{ "\\", ":Neotree reveal<CR>", desc = "NeoTree reveal", silent = true },
	},
	opts = {
		window = {
			width = 70,
			--			auto_expand_width = true,
		},
		default_component_configs = {
			file_size = {
				enabled = true,
			},
			type = {
				enabled = false, -- hide type column
			},
			last_modified = {
				enabled = true,
				last_modified = "relative",
			},
		},
		filesystem = {
			window = {
				mappings = {
					["\\"] = "close_window",
					["p"] = { "toggle_preview", config = { use_float = true } },
					["y"] = "copy_to_clipboard",
					["x"] = "cut_to_clipboard",
					["P"] = "paste_from_clipboard",
				},
			},
		},
	},
}
