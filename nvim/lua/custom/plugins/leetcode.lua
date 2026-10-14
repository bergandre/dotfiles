return {
	"kawre/leetcode.nvim",
	cmd = "Leet",
	dependencies = {
		"nvim-telescope/telescope.nvim",
		"nvim-lua/plenary.nvim",
		"MunifTanjim/nui.nvim",
	},
	keys = {
		{ "<leader>ll", "<cmd>Leet<CR>", desc = "[L]eetcode dashboard" },
		{ "<leader>lr", "<cmd>Leet run<CR>", desc = "[L]eetcode [R]un tests" },
		{ "<leader>ls", "<cmd>Leet submit<CR>", desc = "[L]eetcode [S]ubmit" },
		{ "<leader>lc", "<cmd>Leet console<CR>", desc = "[L]eetcode [C]onsole (test cases)" },
		{ "<leader>ld", "<cmd>Leet desc<CR>", desc = "[L]eetcode toggle [D]escription" },
		{ "<leader>lp", "<cmd>Leet list<CR>", desc = "[L]eetcode [P]roblem list" },
		{ "<leader>lt", "<cmd>Leet tabs<CR>", desc = "[L]eetcode open [T]abs" },
		{ "<leader>lL", "<cmd>Leet lang<CR>", desc = "[L]eetcode change [L]anguage" },
	},
	opts = {
		lang = "java",
	},
}
