return {
	"sindrets/diffview.nvim",
	dependencies = { "nvim-lua/plenary.nvim" },
	keys = {
		{ "<leader>gm", "<cmd>DiffviewOpen<CR>", desc = "[G]it [M]erge conflicts / diff working tree" },
		{ "<leader>gD", "<cmd>DiffviewOpen HEAD~1<CR>", desc = "[G]it [D]iffview last commit" },
		{ "<leader>gh", "<cmd>DiffviewFileHistory<CR>", desc = "[G]it file [H]istory (all)" },
		{ "<leader>gH", "<cmd>DiffviewFileHistory %<CR>", desc = "[G]it file [H]istory (current file)" },
		{ "<leader>gq", "<cmd>DiffviewClose<CR>", desc = "[G]it diffview [Q]uit" },
	},
	config = function()
		local actions = require("diffview.actions")
		require("diffview").setup({
			keymaps = {
				view = {
					-- Swapped: lowercase = whole file, uppercase = single conflict
					{ "n", "<leader>co", actions.conflict_choose_all("ours"), { desc = "Choose OURS (whole file)" } },
					{ "n", "<leader>ct", actions.conflict_choose_all("theirs"), { desc = "Choose THEIRS (whole file)" } },
					{ "n", "<leader>cb", actions.conflict_choose_all("base"), { desc = "Choose BASE (whole file)" } },
					{ "n", "<leader>ca", actions.conflict_choose_all("all"), { desc = "Choose ALL (whole file)" } },
					{ "n", "<leader>cO", actions.conflict_choose("ours"), { desc = "Choose OURS (single conflict)" } },
					{ "n", "<leader>cT", actions.conflict_choose("theirs"), { desc = "Choose THEIRS (single conflict)" } },
					{ "n", "<leader>cB", actions.conflict_choose("base"), { desc = "Choose BASE (single conflict)" } },
					{ "n", "<leader>cA", actions.conflict_choose("all"), { desc = "Choose ALL (single conflict)" } },
				},
			},
		})
	end,
}
