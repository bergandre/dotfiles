// Run on a kpopping.com /kpics/<gallery> page via the Claude in Chrome javascript tool.
// Collects the ORIGINAL file URL of every photo in gallery order (index 1..N), then
//  1) tries to save it as kp-list.txt into Chrome's download folder (~/Downloads), and
//  2) replaces the page body with a compact list for get_page_text (fallback; tool output is capped ~1000 chars).
// Thumbnails are /api/kpics-image?url=<original>&size=... (sometimes wrapped again in /_next/image?url=),
// so we unwrap the url= param until we reach legacy.kpopping.com / cdn.kpopping.com.
await (async () => {
  const unwrap = s => { let u = new URL(s, location.href);
    for (let k = 0; k < 4; k++) { const v = u.searchParams.get('url'); if (!v) break; u = new URL(v, location.href); }
    return u.host + u.pathname; };
  const btn = [...document.querySelectorAll('button')].filter(b => /^View photo \d+$/.test(b.getAttribute('aria-label') || ''));
  const get = b => { const i = b.querySelector('img'); const s = i && (i.currentSrc || i.getAttribute('src'));
    return s && !s.startsWith('data:') ? unwrap(s) : null; };
  const out = [];
  for (const b of btn) { // thumbnails lazy-load: scroll each into view until its src appears
    let p = get(b);
    if (!p) { b.scrollIntoView({ block: 'nearest', inline: 'center' });
      for (let t = 0; t < 40 && !p; t++) { await new Promise(r => setTimeout(r, 50)); p = get(b); } }
    out.push(p);
  }
  const title = document.title;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([out.map(p => p ? 'https://' + p : 'MISSING').join('\n') + '\n'], { type: 'text/plain' }));
  a.download = 'kp-list.txt'; document.body.appendChild(a); a.click(); a.remove();
  // compact form for get_page_text: "L <dir>/<file>" (legacy host), "C <path>" (cdn host), long slugs as $i
  const slugs = [...new Set(out.filter(Boolean).map(p => (p.split('/').pop().match(/^(.*-documents-)/) || [])[1]).filter(Boolean))];
  const compact = out.map(p => { if (!p) return 'MISSING';
    let q = p.replace('legacy.kpopping.com/', 'L ').replace('cdn.kpopping.com/kpics/', 'C ');
    slugs.forEach((s, i) => q = q.replace(s, '$' + i)); return q; });
  document.body.innerHTML = '<article><pre id="kplist"></pre></article>';
  document.getElementById('kplist').textContent = 'SLUGS ' + slugs.map((s, i) => '$' + i + '=' + s).join(' ') + '\n' + compact.join('\n');
  return title.slice(0, 80) + ' | n=' + out.length + ' missing=' + out.filter(x => !x).length;
})()
