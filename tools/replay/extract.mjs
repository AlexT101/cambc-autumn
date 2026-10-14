import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import {
  Engine, compileEngine, engineInfo, WASM_PATH, ENGINE_DIR, SNAPSHOT_SIZE, STEP_KINDS, CHAMPIONS, DRAFT_CHAMPIONS, ITEMS, CONSUMABLES,
  ABILITY_TYPES, BUFFS, CAMPS, CHANNELS, GROUP_STATES, mirror,
} from './engine.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const OUT_ROOT = path.join(ROOT, 'replays', '.analysis');
export const EXTRACTOR_VERSION = 1;
const NONE = 0xFFFFFFFF;
const K = Object.fromEntries(STEP_KINDS.map((n, i) => [n, i]));
const ACTIONS = new Set([K.Move, K.Attack, K['Cast ability'], K.Recall, K['Submit gems'], K.Shop, K['Place ward'], K.Consumable, K['Cancel channel'], K['Place altar lock'], K['Teleport channel'], K['Sell item'], K['Movement blocked']]);
const REN = CHAMPIONS.indexOf('Ren');
const TURN = { none: 0, acted: 1, idle: 2, channel: 3, dead: 4, stunned: 5, fuel: 6 };

const r1 = v => Math.round(v * 10) / 10;
const sha256 = b => crypto.createHash('sha256').update(b).digest('hex');
const writeJson = (f, v) => fs.writeFileSync(f, JSON.stringify(v));

function sourceContext(file) {
  const dir = path.dirname(file), base = path.basename(file, '.repl26a');
  const ctx = { kind: 'file', map: base, teams: [{ name: 'A' }, { name: 'B' }] };
  const groupFile = path.join(dir, 'group.json'), resultsFile = path.join(dir, 'results.json');
  let m;
  if (fs.existsSync(groupFile) && (m = /^(\d+)-(.+)$/.exec(base))) {
    const group = JSON.parse(fs.readFileSync(groupFile, 'utf8'));
    const position = +m[1];
    ctx.kind = 'ladder';
    ctx.map = m[2];
    ctx.position = position;
    ctx.group = { id: group.group?.id, kind: group.group?.kind, createdAt: group.group?.createdAt };
    const sides = group.group?.sides ?? [];
    ctx.teams = ['a', 'b'].map(s => { const x = sides.find(q => q.side === s) ?? {}; return { name: x.teamName, id: x.teamId, ratingBefore: x.ratingBefore }; });
    const match = (group.matches ?? []).find(q => q.position === position) ?? (group.matches ?? [])[position - 1];
    if (match) { ctx.matchId = match.id; ctx.expected = match.statistics ?? null; ctx.mapName = match.map?.name ?? match.mapName; }
  } else if (fs.existsSync(resultsFile) && (m = /^(\d+)-(.+)-(12|21)$/.exec(base))) {
    const res = JSON.parse(fs.readFileSync(resultsFile, 'utf8'));
    const bots = (res.bots ?? []).map(b => path.basename(b));
    const order = m[3] === '12' ? [0, 1] : [1, 0];
    ctx.kind = 'batch';
    ctx.map = m[2];
    ctx.teams = order.map(i => ({ name: bots[i], bot: i }));
    const match = (res.matches ?? []).find(q => path.basename(q.replay ?? '') === path.basename(file));
    if (match) ctx.expected = { winnerBot: match.winner, rounds: match.rounds, order: match.order };
  }
  return ctx;
}

function mapKey(map) {
  return sha256(JSON.stringify([map.width, map.height, map.symmetry, map.spawnA, map.walls, map.holes, map.bushes, map.altars, map.camps, map.groups])).slice(0, 16);
}

function buildMap(map, camps0) {
  // The engine's spawn max is exclusive.
  const a = { minX: map.spawnA.minX, minY: map.spawnA.minY, maxX: map.spawnA.maxX - 1, maxY: map.spawnA.maxY - 1 };
  const spawn = [a];
  const [bx0, by0] = mirror(map, a.minX, a.minY), [bx1, by1] = mirror(map, a.maxX, a.maxY);
  spawn.push({ minX: Math.min(bx0, bx1), minY: Math.min(by0, by1), maxX: Math.max(bx0, bx1), maxY: Math.max(by0, by1) });
  const centre = s => [(s.minX + s.maxX) / 2, (s.minY + s.maxY) / 2];
  const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
  const groups = [];
  camps0.forEach((c, i) => {
    const g = c.group;
    groups[g] ??= { id: g, camps: [], tiles: [] };
    groups[g].camps.push(i);
    groups[g].tiles.push([c.x, c.y]);
  });
  for (const g of groups) {
    const src = map.groups.find(q => q.camps.includes(g.camps[0] >> 1));
    Object.assign(g, { types: g.camps.map(i => CAMPS[camps0[i].type]), gems: src.gems, gold: src.gold, respawn: src.respawn, mirror: camps0[g.camps[0] ^ 1]?.group });
    const c = g.tiles.reduce((a, t) => [a[0] + t[0] / g.tiles.length, a[1] + t[1] / g.tiles.length], [0, 0]);
    const d = spawn.map(s => cheb(c, centre(s)));
    g.side = d[0] < d[1] ? 0 : d[1] < d[0] ? 1 : -1;
  }
  return {
    width: map.width, height: map.height, symmetry: map.symmetry, champsPerTeam: map.champsPerTeam, spawn,
    walls: map.walls, holes: map.holes, bushes: map.bushes, altars: map.altars,
    camps: camps0.map((c, i) => ({ id: i, type: CAMPS[c.type], x: c.x, y: c.y, group: c.group, hp: c.maxHp })),
    groups,
  };
}

function pairs(arr) { const r = []; arr.forEach((v, i) => { if (v) r.push(i, v); }); return r; }
function diffCounts(a, b, names) { const r = {}; b.forEach((v, i) => { if (v !== a[i]) r[names[i]] = v - a[i]; }); return r; }

export function extractGame(engine, file) {
  const t0 = performance.now();
  const bytes = fs.readFileSync(file);
  const hash = sha256(bytes);
  const ctx = sourceContext(file);
  const g = engine.openReplay(bytes);
  try {
    const rawMap = g.map();
    const altarSet = new Set(rawMap.altars.map(([x, y]) => `${x},${y}`));
    const events = [];
    const ev = e => events.push(e);
    let map = null, roster = null, campGroup = null, nGroups = 0, duos = [], rosterType = new Map();
    const R = { round: [], gems: [[], []], champions: [], groupCols: ['round', 'group', 'state', 'team', 'timer', 'respawn', 'awake', 'hp'], groups: [], wards: [], controlWards: [], locks: [] };
    let prev = null, prevCamps = null, prevGroups = null, prevAwake = null, prevItems = null, prevCons = null;
    let round = 0, steps = 0, turnChamp = NONE, turnActed = false;
    const turnStatus = new Map(), sees = new Map();
    let locks = [];
    let lastGroupRow = [];

    const champAt = (st, x, y) => st.find(c => c.alive && c.x === x && c.y === y);
    const campAt = (x, y) => { if (!prevCamps) return -1; for (let i = 0; i < map.camps.length; i++) if (prevCamps.hp[i] > 0 && map.camps[i].x === x && map.camps[i].y === y) return i; return -1; };
    const groupAwake = camps => {
      const a = new Int8Array(nGroups).fill(-1);
      for (let i = 0; i < camps.hp.length; i++) if (camps.hp[i] > 0) { const gg = campGroup[i]; a[gg] = Math.max(a[gg], camps.awake[i]); }
      return a;
    };

    const recordRound = (snap, r, cur, camps, groups) => {
      R.round.push(r);
      const h = snap.header();
      R.gems[0].push(h.submittedGems[0]); R.gems[1].push(h.submittedGems[1]);
      const full = snap.champions();
      full.forEach((c, k) => {
        const col = R.champions[k];
        const lite = cur[k];
        col.x.push(lite.alive && lite.x >= 0 ? lite.x : null);
        col.y.push(lite.alive && lite.y >= 0 ? lite.y : null);
        col.hp.push(r1(lite.hp)); col.maxHp.push(r1(lite.maxHp)); col.alive.push(lite.alive ? 1 : 0); col.respawn.push(c.respawn);
        col.gold.push(c.gold); col.earned.push(c.earnedGold); col.gems.push(c.gems);
        col.chan.push(c.channelType ?? 0); col.chanT.push(c.channelType ? c.channelTimer : 0);
        col.cd0.push(c.cd?.[0] ?? 0); col.cd1.push(c.cd?.[1] ?? 0);
        col.str.push(r1(c.strength ?? 0)); col.foc.push(r1(c.focus ?? 0));
        col.shield.push(r1(lite.shield)); col.stun.push(lite.stun);
        col.items.push(pairs(c.items ?? []));
        col.cons.push(c.consumables ?? [0, 0, 0, 0]);
        col.kills.push(c.kda[0]); col.deaths.push(c.kda[1]); col.assists.push(c.kda[2]);
        col.prio.push(c.priority);
        col.ward.push(c.ward ? [c.ward.charges, c.ward.recharge] : null);
        col.turn.push(turnStatus.get(c.id) ?? TURN.none);
        col.sees.push(sees.get(c.id) ?? []);
      });
      for (const col of R.champions) col.seenBy.push([]);
      R.champions.forEach((col, k) => {
        for (const e of col.sees.at(-1)) {
          const kk = roster.findIndex(q => q.id === e);
          if (kk >= 0) R.champions[kk].seenBy.at(-1).push(full[k].id);
        }
      });
      const awake = groupAwake(camps);
      groups.forEach((q, gi) => {
        let hp = 0;
        for (const ci of map.groups[gi].camps) hp += Math.max(0, camps.hp[ci]);
        const row = [q.state, q.captureTeam, q.captureTimer, q.respawn, awake[gi], r1(hp)];
        const last = lastGroupRow[gi];
        if (!last || row.some((v, i) => v !== last[i])) { R.groups.push([r, gi, ...row]); lastGroupRow[gi] = row; }
      });
      R.wards.push(snap.wards().map(w => [w.owner.id, w.team, w.x, w.y, w.disabled ? 1 : 0]));
      R.controlWards.push(snap.controlWards().map(w => [w.owner.id, w.team, w.x, w.y, w.timer]));
      R.locks.push(locks.map(l => [l.team, l.x, l.y, l.hits]));
      turnStatus.clear(); sees.clear();
    };

    const refreshLocks = (s, h) => {
      const now = g.altarLocks(rawMap.altars);
      const key = l => `${l.team}:${l.x},${l.y}`;
      const before = new Map(locks.map(l => [key(l), l]));
      const after = new Map(now.map(l => [key(l), l]));
      for (const [k2, l] of before) if (!after.has(k2)) ev({ s, r: h.round, t: turnIndex(h), k: 'lock_destroyed', team: l.team, at: [l.x, l.y] });
      locks = now;
      return after;
    };
    const turnIndex = h => h.turn === NONE ? -1 : h.turn;

    g.seekStart();
    let draftDone = false;
    do {
      const snap = g.read();
      const h = snap.header();
      const st = h.step;
      steps++;
      if (h.phase === 12 || st.phase === 12) continue;
      if (!draftDone) {
        draftDone = true;
        const full = snap.champions();
        roster = full.map(c => ({ id: c.id, team: c.team, type: c.type, name: CHAMPIONS[c.type], draftOrder: c.draftOrder, maxHp: c.maxHp }));
        for (const c of roster) rosterType.set(c.id, c.type);
        for (const c of roster) if (c.type === 3) { const i = roster.find(q => q.type === 4 && q.team === c.team && !duos.some(d => d[1] === q.id)); if (i) duos.push([c.id, i.id]); }
        const camps0 = snap.camps();
        map = buildMap(rawMap, camps0);
        campGroup = Int32Array.from(camps0.map(c => c.group));
        nGroups = map.groups.length;
        R.champions = roster.map(c => ({ id: c.id, team: c.team, x: [], y: [], hp: [], maxHp: [], alive: [], respawn: [], gold: [], earned: [], gems: [], chan: [], chanT: [], cd0: [], cd1: [], str: [], foc: [], shield: [], stun: [], items: [], cons: [], kills: [], deaths: [], assists: [], prio: [], ward: [], turn: [], sees: [], seenBy: [] }));
        round = h.round;
      }
      const cur = snap.championsLite();
      const camps = snap.campsLite();
      const groups = snap.groups();

      if (h.round !== round) {
        refreshLocks(steps - 1, h);
        recordRound(snap, round, cur, camps, groups);
        round = h.round;
      }

      if (prev) {
        const s = steps - 1, r = h.round, t = turnIndex(h);
        const actor = st.actor;
        const isChamp = actor.kind === 1;
        const a = isChamp ? actor.index : undefined;
        const byId = new Map(prev.map(c => [c.id, c]));
        const curById = new Map(cur.map(c => [c.id, c]));
        const dmg = [], heal = [], shieldGain = [], cdmg = [], stunned = [];
        let refl = 0;
        const actorTeam = isChamp ? byId.get(a)?.team : undefined;
        const hitStep = st.kind === K.Attack || st.kind === K['Cast ability'];
        const linked = new Map();
        for (const [x, y] of duos) {
          const px = byId.get(x), py = byId.get(y), cx = curById.get(x), cy = curById.get(y);
          if (!(px?.alive && py?.alive && !cx.alive && !cy.alive)) continue;
          const tc = hitStep ? champAt(prev, st.to.x, st.to.y) : undefined;
          const primary = tc?.id === y ? y : tc?.id === x ? x : (py.hp < px.hp ? y : x);
          linked.set(primary === x ? y : x, primary);
        }
        for (const c of cur) {
          const p = byId.get(c.id);
          if (!p || linked.has(c.id)) continue;
          if (p.alive) {
            const hpNow = c.alive ? c.hp : 0;
            const loss = p.hp - hpNow + (hitStep || actor.kind === 2 ? Math.max(0, p.shield - c.shield) : 0);
            if (loss > 0.01) {
              if (isChamp && c.id === a) refl += loss; else dmg.push([c.id, r1(loss)]);
            } else if (c.alive && c.hp - p.hp > 0.01 && (st.kind === K['Cast ability'] || st.kind === K.Attack)) heal.push([c.id, r1(c.hp - p.hp)]);
            if (c.shield - p.shield > 0.01) shieldGain.push([c.id, r1(c.shield - p.shield)]);
            if (c.stun > 0 && !(p.stun > 0)) stunned.push(c.id);
          }
        }
        for (let i = 0; i < camps.hp.length; i++) {
          const loss = prevCamps.hp[i] - Math.max(0, camps.hp[i]);
          if (prevCamps.hp[i] > 0 && loss > 0.01) cdmg.push([i, r1(loss)]);
        }
        const target = () => {
          const out = {};
          const tc = champAt(prev, st.to.x, st.to.y);
          if (tc) out.tgt = tc.id;
          else { const ci = campAt(st.to.x, st.to.y); if (ci >= 0) out.camp = ci; else if (altarSet.has(`${st.to.x},${st.to.y}`)) out.lock = 1; }
          return out;
        };
        const fx = (e) => {
          if (dmg.length) e.dmg = dmg;
          if (cdmg.length) e.cdmg = cdmg;
          if (refl) {
            e.refl = r1(refl);
            const rens = dmg.map(q => q[0]).filter(id => rosterType.get(id) === REN);
            e.reflBy = rens.includes(e.tgt) ? e.tgt : rens[0] ?? e.tgt;
          }
          if (heal.length) e.heal = heal;
          if (shieldGain.length) e.shield = shieldGain;
          if (stunned.length) e.stun = stunned;
          return e;
        };
        let consumed = false;

        if (isChamp && st.phase === 10 && ACTIONS.has(st.kind) && a === turnChamp) turnActed = true;

        switch (st.kind) {
          case K.Move: {
            if (st.phase === 14) break;
            ev({ s, r, t, k: 'move', a, f: [st.from.x, st.from.y], to: [st.to.x, st.to.y] });
            consumed = true; break;
          }
          case K['Movement blocked']: ev({ s, r, t, k: 'blocked', a, f: [st.from.x, st.from.y], to: [st.to.x, st.to.y] }); consumed = true; break;
          case K.Attack: {
            if (isChamp) {
              const e = fx({ s, r, t, k: 'attack', a, f: [st.from.x, st.from.y], to: [st.to.x, st.to.y], ...target() });
              if (e.lock) {
                const after = refreshLocks(s, h);
                const l = [...after.values()].find(q => q.x === st.to.x && q.y === st.to.y && q.team !== actorTeam);
                e.hits = l ? l.hits : 0;
              }
              ev(e);
            } else if (actor.kind === 2) {
              const tc = champAt(prev, st.to.x, st.to.y);
              const e = { s, r, t, k: 'camp_attack', camp: actor.index, g: campGroup[actor.index], tgt: tc?.id };
              const d = dmg.find(q => q[0] === tc?.id);
              e.dmg = d ? d[1] : 0;
              const other = dmg.filter(q => q[0] !== tc?.id);
              if (other.length) e.xdmg = other;
              if (cdmg.length) e.refl = cdmg;
              ev(e);
            }
            consumed = true; break;
          }
          case K['Cast ability']: {
            const p = byId.get(a), c = curById.get(a);
            const e = { s, r, t, k: 'cast', a, slot: st.abilitySlot, ab: ABILITY_TYPES[st.abilityType] ?? st.abilityType, f: [p.x, p.y], to: [st.to.x, st.to.y], ...target() };
            if (p.x !== c.x || p.y !== c.y) e.moved = [c.x, c.y];
            ev(fx(e));
            consumed = true; break;
          }
          case K['Place ward']: ev({ s, r, t, k: 'ward', a, to: [st.to.x, st.to.y] }); consumed = true; break;
          case K.Shop: case K['Sell item']: case K.Consumable: {
            const k2 = roster.findIndex(q => q.id === a);
            const items = snap.items(k2), cons = snap.consumables(k2);
            const e = { s, r, t, k: st.kind === K.Shop ? 'shop' : st.kind === K.Consumable ? 'consumable' : 'sell', a, gold: curById.get(a).gold - byId.get(a).gold };
            const di = diffCounts(prevItems[k2], items, ITEMS), dc = diffCounts(prevCons[k2], cons, CONSUMABLES);
            if (Object.keys(di).length) e.items = di;
            if (Object.keys(dc).length) e.cons = dc;
            if (st.kind === K.Consumable) e.to = [st.to.x, st.to.y];
            prevItems[k2] = items; prevCons[k2] = cons;
            ev(e); consumed = true; break;
          }
          case K['Place altar lock']: {
            const e = { s, r, t, k: 'lock_place', a, team: actorTeam, to: [st.to.x, st.to.y] };
            refreshLocks(s, h);
            const k2 = roster.findIndex(q => q.id === a);
            prevCons[k2] = snap.consumables(k2);
            ev(e); consumed = true; break;
          }
          case K.Recall: ev({ s, r, t, k: 'recall_start', a, gems: curById.get(a).gems, at: [curById.get(a).x, curById.get(a).y] }); consumed = true; break;
          case K['Submit gems']: {
            const c = curById.get(a), p = byId.get(a);
            if (c.ct === 2 && p.ct !== 2) ev({ s, r, t, k: 'tribute_start', a, altar: [st.to.x, st.to.y], gems: c.gems, dur: c.cT, at: [c.x, c.y] });
            else { refreshLocks(s, h); ev({ s, r, t, k: 'tribute_blocked', a, altar: [st.to.x, st.to.y], gems: c.gems }); }
            consumed = true; break;
          }
          case K['Gems submitted']: {
            const p = byId.get(a);
            ev({ s, r, t, k: 'tribute_end', a, gems: p.gems, total: h.submittedGems[p.team] });
            consumed = true; break;
          }
          case K['Teleport channel']: ev({ s, r, t, k: 'teleport_start', a, f: [st.from.x, st.from.y], to: [st.to.x, st.to.y] }); consumed = true; break;
          case K['Teleport complete']: ev({ s, r, t, k: 'teleport_end', a, to: [st.to.x, st.to.y] }); consumed = true; break;
          case K.Resign: ev({ s, r, t, k: 'resign', a, team: actorTeam }); consumed = true; break;
          case K.Sandbox: ev({ s, r, t, k: 'sandbox' }); break;
          case K.Respawn:
            if (isChamp) { const c = curById.get(a); ev({ s, r, t, k: 'respawn', a, at: [c.x, c.y] }); consumed = true; }
            break;
          default: break;
        }

        if (!consumed && (dmg.length || cdmg.length)) {
          const e = fx({ s, r, t, k: 'other_dmg', step: STEP_KINDS[st.kind], actor: [actor.kind, actor.index] });
          ev(e);
        }

        for (const c of cur) {
          const p = byId.get(c.id);
          if (!p) continue;
          if (p.ct && c.ct !== p.ct) {
            const ch = CHANNELS[p.ct] ?? String(p.ct);
            let cause;
            if (p.alive && !c.alive) cause = 'death';
            else if (c.stun > 0 && !(p.stun > 0)) cause = 'stun';
            else if (st.kind === K['Cancel channel'] && a === c.id) cause = 'manual';
            else if (st.kind === K['Place altar lock']) cause = 'lock';
            else if (dmg.some(q => q[0] === c.id)) cause = 'damage';
            else cause = STEP_KINDS[st.kind] || String(st.kind);
            if (p.ct === 2) { if (!(st.kind === K['Gems submitted'] && a === c.id)) ev({ s, r, t, k: 'tribute_cancel', a: c.id, gems: p.gems, cause, left: p.cT }); }
            else if (p.ct === 1) {
              if (st.kind === K.Move && st.phase === 14 && a === c.id) ev({ s, r, t, k: 'recall_end', a: c.id, gems: c.gems, f: [p.x, p.y], to: [c.x, c.y] });
              else ev({ s, r, t, k: 'recall_cancel', a: c.id, gems: p.gems, cause, left: p.cT });
            } else if (!(st.kind === K['Teleport complete'] && a === c.id)) ev({ s, r, t, k: `${ch}_cancel`, a: c.id, cause, left: p.cT });
          }
        }

        for (const c of cur) {
          const p = byId.get(c.id);
          if (!p || !p.alive || c.alive) continue;
          const killer = cur.find(q => q.team !== c.team && q.kills > byId.get(q.id).kills);
          const e = { s, r, t, k: 'death', v: c.id, at: [p.x, p.y], gems: p.gems, hp: r1(p.hp) };
          if (linked.has(c.id)) e.linked = linked.get(c.id);
          if (killer && e.linked !== undefined) e.by = killer.id;
          else if (killer) { e.by = killer.id; e.gold = killer.gold - byId.get(killer.id).gold; e.gemsTo = killer.gems - byId.get(killer.id).gems; }
          else if (actor.kind === 2) e.camp = actor.index;
          else if (isChamp && actorTeam !== c.team) e.by = a;
          const assists = cur.filter(q => q.team !== c.team && q.assists > byId.get(q.id).assists).map(q => q.id);
          if (assists.length) e.assists = assists;
          e.cause = STEP_KINDS[st.kind];
          ev(e);
        }

        for (let i = 0; i < camps.hp.length; i++) if (prevCamps.hp[i] > 0 && camps.hp[i] <= 0) ev({ s, r, t, k: 'camp_death', camp: i, g: campGroup[i], by: isChamp ? a : undefined });

        groups.forEach((q, gi) => {
          const p = prevGroups[gi];
          if (p.state === q.state && p.captureTeam === q.captureTeam) return;
          if (p.state === 1 && q.state === 2) ev({ s, r, t, k: 'group_clear', g: gi, by: isChamp ? a : undefined });
          else if (p.state === 2 && q.state === 3) {
            const shares = cur.filter(c => c.gems > byId.get(c.id).gems || c.gold > byId.get(c.id).gold).map(c => [c.id, c.gems - byId.get(c.id).gems, c.gold - byId.get(c.id).gold]);
            ev({ s, r, t, k: 'capture', g: gi, team: p.captureTeam, shares });
          } else if (p.state === 3 && q.state === 1) ev({ s, r, t, k: 'group_respawn', g: gi });
          else if (q.state === 2 && p.captureTeam !== q.captureTeam) {
            if (p.captureTeam === 2) ev({ s, r, t, k: 'capture_hold', g: gi, team: q.captureTeam, timer: q.captureTimer });
            else if (q.captureTeam === 2) {
              const on = cur.filter(c => c.alive && map.groups[gi].tiles.some(([x, y]) => x === c.x && y === c.y));
              ev({ s, r, t, k: 'capture_reset', g: gi, team: p.captureTeam, left: p.captureTimer, contested: on.some(c => c.team === p.captureTeam) && on.some(c => c.team !== p.captureTeam) });
            }
            else ev({ s, r, t, k: 'capture_flip', g: gi, team: q.captureTeam, from: p.captureTeam });
          } else if (p.state !== q.state) ev({ s, r, t, k: 'group_state', g: gi, from: GROUP_STATES[p.state], to: GROUP_STATES[q.state] });
        });

        const awake = groupAwake(camps);
        for (let gi = 0; gi < nGroups; gi++) {
          if (prevAwake[gi] === 0 && awake[gi] === 1) ev({ s, r, t, k: 'group_wake', g: gi, by: isChamp ? a : undefined });
          else if (prevAwake[gi] === 1 && awake[gi] === 0) ev({ s, r, t, k: 'group_sleep', g: gi });
        }
        prevAwake = awake;

        if ((st.kind === K['End turn'] || st.kind === K['Turn rollover']) && isChamp && a === turnChamp) {
          const p = curById.get(a);
          let status;
          if (st.kind === K['Turn rollover']) status = TURN.fuel;
          else if (turnActed) status = TURN.acted;
          else if (turnStatus.get(a) !== undefined) status = turnStatus.get(a);
          else status = TURN.idle;
          if (status === TURN.idle && !p.alive) status = TURN.dead;
          turnStatus.set(a, status);
          turnChamp = NONE;
        }
      } else {
        prevAwake = groupAwake(camps);
        prevItems = roster.map((_, k) => snap.items(k));
        prevCons = roster.map((_, k) => snap.consumables(k));
      }

      if (h.phase === 10 && h.currentChampion !== NONE && h.currentChampion !== turnChamp) {
        const c = cur.find(q => q.id === h.currentChampion);
        turnChamp = h.currentChampion;
        turnActed = false;
        if (c) {
          if (c.stun > 0) turnStatus.set(c.id, TURN.stunned);
          else if (c.ct) turnStatus.set(c.id, TURN.channel);
          else turnStatus.delete(c.id);
          const view = g.read({ team: c.team, champion: c.id }).knownChampions();
          sees.set(c.id, cur.filter(q => q.team !== c.team && ((view.get(q.id) ?? 0) & 1)).map(q => q.id));
        }
      }

      prev = cur; prevCamps = camps; prevGroups = groups;
    } while (g.next());

    const finalSnap = g.read();
    const fh = finalSnap.header();
    recordRound(finalSnap, round, prev, prevCamps, prevGroups);
    const draft = finalSnap.draft();
    let stats = null, statsError = null;
    try { stats = g.statistics(); } catch (e) { statsError = String(e.message ?? e); }

    const finalChamps = finalSnap.champions();
    const winner = fh.outcome === 1 ? 0 : fh.outcome === 2 ? 1 : null;
    const champions = roster.map((c, k) => {
      const f = finalChamps[k];
      const s = stats?.champions.find(q => q.champion === c.id);
      return {
        ...c, kills: f.kda[0], deaths: f.kda[1], assists: f.kda[2], earnedGold: f.earnedGold, gold: f.gold, gems: f.gems,
        stats: s ? {
          kills: s.kills, deaths: s.deaths, assists: s.assists, earnedGold: s.earnedGold, spentGold: s.spentGold, collectedGems: s.collectedGems, submittedGems: s.submittedGems,
          championDamageDone: s.championDamageDone, championDamageTaken: s.championDamageTaken, monsterDamageDone: s.monsterDamageDone, monsterDamageTaken: s.monsterDamageTaken,
          healingDone: s.healingDone, shieldingDone: s.shieldingDone, itemsBought: pairs(s.itemsBought), consumablesBought: s.consumablesBought,
        } : null,
      };
    });
    const result = { winner, outcome: fh.outcome, rounds: fh.round, gems: fh.submittedGems, steps };
    const validation = validate(ctx, result, champions, events, stats, statsError);
    const mapHash = mapKey(rawMap);
    const metaOut = {
      v: EXTRACTOR_VERSION, engine: engineInfo(), source: path.relative(ROOT, file).split(path.sep).join('/'), sha256: hash, sourceKind: ctx.kind,
      map: { name: ctx.map, hash: mapHash, width: rawMap.width, height: rawMap.height, symmetry: rawMap.symmetry },
      teams: ctx.teams, group: ctx.group, matchId: ctx.matchId, position: ctx.position,
      draft: { rounds: draft.numRounds, picks: draft.picks.map((p, ti) => p.slice(0, draft.counts[ti] || draft.numRounds).map(x => DRAFT_CHAMPIONS[x] ?? x)), pickIds: draft.picks },
      champions, result, faults: stats?.summary.faults ?? null, validation,
      counts: Object.fromEntries(Object.entries(events.reduce((a, e) => (a[e.k] = (a[e.k] || 0) + 1, a), {})).sort()),
      ms: Math.round(performance.now() - t0),
    };
    return { hash, meta: metaOut, map: { hash: mapHash, ...map }, events, rounds: R };
  } finally {
    g.destroy();
  }
}

function validate(ctx, result, champions, events, stats, statsError) {
  const hard = [], soft = [];
  const exp = ctx.expected;
  const check = (list, name, got, want) => { if (want !== undefined && want !== null && got !== want) list.push(`${name}: got ${got}, expected ${want}`); };
  if (statsError) hard.push(`engine statistics unavailable: ${statsError}`);
  if (stats) {
    check(hard, 'engine round', stats.summary.round, result.rounds);
    check(hard, 'engine gems A', stats.summary.submittedGems[0], result.gems[0]);
    check(hard, 'engine gems B', stats.summary.submittedGems[1], result.gems[1]);
  }
  if (ctx.kind === 'ladder') {
    if (!exp) hard.push('no matching statistics in group.json');
    else {
      check(hard, 'round', result.rounds, exp.round);
      exp.teams?.forEach(tm => check(hard, `gems team ${tm.team}`, result.gems[tm.team], tm.submittedGems));
      const want = exp.outcome === 'teamA' ? 0 : exp.outcome === 'teamB' ? 1 : undefined;
      check(hard, 'winner', result.winner, want);
      for (const ec of exp.champions ?? []) {
        const c = champions.find(q => q.id === ec.champion);
        if (!c) { hard.push(`champion ${ec.champion} missing`); continue; }
        check(hard, `champion ${c.id} type`, c.type, ec.type);
        check(hard, `champion ${c.id} kills`, c.kills, ec.kills);
        check(hard, `champion ${c.id} deaths`, c.deaths, ec.deaths);
        check(hard, `champion ${c.id} assists`, c.assists, ec.assists);
        check(hard, `champion ${c.id} earnedGold`, c.earnedGold, ec.earnedGold);
        if (c.stats) for (const f of ['collectedGems', 'submittedGems', 'spentGold', 'championDamageDone', 'championDamageTaken', 'monsterDamageDone', 'monsterDamageTaken', 'healingDone', 'shieldingDone'])
          if (ec[f] !== undefined && Math.abs(c.stats[f] - ec[f]) > 0.5) hard.push(`champion ${c.id} engine ${f}: ${c.stats[f]} vs ${ec[f]}`);
      }
    }
  } else if (ctx.kind === 'batch' && exp) {
    check(hard, 'round', result.rounds, exp.rounds);
    const winnerBot = result.winner === null ? null : ctx.teams[result.winner].bot;
    check(hard, 'winner bot', winnerBot, exp.winnerBot);
  }
  const deaths = new Map(), kills = new Map(), dealt = new Map(), taken = new Map(), monster = new Map(), monsterTaken = new Map(), tributed = new Map(), earned = new Map();
  const add = (m, k, v) => m.set(k, (m.get(k) ?? 0) + v);
  for (const e of events) {
    if (e.k === 'death') { add(deaths, e.v, 1); if (e.by !== undefined && e.linked === undefined) { add(kills, e.by, 1); if (e.gold) add(earned, e.by, e.gold); } }
    if (e.k === 'attack' || e.k === 'cast') {
      for (const [id, v] of e.dmg ?? []) { add(dealt, e.a, v); add(taken, id, v); }
      for (const [, v] of e.cdmg ?? []) add(monster, e.a, v);
      if (e.refl && e.reflBy !== undefined) { add(dealt, e.reflBy, e.refl); add(taken, e.a, e.refl); }
    }
    if (e.k === 'camp_attack') { add(monsterTaken, e.tgt, e.dmg); for (const [, v] of e.refl ?? []) add(monster, e.tgt, v); }
    if (e.k === 'tribute_end') add(tributed, e.a, e.gems);
    if (e.k === 'capture') for (const [id, , gold] of e.shares) add(earned, id, gold);
  }
  for (const c of champions) {
    check(hard, `champion ${c.id} death events`, deaths.get(c.id) ?? 0, c.deaths);
    check(soft, `champion ${c.id} kill events`, kills.get(c.id) ?? 0, c.kills);
    if (c.stats) {
      const near = (name, got, want, tol) => { if (Math.abs(got - want) > tol) soft.push(`champion ${c.id} ${name}: derived ${r1(got)}, engine ${r1(want)}`); };
      near('submittedGems', tributed.get(c.id) ?? 0, c.stats.submittedGems, 0);
      near('championDamageDone', dealt.get(c.id) ?? 0, c.stats.championDamageDone, Math.max(1, 0.02 * c.stats.championDamageDone));
      near('championDamageTaken', taken.get(c.id) ?? 0, c.stats.championDamageTaken, Math.max(1, 0.02 * c.stats.championDamageTaken));
      near('monsterDamageDone', monster.get(c.id) ?? 0, c.stats.monsterDamageDone, Math.max(1, 0.02 * c.stats.monsterDamageDone));
      near('monsterDamageTaken', monsterTaken.get(c.id) ?? 0, c.stats.monsterDamageTaken, Math.max(1, 0.02 * c.stats.monsterDamageTaken));
      near('earnedGold', earned.get(c.id) ?? 0, c.stats.earnedGold, 1);
    }
  }
  return { ok: hard.length === 0, hard, soft };
}

function writeGame(res) {
  const dir = path.join(OUT_ROOT, res.hash.slice(0, 16));
  fs.mkdirSync(dir, { recursive: true });
  const mapsDir = path.join(OUT_ROOT, 'maps');
  fs.mkdirSync(mapsDir, { recursive: true });
  const mapFile = path.join(mapsDir, `${res.map.hash}.json`);
  if (!fs.existsSync(mapFile)) writeJson(mapFile, res.map);
  res.meta.mapFile = `../maps/${res.map.hash}.json`;
  fs.writeFileSync(path.join(dir, 'events.jsonl.gz'), zlib.gzipSync(res.events.map(e => JSON.stringify(e)).join('\n') + '\n'));
  fs.writeFileSync(path.join(dir, 'rounds.json.gz'), zlib.gzipSync(JSON.stringify(res.rounds)));
  writeJson(path.join(dir, 'meta.json'), res.meta);
}

function findReplays(inputs) {
  const out = [];
  const walk = p => {
    const st = fs.statSync(p);
    if (st.isDirectory()) { if (path.basename(p) === '.analysis') return; for (const f of fs.readdirSync(p).sort()) walk(path.join(p, f)); }
    else if (p.endsWith('.repl26a')) out.push(path.resolve(p));
  };
  for (const i of inputs) walk(i);
  return [...new Set(out)];
}

function cachedMeta(hash) {
  try {
    const m = JSON.parse(fs.readFileSync(path.join(OUT_ROOT, hash, 'meta.json'), 'utf8'));
    return m.v === EXTRACTOR_VERSION && m.engine?.sha256 === engineInfo()?.sha256 ? m : null;
  } catch { return null; }
}

function sourceEntry(file) {
  const c = sourceContext(file);
  return { source: path.relative(ROOT, file).split(path.sep).join('/'), kind: c.kind, map: c.map, teams: c.teams, group: c.group, matchId: c.matchId, position: c.position, expected: c.expected };
}

// The same replay can occur more than once (deterministic rematches); every copy is listed in meta.sources.
function mergeSources(hash, files) {
  const f = path.join(OUT_ROOT, hash, 'meta.json');
  const m = JSON.parse(fs.readFileSync(f, 'utf8'));
  const have = new Map((m.sources ?? []).map(q => [q.source, q]));
  let changed = false;
  for (const file of files) {
    const e = sourceEntry(file);
    if (have.has(e.source)) continue;
    const problems = [];
    const x = e.expected;
    if (e.kind === 'ladder' && x) {
      if (x.round !== m.result.rounds) problems.push(`round ${m.result.rounds} vs ${x.round}`);
      const w = x.outcome === 'teamA' ? 0 : x.outcome === 'teamB' ? 1 : null;
      if (w !== m.result.winner) problems.push(`winner ${m.result.winner} vs ${w}`);
    } else if (e.kind === 'batch' && x) {
      if (x.rounds !== m.result.rounds) problems.push(`round ${m.result.rounds} vs ${x.rounds}`);
    }
    delete e.expected;
    if (problems.length) e.problems = problems;
    have.set(e.source, e);
    changed = true;
  }
  if (changed) { m.sources = [...have.values()].sort((a, b) => a.source.localeCompare(b.source)); writeJson(f, m); }
  return m;
}

function writeIndex() {
  const games = [];
  for (const d of fs.readdirSync(OUT_ROOT)) {
    const f = path.join(OUT_ROOT, d, 'meta.json');
    if (!fs.existsSync(f)) continue;
    const m = JSON.parse(fs.readFileSync(f, 'utf8'));
    for (const src of m.sources ?? []) games.push({ dir: d, source: src.source, kind: src.kind, map: m.map.name, mapHash: m.map.hash, teams: src.teams.map(t => t.name), winner: m.result.winner, rounds: m.result.rounds, gems: m.result.gems, ok: m.validation.ok && !src.problems, copies: m.sources.length });
  }
  games.sort((a, b) => a.source.localeCompare(b.source));
  writeJson(path.join(OUT_ROOT, 'index.json'), { v: EXTRACTOR_VERSION, games });
  writeJson(path.join(OUT_ROOT, 'enums.json'), {
    champions: CHAMPIONS, draftChampions: DRAFT_CHAMPIONS, items: ITEMS, consumables: CONSUMABLES, abilityTypes: ABILITY_TYPES, buffs: BUFFS,
    camps: CAMPS, channels: CHANNELS, groupStates: GROUP_STATES, turn: TURN, stepKinds: STEP_KINDS,
  });
}

async function updateEngine() {
  const { spawn } = await import('node:child_process');
  const port = 30000 + Math.floor(Math.random() * 20000);
  const version = await new Promise((res, rej) => {
    const p = spawn('cambc', ['--version'], {});
    let o = ''; p.stdout.on('data', d => o += d); p.on('close', c => c ? rej(new Error('cambc --version failed')) : res(o.trim()));
  });
  const server = spawn('cambc', ['view', '--port', String(port)], { stdio: 'ignore' });
  const base = `http://127.0.0.1:${port}/`;
  try {
    let html;
    for (let i = 0; i < 60 && !html; i++) {
      try { const r = await fetch(base); if (r.ok) html = await r.text(); } catch { await new Promise(r => setTimeout(r, 500)); }
    }
    if (!html) throw new Error(`cambc view did not serve ${base}`);
    const main = /src="\.?\/?(assets\/index-[^"]+\.js)"/.exec(html)?.[1];
    if (!main) throw new Error('main asset not found in index.html');
    const js = await (await fetch(base + main)).text();
    const wasmName = /v0_0_1-[A-Za-z0-9_-]+\.wasm/.exec(js)?.[0];
    if (!wasmName) throw new Error(`no v0_0_1-*.wasm referenced in ${main}`);
    const r = await fetch(base + 'assets/' + wasmName);
    if (!r.ok) throw new Error(`download ${wasmName}: HTTP ${r.status}`);
    const bytes = Buffer.from(await r.arrayBuffer());
    const mod = await WebAssembly.compile(bytes);
    await Engine.create(mod).catch(e => { throw new Error(`downloaded engine rejected: ${e.message}`); });
    fs.mkdirSync(ENGINE_DIR, { recursive: true });
    fs.writeFileSync(WASM_PATH, bytes);
    const info = { cambc: version, asset: wasmName, snapshotSize: SNAPSHOT_SIZE, sha256: sha256(bytes), bytes: bytes.length, updated: new Date().toISOString() };
    fs.writeFileSync(path.join(ENGINE_DIR, 'version.json'), JSON.stringify(info, null, 2) + '\n');
    console.log(`engine updated: ${wasmName} (${version}), sha256 ${info.sha256}`);
  } finally {
    if (process.platform === 'win32') spawn('taskkill', ['/pid', String(server.pid), '/T', '/F'], { stdio: 'ignore' });
    else server.kill();
  }
}

async function main() {
  const args = process.argv.slice(2);
  const opts = { threads: Math.max(1, Math.min(16, os.availableParallelism() - 1)), force: false, update: false, inputs: [] };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--threads') opts.threads = Math.max(1, +args[++i]);
    else if (a === '--force') opts.force = true;
    else if (a === '--update-engine') opts.update = true;
    else if (a === '-h' || a === '--help') { console.log('usage: node tools/replay/extract.mjs <dirs or .repl26a files...> [--threads N] [--force] [--update-engine]'); return 0; }
    else opts.inputs.push(a);
  }
  if (opts.update) await updateEngine();
  if (!opts.inputs.length) { if (!opts.update) console.error('no inputs; see --help'); return opts.update ? 0 : 2; }
  const module = await compileEngine();
  await Engine.create(module);
  fs.mkdirSync(OUT_ROOT, { recursive: true });
  const files = findReplays(opts.inputs);
  const byHash = new Map();
  for (const f of files) {
    const h = sha256(fs.readFileSync(f)).slice(0, 16);
    if (!byHash.has(h)) byHash.set(h, []);
    byHash.get(h).push(f);
  }
  const todo = [], skipped = [];
  for (const [h, fs2] of byHash) { const m = !opts.force && cachedMeta(h); if (m) skipped.push(m); else todo.push(fs2[0]); }
  console.log(`${files.length} replays (${byHash.size} distinct): ${todo.length} to extract, ${skipped.length} cached`);
  const t0 = performance.now();
  const results = [];
  let next = 0, done = 0;
  const nThreads = Math.min(opts.threads, todo.length);
  await Promise.all(Array.from({ length: nThreads }, () => new Promise(resolve => {
    const w = new Worker(fileURLToPath(import.meta.url), { workerData: { module } });
    const feed = () => { if (next < todo.length) w.postMessage(todo[next++]); else { w.terminate(); resolve(); } };
    w.on('message', m => {
      results.push(m);
      done++;
      if (!m.ok || done % 25 === 0 || done === todo.length) console.log(`[${done}/${todo.length}] ${m.ok ? 'ok  ' : 'FAIL'} ${m.source} ${m.error ?? (m.hard?.length ? m.hard.slice(0, 3).join('; ') : '')}`);
      feed();
    });
    w.on('error', e => { results.push({ ok: false, source: '?', error: String(e) }); resolve(); });
    feed();
  })));
  const secs = (performance.now() - t0) / 1000;
  const dupProblems = [];
  for (const [h, fs2] of byHash) if (fs.existsSync(path.join(OUT_ROOT, h, 'meta.json'))) for (const q of mergeSources(h, fs2).sources ?? []) if (q.problems) dupProblems.push(`${q.source}: ${q.problems.join('; ')}`);
  writeIndex();
  const failed = results.filter(r => !r.ok);
  const soft = results.reduce((a, r) => a + (r.soft ?? 0), 0);
  console.log(`extracted ${results.length - failed.length}/${results.length} in ${secs.toFixed(1)} s (${todo.length ? (secs * 1000 / todo.length).toFixed(0) : 0} ms/replay wall, ${nThreads} threads); ${soft} soft validation notes`);
  const cachedFail = skipped.filter(m => !m.validation.ok);
  for (const m of cachedFail) console.log(`cached FAIL ${m.source}: ${m.validation.hard.slice(0, 3).join('; ')}`);
  for (const p of dupProblems) console.log(`duplicate-source mismatch ${p}`);
  if (failed.length || cachedFail.length || dupProblems.length) {
    console.log(`${failed.length + cachedFail.length + dupProblems.length} failures`);
    for (const f of failed) console.log(`  ${f.source}: ${f.error ?? f.hard.join('; ')}`);
    return 1;
  }
  return 0;
}

if (isMainThread) {
  main().then(c => { process.exitCode = c; }, e => { console.error(e.stack ?? e); process.exitCode = 1; });
} else {
  let engine = await Engine.create(workerData.module);
  parentPort.on('message', async file => {
    const source = path.relative(ROOT, file);
    try {
      const res = extractGame(engine, file);
      writeGame(res);
      parentPort.postMessage({ ok: res.meta.validation.ok, source, hard: res.meta.validation.hard, soft: res.meta.validation.soft.length, ms: res.meta.ms });
    } catch (e) {
      engine = await Engine.create(workerData.module);
      parentPort.postMessage({ ok: false, source, error: String(e.stack ?? e) });
    }
  });
}
