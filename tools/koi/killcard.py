"""How a team kills its opponent: lethality metrics from research/FISH.md cause 1, for the selected team (killer) and
its opponent (victim) in the same games.

  py tools/koi/killcard.py replays/scrims/20261018-231915 replays/scrims/20261019-074736 ... --team fish
  py tools/koi/killcard.py "replays/koi2-ab/eng-vs-baselines_hecate-v1-*" --team koi
  py tools/koi/killcard.py --scrims            # the 60 distinct Fish-vs-hecate scrim games (FISH.md)

Sources are extracted replay dirs (globs allowed); --team is a substring of the killer team's name. Copies of a game
count once. Definitions:
- burst death: the victim had at least 90% of its max hp at the start of the round it died in (or of the round
  before, for 'two-round').
- unseen killer: the killer was in none of the victim's start-of-turn `sees` in the death round and the 3 before.
- from a bush: the attacker's tile was a bush when it dealt the damage.
- carrier: 40+ gems at death.
- holds broken: the victim team's capture holds reset before payout while a killer-team champion was within 4 of
  the group's tiles (contested or not).
- steals: captures by a team that dealt under half of the group's camp damage since it last respawned.
"""
import argparse, collections, glob, json, os, statistics, sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / 'replay'))
from analysis.data import Game, load_index, ROOT, chebyshev as cheb  # noqa: E402

SCRIMS = ['replays/scrims/20261018-231915', 'replays/scrims/20261019-074736', 'replays/scrims/20261019-143241',
          'replays/scrims/20261019-152704', 'replays/scrims/20261019-153559', 'replays/scrims/20261019-154258']


def process(job):
    d, S = job
    g = Game(d)
    O = 1 - S
    m = g.map
    tm = g.team_of; nm = g.name_of
    C = collections.Counter()
    C['games'] = 1; C['won'] = int(g.winner == S); C['rounds'] = g.n_rounds
    lst = collections.defaultdict(list)
    lst['rounds'].append(g.n_rounds)
    chs = {c['id']: g.ch(c['id']) for c in g.champs}
    bushes = m.bushes
    camp_group = {c['id']: c['group'] for c in m.camps}
    gtiles = {gr['id']: [tuple(t) for t in gr['tiles']] for gr in m.groups}
    gdmg = collections.defaultdict(lambda: [0.0, 0.0])
    pos = {}
    for c in g.champs:
        pos[c['id']] = (chs[c['id']]['x'][0], chs[c['id']]['y'][0])
    last_hit = {}
    round_dmg = collections.defaultdict(float)
    stunned_at = collections.defaultdict(list)
    holds = {}

    def sees(v, r):
        a = chs[v]['sees']; i = r - 1
        return set(a[i]) if 0 <= i < len(a) else set()

    def hp_start(v, r):
        a = chs[v]['hp']; mx = chs[v]['maxHp']; i = r - 2
        if i < 0: return 1.0
        if i >= len(a): i = len(a) - 1
        return (a[i] or 0) / max(1, mx[i] or 1)

    for e in g.events:
        k = e['k']; r = e['r']
        if k in ('move', 'recall_end', 'teleport_end'):
            pos[e['a']] = tuple(e['to'])
        elif k == 'respawn':
            pos[e['a']] = tuple(e['at'])
        if k in ('attack', 'cast'):
            a = e['a']
            if e.get('moved'): pos[a] = tuple(e['moved'])
            f = tuple(e['f'])
            for camp, amt in e.get('cdmg', []):
                gr = camp_group.get(camp)
                if gr is not None: gdmg[gr][tm[a]] += amt
            hit = [(v, amt) for v, amt in e.get('dmg', []) if v in tm and tm[v] != tm[a] and amt > 0]
            if e.get('stun'):
                for v in e['stun']:
                    if v in tm and tm[v] != tm[a]: stunned_at[v].append(r)
            if hit or (e.get('stun') and any(v in tm and tm[v] != tm[a] for v in e['stun'])):
                t = tm[a]; key = 'S' if t == S else 'O'
                C[key + '_dmg_acts'] += 1
                C[key + '_dmg_acts_bush'] += f in bushes
                if k == 'cast':
                    C[key + '_casts'] += 1; C[key + '_casts_bush'] += f in bushes
                for v, amt in hit:
                    if t == S:
                        unseen = a not in sees(v, r)
                        C['S_dmg'] += amt; C['S_dmg_unseen'] += amt * unseen
                    round_dmg[(v, r)] += amt
                    last_hit[v] = (a, f, r, k, e.get('ab'))
        elif k == 'death':
            v = e['v']; by = e.get('by')
            if tm.get(v) == O:
                C['O_deaths'] += 1
                if e.get('linked'): C['O_deaths_linked'] += 1
                if by == 'camp': C['O_deaths_camp'] += 1
                elif by in tm and tm[by] == S:
                    C['O_deaths_S'] += 1
                    if e.get('linked'): continue
                    C['kills'] += 1
                    C['kill_type_' + nm[by]] += 1
                    h0 = hp_start(v, r); h1 = max(h0, hp_start(v, r - 1))
                    C['burst1'] += h0 >= 0.9; C['burst2'] += h1 >= 0.9
                    seen = any(by in sees(v, rr) for rr in range(r - 3, r + 1))
                    C['unseen'] += not seen
                    lh = last_hit.get(v)
                    bush = bool(lh and lh[0] == by and lh[1] in bushes)
                    C['kill_bush'] += bush
                    if h0 >= 0.9:
                        C['burst1_unseen'] += not seen; C['burst1_bush'] += bush
                    gems = e.get('gems', 0) or 0
                    C['carrier'] += gems >= 40; C['gems_taken'] += gems
                    C['stunned_before'] += any(r - 2 <= s <= r for s in stunned_at[v])
                    vp = e.get('at')
                    if vp:
                        own = m.half(tuple(vp)) if hasattr(m, 'half') else None
                        C['in_victim_half'] += own == O
                    lst['burst_round'].append(round_dmg[(v, r)])
                    if lh and lh[3] == 'cast': C['kill_by_cast'] += 1
            elif tm.get(v) == S:
                C['S_deaths'] += 1
                if by in tm and tm[by] == O and not e.get('linked'): C['S_deaths_O'] += 1
        elif k == 'capture_hold':
            holds[e['g']] = (e['team'], r)
            if e['team'] == O: C['O_holds'] += 1
        elif k == 'capture_reset':
            gr = e['g']
            if e['team'] == O:
                near = any(tm[c] == S and pos.get(c) and min(cheb(pos[c], t) for t in gtiles[gr]) <= 4
                           for c in tm if pos.get(c) is not None)
                C['O_resets'] += 1; C['O_resets_near'] += near; C['O_resets_contested'] += bool(e.get('contested'))
        elif k == 'capture':
            gr = e['g']; t = e['team']
            gems = sum(sh[1] for sh in e['shares'])
            if t == O: C['O_paid'] += 1
            dd = gdmg[gr]; tot = dd[0] + dd[1]
            if tot > 0 and dd[t] < 0.5 * tot:
                C[('S' if t == S else 'O') + '_steal_gems'] += gems
                C[('S' if t == S else 'O') + '_steals'] += 1
            gdmg[gr] = [0.0, 0.0]
        elif k == 'group_respawn':
            gdmg[e['g']] = [0.0, 0.0]
        elif k == 'tribute_end':
            C[('S' if tm[e['a']] == S else 'O') + '_tributed'] += e.get('gems', 0)
    for c in g.champs:
        a = chs[c['id']]['alive']
        C[('S' if c['team'] == S else 'O') + '_dead_rounds'] += sum(1 for x in a if not x)
        C[('S' if c['team'] == S else 'O') + '_body_rounds'] += len(a)
    return C, dict(lst)


def run(jobs, threads):
    tot = collections.Counter(); L = collections.defaultdict(list)
    with Pool(threads) as p:
        for C, lst in p.imap_unordered(process, jobs):
            tot.update(C)
            for k, v in lst.items(): L[k].extend(v)
    return tot, L


def expand(sources):
    out = []
    for s in sources:
        g = glob.glob(s)
        out.extend(sorted(g) if g else [s])
    return out


def select(sources, team, index):
    want = team.lower(); jobs, seen = [], set()
    for src in sources:
        p = Path(src).resolve().relative_to(ROOT).as_posix().rstrip('/')
        rows = [r for r in index if r['source'] == p or r['source'].startswith(p + '/')]
        if not rows: raise SystemExit(f'no extracted replays under {src}')
        for r in rows:
            if not r['ok'] or r['dir'] in seen: continue
            mm = [i for i, n in enumerate(r['teams']) if want in (n or '').lower()]
            if len(mm) == 1:
                seen.add(r['dir']); jobs.append((r['dir'], mm[0]))
    return jobs


def card(C, L):
    n = max(1, C['games']); k = max(1, C['kills'])
    pct = lambda a, b: f'{100 * a / max(1, b):.0f}%'
    rows = [
        ('games / killer win rate', f"{C['games']} / {pct(C['won'], C['games'])}"),
        ('median game length (rounds)', f"{statistics.median(L['rounds']):.0f}" if L['rounds'] else '-'),
        ('victim deaths per game (all / to champions / to camps)',
         f"{C['O_deaths'] / n:.1f} / {C['O_deaths_S'] / n:.1f} / {C['O_deaths_camp'] / n:.2f}"),
        ('killer deaths per game (all / to champions)', f"{C['S_deaths'] / n:.1f} / {C['S_deaths_O'] / n:.1f}"),
        ('kills per game (linked bodies once)', f"{C['kills'] / n:.2f}"),
        ('victim dead share of body-rounds / killer', f"{pct(C['O_dead_rounds'], C['O_body_rounds'])} / {pct(C['S_dead_rounds'], C['S_body_rounds'])}"),
        ('kills from >=90% hp in one round (per game, share)', f"{C['burst1'] / n:.2f}, {pct(C['burst1'], k)}"),
        ('kills from >=90% hp within two rounds', f"{C['burst2'] / n:.2f}, {pct(C['burst2'], k)}"),
        ('killer unseen by victim in the 3 rounds before', pct(C['unseen'], k)),
        ('one-round bursts with the killer unseen / from a bush', f"{pct(C['burst1_unseen'], C['burst1'])} / {pct(C['burst1_bush'], C['burst1'])}"),
        ('killing blow from a bush', pct(C['kill_bush'], k)),
        ('killing blow is a cast', pct(C['kill_by_cast'], k)),
        ('victim stunned in the 2 rounds before death', pct(C['stunned_before'], k)),
        ('kills in the victim\'s half', pct(C['in_victim_half'], k)),
        ('kills on carriers of 40+ (per game, share)', f"{C['carrier'] / n:.2f}, {pct(C['carrier'], k)}"),
        ('gems taken by kills per game', f"{C['gems_taken'] / n:.0f}"),
        ('median damage to the victim in its death round', f"{statistics.median(L['burst_round']):.0f}" if L['burst_round'] else '-'),
        ('killer damaging acts from a bush / victim\'s', f"{pct(C['S_dmg_acts_bush'], C['S_dmg_acts'])} / {pct(C['O_dmg_acts_bush'], C['O_dmg_acts'])}"),
        ('killer casts from a bush / victim\'s', f"{pct(C['S_casts_bush'], C['S_casts'])} / {pct(C['O_casts_bush'], C['O_casts'])}"),
        ('killer champion damage dealt unseen by the target', pct(C['S_dmg_unseen'], C['S_dmg'])),
        ('victim holds reset with a killer within 4 (per game, share of holds)',
         f"{C['O_resets_near'] / n:.2f}, {pct(C['O_resets_near'], C['O_holds'])}"),
        ('victim holds paid', pct(C['O_paid'], C['O_holds'])),
        ('steals per game, gems (killer / victim)',
         f"{C['S_steals'] / n:.2f} {C['S_steal_gems'] / n:.0f} / {C['O_steals'] / n:.2f} {C['O_steal_gems'] / n:.0f}"),
        ('tributed per game (killer / victim)', f"{C['S_tributed'] / n:.0f} / {C['O_tributed'] / n:.0f}"),
    ]
    types = sorted(((v, kk[10:]) for kk, v in C.items() if kk.startswith('kill_type_')), reverse=True)
    rows.append(('kills by killer champion', ', '.join(f'{t} {pct(v, k)}' for v, t in types)))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sources', nargs='*')
    ap.add_argument('--team')
    ap.add_argument('--scrims', action='store_true')
    ap.add_argument('--json')
    ap.add_argument('--threads', type=int, default=12)
    ap.add_argument('--skip-map', action='append', default=[], help='leave out maps whose name contains this')
    a = ap.parse_args()
    if a.scrims: a.sources, a.team = SCRIMS, 'fish'
    jobs = select(expand(a.sources), a.team, load_index())
    if a.skip_map:
        jobs = [j for j in jobs if not any(x in Game(j[0]).map_name for x in a.skip_map)]
    print(f'{len(jobs)} games', file=sys.stderr)
    C, L = run(jobs, a.threads)
    rows = card(C, L)
    w = max(len(r[0]) for r in rows)
    for name, v in rows: print(f'{name:<{w}}  {v}')
    if a.json: Path(a.json).write_text(json.dumps({'rows': rows, 'raw': C}, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
