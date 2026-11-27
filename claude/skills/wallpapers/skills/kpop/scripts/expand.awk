# Expands the compact list printed by extract.js (via get_page_text) into full URLs, one per line.
#   SLUGS $0=<slug> $1=<slug>   -> slug table
#   L xx/n/$0<suffix>           -> https://legacy.kpopping.com/xx/n/<slug><suffix>
#   C yyyy/mm/<name>            -> https://cdn.kpopping.com/kpics/yyyy/mm/<name>
/^SLUGS/ { for (i = 2; i <= NF; i++) { split($i, a, "="); slug[a[1]] = a[2] } next }
/^L /    { p = $2; for (k in slug) gsub("\\" k, slug[k], p); print "https://legacy.kpopping.com/" p; next }
/^C /    { print "https://cdn.kpopping.com/kpics/" $2; next }
