"""Mechanism rates over prism_mech.py rows.  py prism_mech_rates.py ROWS.jsonl [--list SRC...]"""
import json, sys
from collections import Counter

FARM = set('FPQCBWUSXGThHr')  # anything but retreat / recall / none
rows = [json.loads(l) for l in open(sys.argv[1])]
L = 8  # one ability cooldown


def feats(x):
    tr = {row['r']: row for row in x['trace']}
    fh = x['first_hit']
    f = {'camp': x['killer'] == 'camp'}
    if not fh:
        return f
    r0 = fh[0]
    # Rounds before the first hit in which an enemy was in the victim's sight, counted back over the unbroken run.
    pre = 0; gap = 0; r = r0 - 1; farm_pre = 0
    while r in tr and r >= x['D'] - 40:
        if tr[r]['sees']:
            pre = r0 - r; gap = 0
            if tr[r]['br'] in FARM: farm_pre += 1
        else:
            gap += 1
            if gap > 2: break
        r -= 1
    expo = sum(1 for r in range(r0 - 20, r0) if r in tr and tr[r]['sees'])
    expo_farm = sum(1 for r in range(r0 - 20, r0) if r in tr and tr[r]['sees'] and tr[r]['br'] in FARM)
    first_seen = next((r for r in range(r0 - 40, r0 + 1) if r in tr and tr[r]['sees']), None)
    peak_pre = max((tr[r]['en8'] for r in range(r0 - 10, r0 + 1) if r in tr), default=0)
    row = x['fh_row'] or tr.get(r0)
    f.update(expo=expo, expo_farm=expo_farm, peak_pre=peak_pre, pre=pre, farm_pre=farm_pre, blind=x['blind'], al8=row['al8'], en8=row['en8'], br_fh=row['br'], home_fh=row['home'],
             home_d=x['last']['home'], t_kill=x['D'] - r0, nstun=len({s[0] for s in x['stuns'] if s[0] >= r0}),
             by=x['first_hit_by'], hp_fh=row['hp'], ratio=(row['foc'] / row['ofoc']) if row['ofoc'] else None,
             vcasts=x['vcasts'], ally_out=x['ally_out'], enemy_out=x['enemy_out'],
             al_farm=sum(1 for b, d in zip(row['albr'], [None] * 9) if b in 'FPQ'),
             ald_min=min(row['ald']) if row['ald'] else 99)
    return f


def mech(f):
    if f['camp']: return 'camp'
    if 'pre' not in f: return 'other'
    if f['expo_farm'] >= L:
        return 'lingered-outnumbered' if f['al8'] < f['en8'] else 'lingered-team-contest'
    return 'arrival-blind' if f['blind'] else 'arrival-seen'


if '--list' in sys.argv:
    want = sys.argv[sys.argv.index('--list') + 1:]
    for x in rows:
        if x['src'] in want:
            f = feats(x)
            print(x['src'][:28], x['D'], mech(f), {k: (round(v, 2) if isinstance(v, float) else v) for k, v in f.items() if k != 'camp'})
    sys.exit()

F = [(x, feats(x)) for x in rows]
n = len(F)
pct = lambda k: f'{k} ({k / n * 100:.0f}%)'
c = Counter(mech(f) for _, f in F)
print('n', n, {k: pct(v) for k, v in c.most_common()})
for Lx in (4, 12):
    L = Lx; print(f'L={Lx}', dict(Counter(mech(f) for _, f in F).most_common())); 
L = 8
G = [(x, f) for x, f in F if 'pre' in f and not f['camp']]
m = len(G)
def share(pred, S=G): return f'{sum(1 for x, f in S if pred(x, f))}/{len(S)} ({sum(1 for x, f in S if pred(x, f)) / max(1, len(S)) * 100:.0f}%)'
print('non-camp with a first hit', m)
print('enemy in sight >= 8 rounds before first hit', share(lambda x, f: f['pre'] >= 8))
print('enemy in sight >= 4 rounds before first hit', share(lambda x, f: f['pre'] >= 4))
print('first hit blind (attacker unseen)', share(lambda x, f: f['blind']))
print('outnumbered within 8 at first hit', share(lambda x, f: f['al8'] < f['en8']))
print('no ally within 8 at first hit', share(lambda x, f: f['al8'] == 0))
print('victim branch farm-ish at first hit', share(lambda x, f: f['br_fh'] in FARM))
print('first hit by enemy Prism', share(lambda x, f: f['by'] == 'Prism'))
print('first hit is a stun', share(lambda x, f: x['first_stun'] is not None and x['first_stun'] == x['first_hit'][0]))
print('>= 2 stuns on victim from first hit to death', share(lambda x, f: f['nstun'] >= 2))
print('first hit -> death <= 2 rounds (burst)', share(lambda x, f: f['t_kill'] <= 2))
print('first hit -> death >= 8 rounds (one cooldown: chased)', share(lambda x, f: f['t_kill'] >= 8))
print('of chased (>=8): >= 2 stuns', share(lambda x, f: f['nstun'] >= 2, [(x, f) for x, f in G if f['t_kill'] >= 8]))
print('of chased (>=8): got closer to home', share(lambda x, f: f['home_d'] < f['home_fh'], [(x, f) for x, f in G if f['t_kill'] >= 8]))
print('victim dealt damage to enemy champions in fight', share(lambda x, f: f['vcasts'] > 0))
print('allies dealt < 1/3 of enemy damage in last 15', share(lambda x, f: f['ally_out'] < f['enemy_out'] / 3))
print('focus ratio victim/enemy Prism at first hit <0.8 / 0.8-1.25 / >1.25',
      share(lambda x, f: f['ratio'] is not None and f['ratio'] < 0.8), share(lambda x, f: f['ratio'] is not None and 0.8 <= f['ratio'] <= 1.25),
      share(lambda x, f: f['ratio'] is not None and f['ratio'] > 1.25))
import statistics as st
print('home walk dist at first hit median', st.median(f['home_fh'] for _, f in G), 'quartiles', st.quantiles([f['home_fh'] for _, f in G], n=4))
print('pre (rounds enemy seen before first hit) quartiles', st.quantiles([f['pre'] for _, f in G], n=4))
print('exposure (rounds with enemy in sight of the 20 before first hit) quartiles', st.quantiles([f['expo'] for _, f in G], n=4))
print('exposure while farming >= 8', share(lambda x, f: f['expo_farm'] >= 8), '>= 4', share(lambda x, f: f['expo_farm'] >= 4), '>= 12', share(lambda x, f: f['expo_farm'] >= 12))
print('>= 2 enemies within 8 at some point in the 10 rounds before first hit', share(lambda x, f: f['peak_pre'] >= 2))
print('allies on farm/hold branches at first hit: mean', sum(f['al_farm'] for _, f in G) / m, 'of', sum(len(x['picks']) for x, _ in G) / m)
for k in ('lingered-outnumbered', 'lingered-team-contest', 'arrival-seen', 'arrival-blind'):
    S = [(x, f) for x, f in G if mech(f) == k]
    if not S: continue
    print(f'-- {k} n={len(S)}: victim team lost', share(lambda x, f: x['winner'] != x['vteam'], S), '| >=2 stuns', share(lambda x, f: f['nstun'] >= 2, S),
          '| burst<=2', share(lambda x, f: f['t_kill'] <= 2, S), '| by Prism', share(lambda x, f: f['by'] == 'Prism', S),
          '| no ally<=8', share(lambda x, f: f['al8'] == 0, S), '| victim hit back', share(lambda x, f: f['vcasts'] > 0, S),
          '| foc<0.8', share(lambda x, f: f['ratio'] is not None and f['ratio'] < 0.8, S), '| home med', st.median(f['home_fh'] for _, f in S))
