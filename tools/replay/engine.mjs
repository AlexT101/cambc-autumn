import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const emitWarning = process.emitWarning;
process.emitWarning = (w, ...a) => { if (!/WASI is an experimental/.test(String(w?.message ?? w))) emitWarning.call(process, w, ...a); };
const { WASI } = await import('node:wasi');

// One engine per ladder patch (engine/<version>.wasm, listed in engine/version.json): a replay
// plays back only on the engine named in its header.
export const ENGINE_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), 'engine');
export const SNAPSHOT_SIZE = 184696;
export const SNAPSHOT_ABI = 1;
export const OBSERVER = { team: 2, champion: 0xFFFFFFFF };
const NONE = 0xFFFFFFFF;

export const CHAMPIONS = ['Ryth', 'Vesper Vale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'Heart of Ruin'];
export const DRAFT_CHAMPIONS = ['Ryth', 'Vesper Vale', 'Vendetta', 'Cassi & Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'Heart of Ruin'];
export const ITEMS = ['Monster', 'Power', 'Durability', 'Treasure', 'Jungle', 'Home', 'Bruiser'].flatMap(f => ['Strength', 'Focus', 'Health'].flatMap(s => [`${f} Shard of ${s}`, `${f} Emblem of ${s}`]));
export const CONSUMABLES = ['Teleport crystal', 'Control ward', 'Altar lock', 'TP scroll'];
export const ABILITY_TYPES = ['None', 'Attack reset', 'Damage', 'AoE damage', 'CC', 'Heal', 'Dash', 'Shield'];
export const BUFFS = ['Shield', 'Stun', 'Enhanced auto'];
export const CAMPS = ['Wolf', 'Elk', 'Gem cluster', 'Gold cluster', 'Monolith'];
export const SYMMETRIES = ['horizontal', 'vertical', 'rotational'];
export const CHANNELS = ['', 'recall', 'tribute', 'teleport', 'teleport_scroll'];
export const GROUP_STATES = ['unknown', 'camps', 'empty', 'respawning'];
export const ENTITY_KINDS = { 1: 'champion', 2: 'camp', 4: 'spell' };
export const STEP_KINDS = ['Phase', 'Respawn', 'Capture', 'Tick', 'Move', 'Attack', 'Cast ability', 'Input', 'End turn', 'Set priority', '', 'Recall', 'Submit gems', 'Shop', 'Place ward', 'Consumable', 'Cancel channel', 'Sandbox', 'Gems submitted', 'Draft champion', 'Place altar lock', 'Teleport channel', 'Teleport complete', 'Movement blocked', 'Resign', 'Sell item', 'Turn rollover'];
export const PHASES = { 0: 'Round start', 1: 'Camp respawns', 4: 'Spell entities', 7: 'Camp captures', 9: 'Camp turns', 10: 'Champion turns', 11: 'Finished', 12: 'Draft', 13: 'Champion turn end', 14: 'Champion turn start' };
export const ROUND_FLAGS = { attackReady: 2, recallStarted: 64, tributeStarted: 128, recallCancelled: 256, tributeCancelled: 512, castReady: 1024, walked: 2048 };
export const KNOWN = { basic: 1, bag: 2, channel: 4, gold: 8 };

const TABLES = {
  champions: { countOffset: 120, dataOffset: 140, stride: 456, capacity: 16 },
  camps: { countOffset: 124, dataOffset: 7436, stride: 232, capacity: 500 },
  groups: { countOffset: 128, dataOffset: 123436, stride: 20, capacity: 500 },
  wards: { countOffset: 132, dataOffset: 133436, stride: 40, capacity: 128 },
  controlWards: { countOffset: 179568, dataOffset: 179572, stride: 36, capacity: 128 },
  spells: { countOffset: 136, dataOffset: 138556, stride: 40, capacity: 1024 },
};
const DRAFT_OFFSET = 179516;
const EXT_SUBMISSION = 184184, EXT_GOLD = 184248, EXT_KDA = 184504;

export class EngineError extends Error {
  constructor(code, message) { super(`engine error ${code}: ${message}`); this.code = code; }
}

let manifest;
function engineManifest() {
  if (manifest === undefined) {
    try { manifest = JSON.parse(fs.readFileSync(path.join(ENGINE_DIR, 'version.json'), 'utf8')); } catch { manifest = null; }
  }
  return manifest;
}

export function engineVersions() { return Object.keys(engineManifest()?.engines ?? {}).sort(); }
export function latestEngine() { return engineVersions().at(-1); }
export function wasmPath(version = latestEngine()) { return path.join(ENGINE_DIR, `${version}.wasm`); }

export function engineInfo(version = latestEngine()) {
  const m = engineManifest(), e = m?.engines?.[version];
  return e ? { version, cambc: m.cambc, ...e } : null;
}

export async function compileEngine(version = latestEngine()) {
  return WebAssembly.compile(fs.readFileSync(wasmPath(version)));
}

const REPLAY_MAGIC = 125779999602273n;

// The engine version a replay was played on, e.g. 'v0_0_2', from its header.
export function replayEngine(bytes) {
  bytes = unwrapReplay(bytes);
  if (bytes.length < 14 || bytes.readBigUInt64LE(0) !== REPLAY_MAGIC) throw new Error('not a replay file');
  return `v${bytes[8]}_${bytes[9]}_${bytes[10]}`;
}

// Some engine builds import an assertion hook; the viewer logs the failure and returns 1.
export function engineImports(wasi) {
  return { ...wasi.getImportObject(), deep_wasm: { on_assert_fail_impl: () => { console.error('engine assertion failed'); return 1; } } };
}

export class Engine {
  static async create(module) {
    module ??= await compileEngine();
    const wasi = new WASI({ version: 'preview1', args: [], env: {} });
    const instance = await WebAssembly.instantiate(module, engineImports(wasi));
    wasi.initialize(instance);
    return new Engine(instance.exports);
  }

  constructor(x) {
    this.x = x;
    const size = x.Game_Visualiser_SnapshotSize();
    if (size !== SNAPSHOT_SIZE) throw new Error(`Engine snapshot size is ${size}, decoder expects ${SNAPSHOT_SIZE}: the snapshot layout changed, update the decoder in tools/replay/engine.mjs (port it from the viewer's PanelChrome-*.js).`);
    this.out = x.Engine_Malloc(64);
    this.args = x.Engine_Malloc(256);
    this.snap = x.Engine_Malloc(SNAPSHOT_SIZE);
    this.placedCap = 64;
    this.placed = x.Engine_Malloc(this.placedCap * 28);
    this.scratch = x.Engine_Malloc(64 * 1024);
    this.ck(x.Game_Visualiser_GetConstants(this.args));
    const d = this.dv;
    if (d.getUint32(this.args, true) !== SNAPSHOT_ABI || d.getUint32(this.args + 8, true) !== SNAPSHOT_SIZE || d.getUint32(this.args + 12, true) !== 64)
      throw new Error('Unsupported visualiser interface: update the decoder in tools/replay/engine.mjs.');
    const a = this.args;
    this.constants = {
      recallRounds: d.getInt32(a + 16, true), teleportRounds: d.getInt32(a + 20, true), submitBaseRounds: d.getInt32(a + 24, true),
      submitMinimumRounds: d.getInt32(a + 28, true), captureRounds: d.getInt32(a + 32, true), altarLockHits: d.getUint32(a + 36, true),
      wardPlacementRange: d.getFloat32(a + 40, true), controlWardPlacementRange: d.getFloat32(a + 44, true), submitGemsRange: d.getFloat32(a + 48, true),
      flashRounds: d.getInt32(a + 52, true), submitGemMultiplier: d.getFloat64(a + 56, true),
    };
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

  ck(code, what = '') {
    if (code) throw new EngineError(code, `${what ? what + ': ' : ''}${this.lastError()}`);
  }

  openReplay(bytes) {
    bytes = unwrapReplay(bytes);
    const p = this.x.Engine_Malloc(bytes.length);
    try {
      new Uint8Array(this.x.memory.buffer, p, bytes.length).set(bytes);
      this.ck(this.x.Game_FromReplayFileBytes(p, bytes.length, this.out), 'load replay');
    } finally { this.x.Engine_Free(p); }
    return new Game(this, this.dv.getBigUint64(this.out, true));
  }

  openMap(bytes) {
    const p = this.x.Engine_Malloc(bytes.length);
    try {
      new Uint8Array(this.x.memory.buffer, p, bytes.length).set(bytes);
      this.ck(this.x.Game_FromMapFileBytes(p, bytes.length, this.out, 0), 'load map');
    } finally { this.x.Engine_Free(p); }
    return new Game(this, this.dv.getBigUint64(this.out, true));
  }
}

export class Game {
  constructor(engine, handle) {
    this.e = engine;
    this.x = engine.x;
    this.h = handle;
    this.persp = engine.args + 192;
  }

  destroy() { this.x.Game_Destroy(this.h); }

  u32out(fn, ...a) { this.e.ck(fn(this.h, ...a, this.e.out)); return this.e.dv.getUint32(this.e.out, true); }
  i32out(fn, ...a) { this.e.ck(fn(this.h, ...a, this.e.out)); return this.e.dv.getInt32(this.e.out, true); }
  u64out(fn, ...a) { this.e.ck(fn(this.h, ...a, this.e.out)); return this.e.dv.getBigUint64(this.e.out, true); }

  perspective(p = OBSERVER) {
    const d = this.e.dv;
    d.setUint32(this.persp, p.team, true);
    d.setUint32(this.persp + 4, p.champion, true);
    return this.persp;
  }

  metadata() {
    const x = this.x, d = this.e.dv, o = this.e.out;
    this.e.ck(x.Game_GetBitboardMetadata(this.h, o));
    return { width: d.getInt32(o, true), height: d.getInt32(o + 4, true), chunkStride: d.getUint32(o + 16, true) };
  }

  bitboardTiles(ptr, meta) {
    const d = this.e.dv, tiles = [];
    for (let y = 0; y < meta.height; y++)
      for (let x = 0; x < meta.width; x++) if (testBit(d, ptr, meta, x, y)) tiles.push([x, y]);
    return tiles;
  }

  bufferPtr(fn) { this.e.ck(fn(this.h, this.e.out)); return this.e.dv.getUint32(this.e.out, true); }

  // Static map: terrain, spawns, camps and groups (as stored in the map: the canonical half plus mirror index).
  map() {
    const x = this.x, d = this.e.dv, o = this.e.out;
    const meta = this.metadata();
    const tiles = {};
    for (const [k, fn] of [['walls', x.Game_GetWallBuffer], ['holes', x.Game_GetHoleBuffer], ['bushes', x.Game_GetBushBuffer], ['altars', x.Game_GetAltarBuffer]])
      tiles[k] = this.bitboardTiles(this.bufferPtr(fn), meta);
    const symmetry = SYMMETRIES[this.i32out(x.Game_GetSymmetry)];
    const champsPerTeam = this.i32out(x.Game_GetNumChampsPerTeam);
    this.e.ck(x.Game_GetTeamASpawnArea(this.h, o));
    const spawnA = { minX: d.getInt32(o, true), minY: d.getInt32(o + 4, true), maxX: d.getInt32(o + 8, true), maxY: d.getInt32(o + 12, true) };
    const nCamps = this.u32out(x.Game_GetNumCamps);
    const campHandles = [], camps = [];
    for (let i = 0; i < nCamps; i++) {
      const ch = this.u64out(x.Game_GetCampHandle, i);
      campHandles.push(ch);
      this.e.ck(x.Game_GetCamp(this.h, ch, o));
      camps.push({ type: d.getInt32(o, true), x: d.getInt32(o + 4, true), y: d.getInt32(o + 8, true) });
    }
    const nGroups = this.u32out(x.Game_GetNumCampGroups);
    const groups = [];
    for (let g = 0; g < nGroups; g++) {
      const gh = this.u64out(x.Game_GetCampGroupHandle, g);
      this.e.ck(x.Game_GetCampGroup(this.h, gh, o));
      const grp = { gems: d.getUint32(o, true), gold: d.getUint32(o + 4, true), respawn: d.getUint32(o + 8, true), camps: [] };
      const n = d.getUint32(o + 12, true);
      for (let j = 0; j < n; j++) {
        this.e.ck(x.Game_GetCampGroupCamp(this.h, gh, j, o));
        grp.camps.push(campHandles.indexOf(d.getBigUint64(o, true)));
      }
      groups.push(grp);
    }
    return { width: meta.width, height: meta.height, symmetry, champsPerTeam, spawnA, ...tiles, camps, groups };
  }

  timeline() { return this.u64out(this.x.Game_Visualiser_Timeline_GetMain); }

  seekStart() {
    this.tl ??= this.timeline();
    this.e.ck(this.x.Game_Visualiser_Timeline_Seek(this.h, this.tl, 0, 0), 'seek');
  }

  // Returns false at the end of the replay.
  next() {
    const c = this.x.Game_Visualiser_Timeline_ReplayNext(this.h, 1);
    if (c === 0) return true;
    const m = this.e.lastError();
    if (/cannot advance/i.test(m)) return false;
    throw new EngineError(c, `replay next: ${m}`);
  }

  read(p = OBSERVER) {
    this.e.ck(this.x.Game_Visualiser_ReadState(this.h, this.perspective(p), this.e.snap), 'read state');
    return new Snapshot(this.e.dv, this.e.snap);
  }

  // Tile-visibility tester for a perspective; valid until the next engine call that reallocates.
  vision(p, meta) {
    this.e.ck(this.x.Game_Visualiser_GetVisionBuffer(this.h, this.perspective(p), this.e.out), 'vision');
    const ptr = this.e.dv.getUint32(this.e.out, true), d = this.e.dv;
    return (x, y) => x >= 0 && y >= 0 && x < meta.width && y < meta.height && testBit(d, ptr, meta, x, y);
  }

  teleports(p = OBSERVER) {
    const x = this.x, e = this.e, pp = this.perspective(p);
    e.ck(x.Game_API_GetTeleports(this.h, pp, 0, 0, e.out), 'teleports');
    const n = e.dv.getUint32(e.out, true);
    if (!n) return [];
    if (n > e.placedCap) { e.x.Engine_Free(e.placed); e.placedCap = n; e.placed = e.x.Engine_Malloc(n * 28); }
    e.ck(x.Game_API_GetTeleports(this.h, this.perspective(p), e.placed, e.placedCap, e.out), 'teleports');
    const d = e.dv, res = [];
    for (let i = 0; i < n; i++) {
      const b = e.placed + i * 28;
      res.push({ champion: d.getUint32(b, true), type: d.getInt32(b + 4, true), team: d.getUint32(b + 8, true), x: d.getInt32(b + 12, true), y: d.getInt32(b + 16, true), timer: d.getInt32(b + 20, true), channelType: d.getUint32(b + 24, true) });
    }
    return res;
  }

  // Observer view of all altar locks: {team, x, y, hits} where hits is the number of hits remaining.
  // Observer view of all altar locks, checked only at the given altar tiles: {team, x, y, hits} with hits = hits remaining.
  altarLocks(altars) {
    const x = this.x, e = this.e, res = [];
    for (const team of [0, 1]) for (const [ax, ay] of altars) {
      if (x.Game_API_GetAltarLock(this.h, this.perspective(OBSERVER), ax, ay, team, e.args)) continue;
      const a = e.args, d = e.dv;
      res.push({ team: d.getUint32(a + 8, true), x: d.getInt32(a + 12, true), y: d.getInt32(a + 16, true), hits: d.getUint32(a + 20, true) });
    }
    return res;
  }

  // Engine end-of-game statistics (only available once the replay has been played to the end).
  statistics() {
    const x = this.x, e = this.e, b = e.scratch;
    e.ck(x.Game_Statistics_GetSummary(this.h, b), 'statistics');
    let d = e.dv;
    const w = i => d.getUint32(b + i * 4, true);
    const summary = {
      faults: [d.getUint8(b), d.getUint8(b + 1)], flags: d.getUint8(b + 2), outcome: w(1), round: w(2), numChampions: w(3),
      submittedGems: [Number(d.getBigUint64(b + 16, true)), Number(d.getBigUint64(b + 24, true))],
      draftCounts: [w(8), w(9)], drafts: [[10, 11, 12, 13, 14].map(w), [15, 16, 17, 18, 19].map(w)],
    };
    const champions = [];
    for (let i = 0; i < summary.numChampions; i++) {
      e.ck(x.Game_Statistics_GetChampion(this.h, i, b), 'champion statistics');
      d = e.dv;
      const u64 = i => Number(d.getBigUint64(b + i * 4, true));
      const f64 = i => d.getFloat64(b + i * 4, true);
      const arr64 = (s, n) => Array.from({ length: n }, (_, k) => u64(s + 2 * k));
      const arr32 = (s, n) => Array.from({ length: n }, (_, k) => w(s + k));
      champions.push({
        champion: w(0), team: w(1), type: w(2), kills: w(3), deaths: w(4), assists: w(5),
        earnedGold: u64(6), collectedGems: u64(8), submittedGems: u64(10), spentGold: u64(12), w14: w(14), w15: w(15),
        itemsBought: arr64(16, 42), consumablesBought: arr64(100, 4), items: arr32(108, 42), consumables: arr32(150, 4),
        monsterDamageDone: f64(154), monsterDamageTaken: f64(156), championDamageDone: f64(158), championDamageTaken: f64(160),
        healingDone: f64(162), shieldingDone: f64(164),
      });
    }
    return { summary, champions };
  }
}

// Local `cambc run` replays are zip archives holding replay.repl26a; ladder downloads are the raw file.
export function unwrapReplay(bytes) {
  if (bytes.length < 22 || bytes.readUInt32LE(0) !== 0x04034b50) return bytes;
  let eocd = bytes.length - 22;
  while (eocd >= 0 && bytes.readUInt32LE(eocd) !== 0x06054b50) eocd--;
  if (eocd < 0) throw new Error('zip replay: end of central directory not found');
  const n = bytes.readUInt16LE(eocd + 10);
  let p = bytes.readUInt32LE(eocd + 16);
  for (let i = 0; i < n; i++) {
    if (bytes.readUInt32LE(p) !== 0x02014b50) throw new Error('zip replay: bad central directory');
    const method = bytes.readUInt16LE(p + 10), csize = bytes.readUInt32LE(p + 20);
    const nameLen = bytes.readUInt16LE(p + 28), extraLen = bytes.readUInt16LE(p + 30), commentLen = bytes.readUInt16LE(p + 32);
    const local = bytes.readUInt32LE(p + 42), name = bytes.subarray(p + 46, p + 46 + nameLen).toString();
    p += 46 + nameLen + extraLen + commentLen;
    if (!name.endsWith('.repl26a')) continue;
    const start = local + 30 + bytes.readUInt16LE(local + 26) + bytes.readUInt16LE(local + 28);
    const data = bytes.subarray(start, start + csize);
    if (method === 0) return Buffer.from(data);
    if (method === 8) return zlib.inflateRawSync(data);
    throw new Error(`zip replay: unsupported compression method ${method}`);
  }
  throw new Error('zip replay: no .repl26a entry');
}

function testBit(d, ptr, meta, x, y) {
  const chunk = (y >> 3) * meta.chunkStride + (x >> 3);
  const bit = ((y & 7) << 3) + (x & 7);
  const word = d.getUint32(ptr + chunk * 8 + (bit >= 32 ? 4 : 0), true);
  return ((word >>> (bit & 31)) & 1) === 1;
}

export class Snapshot {
  constructor(d, base) { this.d = d; this.b = base; }
  u(o) { return this.d.getUint32(this.b + o, true); }
  i(o) { return this.d.getInt32(this.b + o, true); }
  f(o) { return this.d.getFloat32(this.b + o, true); }
  u64(o) { return Number(this.d.getBigUint64(this.b + o, true)); }
  arr(o, n) { const r = new Array(n); for (let k = 0; k < n; k++) r[k] = this.u(o + k * 4); return r; }

  header() {
    if (this.u(0) !== SNAPSHOT_ABI || this.u(4) !== SNAPSHOT_SIZE) throw new Error('Unsupported game snapshot ABI: update the decoder in tools/replay/engine.mjs.');
    const slot = this.u(108);
    return {
      round: this.u(8), turn: this.u(12), team: this.u(16), awaitingInput: !!this.u(20), phase: this.u(24), outcome: this.u(28),
      submittedGems: [this.u64(32), this.u64(40)], inputPosition: this.u(56), currentChampion: this.u(60),
      step: {
        phase: this.u(64), kind: this.u(68), actor: { kind: this.u(72), index: this.u(76) },
        from: { x: this.i(80), y: this.i(84) }, to: { x: this.i(88), y: this.i(92) },
        round: this.u(96), inputPosition: this.u(100), substep: this.u(104),
        abilitySlot: slot === NONE ? undefined : slot, abilityType: slot === NONE ? undefined : this.u(112), priority: this.i(116),
      },
    };
  }

  draft() {
    const r = DRAFT_OFFSET;
    return { numRounds: this.u(r), counts: [this.u(r + 4), this.u(r + 8)], picks: [0, 1].map(t => [0, 1, 2, 3, 4].map(k => this.i(r + 12 + t * 20 + k * 4))) };
  }

  count(t) {
    const n = this.u(t.countOffset);
    if (n > t.capacity) throw new Error('Invalid snapshot count');
    return n;
  }

  unit(o) {
    const known = this.u(o + 16), basic = !!(known & KNOWN.basic), x = this.i(o + 20), y = this.i(o + 24);
    const u = { kind: this.u(o), id: this.u(o + 4), team: this.u(o + 8), type: this.u(o + 12), known };
    if (basic) {
      if (x >= 0 && y >= 0) { u.x = x; u.y = y; }
      u.hp = this.f(o + 28); u.maxHp = this.f(o + 32);
      const mask = this.u(o + 40), buffs = [];
      for (let r = 0; r < 3; r++) if (mask & (1 << r)) { const s = o + 44 + r * 16; buffs.push({ type: r, timer: this.i(s), mag: this.f(s + 4), src: { kind: this.u(s + 8), id: this.u(s + 12) } }); }
      u.buffs = buffs;
      u.cd = [this.u(o + 92), this.u(o + 96)];
      u.charges = [this.d.getUint16(this.b + o + 100, true), this.d.getUint16(this.b + o + 102, true)];
      u.abilities = [this.u(o + 104), this.u(o + 108)];
      u.focus = this.f(o + 132);
      u.strength = this.f(o + 148);
    }
    if (known & KNOWN.channel) u.roundFlags = this.u(o + 36);
    return u;
  }

  champion(k) {
    const o = TABLES.champions.dataOffset + k * TABLES.champions.stride;
    const c = this.unit(o), known = c.known, id = c.id;
    c.alive = !!this.u(o + 224);
    c.respawn = this.i(o + 228);
    if (known & KNOWN.bag) { c.gems = this.u(o + 236); c.items = this.arr(o + 240, ITEMS.length); }
    if (known & KNOWN.gold) {
      c.gold = this.u(o + 232);
      c.earnedGold = this.u64(EXT_GOLD + id * 16);
      c.treasureGold = this.u64(EXT_GOLD + id * 16 + 8);
    }
    if (known & KNOWN.basic) c.consumables = this.arr(o + 412, 4);
    const ward = !!this.u(o + 408);
    if (ward) c.ward = { charges: this.u(o + 428), recharge: this.i(o + 432) };
    if (ward || (known & KNOWN.channel)) { c.channelTimer = this.i(o + 436); c.channelType = this.u(o + 440); c.submissionDuration = this.i(EXT_SUBMISSION + id * 4); }
    c.kda = [this.u(EXT_KDA + id * 12), this.u(EXT_KDA + id * 12 + 4), this.u(EXT_KDA + id * 12 + 8)];
    c.priority = this.i(o + 444);
    c.nextPriority = this.i(o + 448);
    c.draftOrder = this.u(o + 452);
    return c;
  }

  champions() { const n = this.count(TABLES.champions), r = new Array(n); for (let k = 0; k < n; k++) r[k] = this.champion(k); return r; }

  // Only what per-step diffing needs; assumes an observer read (everything known).
  championsLite() {
    const t = TABLES.champions, n = this.count(t), r = new Array(n);
    for (let k = 0; k < n; k++) {
      const o = t.dataOffset + k * t.stride, id = this.u(o + 4), mask = this.u(o + 40);
      r[k] = {
        id, team: this.u(o + 8), alive: !!this.u(o + 224), x: this.i(o + 20), y: this.i(o + 24), hp: this.f(o + 28), maxHp: this.f(o + 32),
        gold: this.u(o + 232), gems: this.u(o + 236), ct: this.u(o + 440), cT: this.i(o + 436),
        shield: mask & 1 ? this.f(o + 48) : 0, stun: mask & 2 ? this.i(o + 60) : 0,
        kills: this.u(EXT_KDA + id * 12), deaths: this.u(EXT_KDA + id * 12 + 4), assists: this.u(EXT_KDA + id * 12 + 8),
        earned: this.u64(EXT_GOLD + id * 16),
      };
    }
    return r;
  }

  knownChampions() {
    const t = TABLES.champions, n = this.count(t), r = new Map();
    for (let k = 0; k < n; k++) { const o = t.dataOffset + k * t.stride; r.set(this.u(o + 4), this.u(o + 16)); }
    return r;
  }

  items(k) { return this.arr(TABLES.champions.dataOffset + k * TABLES.champions.stride + 240, ITEMS.length); }
  consumables(k) { return this.arr(TABLES.champions.dataOffset + k * TABLES.champions.stride + 412, 4); }

  campsLite() {
    const t = TABLES.camps, n = this.count(t), hp = new Float64Array(n), awake = new Uint8Array(n);
    for (let k = 0; k < n; k++) { const o = t.dataOffset + k * t.stride; hp[k] = this.f(o + 28); awake[k] = this.u(o + 228) ? 1 : 0; }
    return { hp, awake };
  }

  camps() {
    const t = TABLES.camps, n = this.count(t), r = new Array(n);
    for (let k = 0; k < n; k++) {
      const o = t.dataOffset + k * t.stride, c = this.unit(o);
      c.group = this.u(o + 224);
      if (c.known & KNOWN.basic) c.awake = !!this.u(o + 228);
      r[k] = c;
    }
    return r;
  }

  groups() {
    const t = TABLES.groups, n = this.count(t), r = new Array(n);
    for (let k = 0; k < n; k++) {
      const o = t.dataOffset + k * t.stride;
      r[k] = { state: this.u(o), reward: !!this.u(o + 4), captureTeam: this.u(o + 8), captureTimer: this.i(o + 12), respawn: this.i(o + 16) };
    }
    return r;
  }

  placed(t, extra) {
    const n = this.count(t), r = new Array(n);
    for (let k = 0; k < n; k++) {
      const o = t.dataOffset + k * t.stride;
      r[k] = { kind: this.u(o), id: this.u(o + 4), owner: { kind: this.u(o + 8), id: this.u(o + 12) }, team: this.u(o + 16), ...extra(o) };
    }
    return r;
  }

  wards() { return this.placed(TABLES.wards, o => ({ x: this.i(o + 20), y: this.i(o + 24), timer: this.i(o + 28), radius: this.f(o + 32), disabled: !!this.d.getUint8(this.b + o + 36) })); }
  controlWards() { return this.placed(TABLES.controlWards, o => ({ x: this.i(o + 20), y: this.i(o + 24), timer: this.i(o + 28), radius: this.f(o + 32) })); }
  spells() { return this.placed(TABLES.spells, o => ({ type: this.u(o + 20), x: this.i(o + 24), y: this.i(o + 28), timer: this.i(o + 32), radius: this.f(o + 36) })); }
}

// Map a position through the map symmetry (an involution, so it also maps back).
export function mirror(map, x, y) {
  switch (map.symmetry) {
    case 'horizontal': return [map.width - 1 - x, y];
    case 'vertical': return [x, map.height - 1 - y];
    default: return [map.width - 1 - x, map.height - 1 - y];
  }
}

// Position in the team's own frame: team A positions unchanged, team B mirrored into team A's frame.
export function ownFrame(map, team, x, y) {
  return team === 1 ? mirror(map, x, y) : [x, y];
}
