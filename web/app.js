// Minimal README renderer — fetches README.md and renders it as HTML.
// No dependencies beyond a tiny inline markdown subset renderer.
(async () => {
  const el = document.getElementById('content');
  try {
    const md = await (await fetch('README.md')).text();
    el.innerHTML = render(md);
  } catch (e) {
    el.textContent = 'Failed to load README.md: ' + e;
  }
})();

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function inline(s) {
  return esc(s)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function render(md) {
  const lines = md.split('\n');
  let out = '', inCode = false, inList = false, inTable = false, para = [];

  const flushPara = () => {
    if (para.length) { out += '<p>' + inline(para.join(' ')) + '</p>'; para = []; }
  };
  const closeList = () => { if (inList) { out += '</ul>'; inList = false; } };
  const closeTable = () => { if (inTable) { out += '</table>'; inTable = false; } };

  for (const raw of lines) {
    const line = raw.replace(/\r$/, '');
    if (line.startsWith('```')) {
      flushPara(); closeList(); closeTable();
      out += inCode ? '</code></pre>' : '<pre><code>';
      inCode = !inCode;
      continue;
    }
    if (inCode) { out += esc(line) + '\n'; continue; }

    if (/^\|.*\|$/.test(line.trim())) {
      flushPara(); closeList();
      const cells = line.trim().slice(1, -1).split('|').map(c => c.trim());
      if (cells.every(c => /^-{2,}$/.test(c))) continue; // separator row
      if (!inTable) { out += '<table>'; inTable = true; }
      out += '<tr>' + cells.map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>';
      continue;
    }
    closeTable();

    const h = line.match(/^(#{1,4})\s+(.*)/);
    if (h) {
      flushPara(); closeList();
      const n = h[1].length;
      out += `<h${n}>` + inline(h[2]) + `</h${n}>`;
      continue;
    }
    const li = line.match(/^\s*(?:[-*]|\d+\.)\s+(.*)/);
    if (li) {
      flushPara();
      if (!inList) { out += '<ul>'; inList = true; }
      out += '<li>' + inline(li[1]) + '</li>';
      continue;
    }
    closeList();
    if (line.startsWith('> ')) {
      flushPara();
      out += '<blockquote>' + inline(line.slice(2)) + '</blockquote>';
      continue;
    }
    if (line.trim() === '') { flushPara(); continue; }
    para.push(line.trim());
  }
  flushPara(); closeList(); closeTable();
  if (inCode) out += '</code></pre>';
  return out;
}
