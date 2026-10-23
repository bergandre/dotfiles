local vault_root = vim.fn.expand("~/Documents/obsidian")

local function vault(name, overrides)
	return { name = name, path = vault_root .. "/" .. name, overrides = overrides }
end

return {
	{
		-- Community-maintained fork of epwalsh/obsidian.nvim (the original is unmaintained)
		"obsidian-nvim/obsidian.nvim",
		version = "*",
		ft = "markdown",
		cmd = "Obsidian",
		dependencies = { "nvim-lua/plenary.nvim" },
		---@module 'obsidian'
		---@type obsidian.config
		opts = {
			legacy_commands = false, -- only `:Obsidian <subcommand>`, no `:ObsidianFoo`
			workspaces = {
				vault("programming"),
				vault("supernova", {
					templates = { folder = "Templates" },
					attachments = { img_folder = "RANDOM/attachments" },
				}),
				vault("salaryman", { templates = { folder = "templates" } }),
				vault("setup"),
				vault("gaming"),
				vault("syncreborn"),
			},
			picker = { name = "telescope.nvim" },
			-- Keep note filenames equal to their titles, like Obsidian does
			note_id_func = function(title)
				return title or tostring(os.time())
			end,
			-- render-markdown.nvim handles visuals; avoid double-rendering
			ui = { enable = false },
		},
		keys = {
			{ "<leader>oo", "<cmd>Obsidian quick_switch<CR>", desc = "[O]bsidian: switch note" },
			{ "<leader>os", "<cmd>Obsidian search<CR>", desc = "[O]bsidian: [S]earch vault" },
			{ "<leader>on", "<cmd>Obsidian new<CR>", desc = "[O]bsidian: [N]ew note" },
			{ "<leader>ob", "<cmd>Obsidian backlinks<CR>", desc = "[O]bsidian: [B]acklinks" },
			{ "<leader>ol", "<cmd>Obsidian links<CR>", desc = "[O]bsidian: [L]inks in note" },
			{ "<leader>ot", "<cmd>Obsidian tags<CR>", desc = "[O]bsidian: [T]ags" },
			{ "<leader>od", "<cmd>Obsidian today<CR>", desc = "[O]bsidian: [D]aily note" },
			{ "<leader>oT", "<cmd>Obsidian template<CR>", desc = "[O]bsidian: insert [T]emplate" },
			{ "<leader>op", "<cmd>Obsidian paste_img<CR>", desc = "[O]bsidian: [P]aste image" },
			{ "<leader>ow", "<cmd>Obsidian workspace<CR>", desc = "[O]bsidian: switch [W]orkspace" },
		},
	},
	{
		-- Renders headings, checkboxes, tables, callouts, code blocks in-buffer
		"MeanderingProgrammer/render-markdown.nvim",
		ft = "markdown",
		dependencies = { "nvim-treesitter/nvim-treesitter", "nvim-tree/nvim-web-devicons" },
		---@module 'render-markdown'
		---@type render.md.UserConfig
		opts = {
			completions = { blink = { enabled = true } },
		},
		keys = {
			{ "<leader>tm", "<cmd>RenderMarkdown toggle<CR>", desc = "[T]oggle [M]arkdown rendering" },
		},
	},
}
