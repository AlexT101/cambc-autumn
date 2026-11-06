"""Behavioural statistics of the side in "Fish's role" of a scorecard dataset (common.py), computed the
same way on Fish's ladder replays and on local games.

  py tools/fish/scorecard/metrics.py DATASET [--jobs 8] [--force]  ->  replays/fish-scorecard/DATASET/metrics.json

Every statistic is a flat counter key, summed over games, so per-game counters allow a bootstrap:
  NAME#k / NAME#n   a rate (k of n opportunities)
  NAME#s / NAME#n   a mean
  NAME@v            a histogram (a median is read from it)
Sources, per game: the observer caches (obs.mjs, team_decode.mjs; descriptive statistics), the actor
perspectives (extract.mjs; rule inputs are the actor's own view) and the Fish studies' row files
(engage_rows.py, combat_data.py, combat_tiles.py). Definitions follow research/fish-2026-11-05/FISH_MODEL.md;
the section numbers in the comments are its sections. What each name means: metric_defs.py.
"""
import argparse
import collections
import gzip
import json
import math
import multiprocessing as mp
from pathlib import Path

from common import ROOT, entries, parts

import combat_rules as R
import farm3_common
import farm3_describe
from breadth import RANGED, dist, spawn, xy
from combat_common import shield
from engage_common import free
from farm3_common import (ALIVE, CAMP_NAMES, EARNED, ID, NAMES, X, Y, Game, cheb, payouts)

BASE_HP = {0: 1200, 1: 1000, 2: 900, 3: 600, 4: 900, 5: 650, 6: 700, 7: 1200, 8: 700, 9: 900, 10: 1000, 11: 900, 12: 1000}
CAMP_RANGE = {0: 3, 1: 4, 4: 5, 5: 4}  # fighters only; clusters (2, 3) never attack
NB = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def load(path):
    with gzip.open(path) as f:
        return json.load(f)


def rate(C, key, hit, n=1):
    C[key + '#n'] += n; C[key + '#k'] += int(hit)


def mean(C, key, v):
    C[key + '#n'] += 1; C[key + '#s'] += v


def hist(C, key, v):
    C[f'{key}@{v}'] += 1


# ---------------------------------------------------------------- observer pass (sections 6, 7.1, 7.5, 3.2, outcome)

def pass_obs(job):
    part, e = job
    key = e['sha256'][:16]
    farm3_describe.OBS = Path(part['obs']); farm3_common.TEAM = Path(part['team'])
    obs = load(Path(part['obs']) / f'{key}.json.gz')
    C = collections.Counter()
    G = Game(obs)
    side = G.side
    fish = set(G.fish)
    st = farm3_describe.game_stats((part['part'], e))
    if st is None:
        return key, None
    # 6. Turn budget.
    for (name, a), v in st['act'].items():
        C[f'act:{name}:{a}'] += v
        C[f'act:{name}'] += v
    # 7.1 Space.
    sp = st['spread']
    C['side_own#n'] += sp['off']; C['side_own#k'] += sp['side', 1]
    C['side_mid#n'] += sp['off']; C['side_mid#k'] += sp['side', 0]
    C['side_enemy#n'] += sp['off']; C['side_enemy#k'] += sp['side', -1]
    C['ally_within4#n'] += sp['with_other']; C['ally_within4#k'] += sp['ally<=4']
    for d in st['nearest']:
        hist(C, 'nearest_ally', min(d, 40))
    capt = st['capt']
    for s_ in ('own', 'middle', 'enemy'):
        C[f'pay_{s_}#k'] += capt['fish', s_]
        C[f'pay_{s_}#n'] += sum(capt['fish', q] for q in ('own', 'middle', 'enemy'))
    for (k0, *rest), v in capt.items():
        if k0 == 'fish_recipients':
            C['pay_single#n'] += v; C['pay_single#k'] += v if rest[0] == 1 else 0
    for (who, kind, *rest), v in st['clear'].items():
        if who == 'fish':
            C[f'solo_clear:{kind}#n'] += v; C[f'solo_clear:{kind}#k'] += v if rest[0] == 'solo' else 0
    # Team spacing: alive off-spawn Fish bodies each round.
    for snap in obs['rounds']:
        pos = [(c[X], c[Y]) for c in snap['ch'] if c[ID] in fish and c[ALIVE] and (c[X], c[Y]) not in G.own_spawn]
        if len(pos) >= 2:
            cx = sum(p[0] for p in pos) / len(pos); cy = sum(p[1] for p in pos) / len(pos)
            spread = sum(max(abs(p[0] - cx), abs(p[1] - cy)) for p in pos) / len(pos)
            pair = [cheb(a, b) for i, a in enumerate(pos) for b in pos[i + 1:]]
            mean(C, 'centroid_spread', spread); mean(C, 'pair_dist', sum(pair) / len(pair))
            hist(C, 'centroid_spread_h', min(round(spread), 40))
            rate(C, 'team_within8', max(max(abs(p[0] - cx), abs(p[1] - cy)) for p in pos) <= 8)
    # 7.1 Payouts per champion.
    rounds = obs['finalRound'] or len(obs['rounds'])
    pays = [p for p in payouts(G) if p['team'] == side]
    got = collections.defaultdict(list)
    for p in pays:
        for i in p['recipients']:
            if i in fish:
                got[i].append(p['group'])
    for i in G.fish:
        nm = NAMES[G.type[i]]
        v = len(got[i]) * 1000 / max(rounds, 1)
        for k in (nm, 'all'):
            hist(C, f'pay1k:{k}', round(v, 1)); mean(C, f'pay1k_mean:{k}', v)
            mean(C, f'pay_groups:{k}', len(set(got[i])))
    # 7.5 Waking alone.
    T = farm3_common.team_rounds(key)
    snaps = {s['r']: s for s in obs['rounds']}
    for r, Rr in sorted(T.items()):
        cp = Rr.get('cp'); sn = snaps.get(r)
        if not cp or not sn:
            continue
        awake = {k for k, _ in cp['awake']}
        pos = {c[0]: (c[2], c[3]) for c in cp['ch'] if c[1]}
        asleep = {g['id'] for g in G.groups if any(sn['hp'][k] > 0 for k in g['members']) and not any(k in awake for k in g['members'])}
        for t in Rr['turns']:
            for a in t['acts']:
                if len(a) > 7 and a[6] == 2 and a[7] in G.group_of_camp:
                    gid = G.group_of_camp[a[7]]
                    if gid not in asleep:
                        continue
                    asleep.discard(gid)
                    if t['id'] in fish:
                        # As team_campfight.py: no other Fish body within 4 of any of the group's tiles.
                        tiles = G.groups[gid]['tiles']
                        alone = not any(j != t['id'] and j in pos and min(cheb(pos[j], q) for q in tiles) <= 4 for j in fish)
                        kind = CAMP_NAMES[G.groups[gid]['big']]
                        rate(C, 'wake_alone', alone); rate(C, f'wake_alone:{kind}', alone)
            e_ = t.get('end')
            if e_:
                if e_[1]:
                    pos[t['id']] = (e_[2], e_[3])
                else:
                    pos.pop(t['id'], None)
    # 3.2 Shopping, economy; outcome.
    ems = obs['emblems']
    for s in obs['champStats']:
        if s['team'] != side:
            continue
        nm = NAMES[s['type']]
        for k in (nm, 'all'):
            mean(C, f'spent:{k}', s['spentGold']); mean(C, f'shards:{k}', s['shards'])
            first = ems.get(str(s['id']))
            rate(C, f'has_emblem:{k}', bool(first))
            if first:
                hist(C, f'first_emblem:{k}', first[0][0] // 10 * 10)
    mine = [s for s in obs['champStats'] if s['team'] == side]
    C['games'] += 1
    rate(C, 'win', obs['winner'] == side)
    mean(C, 'final_round', rounds); hist(C, 'final_round_h', rounds // 50 * 50)
    rate(C, 'reach_2000', rounds >= 2000)
    mean(C, 'kills', sum(s['kills'] for s in mine)); mean(C, 'deaths', sum(s['deaths'] for s in mine))
    mean(C, 'camp_deaths', sum(1 for _, i in obs['campDeaths'] if i in fish))
    C['camp_death_share#n'] += sum(s['deaths'] for s in mine); C['camp_death_share#k'] += sum(1 for _, i in obs['campDeaths'] if i in fish)
    mean(C, 'champ_damage', sum(s['championDamageDone'] for s in mine))
    for R_ in (300, 600):
        sn = snaps.get(R_)
        gems = sn['sub'][side] if sn else obs['finalGems'][side]
        gold = sum(c[EARNED] for c in sn['ch'] if c[ID] in fish) if sn else sum(s['earnedGold'] for s in mine)
        mean(C, f'gems{R_}', gems); mean(C, f'gold{R_}', gold)
        mean(C, f'gem_lead{R_}', gems - (sn['sub'][1 - side] if sn else obs['finalGems'][1 - side]))
    return key, C


# ---------------------------------------------------------------- engage rows pass (sections 8.1-8.3, 9, 12)

def pass_engage(job):
    part, line = job
    g = json.loads(line)
    key = g['game']
    md = load(Path(part['obs']) / f'{key}.json.gz')['mapData']
    side = g['side']
    block = set(map(tuple, md['walls'] + md['holes'] + md['altars']))
    s = md['spawnA']
    sp = {(x, y) for y in range(s['minY'], s['maxY']) for x in range(s['minX'], s['maxX'])}
    m_ = dict(width=md['width'], height=md['height'], symmetry=md['symmetry'], spawnA=s)
    ehome = spawn(m_, 1 - side)
    home = spawn(m_, side)
    block |= ehome
    bush = set(map(tuple, md['bushes']))
    W, H = md['width'], md['height']
    names = {c['id']: NAMES[c['type']] for c in g['roster']}
    T_home = lambda y: (y['ex'], y['ey']) not in home
    C = collections.Counter()
    for aid, rows in g['actors'].items():
        nm = names[int(aid)]
        byr = {r['r']: r for r in rows}
        last_ward = None
        for i, r in enumerate(rows):
            x, y = r.get('x'), r.get('y')
            if not (x and y):
                continue
            rr = r['r']
            prev = byr.get(rr - 1)
            px, py = (prev.get('x'), prev.get('y')) if prev else (None, None)
            fr = free(x)
            h = x['hp'] / x['mhp']
            rate(C, 'enemy_in_sight', bool(x['E'])); rate(C, f'enemy_in_sight:{nm}', bool(x['E']))
            # 8.1 Prepared recall: started at the end of nearly every turn off spawn, cancelled next turn.
            if fr:
                rate(C, 'tribute_start', y['submit'] and y['ech'] == 2)
                # Turns that could end in a fresh recall: no channel left running, ending off spawn.
                if (x['ch'] == 0 or y['cancel']) and y['ech'] in (0, 1) and T_home(y):
                    rate(C, 'recall_start', y['recall'])
            if fr and y['recall'] and y['ech'] == 1:
                n1 = byr.get(rr + 1)
                if n1 and n1.get('x') and n1.get('y') and n1['x']['ch'] == 1 and not n1['x']['stn']:
                    rate(C, 'recall_survive', not n1['y']['cancel'])
            # 8.2 Timer-1 keep rule and the home gate at completed recalls.
            if x['ch'] == 1 and x['ct'] == 1 and not x['stn'] and not x['home']:
                keep = not y['cancel']
                gate = h <= 0.63 or x['gold'] >= 30
                # Capturing: h<=0.40. On a respawning group's tile (mostly its payout round): h<=0.63.
                # Payout-round proxy: the previous turn stood on the same group while it was empty.
                payout = x['gst'] == 3 and px is not None and px.get('gst') == 2 and px.get('grp') == x['grp']
                pred = h <= 0.40 if x['gst'] == 2 else h <= 0.63 if payout else gate
                rate(C, 'keep_rule', pred == keep); rate(C, 'keep_rate', keep)
                if keep:
                    rate(C, 'home_gate', gate)
                    rate(C, 'home_reason_hurt', h <= 0.63)
            # 8.3 Tributed bags.
            if y['submit'] and y['ech'] == 2:
                for k in (nm, 'all'):
                    hist(C, f'trib_bag:{k}', x['gems'])
            ready = last_ward is None or rr - last_ward >= 10
            if y['ward']:
                last_ward = rr
            if not fr:
                continue
            # 9. Momentum at range 4-8 (free rows: no camp hit, not on an empty group).
            if x['E'] and 4 <= x['d1'] <= 8 and not y['camp'] and x['gst'] != 2:
                E = x['E'][0]
                close = y['ed'][str(E['id'])] < x['d1']
                rate(C, 'range_close', close)
                if px and py:
                    v = (py['ex'] - px['x'], py['ey'] - px['y'])
                    pred = v != (0, 0) and cheb((x['x'] + v[0], x['y'] + v[1]), (E['x'], E['y'])) < x['d1']
                    rate(C, 'momentum', pred == close)
            # 9. Camp hitting continues by nearest enemy distance (last turn hit a camp, awake camp in reach).
            if py and py['camp'] and x['aggro']:
                d1 = x['d1'] if x['E'] else None
                b = 'none' if d1 is None else 'far' if d1 > 8 else 'd1-3' if d1 <= 3 else f'd{d1}'
                b2 = 'none' if d1 is None else 'd>4' if d1 > 4 else 'd<=4'
                rate(C, f'campcont:{b}', bool(y['camp'])); rate(C, f'campcont2:{b2}', bool(y['camp']))
                if d1 is not None:
                    rate(C, 'campcont_rule', (d1 > 4) == bool(y['camp']))
            # 10. Contact: an enemy within 3 at turn start.
            if x['E'] and x['d1'] <= 3:
                rate(C, 'contact_hit', bool(y['hitc'])); rate(C, f'contact_hit:{nm}', bool(y['hitc']))
            # 12. Ward rate with the ward ready (10-round recharge, from the actor's own placements).
            if ready:
                b = 'contact' if x['E'] and x['d1'] <= 5 else 'enemy' if x['E'] else 'none'
                rate(C, f'ward_rate:{b}', y['ward'])
            # 12. Bush tie-break among equal-progress steps toward the tile three turns later.
            r3 = byr.get(rr + 3)
            if y['moves'] == 1 and not y['dash'] and r3 and r3.get('x'):
                p = (x['x'], x['y']); G_ = (r3['x']['x'], r3['x']['y']); e = (y['ex'], y['ey'])
                dg = cheb(p, G_)
                if dg >= 2:
                    P = [(p[0] + a, p[1] + b) for a, b in NB]
                    occ = {(q['x'], q['y']) for q in x['E'] + x['A']}
                    P = [q for q in P if 0 <= q[0] < W and 0 <= q[1] < H and q not in block and q not in occ and cheb(q, G_) == dg - 1]
                    nb = sum(q in bush for q in P)
                    if e in P and 0 < nb < len(P):
                        b = 'contact' if x['E'] and x['d1'] <= 5 else 'enemy' if x['E'] else 'none'
                        rate(C, f'bush_tie:{b}', e in bush); mean(C, f'bush_tie_base:{b}', nb / len(P))
    return key, C


# ---------------------------------------------------------------- actor pass (sections 5, 10.4, 12)

def rank_of(roster, side):
    mine = sorted((c for c in roster if c['team'] == side),
                  key=lambda c: (-BASE_HP[c['type']], 9.5 if c['type'] == 12 else c['type'], c['id']))
    return {c['id']: 2 + k for k, c in enumerate(mine)}, len(mine)


def band(me):
    h = min(1.0, (me['hp'] + shield(me)) / me['maxHp'])
    if me.get('gems', 0) > 0:
        h *= 0.65
    return max(0, math.floor(4 * (1 - h)))


def predicted_mode(ctx):
    me = ctx['me']
    if not me.get('alive') or 'x' not in me:
        return 'dead'
    p = xy(me)
    reach = lambda c: 3 if c['type'] in RANGED else 2
    es = [e for e in ctx['enemies'] if e.get('alive') and 'x' in e]
    for c in ctx['camps']:
        rg = CAMP_RANGE.get(c['type'])
        if rg is None or c['hp'] <= 0 or not c['awake'] or dist(p, xy(c)) > rg:
            continue
        members = [q for q in ctx['camps'] if q['group'] == c['group'] and q['hp'] > 0 and q['awake'] and q['type'] in CAMP_RANGE]
        if any(dist(xy(e), xy(q)) <= CAMP_RANGE.get(q['type'], 0) + 1 for e in es for q in members):
            return 'late'
    allies = [a for a in ctx['allies'] if a.get('alive') and 'x' in a]
    for e in es:
        if dist(xy(e), p) <= max(reach(e), reach(me)) or any(dist(xy(e), xy(a)) <= reach(e) for a in allies):
            return 'contact'
    return 'quiet'


def actual_mode(v, rank, n, alive=True, written=True):
    if v == 0 and not written:
        return 'unset', None
    r = (-v) % (n + 1)
    r = r if r else n + 1
    if r != rank:
        return 'other', None
    L = (-v - r) // (n + 1)
    if L == -1 and not alive:
        return 'dead', L
    if -5 <= L <= -1:
        return 'early', L
    if abs(L) >= 50:
        return 'contact', L
    if 5 <= L <= 8:
        return 'late', L
    if 0 <= L <= 3:
        return 'quiet', L
    return 'other', L


def pass_actor(job):
    part, e = job
    key = e['sha256'][:16]
    g = load(Path(part['actor']) / f'{key}.json.gz')
    side = g['side']
    m = g['map']
    bush = set(map(tuple, m['bushes']))
    ranks, n = rank_of(g['roster'], side)
    names = {c['id']: NAMES[c['type']] for c in g['roster']}
    C = collections.Counter()
    wrote = set()
    for t in g['turns']:
        s = t['start']; me = s['me']; aid = t['id']
        writes = [a for a in t['actions'] if a['kind'] == 'Set priority']
        # As team_rows.py: the view just before the write, else the turn end.
        ctx = (writes[-1].get('before') or s) if writes else (t.get('end') or s)
        v = writes[-1]['value'] if writes else me.get('priority', 0)
        if writes:
            wrote.add(aid)
        for w in writes:
            cur = (w.get('before') or s)['me'].get('priority', 0)
            rate(C, 'prio_write_repeat', w['value'] == cur)
        am, L = actual_mode(v, ranks[aid], n, bool(me.get('alive')), aid in wrote)
        if not me.get('alive'):
            rate(C, 'prio_dead_ok', am == 'dead')
            continue
        if any(b['type'] == 1 for b in me.get('buffs', [])):
            continue
        pm = predicted_mode(ctx)
        hist(C, 'prio_mode', am)
        rate(C, 'prio_rank_ok', am not in ('other', 'unset'))
        rate(C, 'prio_mode_agree', pm == am)
        if pm == 'quiet':
            rate(C, 'prio_quiet_exact', v == -ranks[aid] - (n + 1) * band(ctx['me']))
        # 10.4 Basic attack targets; 12 wards.
        pos = xy(me) if 'x' in me else None
        for a in t['actions']:
            if a['kind'] == 'Move':
                pos = tuple(a['to'])
            if a['kind'] == 'Attack' and a.get('before'):
                b = a['before']; bm = b['me']
                if 'x' not in bm:
                    continue
                rng = 3 if bm['type'] in RANGED else 1
                cands = [q for q in b['enemies'] if q.get('alive') and 'x' in q and dist(xy(q), xy(bm)) <= rng]
                tgt = [q for q in cands if [q['x'], q['y']] == a['to']]
                if cands:
                    rate(C, 'basic_champ_first', bool(tgt))
                if len(cands) >= 2 and tgt:
                    best = min(cands, key=lambda q: (q['hp'] + shield(q), q['id']))
                    rate(C, 'basic_minehp', tgt[0]['id'] == best['id'])
            elif a['kind'] == 'Place ward':
                rate(C, 'ward_bush', tuple(a['to']) in bush)
                if pos is not None:
                    rate(C, 'ward_d2', dist(pos, a['to']) == 2)
        rate(C, 'ward_per_turn', any(a['kind'] == 'Place ward' for a in t['actions']))
        rate(C, f'ward_per_turn:{names[aid]}', any(a['kind'] == 'Place ward' for a in t['actions']))
    return key, C


# ---------------------------------------------------------------- combat rows pass (sections 10.1-10.6)

def pass_combat(part):
    per = collections.defaultdict(collections.Counter)
    last = {}
    for line in gzip.open(part['combat'], 'rt'):
        r = json.loads(line); x = r['x']; y = r['y']; C = per[r['game']]
        prev = last.get((r['game'], r['actor']))
        last[(r['game'], r['actor'])] = r
        prev_y = prev['y'] if prev and prev['round'] == r['round'] - 1 else None
        e = R.chase_opportunity(x, prev_y)
        if e is not None:
            rate(C, 'chase_rule', R.chase(x, e) == R.chased(y, e)); rate(C, 'chase_rate', R.chased(y, e))
        walks = y['moves'] > 0
        s = R.damage_spell_opportunity(x)
        if s is not None and not walks and not any(c['slot'] != s for c in y['casts']):
            rate(C, 'spell_when_still', s in y['cast_champ'])
        if s is not None:
            rate(C, 'stand_to_cast', not walks)
        if R.hor_shield_opportunity(x) and not any(c['ability'] == 6 for c in y['casts']):
            rate(C, 'hor_shield_rule', R.hor_shield(x) == any(c['slot'] == 0 for c in y['casts']))
        rs = R.reset_opportunity(x, y)
        if rs is not None and not any(c['slot'] != rs for c in y['casts']):
            rate(C, 'reset_use', any(c['slot'] == rs for c in y['casts']))
        if x['type'] == 3 and not x['at_home'] and x['channel'] <= 1 and x['cd'][0] != 0 and x['cd'][1] == 0 and \
                any(q['d'] <= 4 and q['type'] != 7 and q['stun'] <= 0 for q in x['enemies']):
            rate(C, 'cassi_stun_on_cd', 1 in y['cast_champ'])
    for line in gzip.open(part['tiles'], 'rt'):
        r = json.loads(line); x = r['x']; C = per[r['game']]
        c = R.contexts(x)
        if c is None:
            continue
        ctx, tiles = c
        actual = R.engaged(x, r['y'])
        _, pred = R.engage(x, True)
        rate(C, 'engage_rule', pred == actual); rate(C, f'engage_rule:{ctx}', pred == actual)
        rate(C, f'engage_rate:{ctx}', actual)
        if any(q['kill'] for q in tiles):
            rate(C, 'kill_override', actual)
    return dict(per)


# ---------------------------------------------------------------- driver

def compute(name, jobs):
    per_game = collections.defaultdict(collections.Counter)
    ps = parts(name)
    with mp.Pool(jobs) as pool:
        for p in ps:
            es = entries(p)
            tag = lambda k: f"{p['part']}:{k}"
            for k, C in pool.imap_unordered(pass_obs, [(p, e) for e in es], chunksize=2):
                if C is not None:
                    per_game[tag(k)].update(C)
            ok = {e['sha256'][:16] for e in es}
            lines = ((p, l) for l in gzip.open(p['engage'], 'rt'))
            for k, C in pool.imap_unordered(pass_engage, lines, chunksize=2):
                if k in ok:
                    per_game[tag(k)].update(C)
            for k, C in pool.imap_unordered(pass_actor, [(p, e) for e in es], chunksize=2):
                per_game[tag(k)].update(C)
            print(f"  {p['dataset']}/{p['part']}: {len(es)} games", flush=True)
        for p, per in zip(ps, pool.map(pass_combat, ps)):
            for k, C in per.items():
                per_game[f"{p['part']}:{k}"].update(C)
    total = collections.Counter()
    for C in per_game.values():
        total.update(C)
    return dict(dataset=name, parts=[p['part'] for p in ps], games=total['games'], total=dict(total),
                per_game={k: dict(v) for k, v in per_game.items()})


def path_of(name):
    return ROOT / name.replace(',', '+') / 'metrics.json'


def get(name, jobs=8, force=False):
    out = path_of(name)
    if out.exists() and not force:
        return json.loads(out.read_text())
    res = compute(name, jobs)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, separators=(',', ':')))
    return res


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('dataset'); ap.add_argument('--jobs', type=int, default=8); ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    r = get(a.dataset, a.jobs, a.force)
    print(a.dataset, r['games'], 'games ->', path_of(a.dataset))
