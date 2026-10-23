-- Obsidian-friendly markdown: soft-wrap instead of hard line breaks
vim.api.nvim_create_autocmd("FileType", {
	pattern = "markdown",
	callback = function()
		vim.opt_local.textwidth = 0
		vim.opt_local.colorcolumn = ""
		vim.opt_local.wrap = true
		vim.opt_local.linebreak = true -- wrap at word boundaries, not mid-word
		vim.opt_local.conceallevel = 2 -- hide link/markup syntax; required by obsidian.nvim

		-- Move by visual lines when wrapped
		vim.keymap.set({ "n", "x" }, "j", "gj", { buffer = true })
		vim.keymap.set({ "n", "x" }, "k", "gk", { buffer = true })
	end,
})
