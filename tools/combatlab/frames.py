"""Frame bank for the combat lab: fight starts from local games as scenario specs (research/notes/COMBAT-LAB.md).

py tools/combatlab/frames.py replays/batch-X [more batch dirs...] --name NAME [--games N] [--copy] [--threads 16]

Writes replays/combatlab/NAME/frames.jsonl (one spec per line) and report.md. Engagements are
tools/replay/analysis/fights.py's clusters; the frame is the state --lead rounds before the first champion damage.
"""
import argparse
import gzip
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'replay'))
from analysis import data as adata  # noqa: E402
from analysis import fights as afights  # noqa: E402
from analysis import params as aparams  # noqa: E402

DEFAULT_BOTS = r'^(ocean|astraeus|oc|ast|g\d+)([-_].*)?$'
CHANNEL = {1: 'recall', 2: 'tribute', 3: 'teleport', 4: 'teleport_scroll'}
SHIELD_TURNS = 5
# Clusters have no attack, but sleep as if their range were 3 (fitted to replay snapshots; not in the rules).
CAMP_RANGE = {'Wolf': 3, 'Elk': 4, 'Golem': 4, 'Monolith': 5, 'Gem cluster': 3, 'Gold cluster': 3}
WINDOWS = (10, 30)


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def rel(p):
    p = Path(p).resolve()
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


# ---------------------------------------------------------------- game list

def batch_games(d):
    """(replay, map, botA, botB) per replay of a batch dir: manifest.txt (team A's bot first), else results.json."""
    d = Path(d)
    rows = []
    man = d / 'manifest.txt'
    if man.exists():
        for line in man.read_text().splitlines():
            f = line.split()
            if len(f) >= 4:
                rows.append((f[3], f[2], Path(f[0]).name, Path(f[1]).name))
    elif (d / 'results.json').exists():
        r = json.loads((d / 'results.json').read_text())
        bots = [Path(b).name for b in r['bots']]
        for m in r['matches']:
            if m.get('replay'):
                o = m.get('order', [0, 1])
                rows.append((m['replay'], m['map'], bots[o[0]], bots[o[1]]))
    out = []
    for rp, mp, a, b in rows:
        rp = Path(rp)
        if not rp.is_absolute():
            rp = d / rp.name
        out.append((str(rp), str(mp), a, b, d.name))
    return out


def find_batches(inputs):
    out = []
    for i in inputs:
        p = Path(i)
        if (p / 'manifest.txt').exists() or (p / 'results.json').exists():
            out.append(p)
        else:
            out += sorted(q.parent for q in p.rglob('manifest.txt'))
    return out


def sha16(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()[:16]


# ---------------------------------------------------------------- per game

class G(adata.Game):
    """analysis.data.Game reading from a cache directory of our own."""

    def __init__(self, cache, d):
        adata.ANALYSIS = Path(cache)
        super().__init__(d)


def group_rows(R):
    """{group: [(round, row)]} change rows, for forward fill."""
    cols = R['groupCols']
    out = defaultdict(list)
    for row in R['groups']:
        d = dict(zip(cols, row))
        out[d['group']].append((d['round'], d))
    return out


def group_at(rows, r):
    """Group row in force at the end of round r."""
    cur = None
    for rr, d in rows:
        if rr > r:
            break
        cur = d
    return cur


class CampHp:
    """Per-camp hp at the end of each round, from camp damage events (rounds.json only keeps group totals)."""

    def __init__(self, g):
        self.g = g
        self.max = {c['id']: c['hp'] for c in g.map.camps}
        self.members = {grp['id']: grp['camps'] for grp in g.map.groups}
        ev = []
        for e in g.events:
            k = e['k']
            if k in ('attack', 'cast') and e.get('cdmg'):
                for c, amt in e['cdmg']:
                    ev.append((e['s'], e['r'], 'd', c, amt))
            elif k == 'camp_attack' and e.get('refl'):
                for c, amt in e['refl']:
                    ev.append((e['s'], e['r'], 'd', c, amt))
            elif k == 'camp_death':
                ev.append((e['s'], e['r'], 'x', e['camp'], 0))
            elif k == 'group_respawn':
                ev.append((e['s'], e['r'], 'g', e['g'], 0))
        ev.sort()
        self.ev = ev
        # Rounds a group was woken from all asleep, and rounds any member took damage.
        self.wakes = defaultdict(list)
        self.hits = defaultdict(set)
        grp_of = {c['id']: c['group'] for c in g.map.camps}
        for e in g.events:
            if e['k'] == 'group_wake':
                self.wakes[e['g']].append(e['r'])
        for s, r, kind, c, amt in ev:
            if kind == 'd':
                self.hits[grp_of[c]].add(r)

    def awake(self, cm, r):
        """Whether a live member of an awake group is itself awake at the end of round r, simulated from the group's
        last wake from all asleep. A monster sleeps after two camp phases in a row with no champion in its range (the
        phase after a wake counts as occupied); damage to the group wakes it only while asleep (damage does not keep
        it awake). Camp phase R sees the champions where they stood at the end of round R-1."""
        rng = CAMP_RANGE.get(cm['type'])
        if rng is None:
            return True
        w = max((x for x in self.wakes[cm['group']] if x <= r), default=None)
        if w is None:
            return True
        hits = self.hits[cm['group']]
        awake, empty, grace = True, 0, True
        for R in range(w + 1, r + 1):
            if awake:
                if grace:
                    grace = False
                    empty = 0
                else:
                    i = R - 2
                    occ = any(ch['alive'][i] and ch['x'][i] is not None and max(abs(ch['x'][i] - cm['x']), abs(ch['y'][i] - cm['y'])) <= rng
                              for ch in self.g.rounds['champions'])
                    empty = 0 if occ else empty + 1
                    if empty >= 2:
                        awake = False
            if not awake and R in hits:
                awake, empty, grace = True, 0, True
        return awake

    def at_end(self, r):
        hp = dict(self.max)
        for s, er, kind, c, amt in self.ev:
            if er > r:
                break
            if kind == 'd':
                hp[c] = hp[c] - amt
            elif kind == 'x':
                hp[c] = 0.0
            else:
                for m in self.members[c]:
                    hp[m] = self.max[m]
        return hp


def shield_casts(g):
    """{champion: [round of each self-shield cast]}."""
    out = defaultdict(list)
    for e in g.events:
        if e['k'] == 'cast' and e.get('ab') == 'Shield':
            out[e['a']].append(e['r'])
    return out


def items_dict(flat):
    return {str(flat[i]): flat[i + 1] for i in range(0, len(flat), 2)}


def process_game(job):
    cache, d, info, P = job
    try:
        return _process_game(cache, d, info, P)
    except Exception as ex:  # one bad game must not stop a bank
        import traceback
        return {'dir': d, 'lines': [], 'stats': [], 'skips': Counter({'game_error': 1}), 'error': f'{d}: {ex!r}\n{traceback.format_exc()}', 'checks': Counter()}


def _process_game(cache, d, info, P):
    g = G(cache, d)
    R = g.rounds
    n = len(R['round'])  # index i = end of round i+1
    last_round = R['round'][-1]
    mp = g.map
    W, H = mp.W, mp.H
    lead, margin, zmargin, core_w = P['lead'], P['margin'], P['zone_margin'], P['core_window']
    skips = Counter()
    checks = Counter()
    lines, stats = [], []

    map_path = info['map']
    if not (ROOT / map_path).exists():
        return {'dir': d, 'lines': [], 'stats': [], 'skips': Counter({'map_missing': 1}), 'checks': checks}

    # Champion damage instances as fights.py builds them, keeping whether each is a Ren reflection.
    inst = []
    for s, r, a, v, amt, ap, vp in g.champ_damage:
        i = g.start_idx(r)
        refl = ap is None
        ap = ap or g.pos(a, i)
        vp = vp or g.pos(v, i)
        inst.append((s, r, a, v, amt, ap, vp, refl))
    base = [x[:7] for x in inst]
    refl_of = {(x[0], x[2], x[3]): x[7] for x in inst}
    clusters = []
    for its in afights._cluster(base, P['radius'], P['gap']):
        clusters += afights._split(its, P['max_dur'])
    clusters.sort(key=lambda c: min(x[0] for x in c))

    # Rounds each champion dealt or took champion damage.
    hot = defaultdict(set)
    for s, r, a, v, *_ in base:
        hot[a].add(r)
        hot[v].add(r)

    camp_hp = None
    recalls = defaultdict(list)
    for e in g.events:
        if e['k'] in ('recall_start', 'recall_cancel', 'recall_end'):
            recalls[e['a']].append((e['s'], e['r'], e['k'], e.get('cause')))
    grows = group_rows(R)
    shields = shield_casts(g)
    ids = [c['id'] for c in g.champs]
    partner = {}
    for t in (0, 1):
        ci = [c['id'] for c in g.champs if c['team'] == t and c['name'] in ('Cassi', 'Issac')]
        if len(ci) == 2:
            partner[ci[0]], partner[ci[1]] = ci[1], ci[0]
    spawn = mp.spawn
    picks = [[p for p in pk if p >= 0] for pk in g.meta['draft']['pickIds']]

    prev_F = None
    used_ids = Counter()
    for its in clusters:
        its = sorted(its)
        r0, r1 = its[0][1], its[-1][1]
        first = next((x for x in its if not refl_of.get((x[0], x[2], x[3]))), its[0])
        initiator = g.team_of[first[2]]
        F = r0 - lead + 1          # spec round: state at the end of round F-1
        si = F - 2                 # rounds index of that state
        if si < 0:
            skips['too_early'] += 1
            continue
        core = set()
        for x in its:
            if x[1] <= r0 + core_w - 1:
                core.add(x[2])
                core.add(x[3])
        alive = {c: g.ch(c)['alive'][si] == 1 and g.ch(c)['x'][si] is not None for c in ids}
        pos = {c: (g.ch(c)['x'][si], g.ch(c)['y'][si]) if alive[c] else None for c in ids}
        dead_core = [c for c in core if not alive[c]]
        if dead_core:
            skips['fighter_dead'] += 1
            continue
        fighters = set(core)
        for c in ids:
            if alive[c] and c not in fighters and any(cheb(pos[c], pos[k]) <= margin for k in core):
                fighters.add(c)
        # Our bots start a recall at the end of most turns and cancel it at the next (a feint). One cancelled by
        # round F only shows to opponents acting before the champion in F, so only longer channels are skipped.
        chans, feints = [], []
        for c in fighters:
            ct = g.ch(c)['chan'][si]
            if not ct:
                continue
            if ct == 1 and recall_ends_by(recalls[c], F - 1, F):
                feints.append(c)
            else:
                chans.append(CHANNEL.get(ct, 'channel'))
        if chans:
            skips['channel_' + sorted(chans)[0]] += 1  # a recall here completes or lasts past round F
            continue
        if any(r in hot[c] for c in fighters for r in range(F - 1, r0)):
            skips['mid_fight'] += 1
            continue
        pts = [pos[c] for c in fighters] + [p for x in its if x[1] == r0 for p in (x[5], x[6]) if p]
        x0 = max(0, min(p[0] for p in pts) - zmargin)
        y0 = max(0, min(p[1] for p in pts) - zmargin)
        x1 = min(W - 1, max(p[0] for p in pts) + zmargin)
        y1 = min(H - 1, max(p[1] for p in pts) + zmargin)
        zone = [x0, y0, x1, y1]
        inzone = lambda p: p is not None and x0 <= p[0] <= x1 and y0 <= p[1] <= y1  # noqa: E731
        # A champion dead now that respawns within 20 rounds on a spawn near the zone could join.
        near = False
        for c in ids:
            ch = g.ch(c)
            if not alive[c] and 0 <= ch['respawn'][si] <= P['respawn_window']:
                s = spawn[g.team_of[c]]
                dx = max(s['minX'] - x1, x0 - s['maxX'], 0)
                dy = max(s['minY'] - y1, y0 - s['maxY'], 0)
                if max(dx, dy) <= P['respawn_dist']:
                    near = True
        if near:
            skips['respawn_near_zone'] += 1
            continue
        # A non-fighter's teleport landing in the zone.
        if any(g.ch(c)['chan'][si] == 3 for c in ids if c not in fighters):
            tp_in = False
            for e in g.events:
                if e['k'] == 'teleport_start' and e['a'] not in fighters and e['r'] <= F - 1 and inzone(tuple(e['to'])):
                    end = next((q for q in g.events if q['k'] in ('teleport_end', 'teleport_cancel') and q['a'] == e['a'] and q['s'] > e['s']), None)
                    if end is None or end['r'] >= F:
                        tp_in = True
            if tp_in:
                skips['teleport_into_zone'] += 1
                continue

        if camp_hp is None:
            camp_hp = CampHp(g)
        chp = camp_hp.at_end(F - 1)

        # Champions.
        champs = []
        for c in ids:
            ch = g.ch(c)
            sh = ch['shield'][si]
            turns = 0
            if sh > 0:
                cast = [r for r in shields.get(c, []) if r <= F - 1]
                if cast:
                    turns = max(0, SHIELD_TURNS - 1 - (F - 1 - cast[-1]))
            champs.append({
                'id': c, 'team': g.team_of[c], 'name': g.name_of[c], 'alive': bool(alive[c]),
                'x': pos[c][0] if alive[c] else None, 'y': pos[c][1] if alive[c] else None,
                'hp': ch['hp'][si], 'maxHp': ch['maxHp'][si], 'gold': ch['gold'][si], 'gems': ch['gems'][si],
                'items': items_dict(ch['items'][si]), 'cons': ch['cons'][si], 'cd': [ch['cd0'][si], ch['cd1'][si]],
                'stun': ch['stun'][si], 'shield': {'amount': sh, 'turns': turns},
                'respawn': ch['respawn'][si] if not alive[c] else 0, 'fighter': c in fighters,
                'prio': ch['prio'][si], 'ward': ch['ward'][si],
            })

        # Camps in the zone, with their groups' capture state.
        camps, groups_in = [], []
        gseen = set()
        for cm in mp.camps:
            if not inzone((cm['x'], cm['y'])):
                continue
            gr = group_at(grows[cm['group']], F - 1)
            hp = max(0.0, chp[cm['id']])
            if hp > 0 and gr:
                # Event amounts are rounded to 0.1: spread the residual against the group's total over its live
                # members by the damage each took.
                mem = camp_hp.members[cm['group']]
                tot = sum(max(0.0, chp[m]) for m in mem)
                lost = sum(camp_hp.max[m] - chp[m] for m in mem if chp[m] > 0)
                if lost > 0:
                    hp += (gr['hp'] - tot) * (camp_hp.max[cm['id']] - hp) / lost
                hp = min(max(hp, 0.05), camp_hp.max[cm['id']])
            awake = bool(gr and gr['awake'] == 1 and hp > 0)
            if awake and len(camp_hp.members[cm['group']]) > 1:
                awake = camp_hp.awake(cm, F - 1)
            camps.append({'id': cm['id'], 'alive': hp > 0, 'hp': round(max(0.0, hp), 1),
                          'awake': awake, 'type': cm['type'], 'group': cm['group'],
                          'x': cm['x'], 'y': cm['y']})
            if cm['group'] not in gseen:
                gseen.add(cm['group'])
                tot = sum(max(0.0, chp[m]) for m in camp_hp.members[cm['group']])
                checks['group_hp'] += 1
                if gr and abs(tot - gr['hp']) > 5:
                    checks['group_hp_mismatch'] += 1
                if gr:
                    groups_in.append({'id': cm['group'], 'state': gr['state'], 'team': gr['team'], 'timer': gr['timer'],
                                      'respawn': gr['respawn'], 'awake': gr['awake'], 'hp': gr['hp']})

        counts = [sum(1 for c in fighters if g.team_of[c] == t) for t in (0, 1)]
        kind = f'{max(counts)}v{min(counts)}'
        # Picks: Cassi and Issac are one pick, two bodies.
        pk = [len({partner.get(c, c) if partner.get(c, c) < c else c for c in fighters if g.team_of[c] == t}) for t in (0, 1)]
        late = sorted({c for x in its for c in (x[2], x[3])} - fighters)
        cut_partner = sorted(c for c in fighters if c in partner and partner[c] not in fighters)
        wards = [w for w in R['wards'][si]] if si < len(R['wards']) else []
        locks = R['locks'][si] if si < len(R['locks']) else []

        observed = {}
        for Wn in WINDOWS:
            observed[str(Wn)] = observe(g, fighters, zone, F, Wn, last_round, n)

        used_ids[F] += 1
        frame_id = f'{d}-r{F}' + (f'-{used_ids[F]}' if used_ids[F] > 1 else '')
        spec = {
            'id': frame_id,
            'source': {'replay': info['replay'], 'round': F, 'game': d, 'batch': info['batch']},
            'map': info['map'],
            'picks': picks,
            'round': F,
            'champions': champs,
            'camps': camps,
            # Every ward on the map (the runner places them as their owners): position and the owner's recharge.
            'wards': [{'owner': w[0], 'team': w[1], 'x': w[2], 'y': w[3], 'disabled': bool(w[4]),
                       'recharge': (g.ch(w[0])['ward'][si] or [0, 0])[1]} for w in wards],
            'fight': {'zone': zone, 'kind': kind, 'initiator': initiator, 'counts': counts, 'pick_counts': pk, 'first_damage': r0,
                      'last_damage': r1, 'length': r1 - r0 + 1, 'lead': lead, 'core': sorted(core)},
            'context': {
                'bots': [info['bots'][0], info['bots'][1]], 'map_name': Path(info['map']).stem, 'game_rounds': last_round,
                'winner': g.winner, 'tributed': [R['gems'][0][si], R['gems'][1][si]],
                'feints': sorted(feints), 'groups': groups_in, 'wards': wards, 'locks': locks, 'late_joiners': late, 'partner_outside': cut_partner,
                'quiet': quiet_rounds(hot, fighters, F),
                'since_prev_frame': None if prev_F is None else F - prev_F,
            },
            'observed': observed,
        }
        prev_F = F
        lines.append(json.dumps(spec, separators=(',', ':')))
        stats.append({
            'kind': kind, 'counts': counts, 'pick_counts': pk, 'init': initiator, 'round': F, 'len': r1 - r0 + 1,
            'types': [g.name_of[c] for c in fighters], 'bots': info['bots'], 'camps': len(camps),
            'zone': max(x1 - x0 + 1, y1 - y0 + 1), 'late': len(late), 'partner': len(cut_partner),
            'obs': {k: {'deaths': o['deaths'], 'kills': o['kills'], 'gems_won': o['gems_won'], 'left': [len(o['left'][0]), len(o['left'][1])],
                        'truncated': o['truncated'], 'camp_deaths': o['camp_deaths']} for k, o in observed.items()},
            'wards_in_zone': sum(1 for w in wards if inzone((w[2], w[3]))),
        })
    return {'dir': d, 'lines': lines, 'stats': stats, 'skips': skips, 'checks': checks, 'clusters': len(clusters)}


def recall_ends_by(evs, r_state, r_by):
    """Whether the recall in progress at the end of round r_state is cancelled (by the champion, damage, a stun or
    death) by round r_by: by its own turn in r_by the champion is then not channelling, as in a spec without one."""
    start = None
    for i, (s, r, k, cause) in enumerate(evs):
        if r > r_state:
            break
        if k == 'recall_start':
            start = i
    if start is None:
        return False
    nxt = next((x for x in evs[start + 1:] if x[2] != 'recall_start'), None)
    return nxt is not None and nxt[2] == 'recall_cancel' and nxt[1] <= r_by


def quiet_rounds(hot, fighters, F):
    """Rounds since any fighter last dealt or took champion damage, before the frame state (None: never)."""
    last = max((r for c in fighters for r in hot[c] if r <= F - 1), default=None)
    return None if last is None else F - 1 - last


def observe(g, fighters, zone, F, Wn, last_round, n):
    """What happened among the fighters in rounds F..F+Wn-1 of the real game."""
    r_end = min(F + Wn - 1, last_round)
    ei = min(r_end - 1, n - 1)
    x0, y0, x1, y1 = zone
    deaths, kills, camp_d, gw, gl, kgold, dmg = [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0.0, 0.0]
    victims, first_death = [], None
    for e in g.deaths:
        if not (F <= e['r'] <= r_end) or e['v'] not in fighters:
            continue
        t = g.team_of[e['v']]
        gl[t] += e.get('gems', 0)
        if 'linked' in e:
            continue
        victims.append([e['v'], e['r'] - F])
        deaths[t] += 1
        first_death = e['r'] - F if first_death is None else first_death
        if 'by' in e and e['by'] in g.team_of:
            kt = g.team_of[e['by']]
            kills[kt] += 1
            gw[kt] += e.get('gemsTo', 0)
            kgold[kt] += e.get('gold', 0)
        else:
            camp_d[t] += 1
    for s, r, a, v, amt, *_ in g.champ_damage:
        if F <= r <= r_end and a in fighters and v in fighters:
            dmg[g.team_of[a]] += amt
    recalled, tributed = [0, 0], [0, 0]
    for e in g.events:
        if F <= e['r'] <= r_end and e.get('a') in fighters:
            if e['k'] == 'recall_end':
                recalled[g.team_of[e['a']]] += 1
            elif e['k'] == 'tribute_end':
                tributed[g.team_of[e['a']]] += e.get('gems', 0)
    hp, left = {}, [[], []]
    hpsum, hpmax = [0.0, 0.0], [0.0, 0.0]
    for c in sorted(fighters):
        ch = g.ch(c)
        t = g.team_of[c]
        hpmax[t] += ch['maxHp'][F - 2]
        if ch['alive'][ei] and ch['x'][ei] is not None:
            hp[str(c)] = ch['hp'][ei]
            hpsum[t] += ch['hp'][ei]
            p = (ch['x'][ei], ch['y'][ei])
            if not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1):
                left[t].append(c)
        else:
            hp[str(c)] = None
    return {'rounds': r_end - F + 1, 'truncated': F + Wn - 1 > last_round, 'deaths': deaths, 'kills': kills, 'camp_deaths': camp_d,
            'gems_won': gw, 'gems_lost': gl, 'kill_gold': kgold, 'dmg': [round(x, 1) for x in dmg], 'victims': victims,
            'first_death': first_death, 'hp': hp, 'hp_frac': [round(hpsum[t] / hpmax[t], 3) if hpmax[t] else None for t in (0, 1)],
            'left': left, 'recalled': recalled, 'tributed': tributed}


# ---------------------------------------------------------------- report

class Agg:
    def __init__(self):
        self.games = 0
        self.games_with = 0
        self.frames = 0
        self.clusters = 0
        self.per_game = Counter()
        self.kinds = Counter()
        self.pick_kinds = Counter()
        self.counts = Counter()
        self.types = Counter()
        self.rounds = Counter()
        self.lens = Counter()
        self.zone = Counter()
        self.camps = Counter()
        self.skips = Counter()
        self.checks = Counter()
        self.bots_team = [Counter(), Counter()]
        self.bot_pairs = Counter()
        self.games_by_pair = Counter()
        self.late = 0
        self.partner = 0
        self.wards = 0
        self.obs = defaultdict(lambda: defaultdict(Counter))
        self.errors = []

    def add(self, res, info):
        self.games += 1
        self.clusters += res.get('clusters', 0)
        self.skips.update(res['skips'])
        self.checks.update(res['checks'])
        if res.get('error'):
            self.errors.append(res['error'])
        st = res['stats']
        self.per_game[min(len(st), 40)] += 1
        self.games_with += bool(st)
        self.games_by_pair[tuple(info['bots'])] += 1
        for s in st:
            self.frames += 1
            self.kinds[s['kind']] += 1
            self.pick_kinds[f"{max(s['pick_counts'])}v{min(s['pick_counts'])}"] += 1
            self.counts[tuple(s['counts'])] += 1
            for t in s['types']:
                self.types[t] += 1
            self.rounds[bucket(s['round'], [100, 200, 300, 500, 750, 1000, 1500, 2001])] += 1
            self.lens[bucket(s['len'], [1, 3, 6, 10, 15, 20, 25, 10**9])] += 1
            self.zone[bucket(s['zone'], [6, 9, 12, 16, 20, 10**9])] += 1
            self.camps[min(s['camps'], 5)] += 1
            self.bots_team[0][s['bots'][0]] += 1
            self.bots_team[1][s['bots'][1]] += 1
            self.bot_pairs[tuple(s['bots'])] += 1
            self.late += s['late'] > 0
            self.partner += s['partner'] > 0
            self.wards += s['wards_in_zone'] > 0
            ini = s['init']
            nA, nB = s['counts']
            for w, o in s['obs'].items():
                for key in (s['kind'], 'all'):
                    c = self.obs[w][key]
                    c['n'] += 1
                    d = o['deaths']
                    c['any_death'] += (d[0] + d[1]) > 0
                    c['deaths'] += d[0] + d[1]
                    c['kills'] += o['kills'][0] + o['kills'][1]
                    c['camp_deaths'] += o['camp_deaths'][0] + o['camp_deaths'][1]
                    k = o['kills']
                    c['init_more_kills'] += k[ini] > k[1 - ini]
                    c['init_fewer_kills'] += k[ini] < k[1 - ini]
                    c['gems_won'] += o['gems_won'][0] + o['gems_won'][1]
                    c['someone_left'] += (o['left'][0] + o['left'][1]) > 0
                    c['truncated'] += o['truncated']
                    if nA != nB:
                        big = 0 if nA > nB else 1
                        c['uneven'] += 1
                        c['big_more_kills'] += k[big] > k[1 - big]
                        c['big_fewer_kills'] += k[big] < k[1 - big]


def bucket(x, edges):
    lo = None
    for e in edges:
        if x <= e:
            return (lo, e)
        lo = e
    return (lo, None)


def bucket_label(b):
    lo, hi = b
    if lo is None:
        return f'<= {hi}'
    if hi is None or hi >= 10**9:
        return f'> {lo}'
    return f'{lo + 1}-{hi}' if hi != lo + 1 else f'{hi}'


def pct(a, b):
    return f'{100 * a / b:.1f}%' if b else '-'


def table(rows, head):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    out += ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows]
    return '\n'.join(out)


def kind_key(k):
    a, b = k.split('v')
    return (int(a) + int(b), int(a))


def write_report(path, A, args, secs, n_input, n_sel):
    L = [f'# Frame bank: {args.name}', '',
         f'Built {time.strftime("%Y-%m-%d %H:%M")} by `tools/combatlab/frames.py` in {secs:.0f} s. Lead {args.lead} '
         f'(state at the end of round first_damage - {args.lead}), fighter margin {args.margin}, zone margin {args.zone_margin}, '
         f'core window {args.core_window} rounds.', '',
         '## Totals', '',
         table([['replays in the inputs (bots matching)', n_input], ['games selected', n_sel], ['games processed', A.games],
                ['games with at least one frame', A.games_with], ['engagements', A.clusters], ['frames', A.frames],
                ['frames per game', f'{A.frames / A.games:.2f}' if A.games else '-'],
                ['frames with a late joiner (takes part after the core window, not a fighter)', pct(A.late, A.frames)],
                ['frames with a Cassi/Issac partner outside the fighters', pct(A.partner, A.frames)],
                ['frames with a ward in the zone', pct(A.wards, A.frames)],
                ['camp groups checked: event-derived hp off rounds.json group hp by over 5',
                 f'{A.checks["group_hp_mismatch"]} / {A.checks["group_hp"]}'],
                ['game errors', len(A.errors)]], ['', '']), '',
         '## Frames per game', '',
         table([[k if k < 40 else '40+', v] for k, v in sorted(A.per_game.items())], ['frames', 'games']), '',
         '## Kinds (alive fighter bodies, larger side first; Cassi and Issac count as two)', '',
         table([[k, v, pct(v, A.frames)] for k, v in sorted(A.kinds.items(), key=lambda kv: kind_key(kv[0]))], ['kind', 'frames', 'share']), '',
         '## Kinds by picks (Cassi and Issac count as one)', '',
         table([[k, v, pct(v, A.frames)] for k, v in sorted(A.pick_kinds.items(), key=lambda kv: kind_key(kv[0]))], ['kind', 'frames', 'share']), '',
         '## Skips', '',
         table([[k, v] for k, v in A.skips.most_common()], ['reason', 'engagements']), '',
         '## Champions among the fighters', '',
         table([[k, v, pct(v, A.frames)] for k, v in A.types.most_common()], ['champion', 'fighter slots', 'per frame']), '',
         '## Frame rounds', '',
         table([[bucket_label(k), v, pct(v, A.frames)] for k, v in sorted(A.rounds.items(), key=lambda kv: kv[0][1])], ['round', 'frames', 'share']), '',
         '## Fight length (rounds from first to last champion damage)', '',
         table([[bucket_label(k), v, pct(v, A.frames)] for k, v in sorted(A.lens.items(), key=lambda kv: kv[0][1])], ['rounds', 'frames', 'share']), '',
         '## Zone size (larger side of the box, tiles)', '',
         table([[bucket_label(k), v, pct(v, A.frames)] for k, v in sorted(A.zone.items(), key=lambda kv: kv[0][1])], ['tiles', 'frames', 'share']), '',
         '## Camps in the zone', '',
         table([[k if k < 5 else '5+', v, pct(v, A.frames)] for k, v in sorted(A.camps.items())], ['camps', 'frames', 'share']), '']
    for w in sorted(A.obs, key=int):
        rows = []
        for k, c in sorted(A.obs[w].items(), key=lambda kv: (kv[0] == 'all', kind_key(kv[0]) if kv[0] != 'all' else (0, 0))):
            n = c['n']
            rows.append([k, n, pct(c['any_death'], n), f'{c["deaths"] / n:.2f}', f'{c["kills"] / n:.2f}', pct(c['camp_deaths'], n),
                         pct(c['init_more_kills'], n), pct(c['init_fewer_kills'], n),
                         pct(c['big_more_kills'], c['uneven']) if c['uneven'] else '-',
                         pct(c['big_fewer_kills'], c['uneven']) if c['uneven'] else '-',
                         f'{c["gems_won"] / n:.1f}', pct(c['someone_left'], n), pct(c['truncated'], n)])
        L += [f'## Observed outcome in the next {w} rounds, by kind', '',
              'Among the fighters. `init +` / `init -`: the initiator\'s team got more / fewer kills; `big +` / `big -`: the larger '
              'side (uneven kinds) did; camp deaths per frame; gems taken by kills per frame; someone left: an alive fighter ends '
              'outside the zone; truncated: the game ended inside the window.', '',
              table(rows, ['kind', 'frames', 'any death', 'deaths', 'kills', 'camp deaths', 'init +', 'init -', 'big +', 'big -',
                           'gems by kills', 'someone left', 'truncated']), '']
    L += ['## Bots', '',
          table([[a, b, A.games_by_pair[(a, b)], v] for (a, b), v in A.bot_pairs.most_common()], ['team A', 'team B', 'games', 'frames']), '',
          table([[k, A.bots_team[0][k], A.bots_team[1][k]] for k in sorted(set(A.bots_team[0]) | set(A.bots_team[1]))],
                ['bot', 'frames as team A', 'frames as team B']), '']
    if A.errors:
        L += ['## Errors', '', '```', *[e.splitlines()[0] for e in A.errors[:20]], '```', '']
    Path(path).write_text('\n'.join(L))


# ---------------------------------------------------------------- main

def extract(files, cache, threads, log):
    cmd = ['node', str(ROOT / 'tools/replay/extract.mjs'), *files, '--out', str(cache), '--threads', str(threads)]
    with open(log, 'a') as f:
        return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT).returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inputs', nargs='+', help='batch dirs (with manifest.txt or results.json), or dirs holding them')
    ap.add_argument('--name', required=True)
    ap.add_argument('--out', help='output dir (default replays/combatlab/NAME)')
    ap.add_argument('--cache', default=str(ROOT / 'replays/combatlab/cache'), help='extract.mjs --out dir (shared by banks)')
    ap.add_argument('--games', type=int, default=0, help='games to sample over all batches, evenly per batch (0: all)')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--bots', default=DEFAULT_BOTS, help='regex both bots\' directory names must match')
    ap.add_argument('--copy', action='store_true', help='copy the selected replays under OUT/replays/ (batches get pruned)')
    ap.add_argument('--threads', type=int, default=16)
    ap.add_argument('--chunk', type=int, default=800, help='replays per extract.mjs call')
    ap.add_argument('--gz', action='store_true', help='write frames.jsonl.gz (about 5 KB a frame uncompressed)')
    ap.add_argument('--prune', action='store_true', help='delete each game\'s extraction once its frames are written')
    ap.add_argument('--lead', type=int, default=2, help='state at the end of round first_damage - LEAD (spec round = that + 1)')
    ap.add_argument('--margin', type=int, default=4, help='alive champions within this Chebyshev distance of a core champion are fighters')
    ap.add_argument('--zone-margin', type=int, default=3)
    ap.add_argument('--core-window', type=int, default=5, help='core: champions dealing or taking champion damage in the first N rounds')
    ap.add_argument('--respawn-window', type=int, default=20)
    ap.add_argument('--respawn-dist', type=int, default=8, help='skip if a champion respawning within the window has its spawn this near the zone')
    args = ap.parse_args()
    if args.threads > 16:
        sys.exit('at most 16 threads on the shared box')
    out = Path(args.out or ROOT / 'replays/combatlab' / args.name)
    out.mkdir(parents=True, exist_ok=True)
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    log = out / 'extract.log'
    t0 = time.time()

    bre = re.compile(args.bots)
    games = defaultdict(list)
    n_input = 0
    for b in find_batches(args.inputs):
        for rp, mpath, a, bb, batch in batch_games(b):
            if 'fish' in a.lower() or 'fish' in bb.lower() or not (bre.match(a) and bre.match(bb)):
                continue
            copy = out / 'replays' / batch / Path(rp).name
            if args.copy and copy.exists():
                rp = str(copy)
            elif not Path(rp).exists():
                continue
            n_input += 1
            games[batch].append({'replay': rp, 'map': mpath, 'bots': [a, bb], 'batch': batch})
    rng = random.Random(args.seed)
    sel = []
    if args.games:
        per = defaultdict(list)
        for b in sorted(games):
            lst = games[b][:]
            rng.shuffle(lst)
            per[b] = lst
        # Round-robin over batches until N games.
        while len(sel) < args.games and any(per.values()):
            for b in sorted(per):
                if per[b] and len(sel) < args.games:
                    sel.append(per[b].pop())
    else:
        sel = [x for b in sorted(games) for x in games[b]]
    print(f'{n_input} matching replays in {len(games)} batches; {len(sel)} selected', flush=True)

    if args.copy:
        kept = []
        for x in sel:
            dst = out / 'replays' / x['batch'] / Path(x['replay']).name
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                if not dst.exists():
                    shutil.copy2(x['replay'], dst)
            except FileNotFoundError:
                continue
            x['replay'] = str(dst)
            kept.append(x)
        sel = kept
        # Each copy dir gets a manifest, so it is an input of its own.
        by = defaultdict(dict)
        for x in sel:
            by[x['batch']][Path(x['replay']).name] = x
        for b, xs in by.items():
            man = out / 'replays' / b / 'manifest.txt'
            old = {}
            if man.exists():
                for line in man.read_text().splitlines():
                    f = line.split()
                    if len(f) >= 4:
                        old[Path(f[3]).name] = line
            for name, x in xs.items():
                old[name] = ' '.join([x['bots'][0], x['bots'][1], str(Path(x['map']).resolve()), str(Path(x['replay']).resolve())])
            man.write_text('\n'.join(old[k] for k in sorted(old)) + '\n')
    for x in sel:
        x['replay'] = rel(x['replay'])
        x['map'] = rel(x['map'])

    with open(out / 'games.txt', 'w') as f:
        for x in sel:
            f.write(f"{x['bots'][0]} {x['bots'][1]} {x['map']} {x['replay']}\n")

    params = dict(aparams.DEFAULTS)
    params.update(lead=args.lead, margin=args.margin, zone_margin=args.zone_margin, core_window=args.core_window,
                  respawn_window=args.respawn_window, respawn_dist=args.respawn_dist)
    A = Agg()
    seen = set()
    frames_path = out / ('frames.jsonl.gz' if args.gz else 'frames.jsonl')
    tmp = out / (frames_path.name + '.part')
    opener = (lambda p: gzip.open(p, 'wt', compresslevel=6)) if args.gz else (lambda p: open(p, 'w'))
    with opener(tmp) as fo, ProcessPoolExecutor(max_workers=args.threads) as pool:
        for k in range(0, len(sel), args.chunk):
            chunk = sel[k:k + args.chunk]
            todo = []
            for x in chunk:
                try:
                    h = sha16(ROOT / x['replay'])
                except FileNotFoundError:
                    A.skips['replay_missing'] += 1
                    continue
                if h in seen:
                    A.skips['duplicate_game'] += 1
                    continue
                seen.add(h)
                todo.append((h, x))
            need = [str(ROOT / x['replay']) for h, x in todo if not (cache / h / 'meta.json').exists()]
            if need:
                extract(need, cache, args.threads, log)
            futs = {}
            for h, x in todo:
                if not (cache / h / 'meta.json').exists():
                    A.skips['extract_failed'] += 1
                    continue
                futs[pool.submit(process_game, (str(cache), h, x, params))] = x
            for f in as_completed(futs):
                res = f.result()
                for line in res['lines']:
                    fo.write(line + '\n')
                A.add(res, futs[f])
                if args.prune:
                    shutil.rmtree(cache / res['dir'], ignore_errors=True)
            fo.flush()
            print(f'[{min(k + args.chunk, len(sel))}/{len(sel)}] games {A.games}, frames {A.frames}, {time.time() - t0:.0f} s', flush=True)
    tmp.replace(frames_path)
    write_report(out / 'report.md', A, args, time.time() - t0, n_input, len(sel))
    for e in A.errors[:5]:
        print(e, file=sys.stderr)
    print(f'{A.frames} frames from {A.games} games -> {rel(frames_path)}; report {rel(out / "report.md")}')


if __name__ == '__main__':
    main()
