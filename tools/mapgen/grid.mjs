export const GROUND = 0, WALL = 1, HOLE = 2, BUSH = 3, ALTAR = 4;
export const KIND_KEYS = { [WALL]: 'walls', [HOLE]: 'holes', [BUSH]: 'bushes', [ALTAR]: 'altars' };
export const CAMP = {
  wolf: { gems: 4, gold: 40, respawn: 40 },
  elk: { gems: 15, gold: 90, respawn: 60 },
  gem_cluster: { gems: 7, gold: 0, respawn: 50 },
  gold_cluster: { gems: 0, gold: 20, respawn: 50 },
  monolith: { gems: 200, gold: 300, respawn: 150 },
  golem: { gems: 36, gold: 160, respawn: 80 },
};
const N8 = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]];
const N4 = N8.slice(0, 4);

export function makeRng(seed) {
  let h = 1779033703 ^ seed.length;
  for (let i = 0; i < seed.length; i++) { h = Math.imul(h ^ seed.charCodeAt(i), 3432918353); h = (h << 13) | (h >>> 19); }
  const next = () => { h = Math.imul(h ^ (h >>> 16), 2246822507); h = Math.imul(h ^ (h >>> 13), 3266489909); return (h ^= h >>> 16) >>> 0; };
  let a = next(), b = next(), c = next(), d = next();
  const float = () => {
    const t = (((a + b) | 0) + d) | 0;
    d = (d + 1) | 0; a = b ^ (b >>> 9); b = (c + (c << 3)) | 0; c = (c << 21) | (c >>> 11); c = (c + t) | 0;
    return (t >>> 0) / 4294967296;
  };
  const rng = {
    float,
    uniform: (lo, hi) => lo + (hi - lo) * float(),
    int: (lo, hi) => lo + Math.floor(float() * (hi - lo + 1)),
    chance: p => float() < p,
    choice: arr => arr[Math.floor(float() * arr.length)],
    weighted: obj => {
      const entries = Object.entries(obj), total = entries.reduce((s, [, w]) => s + w, 0);
      let r = float() * total;
      for (const [k, w] of entries) if ((r -= w) < 0) return k;
      return entries.at(-1)[0];
    },
    shuffle: arr => { for (let i = arr.length - 1; i > 0; i--) { const j = Math.floor(float() * (i + 1)); [arr[i], arr[j]] = [arr[j], arr[i]]; } return arr; },
  };
  return rng;
}

// Smooth value noise in [0, 1] with the given cell size and octaves.
export function valueNoise(rng, w, h, cell, octaves = 3) {
  const out = new Float32Array(w * h);
  let amp = 1, total = 0;
  for (let o = 0; o < octaves; o++, cell = Math.max(2, cell / 2), amp /= 2) {
    const gw = Math.ceil(w / cell) + 2, gh = Math.ceil(h / cell) + 2, lattice = Float32Array.from({ length: gw * gh }, rng.float);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const fx = x / cell, fy = y / cell, ix = Math.floor(fx), iy = Math.floor(fy);
      const sx = (fx - ix) ** 2 * (3 - 2 * (fx - ix)), sy = (fy - iy) ** 2 * (3 - 2 * (fy - iy));
      const v = (i, j) => lattice[(iy + j) * gw + ix + i];
      out[y * w + x] += amp * ((v(0, 0) * (1 - sx) + v(1, 0) * sx) * (1 - sy) + (v(0, 1) * (1 - sx) + v(1, 1) * sx) * sy);
    }
    total += amp;
  }
  for (let i = 0; i < out.length; i++) out[i] /= total;
  return out;
}

export class Grid {
  constructor(width, height, symmetry) {
    this.W = width; this.H = height; this.sym = symmetry;
    this.t = new Uint8Array(width * height);
    this.camps = [];
    this.spawn = null;
    this.picks = 3;
    this.vaults = new Set();
    this.meta = {};
  }

  clone() {
    const g = new Grid(this.W, this.H, this.sym);
    g.t = this.t.slice(); g.camps = this.camps.map(c => ({ ...c })); g.spawn = this.spawn && { ...this.spawn }; g.picks = this.picks; g.vaults = new Set(this.vaults); g.meta = structuredClone(this.meta);
    return g;
  }

  in(x, y) { return x >= 0 && y >= 0 && x < this.W && y < this.H; }
  idx(x, y) { return y * this.W + x; }
  get(x, y) { return this.t[y * this.W + x]; }
  mirrorXY(x, y) {
    if (this.sym === 'horizontal') return [this.W - 1 - x, y];
    if (this.sym === 'vertical') return [x, this.H - 1 - y];
    return [this.W - 1 - x, this.H - 1 - y];
  }
  mirror(i) { const [x, y] = this.mirrorXY(i % this.W, Math.floor(i / this.W)); return y * this.W + x; }

  // Sets a tile and its mirror.
  set(x, y, kind) {
    if (!this.in(x, y)) return;
    const [mx, my] = this.mirrorXY(x, y);
    this.t[y * this.W + x] = kind; this.t[my * this.W + mx] = kind;
  }

  // Copies the lower-index tile of every mirror pair onto the other, so free drawing becomes symmetric.
  symmetrize() {
    for (let i = 0; i < this.t.length; i++) { const m = this.mirror(i); if (i < m) this.t[m] = this.t[i]; }
  }

  isSymmetric() {
    for (let i = 0; i < this.t.length; i++) if (this.t[i] !== this.t[this.mirror(i)]) return false;
    return true;
  }

  spawnTiles(team = 0) {
    const s = this.spawn, out = [];
    for (let y = s.y; y < s.y + s.h; y++) for (let x = s.x; x < s.x + s.w; x++) out.push(team ? this.mirror(this.idx(x, y)) : this.idx(x, y));
    return out;
  }

  allCamps() {
    const out = [];
    // A camp on a self-mirrored tile (on the symmetry axis, or the centre under rotation) is its own mirror.
    for (const c of this.camps) {
      const [x, y] = this.mirrorXY(c.x, c.y);
      if (x === c.x && y === c.y) { out.push({ ...c, team: 2 }); continue; }
      out.push({ ...c, team: 0 }, { ...c, x, y, team: 1 });
    }
    return out;
  }

  campMask() {
    const m = new Uint8Array(this.t.length);
    for (const c of this.allCamps()) m[c.y * this.W + c.x] = 1;
    return m;
  }

  // Walkable for champions: ground and bush, minus camp tiles when `blockers` is given.
  walkable(blockers) {
    const w = new Uint8Array(this.t.length);
    for (let i = 0; i < w.length; i++) w[i] = (this.t[i] === GROUND || this.t[i] === BUSH) && !(blockers && blockers[i]) ? 1 : 0;
    return w;
  }

  // 8-neighbour walking distances from `starts` over `pass`.
  bfs(starts, pass) {
    const { W, H } = this, dist = new Int32Array(W * H).fill(-1), q = new Int32Array(W * H);
    let head = 0, tail = 0;
    for (const s of starts) if (pass[s] && dist[s] < 0) { dist[s] = 0; q[tail++] = s; }
    while (head < tail) {
      const i = q[head++], x = i % W, y = (i - x) / W;
      for (const [dx, dy] of N8) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
        const j = ny * W + nx;
        if (pass[j] && dist[j] < 0) { dist[j] = dist[i] + 1; q[tail++] = j; }
      }
    }
    return dist;
  }

  // Distance from a set of tiles to the nearest reached tile adjacent (8-neighbour) to it.
  reachNear(dist, x, y, r = 1) {
    let best = -1;
    for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
      const nx = x + dx, ny = y + dy;
      if ((dx || dy) && this.in(nx, ny)) { const d = dist[ny * this.W + nx]; if (d >= 0 && (best < 0 || d < best)) best = d; }
    }
    return best;
  }

  components(pass) {
    const { W, H } = this, comp = new Int32Array(this.t.length).fill(-1), sizes = [], q = new Int32Array(W * H);
    for (let s = 0; s < comp.length; s++) {
      if (!pass[s] || comp[s] >= 0) continue;
      const id = sizes.length;
      let head = 0, tail = 0;
      comp[s] = id; q[tail++] = s;
      while (head < tail) {
        const i = q[head++], x = i % W, y = (i - x) / W;
        for (const [dx, dy] of N8) {
          const nx = x + dx, ny = y + dy, j = ny * W + nx;
          if (nx >= 0 && ny >= 0 && nx < W && ny < H && pass[j] && comp[j] < 0) { comp[j] = id; q[tail++] = j; }
        }
      }
      sizes.push(tail);
    }
    return { comp, sizes };
  }

  // Camp groups as the engine forms them: cardinally connected camps over the whole map. A group
  // is shared when the symmetry maps it onto itself; otherwise its mirror is another group.
  groups() {
    const all = this.allCamps(), at = new Map(all.map((c, k) => [c.y * this.W + c.x, k])), seen = new Set(), out = [];
    for (let k = 0; k < all.length; k++) {
      if (seen.has(k)) continue;
      const members = [], stack = [k];
      seen.add(k);
      while (stack.length) {
        const c = all[stack.pop()];
        members.push(c);
        for (const [dx, dy] of N4) {
          const j = at.get((c.y + dy) * this.W + c.x + dx);
          if (j !== undefined && this.in(c.x + dx, c.y + dy) && !seen.has(j)) { seen.add(j); stack.push(j); }
        }
      }
      const tiles = new Set(members.map(c => c.y * this.W + c.x)), first = members[0];
      const [mx, my] = this.mirrorXY(first.x, first.y);
      out.push({ members, tiles, shared: tiles.has(my * this.W + mx), gems: members.reduce((s, c) => s + CAMP[c.type].gems, 0), gold: members.reduce((s, c) => s + CAMP[c.type].gold, 0) });
    }
    return out;
  }

  // Chebyshev distance from a tile to the nearest non-walkable tile or the map edge.
  clearance() {
    const { W, H } = this, pass = this.walkable(), d = new Int32Array(W * H).fill(-1), q = [];
    for (let i = 0; i < d.length; i++) {
      const x = i % W, y = (i - x) / W;
      if (!pass[i]) { d[i] = 0; q.push(i); } else if (x === 0 || y === 0 || x === W - 1 || y === H - 1) { d[i] = 1; q.push(i); }
    }
    for (let h = 0; h < q.length; h++) {
      const i = q[h], x = i % W, y = (i - x) / W;
      for (const [dx, dy] of N8) {
        const nx = x + dx, ny = y + dy;
        if (nx >= 0 && ny >= 0 && nx < W && ny < H && d[ny * W + nx] < 0) { d[ny * W + nx] = d[i] + 1; q.push(ny * W + nx); }
      }
    }
    return d;
  }

  toMap() {
    const out = { width: this.W, height: this.H, symmetry: this.sym, picks: this.picks, walls: [], holes: [], bushes: [], altars: [] };
    for (let i = 0; i < this.t.length; i++) { const k = KIND_KEYS[this.t[i]]; if (k) out[k].push([i % this.W, Math.floor(i / this.W)]); }
    const s = this.spawn;
    out.spawn = { minX: s.x, minY: s.y, maxX: s.x + s.w, maxY: s.y + s.h };
    out.camps = this.camps.map(({ type, x, y }) => ({ type, x, y }));
    return out;
  }

  static fromMap(m) {
    const g = new Grid(m.width, m.height, m.symmetry);
    for (const [kind, key] of [[WALL, 'walls'], [HOLE, 'holes'], [BUSH, 'bushes'], [ALTAR, 'altars']]) for (const [x, y] of m[key]) g.t[y * g.W + x] = kind;
    g.picks = m.picks;
    g.spawn = { x: m.spawn.minX, y: m.spawn.minY, w: m.spawn.maxX - m.spawn.minX, h: m.spawn.maxY - m.spawn.minY };
    g.camps = m.camps.map(c => ({ ...c }));
    return g;
  }

  render() {
    const ch = { wolf: 'w', elk: 'e', gem_cluster: 'g', gold_cluster: '$', monolith: 'm', golem: 'k' }, rows = [];
    const glyph = ['.', '#', 'o', '"', 'A'], cells = Array.from(this.t, k => glyph[k]);
    for (const c of this.allCamps()) cells[c.y * this.W + c.x] = c.team === 1 ? ch[c.type].toUpperCase() : ch[c.type];
    for (const team of [0, 1]) for (const i of this.spawnTiles(team)) cells[i] = String(team + 1);
    for (let y = this.H - 1; y >= 0; y--) rows.push(cells.slice(y * this.W, (y + 1) * this.W).join(''));
    return rows.join('\n');
  }
}

export { N4, N8 };
