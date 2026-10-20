import fs from 'node:fs';
import { wasmPath, engineImports } from '../replay/engine.mjs';

const { WASI } = await import('node:wasi');

export const SYMMETRIES = ['horizontal', 'vertical', 'rotational'];
export const CAMP_TYPES = ['wolf', 'elk', 'gem_cluster', 'gold_cluster', 'monolith', 'golem'];

let modulePromise;

export async function createEngine() {
  modulePromise ??= WebAssembly.compile(fs.readFileSync(wasmPath()));
  const wasi = new WASI({ version: 'preview1', args: [], env: {} });
  const instance = await WebAssembly.instantiate(await modulePromise, engineImports(wasi));
  wasi.initialize(instance);
  return new MapEngine(instance.exports);
}

export class MapError extends Error {}

class MapEngine {
  constructor(x) {
    this.x = x;
    this.out = x.Engine_Malloc(64);
  }

  get dv() {
    if (this._dv?.buffer !== this.x.memory.buffer) this._dv = new DataView(this.x.memory.buffer);
    return this._dv;
  }

  lastError() {
    const p = this.x.GetLastErrorMsg();
    const m = new Uint8Array(this.x.memory.buffer, p, 1024);
    const end = m.indexOf(0);
    return Buffer.from(m.subarray(0, end < 0 ? 1024 : end)).toString();
  }

  ck(code, what) {
    if (code) throw new MapError(`${what}: ${this.lastError() || `engine error ${code}`}`);
  }

  withBytes(bytes, fn) {
    const p = this.x.Engine_Malloc(bytes.length);
    try {
      new Uint8Array(this.x.memory.buffer, p, bytes.length).set(bytes);
      return fn(p, bytes.length);
    } finally { this.x.Engine_Free(p); }
  }

  // Decodes a map through the builder: the canonical (team A) description the file stores.
  decode(bytes) {
    const x = this.x, o = this.out;
    this.withBytes(bytes, (p, n) => this.ck(x.MapBuilder_FromFileBytes(p, n, o), 'decode map'));
    const h = this.dv.getBigUint64(o, true);
    try { return this.describe(h); } finally { x.MapBuilder_Destroy(h); }
  }

  describe(h) {
    const x = this.x, o = this.out;
    const u32 = (fn, ...a) => { this.ck(fn(h, ...a, o), fn.name); return this.dv.getUint32(o, true); };
    const u64 = (fn, ...a) => { this.ck(fn(h, ...a, o), fn.name); return this.dv.getBigUint64(o, true); };
    this.ck(x.MapBuilder_GetBitboardMetadata(h, o), 'metadata');
    const d = this.dv;
    const width = d.getInt32(o, true), height = d.getInt32(o + 4, true), stride = d.getUint32(o + 16, true);
    const board = fn => {
      this.ck(fn(h, o), 'buffer');
      const ptr = this.dv.getUint32(o, true), dv = this.dv, tiles = [];
      for (let y = 0; y < height; y++) for (let xx = 0; xx < width; xx++) {
        const word = (y >> 3) * stride + (xx >> 3), bit = ((y & 7) << 3) + (xx & 7);
        if ((dv.getBigUint64(ptr + word * 8, true) >> BigInt(bit)) & 1n) tiles.push([xx, y]);
      }
      return tiles;
    };
    const tiles = { walls: board(x.MapBuilder_GetWallBuffer), holes: board(x.MapBuilder_GetHoleBuffer), bushes: board(x.MapBuilder_GetBushBuffer), altars: board(x.MapBuilder_GetAltarBuffer) };
    const symmetry = SYMMETRIES[u32(x.MapBuilder_GetSymmetry)];
    const picks = u32(x.MapBuilder_GetNumChampsPerTeam);
    this.ck(x.MapBuilder_GetTeamASpawnArea(h, o), 'spawn');
    const spawn = { minX: this.dv.getInt32(o, true), minY: this.dv.getInt32(o + 4, true), maxX: this.dv.getInt32(o + 8, true), maxY: this.dv.getInt32(o + 12, true) };
    const handles = [], camps = [];
    for (let i = 0, n = u32(x.MapBuilder_GetNumCamps); i < n; i++) {
      const ch = u64(x.MapBuilder_GetCampHandle, i);
      handles.push(ch);
      this.ck(x.MapBuilder_GetCamp(h, ch, o), 'camp');
      camps.push({ type: CAMP_TYPES[this.dv.getInt32(o, true)], x: this.dv.getInt32(o + 4, true), y: this.dv.getInt32(o + 8, true) });
    }
    const groups = [];
    for (let g = 0, n = u32(x.MapBuilder_GetNumCampGroups); g < n; g++) {
      const gh = u64(x.MapBuilder_GetCampGroupHandle, g);
      this.ck(x.MapBuilder_GetCampGroup(h, gh, o), 'group');
      const dv = this.dv;
      const grp = { gems: dv.getUint32(o, true), gold: dv.getUint32(o + 4, true), respawn: dv.getUint32(o + 8, true), camps: [] };
      for (let j = 0, m = dv.getUint32(o + 12, true); j < m; j++) grp.camps.push(handles.indexOf(u64(x.MapBuilder_GetCampGroupCamp, gh, j)));
      groups.push(grp);
    }
    return { width, height, symmetry, picks, spawn, ...tiles, camps, groups };
  }
}

// The map editor's default theme, which the competition maps use.
const THEME = [['GroundGrassColor', 6188837], ['GroundGrassHighlightColor', 9281061], ['GroundGrassShadeColor', 3756325], ['GroundGrassWallColor', 4942119], ['GroundDirtColor', 5262886], ['GroundDirtDarkColor', 4539681], ['GroundDirtDustyColor', 5789228], ['GroundDirtMossColor', 4475939], ['GroundPebbleColor', 5526599], ['GroundSlabColor', 5526082], ['GroundFlowerColorA', 14273676], ['GroundFlowerColorB', 12099289], ['GroundFlowersEnabled', 1], ['BushBaseColor', 340778]];
const BUSH_TINT = [7901285, 12637856];

const TILE_FNS = { wall: ['MapBuilder_AddWall', 'MapBuilder_RemoveWall'], hole: ['MapBuilder_AddHole', 'MapBuilder_RemoveHole'], bush: ['MapBuilder_AddBush', 'MapBuilder_RemoveBush'], altar: ['MapBuilder_AddAltar', 'MapBuilder_RemoveAltar'] };

Object.assign(MapEngine.prototype, {
  // Builds a map with the engine's MapBuilder (the map editor's backend). Each tile and camp is
  // given once; the builder adds its mirror.
  encode(map) {
    const x = this.x, o = this.out;
    this.ck(x.MapBuilder_Create(map.width, map.height, SYMMETRIES.indexOf(map.symmetry), o), 'create');
    const h = this.dv.getBigUint64(o, true);
    try {
      for (const [k, v] of THEME) this.ck(x[`MapBuilder_Set${k}`](h, v), k);
      this.ck(x.MapBuilder_SetBushTintRange(h, ...BUSH_TINT), 'bush tint');
      this.ck(x.MapBuilder_SetNumChampsPerTeam(h, map.picks), 'picks');
      const s = map.spawn, d = this.dv;
      d.setInt32(o, s.minX, true); d.setInt32(o + 4, s.minY, true); d.setInt32(o + 8, s.maxX, true); d.setInt32(o + 12, s.maxY, true);
      this.ck(x.MapBuilder_SetTeamASpawnArea(h, o), 'spawn');
      for (const [kind, key] of [['wall', 'walls'], ['hole', 'holes'], ['bush', 'bushes'], ['altar', 'altars']])
        for (const [tx, ty] of map[key] ?? []) this.ck(x[TILE_FNS[kind][0]](h, tx, ty), `${kind} at (${tx}, ${ty})`);
      for (const c of map.camps ?? []) this.ck(x.MapBuilder_AddCamp(h, CAMP_TYPES.indexOf(c.type), c.x, c.y, o), `${c.type} at (${c.x}, ${c.y})`);
      this.ck(x.MapBuilder_VerifyIntegrity(h), 'verify');
      this.ck(x.MapBuilder_Encode(h, o, o + 4), 'encode');
      const ptr = this.dv.getUint32(o, true), len = this.dv.getUint32(o + 4, true);
      return Buffer.from(new Uint8Array(this.x.memory.buffer, ptr, len));
    } finally { x.MapBuilder_Destroy(h); }
  },

  // Loads a map as a game would (Game_FromMapFileBytes); throws if the engine rejects it.
  load(bytes) {
    const x = this.x, o = this.out;
    this.withBytes(bytes, (p, n) => this.ck(x.Game_FromMapFileBytes(p, n, o, 0), 'load map'));
    x.Game_Destroy(this.dv.getBigUint64(o, true));
  },
});
