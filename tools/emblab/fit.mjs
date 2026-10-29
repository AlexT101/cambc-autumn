// Emblem lab fit (tools/emblab/README.md): P(A wins) from the draft and the table's emblem assignments, over one
// or more labs' games, by penalised logistic regression (L-BFGS) with cross-validation over maps.
//   node tools/emblab/fit.mjs --labs main,pilot [--out replays/emblab/main/model.json] [--search] [--boot N] [--threads 90]
//
// logit P(A wins) = side + sum over A's champions of (b_c + w_c . z) + sum over A's assigned arms of value(arm)
//                 - the same for B,
// value(arm) for a champion of type t at its k-th new emblem (kb = min(k, 3)) on a map with features z:
//   ET[t, family] + ST[t, stat] + EK[kb, family] + SK[kb, stat] + MZ[family] . z - (MD[kb] + MDT[t]),
// MD + MDT being what the model's own (state-dependent) choice is worth. Every block but MZ also has a copy per
// pick count (3, 4, 5), penalised toward 0 on its own: each pick count's model is the shared one plus its deviation,
// as the draft lab fits each pick count toward the pooled fit. Assignments come from the table, not the
// logged decisions: they are random whether or not the game reaches them, while how many emblems a champion
// reaches depends on how its game goes (an intention-to-treat fit; a reached decision's log is not needed).
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
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

// Column layout and penalty groups. MZ goes last, so a fit without it stops each row at MZ (cut).
const PICKS = [3, 4, 5];
const L = {}, N = {};
let P = 0;
const GROUPS = [];
function block(name, n, group) { L[name] = P; N[name] = n; for (let i = 0; i < n; i++) GROUPS.push(group); P += n; }
function sized(name, n, group, pgroup) { block(name, n, group); block(name + 'P', n * PICKS.length, pgroup); }
sized('SIDE', 1, 'side', 'side');
sized('B', NC, 'b', 'bp');
sized('W', NC * K, 'w', 'wp');
sized('ET', NT * NF, 'e', 'ep');
sized('ST', NT * 3, 'e', 'ep');
sized('EK', KB * NF, 'k', 'kp');
sized('SK', KB * 3, 'k', 'kp');
sized('MD', KB, 'md', 'mdp');
sized('MDT', NT, 'mdt', 'mdtp');
block('MZ', NF * K, 'mz');
const GNAMES = ['side', 'b', 'w', 'e', 'k', 'md', 'mdt', 'bp', 'wp', 'ep', 'kp', 'mdp', 'mdtp', 'mz'];
const GI = Object.fromEntries(GNAMES.map((g, i) => [g, i]));
const GROUP = Int8Array.from(GROUPS, g => GI[g]);
const SIZED = ['bp', 'wp', 'ep', 'kp', 'mdp', 'mdtp'];
const VARIANTS = {
  draft: ['side', 'b', 'w'],
  draft_sized: ['side', 'b', 'w', 'bp', 'wp'],
  emblem: ['side', 'b', 'w', 'md', 'mdt', 'e', 'k'],
  sized: ['side', 'b', 'w', 'md', 'mdt', 'e', 'k', ...SIZED],
  map: ['side', 'b', 'w', 'md', 'mdt', 'e', 'k', ...SIZED, 'mz'],
};
const DEFAULT_LAM = { side: 0.01, b: 1, w: 81, e: 270, k: 81, mz: 2700, md: 0.1, mdt: 90, bp: 4, wp: 320, ep: 1000, kp: 320, mdp: 1, mdtp: 360 };
// A shared column and its copy for pick count index pi: the value read off a fit for that pick count.
const at = (th, name, i, pi) => th[L[name] + i] + th[L[name + 'P'] + pi * N[name] + i];

// Line by line: games.jsonl outgrows Node's longest string.
function* readJsonl(f) {
  if (!fs.existsSync(f)) return;
  const fd = fs.openSync(f, 'r'), buf = Buffer.alloc(1 << 24);
  let rest = '';
  try {
    for (let n; (n = fs.readSync(fd, buf, 0, buf.length, null)) > 0;) {
      const lines = (rest + buf.toString('utf8', 0, n)).split('\n');
      rest = lines.pop();
      for (const l of lines) if (l) yield JSON.parse(l);
    }
    if (rest) yield JSON.parse(rest);
  } finally { fs.closeSync(fd); }
}
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
  const maps = [...readJsonl(path.join(lab, 'maps.jsonl'))];
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

function loadLab(lab, table, rows) {
  for (const g of readJsonl(path.join(lab, 'games.jsonl'))) {
    if (g.error || g.winner === undefined || g.draft_ok === false || !g.wealth) continue;
    const m = table.byKey.get(g.key), pi = PICKS.indexOf(m?.picks);
    if (pi < 0) continue;
    const r = new Row(), put = (name, i, v) => { r.add(L[name] + i, v); r.add(L[name + 'P'] + pi * N[name] + i, v); };
    put('SIDE', 0, 1);
    for (const [S, s] of [['A', 1], ['B', -1]]) {
      const T = g[S], arms = g[`arms${S}`];
      for (const c of T) { const i = CHAMPS.indexOf(c); put('B', i, s); for (let k = 0; k < K; k++) put('W', i * K + k, s * m.z[k]); }
      if (!arms) continue;
      const rows_ = T.map((c, i) => [i, typeOf(c)]);
      if (T.includes('cassi_and_issac')) rows_.push([5, TYPES.indexOf('issac')]);
      for (const [row, t] of rows_)
        for (let k = 0; k < ORDINALS; k++) {
          const arm = arms[row][k];
          if (arm === MODEL) continue;
          const kb = Math.min(k, KB - 1), f = Math.floor(arm / 3), st = arm % 3;
          put('ET', t * NF + f, s); put('ST', t * 3 + st, s); put('EK', kb * NF + f, s); put('SK', kb * 3 + st, s);
          put('MD', kb, -s); put('MDT', t, -s);
          for (let q = 0; q < K; q++) if (m.z[q]) r.add(L.MZ + f * K + q, s * m.z[q]);
        }
    }
    const [a, b] = g.wealth;
    rows.push({ ...r.pack(), win: g.winner === 0 ? 1 : 0, soft: sigmoid(KAPPA * (a - b) / (a + b + 50)), fold: hash(g.key) % FOLDS, key: g.key, pi });
  }
}

// All rows as one CSR matrix in shared memory, for the workers.
function pack(rows) {
  const nnz = rows.reduce((a, r) => a + r.idx.length, 0), n = rows.length;
  const sab = (T, len) => new T(new SharedArrayBuffer(len * T.BYTES_PER_ELEMENT));
  const D = { n, ptr: sab(Int32Array, n + 1), cut: sab(Int32Array, n), idx: sab(Int32Array, nnz), val: sab(Float64Array, nnz),
    win: sab(Uint8Array, n), soft: sab(Float64Array, n), fold: sab(Uint8Array, n), pi: sab(Uint8Array, n), key: sab(Int32Array, n) };
  const keys = new Map();
  let o = 0;
  rows.forEach((r, i) => {
    D.ptr[i] = o;
    D.idx.set(r.idx, o); D.val.set(r.val, o); o += r.idx.length;
    let c = D.ptr[i];
    while (c < o && D.idx[c] < L.MZ) c++;
    D.cut[i] = c;
    D.win[i] = r.win; D.soft[i] = r.soft; D.fold[i] = r.fold; D.pi[i] = r.pi;
    if (!keys.has(r.key)) keys.set(r.key, keys.size);
    D.key[i] = keys.get(r.key);
  });
  D.ptr[n] = o;
  D.nkeys = keys.size;
  return D;
}

// ---- optimisation ----------------------------------------------------------------------------------
// Weighted penalised log loss on target y = (1 - alpha) win + alpha soft; rows with weight 0 are skipped.
function objective(D, w, alpha, mz, th, lam, grad) {
  grad.fill(0);
  let f = 0;
  for (let i = 0; i < D.n; i++) {
    const wi = w[i];
    if (!wi) continue;
    const a = D.ptr[i], b = mz ? D.ptr[i + 1] : D.cut[i], y = (1 - alpha) * D.win[i] + alpha * D.soft[i];
    let e = 0;
    for (let k = a; k < b; k++) e += th[D.idx[k]] * D.val[k];
    f += wi * (softplus(e) - y * e);
    const g = wi * (sigmoid(e) - y);
    for (let k = a; k < b; k++) grad[D.idx[k]] += g * D.val[k];
  }
  for (let j = 0; j < th.length; j++) if (lam[j]) { f += 0.5 * lam[j] * th[j] * th[j]; grad[j] += lam[j] * th[j]; }
  return f;
}

function lbfgs(D, w, alpha, lamv, init, iters = 300, m = 12) {
  const n = P, th = Float64Array.from(init ?? new Float64Array(n)), g = new Float64Array(n), gn = new Float64Array(n), tn = new Float64Array(n);
  const S = [], Y = [], R = [];
  // Infinite penalties freeze a column at 0: a variant without that group.
  const live = Uint8Array.from(lamv, v => Number.isFinite(v) ? 1 : 0);
  const lam = Float64Array.from(lamv, v => Number.isFinite(v) ? v : 0);
  const mz = live[L.MZ] === 1;
  for (let j = 0; j < n; j++) if (!live[j]) th[j] = 0;
  let f = objective(D, w, alpha, mz, th, lam, g);
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
      fn = objective(D, w, alpha, mz, tn, lam, gn);
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
  const on = new Set(VARIANTS[variant]);
  return Float64Array.from(GROUP, g => on.has(GNAMES[g]) ? lam[GNAMES[g]] : Infinity);
}

// One job: {fold} fits without that fold and scores it on wins (sum and count per pick count);
// {boot} fits on maps resampled with that seed; neither fits everything.
function job(D, { variant, lam, alpha, fold, boot, init }) {
  const w = new Float64Array(D.n), lamv = lamVector(variant, lam);
  if (fold !== undefined) for (let i = 0; i < D.n; i++) w[i] = D.fold[i] !== fold ? 1 : 0;
  else if (boot !== undefined) {
    const r = rng(12345 + 7919 * boot), cnt = new Float64Array(D.nkeys);
    for (let i = 0; i < D.nkeys; i++) cnt[Math.floor(r() * D.nkeys)]++;
    for (let i = 0; i < D.n; i++) w[i] = cnt[D.key[i]];
  } else w.fill(1);
  const th = lbfgs(D, w, alpha, lamv, init && Float64Array.from(init));
  if (fold === undefined) return { theta: Array.from(th) };
  const loss = PICKS.map(() => 0), n = PICKS.map(() => 0), mz = Number.isFinite(lamv[L.MZ]);
  for (let i = 0; i < D.n; i++) if (D.fold[i] === fold) {
    let e = 0;
    for (let k = D.ptr[i], b = mz ? D.ptr[i + 1] : D.cut[i]; k < b; k++) e += th[D.idx[k]] * D.val[k];
    const p = Math.min(1 - 1e-9, Math.max(1e-9, sigmoid(e)));
    loss[D.pi[i]] -= D.win[i] ? Math.log(p) : Math.log(1 - p);
    n[D.pi[i]]++;
  }
  return { loss, n };
}

class Pool {
  constructor(D, threads) {
    this.free = []; this.queue = [];
    for (let t = 0; t < threads; t++) {
      const w = new Worker(fileURLToPath(import.meta.url), { workerData: { ...D, kind: 'fit' } });
      w.on('message', res => { const cb = w.cb; w.cb = null; this.free.push(w); this.pump(); cb(res); });
      w.on('error', e => { throw e; });
      this.free.push(w);
    }
  }
  run(task) { return new Promise(resolve => { this.queue.push([task, resolve]); this.pump(); }); }
  pump() { while (this.free.length && this.queue.length) { const w = this.free.pop(), [task, cb] = this.queue.shift(); w.cb = cb; w.postMessage(task); } }
  close() { for (const w of this.free) w.terminate(); }
}

// CV log loss on wins: overall and per pick count.
async function cvLoss(pool, variant, lam, alpha) {
  const parts = await Promise.all(Array.from({ length: FOLDS }, (_, fold) => pool.run({ variant, lam, alpha, fold })));
  const loss = PICKS.map((_, p) => parts.reduce((a, x) => a + x.loss[p], 0)), n = PICKS.map((_, p) => parts.reduce((a, x) => a + x.n[p], 0));
  return { all: loss.reduce((a, b) => a + b) / n.reduce((a, b) => a + b), picks: PICKS.map((_, p) => loss[p] / n[p]) };
}
const fmt = c => `${c.all.toFixed(5)} (` + PICKS.map((p, i) => `${p}: ${c.picks[i].toFixed(4)}`).join(', ') + ')';

// ---- policy -------------------------------------------------------------------------------------
// Every arm's value against the model's choice (logit), for type t at bucket kb, pick count index pi, on map z
// (z null: the average map).
export function armGains(th, t, kb, pi, z) {
  const out = new Map(), md = at(th, 'MD', kb, pi) + at(th, 'MDT', t, pi);
  for (const arm of ARMS) {
    const f = Math.floor(arm / 3), st = arm % 3;
    let s = at(th, 'ET', t * NF + f, pi) + at(th, 'ST', t * 3 + st, pi) + at(th, 'EK', kb * NF + f, pi) + at(th, 'SK', kb * 3 + st, pi) - md;
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

// Also writes <out>.policy.json: per pick count, type and bucket, the best arm, its gain (logit), bootstrap agreement
// and 10th percentile (tools/emblab/policy.py turns it into astraeus's table).
function report(th, boots, table, out, mz) {
  const lines = [], cells = [];
  lines.push('Champion strength b_c by pick count (win points, x25 logit, on the average map):');
  for (let c = 0; c < NC; c++) lines.push(`  ${CHAMPS[c].padEnd(16)}` + PICKS.map((p, pi) => `${p}: ${(PTS * at(th, 'B', c, pi)).toFixed(1).padStart(5)}`).join('  '));
  lines.push('');
  lines.push('Best arms against the model\'s choice on the average map (win points); a negative best means the model\'s choice');
  lines.push('wins. maps: the share of pool maps where some arm beats it (100% or 0% without map terms). boot: how often');
  lines.push('bootstrap refits agree on the best arm, and the 10th percentile of its gain.');
  PICKS.forEach((p, pi) => {
    lines.push('');
    lines.push(`${p} picks. Model choice term MD by ordinal ` + [0, 1, 2, 3].map(k => `k${k} ${at(th, 'MD', k, pi).toFixed(3)}`).join(', '));
    const maps = table.maps.filter(m => m.picks === p);
    for (let t = 0; t < NT; t++) {
      if (TYPES[t] === 'stellar') continue;
      for (let kb = 0; kb < KB; kb++) {
        const g = armGains(th, t, kb, pi, null), ranked = [...g].sort((a, b) => b[1] - a[1]);
        const beats = mz ? maps.filter(m => best(armGains(th, t, kb, pi, m.z))[1] > 0).length / maps.length : +(ranked[0][1] > 0);
        let agree = '', p10 = '';
        const cell = { picks: p, type: TYPES[t], kb, arm: ranked[0][0], name: armName(ranked[0][0]), gain: ranked[0][1] };
        if (boots.length) {
          const top = ranked[0][0], gains = boots.map(b => armGains(b, t, kb, pi, null)).map(x => [best(x)[0], x.get(top)]);
          cell.agree = gains.filter(([a]) => a === top).length / boots.length;
          const s = gains.map(x => x[1]).sort((a, b) => a - b);
          cell.p10 = s[Math.floor(0.1 * s.length)];
          agree = ` boot ${(100 * cell.agree).toFixed(0)}%`;
          p10 = ` p10 ${(PTS * cell.p10).toFixed(1)}`;
        }
        cells.push(cell);
        lines.push(`  ${TYPES[t].padEnd(14)} k${kb}${kb === 3 ? '+' : ' '} ` + ranked.slice(0, 4).map(([a, v]) => `${armName(a)} ${(PTS * v).toFixed(1)}`).join(', ') +
          `  | worst ${armName(ranked.at(-1)[0])} ${(PTS * ranked.at(-1)[1]).toFixed(1)} | maps ${(100 * beats).toFixed(0)}%${agree}${p10}`);
      }
    }
  });
  fs.writeFileSync(out.replace(/\.json$/, '.md'), lines.join('\n') + '\n');
  fs.writeFileSync(out.replace(/\.json$/, '.policy.json'), JSON.stringify({ boots: boots.length, buckets: KB, cells }, null, 1) + '\n');
  console.log(lines.join('\n'));
}

// ---- main ---------------------------------------------------------------------------------------
async function main() {
  const o = args();
  const labs = String(o.labs ?? 'main,pilot').split(',').map(l => path.join(ROOT, 'replays', 'emblab', l));
  const out = path.resolve(o.out ?? path.join(labs[0], 'model.json'));
  const table = mapTable(labs[0]);
  const rows = [];
  const t0 = Date.now(), secs = () => ((Date.now() - t0) / 1000).toFixed(0);
  for (const lab of labs) loadLab(lab, table, rows);
  const D = pack(rows);
  rows.length = 0;
  console.log(`${D.n} games (` + PICKS.map((p, pi) => `${p}: ${D.pi.filter(x => x === pi).length}`).join(', ') + `), ${P} columns, ${D.ptr[D.n]} entries; loaded in ${secs()} s`);
  const pool = new Pool(D, +(o.threads ?? Math.max(1, os.cpus().length - 6)));
  const prev = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')) : null;
  let lam = { ...DEFAULT_LAM, ...(prev?.lam ?? {}) }, alpha = prev?.alpha ?? 0.15;
  let cv = {};
  if (o.search) {
    // Rounds of coordinate search, scored on wins: every group's two multipliers at once from the same start, then
    // all the improving ones together (or the single best if together is worse).
    let base = (await cvLoss(pool, 'sized', lam, alpha)).all;
    console.log(`start ${base.toFixed(5)} (${secs()} s)`);
    const groups = ['w', 'e', 'k', 'mdt', ...SIZED];
    for (let round = 0; round < 3; round++) {
      const trials = groups.flatMap(g => [0.25, 4].map(mult => ({ g, mult, lam: { ...lam, [g]: lam[g] * mult } })));
      const scores = await Promise.all(trials.map(t => cvLoss(pool, 'sized', t.lam, alpha)));
      const better = {};
      trials.forEach((t, i) => { if (scores[i].all < base - 1e-6 && (!better[t.g] || scores[i].all < better[t.g].s)) better[t.g] = { ...t, s: scores[i].all }; });
      const moves = Object.values(better);
      console.log(`round ${round}: ` + trials.map((t, i) => `${t.g} x${t.mult} ${scores[i].all.toFixed(5)}`).join(', ') + ` (${secs()} s)`);
      if (!moves.length) break;
      const together = { ...lam };
      for (const m of moves) together[m.g] = m.lam[m.g];
      const single = moves.sort((a, b) => a.s - b.s)[0], tog = moves.length > 1 ? (await cvLoss(pool, 'sized', together, alpha)).all : single.s;
      if (tog <= single.s) { lam = together; base = tog; } else { lam = single.lam; base = single.s; }
      console.log(`  -> ${base.toFixed(5)} ${JSON.stringify(lam)}`);
    }
    const alphas = [0, 0.3].map(a => [a, cvLoss(pool, 'sized', lam, a)]);
    for (const [a, p] of alphas) { const c = await p; console.log(`  alpha ${a}: ${c.all.toFixed(5)}`); if (c.all < base - 1e-6) { base = c.all; alpha = a; } }
    const names = Object.keys(VARIANTS), res = await Promise.all([...names.map(v => cvLoss(pool, v, lam, alpha)), cvLoss(pool, 'map', { ...lam, mz: lam.mz * 4 }, alpha)]);
    names.forEach((v, i) => cv[v] = res[i]);
    if (res.at(-1).all < cv.map.all) { cv.map = res.at(-1); lam = { ...lam, mz: lam.mz * 4 }; }
    console.log('cv log loss on wins by variant (overall, and by pick count):');
    for (const v of names) console.log(`  ${v.padEnd(12)} ${fmt(cv[v])}`);
  }
  const scored = Object.keys(cv).length ? cv : prev?.cv ?? {};
  const variant = o.variant ?? (Object.keys(scored).length ? Object.entries(scored).sort((a, b) => a[1].all - b[1].all)[0][0] : 'sized');
  const th = Float64Array.from((await pool.run({ variant, lam, alpha })).theta);
  // Bootstrap over maps, warm-started from the fit.
  const boots = (await Promise.all(Array.from({ length: +(o.boot ?? 0) }, (_, boot) => pool.run({ variant, lam, alpha, boot, init: Array.from(th) }))))
    .map(r => Float64Array.from(r.theta));
  pool.close();
  const model = { created: new Date().toISOString(), labs: labs.map(l => path.basename(l)), games: D.n, picks: PICKS, variant, lam, alpha, cv: scored, L, N, P,
    features: FEATURES, mean: table.mean, sd: table.sd, theta: Array.from(th), boots: boots.length };
  fs.writeFileSync(out, JSON.stringify(model) + '\n');
  console.log(`wrote ${path.relative(ROOT, out)} (variant ${variant}, alpha ${alpha}, lam ${JSON.stringify(lam)}, ${boots.length} bootstrap refits) in ${secs()} s`);
  report(th, boots, table, out, VARIANTS[variant].includes('mz'));
}

const self = p => fs.realpathSync(p).toLowerCase();
// Only this module's own workers: dfit.mjs's import it too.
if (!isMainThread && workerData?.kind === 'fit') {
  const D = workerData;
  parentPort.on('message', task => parentPort.postMessage(job(D, task)));
} else if (process.argv[1] && self(process.argv[1]) === self(fileURLToPath(import.meta.url))) await main();
