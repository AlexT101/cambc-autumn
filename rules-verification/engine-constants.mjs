// Dumps every balance constant the visualiser engine (tools/replay/engine/v0_0_1.wasm) exposes to engine-constants.json.
//   node rules-verification/engine-constants.mjs [replay.repl26a ...]
// Record layouts follow sdk/cpp/cambc.h (game_settings) and sdk/cpp/imports.h (item_info, consumable_info, unit_definition,
// ability_props, champion_design, camp_design); the visualiser-only records follow the viewer's index.js.
// Replays (default: every .repl26a under replays/ladder) add live per-champion ability props, to cross-check the designs.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Engine, OBSERVER, CHAMPIONS, ITEMS, CONSUMABLES, CAMPS, ABILITY_TYPES, engineInfo } from '../tools/replay/engine.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'rules-verification', 'engine-constants.json');
const CHAMPION_PASSIVES = ['none', 'bonus_gold', 'remote_shop', 'gem_focus', 'splash_attack', 'health_strength', 'reset_cooldowns_on_kill', 'retaliation', 'stun_immunity'];
const ITEM_PASSIVES = ['none', 'monster', 'durability', 'treasure', 'jungle', 'home'];
const TARGETS = { 1: 'camps', 2: 'enemies', 4: 'allies', 8: 'self', 16: 'ground' };
const ATTRIBUTES = { 1: 'exclusive_with_movement' };

const e = await Engine.create();
const x = e.x;
const buf = x.Engine_Malloc(1024);
const dv = () => e.dv;
const r = {
  u: o => dv().getUint32(buf + o, true), i: o => dv().getInt32(buf + o, true), f: o => round(dv().getFloat32(buf + o, true)),
  d: o => dv().getFloat64(buf + o, true), b: o => dv().getUint8(buf + o),
};
const round = v => Number.isFinite(v) ? Math.round(v * 1e6) / 1e6 : v;
const fill = (n = 256) => new Uint8Array(x.memory.buffer, buf, n).fill(0xAB);
const written = (n = 256) => { const m = new Uint8Array(x.memory.buffer, buf, n); let k = n; while (k > 0 && m[k - 1] === 0xAB) k--; return k; };
const raw = n => Array.from(new Uint32Array(x.memory.buffer.slice(buf, buf + n)), v => '0x' + v.toString(16).padStart(8, '0'));
const call = (what, fn) => { fill(); const c = fn(); if (c) return { error: c, message: e.lastError(), what }; return null; };
const flags = (v, names) => {
  const known = Object.keys(names).reduce((a, b) => a | Number(b), 0), rest = v & ~known;
  return Object.entries(names).filter(([bit]) => v & Number(bit)).map(([, n]) => n).concat(rest ? ['0x' + rest.toString(16)] : []);
};

function settings() {
  const err = call('settings', () => x.Game_API_GetSettings(buf));
  if (err) return err;
  return {
    capture_time: r.i(0), camp_sleep_time: r.i(4), respawn_time: r.i(8), recall_time: r.i(12),
    submit_gem_duration_multiplier: r.d(16), submit_gem_base_duration: r.i(24), submit_gem_minimum_duration: r.i(28), submit_gems_range: r.i(32),
    max_rounds: r.u(36), winning_gems: r.u(40), kill_gold: r.u(44), assist_gold: r.u(48), passive_gold: r.u(52), spawn_healing: r.f(56),
    active_wards: r.u(60), ward_charges: r.u(64), shared_memory_bytes: r.u(68), draft_memory_bytes: r.u(72), tile_reveal_rounds: r.u(76),
    ward_cooldown: r.i(80), ward_lifetime: r.i(84), ward_vision_radius: r.f(88), ward_placement_radius: r.f(92),
    control_ward_vision_radius: r.f(96), control_ward_placement_radius: r.f(100), altar_lock_hits: r.u(104), tp_scroll_time: r.i(108),
    tp_crystal_time: r.i(112), reserved: r.u(116), bytes_written: written(),
  };
}

function visualiserConstants() {
  const err = call('constants', () => x.Game_Visualiser_GetConstants(buf));
  if (err) return err;
  return {
    abi: r.u(0), field_4: r.u(4), snapshot_size: r.u(8), field_12: r.u(12), recall_rounds: r.i(16), teleport_rounds: r.i(20),
    submit_base_rounds: r.i(24), submit_minimum_rounds: r.i(28), capture_rounds: r.i(32), altar_lock_hits: r.u(36),
    ward_placement_range: r.f(40), control_ward_placement_range: r.f(44), submit_gems_range: r.f(48), flash_rounds: r.i(52),
    submit_gem_multiplier: r.d(56), bytes_written: written(), raw: raw(64),
  };
}

function itemInfo(id) {
  const err = call('item', () => x.Game_API_GetItemInfo(id, buf));
  if (err) return { name: ITEMS[id], ...err };
  const it = {
    id, name: ITEMS[id], cost: r.u(0), purchasable: !!r.u(4), health_points: r.i(8), strength_points: r.i(12), focus_points: r.i(16),
    passive: ITEM_PASSIVES[r.u(20)] ?? r.u(20), passive_magnitude: r.f(24), combine_count: r.u(28),
    result: r.u(28) ? ITEMS[r.u(32)] ?? r.u(32) : null, combine_cost: r.u(36),
  };
  const shop = call('shop', () => x.Game_Visualiser_GetShopEntry(0, id, buf));
  it.shop_entry = shop ?? {
    cost: r.u(0), combine_count: r.u(4), result: r.u(4) ? ITEMS[r.u(8)] ?? r.u(8) : null, carry_limit: r.u(12),
    health_points: r.i(16), strength_points: r.i(20), focus_points: r.i(24), passive: ITEM_PASSIVES[r.u(28)] ?? r.u(28),
    passive_magnitude: r.f(32), purchasable: !!r.u(36),
  };
  return it;
}

function consumableInfo(id) {
  const err = call('consumable', () => x.Game_API_GetConsumableInfo(id, buf));
  const c = err ? { id, name: CONSUMABLES[id], ...err } : { id, name: CONSUMABLES[id], cost: r.u(0), carry_limit: r.u(4), bytes_written: written() };
  const shop = call('shop', () => x.Game_Visualiser_GetShopEntry(1, id, buf));
  c.shop_entry = shop ?? { cost: r.u(0), combine_count: r.u(4), result: r.u(8), carry_limit: r.u(12), health_points: r.i(16), strength_points: r.i(20), focus_points: r.i(24), passive: r.u(28), passive_magnitude: r.f(32), purchasable: !!r.u(36) };
  return c;
}

function ability(o) {
  const kind = r.u(o);
  if (!kind) return null;
  const p = o + 20;
  const a = {
    kind: ABILITY_TYPES[kind] ?? kind, cooldown: r.i(o + 4), max_charges: r.u(o + 8), targets: flags(r.u(o + 12), TARGETS),
    attributes: flags(r.u(o + 16), ATTRIBUTES),
  };
  switch (kind) {
    case 1: a.enhanced_attack = r.u(p); break;
    case 2: case 5: a.range = r.f(p); a.modifier = r.f(p + 4); break;
    case 3: a.range = r.f(p); a.radius = r.f(p + 4); a.modifier = r.f(p + 8); a.duration = r.i(p + 12); break;
    case 4: case 7: a.range = r.f(p); a.modifier = r.f(p + 4); a.duration = r.i(p + 8); break;
    case 6: a.dash_range = r.f(p); break;
  }
  a.payload_raw = raw(o + 36).slice((o + 20) / 4);
  return a;
}

function unitDefinition() {
  return {
    type: r.i(0), vision_type: r.u(4), passive_type: r.b(8), abilities: [ability(12), ability(48)],
    attack_type: r.b(84) === 0 ? 'melee' : r.b(84) === 1 ? 'ranged' : r.b(84),
  };
}

function championDesign(game, type) {
  const err = call('champion design', () => x.Game_API_Champion_Design(game.h, type, buf));
  if (err) return { type, name: CHAMPIONS[type], ...err };
  const def = unitDefinition(), s = 88;
  const d = {
    type, name: CHAMPIONS[type], ...def, passive: CHAMPION_PASSIVES[def.passive_type] ?? def.passive_type,
    stats: {
      vision_radius: r.i(s), base_move_speed: r.i(s + 4), base_attack_range: r.i(s + 8), base_health: r.f(s + 12), health_growth: r.f(s + 16),
      base_strength: r.f(s + 20), strength_growth: r.f(s + 24), base_focus: r.f(s + 28), focus_growth: r.f(s + 32), camp_damage_multiplier: r.f(s + 36),
    },
    bytes_written: written(),
  };
  const perr = call('passive', () => x.Game_API_GetChampionPassiveInfo(type, buf));
  d.passive_info = perr ?? { type: CHAMPION_PASSIVES[r.u(0)] ?? r.u(0), magnitude: r.f(4), bytes_written: written() };
  return d;
}

function campDesign(game, type) {
  const err = call('camp design', () => x.Game_API_Camp_Design(game.h, type, buf));
  if (err) return { type, name: CAMPS[type], ...err };
  const s = 88;
  return {
    type, name: CAMPS[type], ...unitDefinition(),
    stats: {
      vision_radius: r.f(s), base_move_speed: r.i(s + 4), base_attack_range: r.i(s + 8), base_health: r.f(s + 12), health_growth: r.f(s + 16),
      base_strength: r.f(s + 20), strength_growth: r.f(s + 24), base_focus: r.f(s + 28), focus_growth: r.f(s + 32),
    },
    bytes_written: written(),
  };
}

function mapInfo(file) {
  const game = e.openMap(fs.readFileSync(file));
  try {
    const m = game.map();
    const designs = { champions: CHAMPIONS.map((_, t) => championDesign(game, t)), camps: CAMPS.map((_, t) => campDesign(game, t)) };
    const groups = m.groups.map(g => ({ members: g.camps.map(c => CAMPS[m.camps[c].type]), gold: g.gold, gems: g.gems, respawn: g.respawn }));
    return { map: { name: path.basename(file, '.map26a'), width: m.width, height: m.height, symmetry: m.symmetry, picks: m.champsPerTeam, spawnA: m.spawnA, groups }, designs };
  } finally { game.destroy(); }
}

function liveAbilities(file, seen) {
  const game = e.openReplay(fs.readFileSync(file));
  try {
    game.seekStart();
    for (let k = 0; k < 400; k++) {
      const h = game.read().header();
      if (h.phase !== 12 && h.round >= 1) break;
      try { if (!game.next()) break; } catch { break; }
    }
    for (const c of game.read().champions()) {
      if (seen.has(c.type)) continue;
      const slots = [0, 1].map(slot => {
        const err = call('ability props', () => x.Game_API_Champion_GetAbilityProps(game.h, game.perspective(OBSERVER), c.id, slot, buf));
        return err ?? ability(0);
      });
      seen.set(c.type, { name: CHAMPIONS[c.type], from: path.relative(ROOT, file), max_health: round(c.maxHp), strength: round(c.strength), focus: round(c.focus), abilities: slots });
    }
    const apiGroups = [];
    x.Game_API_Map_GetNumCampGroups(game.h, buf);
    const n = r.u(0), list = x.Engine_Malloc(4 * n + 4);
    e.ck(x.Game_API_Map_GetCampGroups(game.h, list, n, buf), 'camp groups');
    for (let k = 0; k < n; k++) {
      const h = dv().getUint32(list + 4 * k, true), g = { handle: h };
      e.ck(x.Game_API_Map_CampGroup_Get(game.h, h, buf), 'camp group'); g.gems = r.u(0); g.gold = r.u(4);
      e.ck(x.Game_API_Map_CampGroup_GetRespawnTime(game.h, h, buf), 'respawn time'); g.respawn = r.i(0);
      e.ck(x.Game_API_Map_CampGroup_GetNumCamps(game.h, h, buf), 'num camps'); g.num_camps = r.u(0);
      apiGroups.push(g);
    }
    x.Engine_Free(list);
    const camps = game.read().camps();
    const campAbilities = {};
    for (const c of camps) {
      if (campAbilities[CAMPS[c.type]]) continue;
      campAbilities[CAMPS[c.type]] = [0, 1].map(slot => call('camp ability', () => x.Game_API_Camp_GetAbilityProps(game.h, game.perspective(OBSERVER), c.id, slot, buf)) ?? ability(0));
    }
    return { campAbilities, apiGroups, size: [game.metadata().width, game.metadata().height] };
  } finally { game.destroy(); }
}

const mapFiles = fs.readdirSync(path.join(ROOT, 'maps')).filter(f => f.endsWith('.map26a')).map(f => path.join(ROOT, 'maps', f));
const maps = [];
let designs = null;
for (const f of mapFiles) {
  const info = mapInfo(f);
  maps.push(info.map);
  const s = JSON.stringify(info.designs);
  if (!designs) designs = info.designs;
  else if (s !== JSON.stringify(designs)) maps[maps.length - 1].designs_differ = true;
}

const rewardsByCamp = {};
for (let pass = 0; pass < 3; pass++) for (const m of maps) for (const g of m.groups) {
  const unknown = [...new Set(g.members.filter(t => !rewardsByCamp[t]))];
  if (unknown.length !== 1) continue;
  const k = unknown[0], n = g.members.filter(t => t === k).length, rest = g.members.filter(t => t !== k);
  const gold = (g.gold - rest.reduce((a, t) => a + rewardsByCamp[t].gold, 0)) / n, gems = (g.gems - rest.reduce((a, t) => a + rewardsByCamp[t].gems, 0)) / n;
  if (g.members.length === 1 || rest.every(t => rewardsByCamp[t].respawn < g.respawn)) rewardsByCamp[k] = { gold, gems, respawn: g.respawn, from: `${m.name} group of ${g.members.join('+')}` };
}
const groupChecks = [];
for (const m of maps) for (const g of m.groups) {
  if (g.members.some(t => !rewardsByCamp[t])) continue;
  const gold = g.members.reduce((a, t) => a + rewardsByCamp[t].gold, 0), gems = g.members.reduce((a, t) => a + rewardsByCamp[t].gems, 0);
  const respawn = Math.max(...g.members.map(t => rewardsByCamp[t].respawn));
  g.check = gold === g.gold && gems === g.gems && respawn === g.respawn ? 'sum'
    : 2 * gold === g.gold && 2 * gems === g.gems && respawn === g.respawn ? 'sum, self-mirrored (members listed once, mirror camps join the group)' : 'MISMATCH';
  if (g.check === 'MISMATCH') groupChecks.push({ map: m.name, ...g, expected: { gold, gems, respawn } });
}

const findReplays = dir => fs.existsSync(dir) ? fs.readdirSync(dir, { withFileTypes: true }).flatMap(d => d.isDirectory() ? findReplays(path.join(dir, d.name)) : d.name.endsWith('.repl26a') ? [path.join(dir, d.name)] : []) : [];
const replays = process.argv.length > 2 ? process.argv.slice(2) : findReplays(path.join(ROOT, 'replays', 'ladder'));
const live = new Map();
let campAbilities = null;
const apiGroups = {};
for (const f of replays) {
  if (live.size >= 12 && campAbilities && Object.keys(apiGroups).length >= maps.length) break;
  try {
    const res = liveAbilities(f, live);
    campAbilities ??= res.campAbilities;
    const m = maps.find(q => q.width === res.size[0] && q.height === res.size[1] && !apiGroups[q.name]
      && res.apiGroups.every(g => q.groups.some(c => c.gold === g.gold && c.gems === g.gems && c.respawn === g.respawn)));
    if (m) apiGroups[m.name] = res.apiGroups;
  } catch (err) { console.error(`${f}: ${err.message}`); }
}
for (const m of maps) if (apiGroups[m.name]) m.api_groups = apiGroups[m.name];

const out = {
  engine: engineInfo(),
  settings: settings(),
  visualiser_constants: visualiserConstants(),
  champions: designs.champions,
  champion_live_abilities: Object.fromEntries([...live].sort((a, b) => a[0] - b[0]).map(([t, v]) => [t, v])),
  camps: designs.camps,
  camp_live_abilities: campAbilities,
  camp_rewards: rewardsByCamp,
  camp_group_mismatches: groupChecks,
  items: ITEMS.map((_, id) => itemInfo(id)),
  consumables: CONSUMABLES.map((_, id) => consumableInfo(id)),
  maps,
};
fs.writeFileSync(OUT, JSON.stringify(out, null, 1) + '\n');
console.log(`wrote ${path.relative(ROOT, OUT)}: ${out.champions.length} champions, ${out.camps.length} camps, ${out.items.length} items, ${maps.length} maps, live abilities for ${live.size} champion types`);
