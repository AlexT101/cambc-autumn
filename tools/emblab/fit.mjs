// Emblem lab fit (tools/emblab/README.md): P(A wins) from the draft and the table's emblem assignments, over one
// or more labs' games, by penalised logistic regression (L-BFGS) with cross-validation over maps.
//   node tools/emblab/fit.mjs --labs main,pilot [--out replays/emblab/main/model.json] [--search] [--boot N]
//
// logit P(A wins) = side + sum over A's champions of (b_c + w_c . z) + sum over A's assigned arms of value(arm)
//                 - the same for B,
// value(arm) for a champion of type t at its k-th new emblem (kb = min(k, 3)) on a map with features z:
//   ET[t, family] + ST[t, stat] + EK[kb, family] + SK[kb, stat] + MZ[family] . z - (MD[kb] + MDT[t]),
// MD + MDT being what the model's own (state-dependent) choice is worth. Assignments come from the table, not the
// logged decisions: they are random whether or not the game reaches them, while how many emblems a champion
// reaches depends on how its game goes (an intention-to-treat fit; a reached decision's log is not needed).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { FEATURES } from '../draftlab/model.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const CHAMPS = ['ryth', 'vesper_vale', 'vendetta', 'cassi_and_issac', 'stellar', 'prism', 'marcella', 'willow', 'ren', 'varg', 'tavi', 'heart_of_ruin'];
export const TYPES = ['ryth', 'vesper_vale', 'vendetta', 'cassi', 'issac', 'stellar', 'prism', 'marcella', 'willow', 'ren', 'varg', 'tavi', 'heart_of_ruin'];
export const FAMILIES = ['monster', 'power', 'durability', 'treasure', 'jungle', 'home', 'bruiser', 'tribute', 'capture', 'prospector', 'hunter', 'skirmish', 'greed', 'collectors'];
export const STATS = ['strength', 'focus', 'health'];
const NC = CHAMPS.length, NT = TYPES.length, NF = FAMILIES.length, K = FEATURES.length, KB = 4, ORDINALS = 8, MODEL = 255;
const FOLDS = 5, KAPPA = 5, PTS = 25;
const ARMS = [];
for (let f = 0; f < NF; f++) if (FAMILIES[f] !== 'greed') for (let s = 0; s < 3; s++) ARMS.push(f * 3 + s);
const armName = a => `${FAMILIES[Math.floor(a / 3)]}-${STATS[a % 3]}`;
// A draft pick's arm rows' champion types: pick i's row i (Cassi for Cassi and Issac), Issac's row 5.
const typeOf = name => name === 'cassi_and_issac' ? 3 : TYPES.indexOf(name);

// Column layout and penalty groups.
const L = {};
let P = 0;
const GROUPS = [];
function block(name, n, group) { L[name] = P; for (let i = 0; i < n; i++) GROUPS.push(group); P += n; }
block('SIDE', 1, 'side');
block('B', NC, 'b');
block('W', NC * K, 'w');
block('ET', NT * NF, 'e');
block('ST', NT * 3, 'e');
block('EK', KB * NF, 'k');
block('SK', KB * 3, 'k');
block('MZ', NF * K, 'mz');
block('MD', KB, 'md');
block('MDT', NT, 'mdt');
const GI = { side: 0, b: 1, w: 2, e: 3, k: 4, mz: 5, md: 6, mdt: 7 };
const GROUP = Int8Array.from(GROUPS, g => GI[g]);
const VARIANTS = {
  draft: ['side', 'b', 'w'],
  forced: ['side', 'b', 'w', 'md', 'mdt'],
  emblem: ['side', 'b', 'w', 'md', 'mdt', 'e', 'k'],
  map: ['side', 'b', 'w', 'md', 'mdt', 'e', 'k', 'mz'],
};
const DEFAULT_LAM = { side: 0.01, b: 1, w: 270, e: 90, k: 27, mz: 900, md: 0.1, mdt: 30 };

const readJsonl = f => fs.existsSync(f) ? fs.readFileSync(f, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l)) : [];
function hash(str) { let h = 2166136261; for (let i = 0; i < str.length; i++) h = Math.imul(h ^ str.charCodeAt(i), 16777619); return h >>> 0; }
function rng(seed) {
  let s = (seed >>> 0) || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}
const sigmoid = x => 1 / (1 + Math.exp(-x));
const softplus = x => x > 30 ? x : x < -30 ? Math.exp(x) : Math.log1p(Math.exp(x));

function args() {
  const a = process.argv.slice(2), o = {};
  for (let i = 0; i < a.length; i++) {
    const k = a[i].slice(2), v = a[i + 1] && !a[i + 1].startsWith('--') ? a[++i] : true;
    o[k] = v;
  }
  return o;
}

// ---- maps ---------------------------------------------------------------------------------------
function raw(m, [name, tf]) {
  const v = m.f[name];
  if (v === null || v === undefined || !Number.isFinite(v)) return NaN;
  return tf === 'log' ? Math.log(Math.max(v, 1)) : tf === 'log1p' ? Math.log1p(Math.max(v, 0)) : v;
}
// Standardised over the first lab's pool, so z(map) is the same in every fit of that lab.
export function mapTable(lab) {
  const maps = readJsonl(path.join(lab, 'maps.jsonl'));
  const mean = FEATURES.map(f => { const v = maps.map(m => raw(m, f)).filter(Number.isFinite); return v.reduce((a, b) => a + b, 0) / Math.max(1, v.length); });
  const sd = FEATURES.map((f, k) => { const v = maps.map(m => raw(m, f)).filter(Number.isFinite); return Math.sqrt(v.reduce((a, b) => a + (b - mean[k]) ** 2, 0) / Math.max(1, v.length)) || 1; });
  const byKey = new Map();
  for (const m of maps) {
    m.z = Float64Array.from(FEATURES, (f, k) => { const v = (raw(m, f) - mean[k]) / sd[k]; return Number.isFinite(v) ? Math.max(-4, Math.min(4, v)) : 0; });
    byKey.set(m.key, m);
  }
  return { maps, byKey, mean, sd };
}

// ---- rows ---------------------------------------------------------------------------------------
class Row {
  constructor() { this.m = new Map(); }
  add(i, v) { if (v) this.m.set(i, (this.m.get(i) ?? 0) + v); }
  pack() {
    const e = [...this.m].filter(([, v]) => Math.abs(v) > 1e-12).sort((a, b) => a[0] - b[0]);
    return { idx: Int32Array.from(e, x => x[0]), val: Float64Array.from(e, x => x[1]) };
  }
}

// value(arm) for type t at bucket kb on a map z, into row r with sign s.
function addArm(r, s, t, kb, arm, z) {
  const f = Math.floor(arm / 3), st = arm % 3;
  r.add(L.ET + t * NF + f, s);
  r.add(L.ST + t * 3 + st, s);
  r.add(L.EK + kb * NF + f, s);
  r.add(L.SK + kb * 3 + st, s);
  for (let k = 0; k < K; k++) if (z[k]) r.add(L.MZ + f * K + k, s * z[k]);
  r.add(L.MD + kb, -s);
  r.add(L.MDT + t, -s);
}

function loadLab(lab, table, rows) {
  for (const g of readJsonl(path.join(lab, 'games.jsonl'))) {
    if (g.error || g.winner === undefined || g.draft_ok === false || !g.wealth) continue;
    const m = table.byKey.get(g.key);
    if (!m) continue;
    const r = new Row();
    r.add(L.SIDE, 1);
    for (const [S, s] of [['A', 1], ['B', -1]]) {
      const T = g[S], arms = g[`arms${S}`];
      for (const c of T) { const i = CHAMPS.indexOf(c); r.add(L.B + i, s); for (let k = 0; k < K; k++) r.add(L.W + i * K + k, s * m.z[k]); }
      const rows_ = T.map((c, i) => [i, typeOf(c)]);
      if (T.includes('cassi_and_issac')) rows_.push([5, TYPES.indexOf('issac')]);
      for (const [row, t] of rows_)
        for (let k = 0; k < ORDINALS; k++) if (arms[row][k] !== MODEL) addArm(r, s, t, Math.min(k, KB - 1), arms[row][k], m.z);
    }
    const [a, b] = g.wealth;
    rows.push({ ...r.pack(), win: g.winner === 0 ? 1 : 0, soft: sigmoid(KAPPA * (a - b) / (a + b + 50)), fold: hash(g.key) % FOLDS, key: g.key });
  }
}

// ---- optimisation ----------------------------------------------------------------------------------
function objective(rows, th, lam, grad) {
  grad.fill(0);
  let f = 0;
  for (const { idx, val, y, w = 1 } of rows) {
    let e = 0;
    for (let k = 0; k < idx.length; k++) e += th[idx[k]] * val[k];
    f += w * (softplus(e) - y * e);
    const g = w * (sigmoid(e) - y);
    for (let k = 0; k < idx.length; k++) grad[idx[k]] += g * val[k];
  }
  for (let j = 0; j < th.length; j++) if (lam[j]) { f += 0.5 * lam[j] * th[j] * th[j]; grad[j] += lam[j] * th[j]; }
  return f;
}

function lbfgs(rows, lamv, init, iters = 300, m = 12) {
  const n = P, th = Float64Array.from(init ?? new Float64Array(n)), g = new Float64Array(n), gn = new Float64Array(n), tn = new Float64Array(n);
  const S = [], Y = [], R = [];
  // Infinite penalties freeze a column at 0: a variant without that group.
  const live = Uint8Array.from(lamv, v => Number.isFinite(v) ? 1 : 0);
  const lam = Float64Array.from(lamv, v => Number.isFinite(v) ? v : 0);
  for (let j = 0; j < n; j++) if (!live[j]) th[j] = 0;
  let f = objective(rows, th, lam, g);
  for (let j = 0; j < n; j++) if (!live[j]) g[j] = 0;
  for (let it = 0; it < iters; it++) {
    const q = Float64Array.from(g), a = [];
    for (let i = S.length - 1; i >= 0; i--) { let s = 0; for (let j = 0; j < n; j++) s += S[i][j] * q[j]; a[i] = R[i] * s; for (let j = 0; j < n; j++) q[j] -= a[i] * Y[i][j]; }
    if (S.length) { const i = S.length - 1; let sy = 0, yy = 0; for (let j = 0; j < n; j++) { sy += S[i][j] * Y[i][j]; yy += Y[i][j] * Y[i][j]; } const gam = sy / yy; for (let j = 0; j < n; j++) q[j] *= gam; }
    else { let gg = 0; for (let j = 0; j < n; j++) gg += g[j] * g[j]; const sc = 1 / Math.max(1, Math.sqrt(gg)); for (let j = 0; j < n; j++) q[j] *= sc; }
    for (let i = 0; i < S.length; i++) { let s = 0; for (let j = 0; j < n; j++) s += Y[i][j] * q[j]; const b = R[i] * s; for (let j = 0; j < n; j++) q[j] += S[i][j] * (a[i] - b); }
    let gd = 0;
    for (let j = 0; j < n; j++) { q[j] = -q[j] * live[j]; gd += q[j] * g[j]; }
    if (gd >= 0) { for (let j = 0; j < n; j++) q[j] = -g[j]; gd = 0; for (let j = 0; j < n; j++) gd += q[j] * g[j]; S.length = Y.length = R.length = 0; }
    let step = 1, fn;
    for (let ls = 0; ls < 30; ls++) {
      for (let j = 0; j < n; j++) tn[j] = th[j] + step * q[j];
      fn = objective(rows, tn, lam, gn);
      if (fn <= f + 1e-4 * step * gd) break;
      step *= 0.5;
    }
    for (let j = 0; j < n; j++) if (!live[j]) gn[j] = 0;
    const s = new Float64Array(n), y = new Float64Array(n);
    let sy = 0;
    for (let j = 0; j < n; j++) { s[j] = tn[j] - th[j]; y[j] = gn[j] - g[j]; sy += s[j] * y[j]; }
    const done = Math.abs(f - fn) < 1e-9 * Math.max(1, Math.abs(f));
    th.set(tn); g.set(gn); f = fn;
    if (sy > 1e-12) { S.push(s); Y.push(y); R.push(1 / sy); if (S.length > m) { S.shift(); Y.shift(); R.shift(); } }
    if (done) break;
  }
  return th;
}

function lamVector(variant, lam) {
  const on = new Set(VARIANTS[variant]), names = Object.keys(GI);
  return Float64Array.from(GROUP, g => on.has(names[g]) ? lam[names[g]] : Infinity);
}

const prepare = (rows, alpha) => rows.map(r => ({ idx: r.idx, val: r.val, y: (1 - alpha) * r.win + alpha * r.soft }));

function cvLoss(rows, variant, lam, alpha) {
  let loss = 0, n = 0;
  const lamv = lamVector(variant, lam);
  for (let f = 0; f < FOLDS; f++) {
    const th = lbfgs(prepare(rows.filter(r => r.fold !== f), alpha), lamv);
    for (const r of rows) if (r.fold === f) {
      let e = 0;
      for (let k = 0; k < r.idx.length; k++) e += th[r.idx[k]] * r.val[k];
      const p = Math.min(1 - 1e-9, Math.max(1e-9, sigmoid(e)));
      loss -= r.win ? Math.log(p) : Math.log(1 - p);
      n++;
    }
  }
  return loss / n;
}

// ---- policy -------------------------------------------------------------------------------------
// Every arm's value against the model's choice (logit), for type t at bucket kb on map z (z null: the average map).
export function armGains(th, t, kb, z) {
  const out = new Map(), md = th[L.MD + kb] + th[L.MDT + t];
  for (const arm of ARMS) {
    const f = Math.floor(arm / 3), st = arm % 3;
    let s = th[L.ET + t * NF + f] + th[L.ST + t * 3 + st] + th[L.EK + kb * NF + f] + th[L.SK + kb * 3 + st] - md;
    if (z) for (let k = 0; k < K; k++) s += th[L.MZ + f * K + k] * z[k];
    out.set(arm, s);
  }
  return out;
}
function best(gains) {
  let b = null;
  for (const [a, g] of gains) if (!b || g > b[1]) b = [a, g];
  return b;
}

function report(th, boots, table, out) {
  const lines = [];
  lines.push(`Model choice term MD by ordinal ` + [0, 1, 2, 3].map(k => `k${k} ${th[L.MD + k].toFixed(3)}`).join(', ') +
    `; MDT by type ` + TYPES.map((t, i) => `${t} ${th[L.MDT + i].toFixed(2)}`).join(', '));
  lines.push('');
  lines.push('Best arms against the model\'s choice on the average map (win points, x25 logit); a negative best means the model\'s');
  lines.push('choice wins. maps: the share of pool maps where some arm beats the model. boot: how often bootstrap refits agree on');
  lines.push('the best arm, and the 10th percentile of its gain.');
  for (let t = 0; t < NT; t++) {
    if (TYPES[t] === 'stellar') continue;
    for (let kb = 0; kb < KB; kb++) {
      const g = armGains(th, t, kb, null), ranked = [...g].sort((a, b) => b[1] - a[1]);
      const beats = table.maps.filter(m => best(armGains(th, t, kb, m.z))[1] > 0).length / table.maps.length;
      let agree = '', p10 = '';
      if (boots.length) {
        const top = ranked[0][0], gains = boots.map(b => armGains(b, t, kb, null)).map(x => [best(x)[0], x.get(top)]);
        agree = ` boot ${(100 * gains.filter(([a]) => a === top).length / boots.length).toFixed(0)}%`;
        const s = gains.map(x => x[1]).sort((a, b) => a - b);
        p10 = ` p10 ${(PTS * s[Math.floor(0.1 * s.length)]).toFixed(1)}`;
      }
      lines.push(`  ${TYPES[t].padEnd(14)} k${kb}${kb === 3 ? '+' : ' '} ` + ranked.slice(0, 4).map(([a, v]) => `${armName(a)} ${(PTS * v).toFixed(1)}`).join(', ') +
        `  | worst ${armName(ranked.at(-1)[0])} ${(PTS * ranked.at(-1)[1]).toFixed(1)} | maps ${(100 * beats).toFixed(0)}%${agree}${p10}`);
    }
  }
  fs.writeFileSync(out.replace(/\.json$/, '.md'), lines.join('\n') + '\n');
  console.log(lines.join('\n'));
}

// ---- main ---------------------------------------------------------------------------------------
async function main() {
  const o = args();
  const labs = String(o.labs ?? 'main,pilot').split(',').map(l => path.join(ROOT, 'replays', 'emblab', l));
  const out = path.resolve(o.out ?? path.join(labs[0], 'model.json'));
  const table = mapTable(labs[0]);
  const rows = [];
  const t0 = Date.now();
  for (const lab of labs) loadLab(lab, table, rows);
  console.log(`${rows.length} games, ${P} columns; loaded in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  const prev = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')) : null;
  let lam = { ...DEFAULT_LAM, ...(prev?.lam ?? {}) }, alpha = prev?.alpha ?? 0.3;
  const cv = {};
  if (o.search) {
    // Coordinate search, scored on wins.
    let bestLoss = cvLoss(rows, 'map', lam, alpha);
    for (const g of ['e', 'k', 'mdt', 'mz', 'w']) {
      for (const mult of [0.3, 3]) {
        const trial = { ...lam, [g]: lam[g] * mult }, loss = cvLoss(rows, 'map', trial, alpha);
        console.log(`  ${g} x${mult}: ${loss.toFixed(5)}`);
        if (loss < bestLoss - 1e-6) { bestLoss = loss; lam = trial; }
      }
    }
    for (const a of [0, 0.15, 0.45]) {
      const loss = cvLoss(rows, 'map', lam, a);
      console.log(`  alpha ${a}: ${loss.toFixed(5)}`);
      if (loss < bestLoss - 1e-6) { bestLoss = loss; alpha = a; }
    }
    for (const v of Object.keys(VARIANTS)) cv[v] = cvLoss(rows, v, lam, alpha);
    console.log('cv log loss by variant (chosen penalties):', Object.entries(cv).map(([k, v]) => `${k} ${v.toFixed(5)}`).join(', '));
  }
  const lamv = lamVector('map', lam), data = prepare(rows, alpha);
  const th = lbfgs(data, lamv);
  // Bootstrap over maps: refits on resampled maps, warm-started from the fit.
  const boots = [];
  const keys = [...new Set(rows.map(r => r.key))], byKey = new Map(keys.map(k => [k, []]));
  rows.forEach((r, i) => byKey.get(r.key).push(i));
  const r = rng(12345);
  for (let b = 0; b < +(o.boot ?? 0); b++) {
    const w = new Float64Array(rows.length);
    for (let i = 0; i < keys.length; i++) for (const j of byKey.get(keys[Math.floor(r() * keys.length)])) w[j]++;
    boots.push(lbfgs(data.map((x, j) => ({ ...x, w: w[j] })).filter(x => x.w), lamv, th));
  }
  const model = { created: new Date().toISOString(), labs: labs.map(l => path.basename(l)), games: rows.length, lam, alpha, cv, L, P,
    features: FEATURES, mean: table.mean, sd: table.sd, theta: Array.from(th), boots: boots.length };
  fs.writeFileSync(out, JSON.stringify(model) + '\n');
  console.log(`wrote ${path.relative(ROOT, out)} (alpha ${alpha}, lam ${JSON.stringify(lam)}, ${boots.length} bootstrap refits) in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  report(th, boots, table, out);
}

const self = p => fs.realpathSync(p).toLowerCase();
if (process.argv[1] && self(process.argv[1]) === self(fileURLToPath(import.meta.url))) await main();
