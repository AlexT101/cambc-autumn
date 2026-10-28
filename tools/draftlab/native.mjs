// Offline parity of astraeus's draft model (bots/astraeus/src/draft/map_features.cc) with features.mjs and
// model.mjs: builds tools/draftlab/native_main.cc natively (zig c++), feeds it decoded map files and
// compares the map key, the 19 features and the chosen team. No games; the JS features take ~0.1 s a map.
//   node tools/draftlab/native.mjs --lab replays/draftlab/night1 maps [maps/gen ...] [--show 5]
// The bot's own walking fields come from the engine (draft.cc engine_walk); this checks our BFS
// instead, so the in-game check (parity.py) is still the last word.
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { Grid } from '../mapgen/grid.mjs';
import { createEngine, CAMP_TYPES, SYMMETRIES } from '../mapgen/wasm.mjs';
import { mapRow } from './features.mjs';
import { FEATURES, CHAMPS, deployedTeam, loadDeployed } from './model.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const SRC = path.join(ROOT, 'bots', 'astraeus', 'src', 'draft');

function build(out) {
  const exe = path.join(out, process.platform === 'win32' ? 'feat.exe' : 'feat');
  const deps = [path.join(ROOT, 'tools', 'draftlab', 'native_main.cc'), ...['map_features.cc', 'map_features.h', 'draft_model.h'].map(f => path.join(SRC, f))];
  if (fs.existsSync(exe) && deps.every(f => fs.statSync(f).mtimeMs < fs.statSync(exe).mtimeMs)) return exe;
  fs.mkdirSync(out, { recursive: true });
  // No FMA contraction: the bot's WASM has none, and the comparison is exact.
  const r = spawnSync('zig', ['c++', '-std=c++20', '-O2', '-ffp-contract=off', '-o', exe, deps[0]], { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`zig c++ failed (is zig on PATH?):\n${r.stderr || r.error}`);
  return exe;
}

const same = (js, c) => (js === null || js === undefined) ? Number.isNaN(c) : js === c;

async function main() {
  const args = process.argv.slice(2), inputs = [];
  let lab = null, show = 5;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--lab') lab = args[++i];
    else if (args[i] === '--show') show = +args[++i];
    else inputs.push(args[i]);
  }
  if (!lab || !inputs.length) { console.error('usage: node tools/draftlab/native.mjs --lab DIR MAPS_OR_DIRS... [--show N]'); return 2; }
  const files = [];
  // Not recursive (maps/ holds maps/gen*/): name each directory.
  for (const p of inputs.map(q => path.resolve(ROOT, q)))
    if (fs.statSync(p).isDirectory()) files.push(...fs.readdirSync(p).sort().filter(f => f.endsWith('.map26a')).map(f => path.join(p, f)));
    else files.push(p);
  const { model, prior } = loadDeployed(path.resolve(lab));
  const engine = await createEngine(), rows = [], dump = [];
  for (const file of files) {
    const rel = path.relative(ROOT, file).split(path.sep).join('/');
    let g, row;
    try { g = Grid.fromMap(engine.decode(fs.readFileSync(file))); row = mapRow(g, rel); } catch (e) { console.error(`skip ${rel}: ${e.message}`); continue; }
    // Camps reversed: the engine's handle order is not the file's, and nothing may depend on it.
    const camps = g.allCamps().reverse();
    const s = g.spawn;
    dump.push(`MAP ${g.W} ${g.H} ${SYMMETRIES.indexOf(g.sym)} ${s.x} ${s.y} ${s.w} ${s.h} ${g.picks} ${camps.length}`, Array.from(g.t).join(''),
      ...camps.map(c => `${CAMP_TYPES.indexOf(c.type)} ${c.x} ${c.y}`));
    rows.push(row);
  }
  const exe = build(path.join(ROOT, 'replays', 'draftlab', 'native'));
  const r = spawnSync(exe, [], { input: dump.join('\n') + '\n', encoding: 'utf8', maxBuffer: 1 << 28 });
  if (r.status !== 0) throw new Error(`${exe} failed: ${r.stderr}`);
  const lines = r.stdout.split('\n').filter(Boolean);
  let li = 0, keyBad = 0, featBad = 0, teamBad = 0, fail = 0, shown = 0;
  const perFeature = new Map();
  for (const row of rows) {
    const line = lines[li++] ?? '';
    const [tag, key, ...vals] = line.trim().split(/\s+/);
    if (key !== row.key) keyBad++;
    if (tag === 'FAIL') { fail++; if (shown++ < show) console.log(`${row.path}: C++ failed: ${vals.join(' ')}`); continue; }
    const team = (lines[li++] ?? '').trim().split(/\s+/)[3];
    const diffs = [];
    FEATURES.forEach(([name], k) => {
      const c = Number(vals[k]), js = row.f[name];
      if (!same(js, c)) { diffs.push(`${name} js ${js} c++ ${vals[k]}`); perFeature.set(name, (perFeature.get(name) ?? 0) + 1); }
    });
    const T = deployedTeam(model, prior, row), want = T ? T.map(c => CHAMPS[c]).join(',') : '-';
    if (diffs.length) featBad++;
    if (team !== want) teamBad++;
    if ((diffs.length || team !== want || key !== row.key) && shown++ < show)
      console.log(`${row.path} (${row.key}${key !== row.key ? ` c++ ${key}` : ''}): ${diffs.join('; ') || 'features equal'}${team !== want ? `; team js ${want} c++ ${team}` : ''}`);
  }
  console.log(`${rows.length} maps: ${keyBad} key mismatches, ${featBad} with feature mismatches` +
    `${perFeature.size ? ` (${[...perFeature].map(([n, c]) => `${n} ${c}`).join(', ')})` : ''}, ${teamBad} team mismatches, ${fail} C++ failures`);
  return keyBad || featBad || teamBad || fail ? 1 : 0;
}

process.exitCode = await main();
