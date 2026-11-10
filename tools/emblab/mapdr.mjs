// Map-keyed emblem policies (PLAN-draft3.md, open question "map-conditioned emblems"), from dfit.mjs --mapdr.
// Each map gets a bin in every partition: 8 quantile bins of each standardised draft feature, and k-means clusters
// of all of them for k 2-6. drStats sums the doubly robust D = Gamma(candidate) - Gamma(base) per (fold, cell,
// partition bin, candidate). A policy config is a granularity (cell = picks x type x ordinal; type x ordinal bucket;
// type), a split (none; one feature at a bin threshold; a clustering) and z; per (granularity cell, side) it takes
// the candidate whose mean D clears z standard errors, else the base. Nested cross-fitting: per outer fold, the
// config with the best cross-fitted gain on the other four folds is chosen there and its selection on those four
// is scored on the outer fold, so the estimate stays honest however many configs are searched.
import fs from 'node:fs';
import { FEATURES } from '../draftlab/model.mjs';

export const NB = 8;
const SEARCH = { cuts: null };
const ZS = [0, 1, 2, 3], MIN_N = 30;

function kmeans(points, k, dim) {
  let s = 12345 + k;
  const rnd = () => (s = (Math.imul(s, 1103515245) + 12345) >>> 0) / 4294967296;
  const n = points.length, centres = [points[Math.floor(rnd() * n)].slice()], d2 = new Float64Array(n).fill(Infinity);
  const dist = (p, c) => { let e = 0; for (let j = 0; j < dim; j++) e += (p[j] - c[j]) ** 2; return e; };
  while (centres.length < k) {
    let sum = 0;
    for (let i = 0; i < n; i++) { d2[i] = Math.min(d2[i], dist(points[i], centres[centres.length - 1])); sum += d2[i]; }
    let u = rnd() * sum, i = 0;
    while (i < n - 1 && (u -= d2[i]) > 0) i++;
    centres.push(points[i].slice());
  }
  const assign = new Uint8Array(n);
  for (let it = 0; it < 50; it++) {
    let changed = 0;
    for (let i = 0; i < n; i++) {
      let best = 0, bd = Infinity;
      for (let c = 0; c < k; c++) { const e = dist(points[i], centres[c]); if (e < bd) bd = e, best = c; }
      if (assign[i] !== best || it === 0) changed++;
      assign[i] = best;
    }
    const sum = Array.from({ length: k }, () => new Float64Array(dim)), cnt = new Float64Array(k);
    for (let i = 0; i < n; i++) { cnt[assign[i]]++; for (let j = 0; j < dim; j++) sum[assign[i]][j] += points[i][j]; }
    for (let c = 0; c < k; c++) if (cnt[c]) for (let j = 0; j < dim; j++) centres[c][j] = sum[c][j] / cnt[c];
    if (!changed) break;
  }
  return { assign, centres: centres.map(c => Array.from(c)) };
}

// bins: Uint8Array (shared) of maps x partitions. opts (round 4 on; without it every feature, every cut, k-means 2-6):
// splits: the feature names to split on (a short list stated before the run keeps the nested search's choice
// stable); cuts: the bin thresholds tried (1..NB-1); kmeans: the cluster counts, over the first `dims` features.
export function partitions(table, opts = {}) {
  const maps = table.maps, n = maps.length, K = FEATURES.length, list = [];
  SEARCH.cuts = opts.cuts ?? null;
  for (let k = 0; k < K; k++) {
    if (opts.splits && !opts.splits.includes(FEATURES[k][0])) continue;
    const v = maps.map(m => m.z[k]).sort((a, b) => a - b);
    // bin = number of cuts at or below the value; ties can leave bins empty.
    const cuts = Array.from({ length: NB - 1 }, (_, j) => v[Math.floor(n * (j + 1) / NB)]);
    list.push({ name: FEATURES[k][0], kind: 'feature', feature: k, nb: NB, cuts, binOf: m => { let b = 0; while (b < NB - 1 && m.z[k] >= cuts[b]) b++; return b; } });
  }
  const dims = opts.dims ?? K, pts = maps.map(m => Array.from(m.z.subarray(0, dims)));
  for (const kc of opts.kmeans ?? [2, 3, 4, 5, 6]) {
    const { assign, centres } = kmeans(pts, kc, dims);
    list.push({ name: `kmeans${kc}`, kind: 'cluster', nb: kc, centres, binOf: (m, i) => assign[i] });
  }
  const bins = new Uint8Array(new SharedArrayBuffer(n * list.length));
  maps.forEach((m, i) => list.forEach((p, j) => { bins[i * list.length + j] = p.binOf(m, i); }));
  return { list, bins, npart: list.length, nslot: list.length * NB };
}

// F: per fold Float64Array(ncell0 * nslot * ncand * 3) of (sum D, sum D^2, n). dims: { NP, NT, ORD, NKC, KC, NCAND, NA,
// TYPES, armName }.
export function mapReport(F, rows, parts, dims, out) {
  const { NP, NT, ORD, NKC, KC, NCAND, NA, TYPES, armName } = dims, NCELL0 = NP * NT * ORD, FOLDS = F.length, NSLOT = parts.nslot;
  const GRAN = [
    { name: 'cell', n: NCELL0, of: c => c },
    { name: 'type x bucket', n: NT * NKC, of: c => (Math.floor(c / ORD) % NT) * NKC + KC(c % ORD) },
    { name: 'type', n: NT, of: c => Math.floor(c / ORD) % NT },
  ];
  const configs = [];
  for (let g = 0; g < GRAN.length; g++) {
    configs.push({ g, p: -1, ns: 1, side: () => 0 });
    parts.list.forEach((p, pi) => {
      if (p.kind === 'cluster') configs.push({ g, p: pi, ns: p.nb, side: b => b });
      else for (let j = 1; j < NB; j++) if ((!SEARCH.cuts || SEARCH.cuts.includes(j)) && (j === 1 || p.cuts[j - 1] !== p.cuts[j - 2])) configs.push({ g, p: pi, j, ns: 2, side: b => b >= j ? 1 : 0 });
    });
  }
  const label = c => `${GRAN[c.g].name}, ${c.p < 0 ? 'static' : parts.list[c.p].kind === 'cluster' ? parts.list[c.p].name
    : `${parts.list[c.p].name} >= ${parts.list[c.p].cuts[c.j - 1].toFixed(2)} (z, bin ${c.j}/${NB})`}`;
  const sides = (S, c) => {
    const G = GRAN[c.g], out = new Float64Array(G.n * c.ns * NCAND * 3), p = Math.max(0, c.p), nb = c.p < 0 ? NB : parts.list[c.p].nb;
    for (let c0 = 0; c0 < NCELL0; c0++) {
      const gc = G.of(c0);
      for (let b = 0; b < nb; b++) {
        const src = ((c0 * NSLOT + p * NB + b) * NCAND) * 3, dst = ((gc * c.ns + c.side(b)) * NCAND) * 3;
        for (let x = 0; x < NCAND * 3; x++) out[dst + x] += S[src + x];
      }
    }
    return out;
  };
  const selectAll = (S, ncell) => ZS.map(z => {
    const sel = new Int16Array(ncell).fill(-1);
    for (let c = 0; c < ncell; c++) {
      let bm = 0;
      for (let k = 0; k < NCAND; k++) {
        const o = (c * NCAND + k) * 3, n = S[o + 2];
        if (n < MIN_N) continue;
        const m = S[o] / n, se = Math.sqrt(Math.max(0, S[o + 1] / n - m * m) / n);
        if (m - z * se > bm) bm = m - z * se, sel[c] = k;
      }
    }
    return sel;
  });
  const score = (sel, S) => {
    let gain = 0, v = 0, moved = 0;
    for (let c = 0; c < sel.length; c++) {
      if (sel[c] < 0) continue;
      const o = (c * NCAND + sel[c]) * 3, n = S[o + 2];
      if (!n) continue;
      gain += S[o]; v += S[o + 1] - S[o] * S[o] / n; moved += n;
    }
    return { gain, v, moved };
  };
  const minus = (T, ...xs) => { const r = Float64Array.from(T); for (const x of xs) for (let i = 0; i < r.length; i++) r[i] -= x[i]; return r; };

  // Per (config, z): single-level cross-fitted score, and per outer fold the inner score and the outer score.
  const H = [];
  for (const c of configs) {
    const Sd = F.map(S => sides(S, c)), ncell = GRAN[c.g].n * c.ns;
    const T = new Float64Array(Sd[0].length);
    for (const S of Sd) for (let i = 0; i < T.length; i++) T[i] += S[i];
    const hs = ZS.map(z => ({ c, z, cv: { gain: 0, v: 0, moved: 0 }, inner: new Float64Array(FOLDS), outer: [] }));
    for (let f = 0; f < FOLDS; f++) {
      const so = selectAll(minus(T, Sd[f]), ncell);
      ZS.forEach((_, zi) => { const s = score(so[zi], Sd[f]); hs[zi].outer[f] = s; for (const k of ['gain', 'v', 'moved']) hs[zi].cv[k] += s[k]; });
      for (let i = 0; i < FOLDS; i++) if (i !== f) {
        const si = selectAll(minus(T, Sd[f], Sd[i]), ncell);
        ZS.forEach((_, zi) => { hs[zi].inner[f] += score(si[zi], Sd[i]).gain; });
      }
    }
    H.push(...hs);
  }
  const pts = x => (100 * x / rows).toFixed(3), se = v => (100 * Math.sqrt(v) / rows).toFixed(3);
  const nested = pool => {
    let gain = 0, v = 0, moved = 0;
    const chosen = [];
    for (let f = 0; f < FOLDS; f++) {
      const h = pool.reduce((a, b) => b.inner[f] > a.inner[f] ? b : a);
      chosen.push(`${label(h.c)}, z ${h.z}`);
      gain += h.outer[f].gain; v += h.outer[f].v; moved += h.outer[f].moved;
    }
    return { gain, v, moved, chosen };
  };
  const lines = ['', `Map-keyed policies (${configs.length * ZS.length} configs: ${configs.length} granularity x split, z ${ZS.join('/')}), ${rows} decisions; ` +
    'gains in win points per decision +- se.'];
  for (const [name, pool] of [['all configs', H], ['static configs only', H.filter(h => h.c.p < 0)], ['map-keyed configs only', H.filter(h => h.c.p >= 0)]]) {
    const r = nested(pool);
    lines.push(`  nested, ${name}: ${pts(r.gain)} +- ${se(r.v)}; moves ${(100 * r.moved / rows).toFixed(0)}%; chosen per outer fold: ${r.chosen.join(' | ')}`);
  }
  const ranked = [...H].sort((a, b) => b.cv.gain - a.cv.gain);
  lines.push(`  top 15 by single-level cross-fitted gain (optimistic: best of ${H.length}):`);
  for (const h of ranked.slice(0, 15)) lines.push(`    ${pts(h.cv.gain)} +- ${se(h.cv.v)}, moves ${(100 * h.cv.moved / rows).toFixed(0)}%: ${label(h.c)}, z ${h.z}`);
  lines.push('  static, per granularity and z:');
  for (const h of H.filter(h => h.c.p < 0)) lines.push(`    ${pts(h.cv.gain)} +- ${se(h.cv.v)}, moves ${(100 * h.cv.moved / rows).toFixed(0)}%: ${label(h.c)}, z ${h.z}`);

  // The user's hypothesis, stated before the run: Prospector is better on maps with many gem clusters.
  // Descriptive (all folds): mean D of always taking each Prospector arm, by cluster_share bin.
  const pc = parts.list.findIndex(p => p.name === 'cluster_share');
  if (pc >= 0) {
    const T = new Float64Array(F[0].length);
    for (const S of F) for (let i = 0; i < T.length; i++) T[i] += S[i];
    const cuts = parts.list[pc].cuts;
    lines.push(`  Prospector by cluster_share bin (z cuts ${cuts.map(x => x.toFixed(2)).join(', ')}; empty bins are ties), mean D in points +- se, n:`);
    for (let a = 0; a < NA; a++) {
      if (!armName(a).startsWith('prospector')) continue;
      const cell = [];
      for (let b = 0; b < NB; b++) {
        let s = 0, s2 = 0, n = 0;
        for (let c0 = 0; c0 < NCELL0; c0++) { const o = ((c0 * NSLOT + pc * NB + b) * NCAND + a) * 3; s += T[o]; s2 += T[o + 1]; n += T[o + 2]; }
        cell.push(n ? `b${b} ${(100 * s / n).toFixed(2)}+-${(100 * Math.sqrt(Math.max(0, s2 / n - (s / n) ** 2) / n)).toFixed(2)} (${(n / 1e6).toFixed(2)}M)` : `b${b} -`);
      }
      lines.push(`    ${armName(a)}: ${cell.join(', ')}`);
    }
    lines.push('    per type, top half of bins against bottom half (cluster_share z >= cut 4), best Prospector arm by top-half mean:');
    for (let t = 0; t < NT; t++) {
      let best = null;
      for (let a = 0; a < NA; a++) {
        if (!armName(a).startsWith('prospector')) continue;
        const acc = [[0, 0, 0], [0, 0, 0]];
        for (let c0 = 0; c0 < NCELL0; c0++) {
          if (Math.floor(c0 / ORD) % NT !== t) continue;
          for (let b = 0; b < NB; b++) { const o = ((c0 * NSLOT + pc * NB + b) * NCAND + a) * 3, h = b >= NB / 2 ? 1 : 0; for (let x = 0; x < 3; x++) acc[h][x] += T[o + x]; }
        }
        const m = acc.map(([s, s2, n]) => n ? { m: s / n, se: Math.sqrt(Math.max(0, s2 / n - (s / n) ** 2) / n), n } : null);
        if (m[1] && (!best || m[1].m > best.m[1].m)) best = { a, m };
      }
      if (best) lines.push(`      ${TYPES[t]}: ${armName(best.a)} low ${best.m[0] ? `${(100 * best.m[0].m).toFixed(2)}+-${(100 * best.m[0].se).toFixed(2)}` : '-'}, ` +
        `high ${(100 * best.m[1].m).toFixed(2)}+-${(100 * best.m[1].se).toFixed(2)} (${(best.m[1].n / 1e3).toFixed(0)}k)`);
    }
  }

  // Selections on all folds: every static config, and the 8 best by single-level cross-fitted gain (the first of
  // those is what rounds before 4 wrote alone). candidate.py --mappolicy reads one by its label.
  const emit = h => {
    const c = h.c, ncell = GRAN[c.g].n * c.ns;
    const T = new Float64Array(ncell * NCAND * 3);
    for (const S of F) { const sd = sides(S, c); for (let i = 0; i < T.length; i++) T[i] += sd[i]; }
    const sel = selectAll(T, ncell)[ZS.indexOf(h.z)], cells = [];
    for (let x = 0; x < ncell; x++) if (sel[x] >= 0) {
      const o = (x * NCAND + sel[x]) * 3;
      cells.push({ cell: Math.floor(x / c.ns), side: x % c.ns, choice: sel[x] === NA ? 'current' : armName(sel[x]), arm: sel[x] === NA ? -1 : sel[x], gain: T[o] / T[o + 2], n: T[o + 2] });
    }
    const p = c.p >= 0 ? parts.list[c.p] : null;
    return { config: label(c), z: h.z, granularity: GRAN[c.g].name, cv: { gain: 100 * h.cv.gain / rows, se: 100 * Math.sqrt(h.cv.v) / rows, moved: h.cv.moved / rows },
      partition: p && { name: p.name, kind: p.kind, feature: p.feature, threshold_z: p.kind === 'feature' ? p.cuts[c.j - 1] : undefined, centres: p.centres }, cells };
  };
  const wanted = [...ranked.slice(0, 8), ...H.filter(h => h.c.p < 0 && !ranked.slice(0, 8).includes(h))];
  fs.writeFileSync(out.replace(/\.json$/, '.mappolicy.json'), JSON.stringify({ ...emit(ranked[0]), all: wanted.map(emit) }) + '\n');
  return lines;
}
