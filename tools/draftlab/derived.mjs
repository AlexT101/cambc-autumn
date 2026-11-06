// Derived map features (draftfeat, 2026-11-06): values computed from a maps.jsonl row's f (features.mjs mapRow adds
// them; model.mjs raw() computes them for rows written before). map_features.cc computes the same from compute()'s values.
//   one_altar           1 when the map has exactly one altar, else 0
//   sq_<a>              T(a)^2, T = a's model.mjs FEATURES transform
//   pr_<a>__<b>         T(a) * T(b)
// A missing component (null) makes the value NaN (z 0), as a missing feature does.
export const BASE_TRANSFORMS = {
  area: 'log', reach_frac: null, spawn_dist: 'log', detour: null, choke_rel: null, openness: null, bushes: null, holes: null,
  altars: 'log1p', altar_ratio: null, altar_centre: null, gems_side: 'log1p', gold_side: 'log1p', big_share: null,
  cluster_share: null, contested_share: null, big_camp_share: null, dash_short: null, camp_near: 'log1p',
  dash_gain: 'log', narrow: null, spawn_ring: null, max_group: 'log1p', camp_altar: 'log', sight_gap: null,
};

export function transformed(f, name) {
  const v = f[name];
  if (v === null || v === undefined || !Number.isFinite(v)) return NaN;
  const tf = BASE_TRANSFORMS[name];
  return tf === 'log' ? Math.log(Math.max(v, 1)) : tf === 'log1p' ? Math.log1p(Math.max(v, 0)) : v;
}

// The value of a derived feature, or undefined for a name that is not one.
export function derived(f, name) {
  if (name === 'one_altar') return f.altars === null || f.altars === undefined ? NaN : +(f.altars === 1);
  let m = /^sq_(\w+)$/.exec(name);
  if (m && m[1] in BASE_TRANSFORMS) { const v = transformed(f, m[1]); return v * v; }
  m = /^pr_(\w+?)__(\w+)$/.exec(name);
  if (m && m[1] in BASE_TRANSFORMS && m[2] in BASE_TRANSFORMS) return transformed(f, m[1]) * transformed(f, m[2]);
  return undefined;
}
