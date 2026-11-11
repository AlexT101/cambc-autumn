// Generated C++ (bots/<bot>/src/**, bots/<bot>/.cambc/hgen/*.h) -> the .htb line it came from, via hgen's #line markers.
const fs = require('fs');
const path = require('path');

const cache = new Map();   // file -> { mtime, lines }

function generatedRoot(file) {   // the project root when `file` is hgen output, else null
  const parts = file.split(path.sep), i = parts.lastIndexOf('bots');
  const j = i + (parts[i + 1] === 'archives' ? 3 : 2);   // past bots/<bot> or bots/archives/<bot>
  if (i < 0 || j >= parts.length) return null;
  const inside = parts[j];
  return inside === 'src' || (inside === '.cambc' && parts[j + 1] === 'hgen') ? parts.slice(0, i).join(path.sep) : null;
}

// { file, line } (0-based line) for a 0-based line of a generated file, or null when it isn't one / has no marker above.
function toSource(file, line) {
  const root = generatedRoot(file);
  if (!root) return null;
  let entry = cache.get(file);
  let mtime = 0;
  try { mtime = fs.statSync(file).mtimeMs; } catch (e) { return null; }
  if (!entry || entry.mtime !== mtime) {
    entry = { mtime, lines: fs.readFileSync(file, 'utf8').split('\n') };
    cache.set(file, entry);
  }
  for (let k = Math.min(line, entry.lines.length - 1); k >= 0; k--) {
    const m = /^\s*#line\s+(\d+)\s+"([^"]+)"/.exec(entry.lines[k]);
    if (m && m[2].endsWith('.htb')) return { file: path.join(root, m[2]), line: Number(m[1]) - 1 + (line - k - 1) };
  }
  return null;
}

module.exports = { toSource };
