"""Per-turn priority rows (v2 adds camp-contest features) for the turn-order study (TEAM.md section 1).

One row per completed Fish turn: the priority in effect next round (last write, else the
current one; Fish writes only on change), its decoded rank/level/mode, and causal features
from the actor's own view at the decision point (just before the write, else turn end).
Observer-only columns are prefixed `obs_` and are diagnostics, never rule inputs.

    python3 tools/fish/team_rows.py OUT.jsonl.gz [--cohorts model,confirm,...]
"""
import argparse
import gzip
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import breadth  # noqa: E402
from combat_common import ehp, one_turn_damage, shield  # noqa: E402
from team_common import (ALIVE, CAMP_RANGE, HELD_OUT, ID, RANGED, X, Y, band, cheb, decode_level, entries,  # noqa: E402
                         load_actor, load_team, mode_of, spawn_tiles, starts)


def reach(c):
    # Basic-attack reach next turn: melee walk + attack, ranged attack (a ranged walk spends it).
    return 3 if c['type'] in RANGED else 2


def rows_for(cohort, cache, entry):
    key = entry['sha256'][:16]
    a = load_actor(cache, key)
    g = load_team(key)
    side = a['side']
    team = {r['id']: r['team'] for r in a['roster']}
    n = sum(1 for r in a['roster'] if r['team'] == side)
    sp = spawn_tiles(a['map'], side)
    _, tile2g = breadth.static_groups(a['map'])
    # Observer positions at each Fish turn end (diagnostic).
    obs = {}
    pos = {}
    for R in g['rounds']:
        if R['cp']:
            for c in R['cp']['ch']:
                pos[c[ID]] = (c[X], c[Y], c[ALIVE])
        for t in R['turns']:
            if t.get('end'):
                pos[t['id']] = (t['end'][X], t['end'][Y], t['end'][ALIVE])
            if team[t['id']] == side:
                obs[(R['r'], t['id'])] = dict(pos)
    last_seen, last_hurt, prev_hp, prev_mode = {}, {}, {}, {}
    out = []
    for t in a['turns']:
        aid, rnd = t['id'], t['round']
        start = t['start']['me']
        if aid in prev_hp and start.get('alive') and start['hp'] < prev_hp[aid] - 1e-6:
            last_hurt[aid] = rnd
        writes = [x for x in t['actions'] if x['kind'] == 'Set priority']
        ctx = writes[-1]['before'] if writes else t.get('end')
        for c in [t['start']] + [x['before'] for x in t['actions'] if 'before' in x]:
            if any('x' in e for e in c['enemies']):
                last_seen[aid] = rnd
        if ctx is None:
            continue
        nextp = writes[-1]['value'] if writes else start['priority']
        rank, L = decode_level(nextp, n)
        m = ctx['me']
        row = dict(game=key, cohort=cohort, held_out=cohort in HELD_OUT, round=rnd, id=aid, type=m['type'], n=n,
                   value=nextp, wrote=bool(writes), rank=rank, L=L, alive=m['alive'],
                   fish_starts_next=starts(side, rnd + 1))
        if m['alive']:
            sh = shield(m)
            b = band(m['hp'], sh, m['maxHp'], m['gems'])
            vis = [e for e in ctx['enemies'] if 'x' in e]
            U = [m] + [q for q in ctx['allies'] if 'x' in q]
            dself = min((cheb((e['x'], e['y']), (m['x'], m['y'])) for e in vis), default=99)
            dteam = min((cheb((e['x'], e['y']), (u['x'], u['y'])) for e in vis for u in U), default=99)
            inreach = any(cheb((e['x'], e['y']), (u['x'], u['y'])) <= reach(e) for e in vis for u in U) or \
                any(cheb((e['x'], e['y']), (m['x'], m['y'])) <= reach(m) for e in vis)
            threat = sum(one_turn_damage(e, cheb((e['x'], e['y']), (m['x'], m['y']))) for e in vis)
            ally_modes = [mode_of(decode_level(q['priority'], n)[1]) for q in ctx['allies'] if 'priority' in q and q['priority'] != 0]
            # Camps in Fish's view: visible, awake, alive, with a range (not clusters).
            awake = [c for c in ctx['camps'] if c.get('awake') and c['hp'] > 0 and CAMP_RANGE[c['type']] > 0]
            mine = {c['group'] for c in awake if cheb((c['x'], c['y']), (m['x'], m['y'])) <= CAMP_RANGE[c['type']]}
            gm = [c for c in awake if c['group'] in mine]
            contest = {k: any(cheb((e['x'], e['y']), (c['x'], c['y'])) <= CAMP_RANGE[c['type']] + k for e in vis for c in gm) for k in (0, 1, 2)}
            p = obs.get((rnd, aid), {})
            fish = [v for i, v in p.items() if team[i] == side and v[2] and v[0] >= 0]
            foes = [v for i, v in p.items() if team[i] != side and v[2] and v[0] >= 0]
            row.update(band=b, mode=mode_of(L, b), hpf=m['hp'] / m['maxHp'], ehp=ehp(m), gems=m['gems'],
                       stun=max((x['timer'] for x in m['buffs'] if x['type'] == 1), default=-1),
                       chan=m.get('channelType', 0), on_spawn=(m['x'], m['y']) in sp, on_camp_tile=(m['x'], m['y']) in tile2g,
                       n_vis=len(vis), n_allies_vis=len(U) - 1, dself=dself, dteam=dteam, inreach=inreach,
                       threat=threat, threat_ratio=threat / max(1.0, ehp(m)),
                       since_seen=rnd - last_seen.get(aid, -999), since_hurt=rnd - last_hurt.get(aid, -999),
                       ally_late=sum(x == 'late' for x in ally_modes), ally_contact=sum(x.startswith('contact') for x in ally_modes),
                       ally_quiet=sum(x == 'quiet' for x in ally_modes), prev_mode=prev_mode.get(aid),
                       camp_self=bool(mine), contest0=contest[0], contest1=contest[1], contest2=contest[2],
                       enemy_in_any_camp_range=any(cheb((e['x'], e['y']), (c['x'], c['y'])) <= CAMP_RANGE[c['type']] for e in vis for c in awake),
                       obs_dteam=min((cheb(f, e) for f in fish for e in foes), default=99),
                       obs_dself=min((cheb((m['x'], m['y']), e) for e in foes), default=99))
            prev_mode[aid] = row['mode']
        else:
            row.update(mode=mode_of(L))
        if t.get('end') and t['end']['me'].get('alive'):
            prev_hp[aid] = t['end']['me']['hp']
        out.append(row)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--cohorts', default='model,confirm,third,fourth,fifth,sixth')
    a = p.parse_args()
    if Path(a.out).exists():
        raise SystemExit(f'refusing to overwrite {a.out}')
    want = set(a.cohorts.split(','))
    n = 0
    with gzip.open(a.out + '.tmp', 'wt') as f:
        for cohort, cache, e in entries():
            if cohort not in want:
                continue
            for r in rows_for(cohort, cache, e):
                f.write(json.dumps(r, separators=(',', ':')) + '\n')
                n += 1
    Path(a.out + '.tmp').rename(a.out)
    print(n, 'rows ->', a.out)


if __name__ == '__main__':
    main()
