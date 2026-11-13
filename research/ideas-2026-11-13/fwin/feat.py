"""Per-game features of a Fish r8 game, both teams, from extract.mjs output.
    py feat.py EXT ROWS.json OUT.jsonl
ROWS maps match id -> {fish: 0|1 (Fish's team index, A=0), opp, ...extra}.
Per team at checkpoints C: earned gold, capture gold (all / from Fish's half / from the opponent's half / middle),
kills, deaths, tributed gems; Fish's Vesper gold and deaths; first tribute; 100+ bags; Greed round."""
import gzip, json, os, sys, collections
from multiprocessing import Pool
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
import mstats
C = (100, 200, 300, 400, 500, 650, 800, 1000)
MASK = {int(k): {int(r): v for r, v in d.items()} for k, d in json.load(open('/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/fishr8/mask_r8.json')).items()}
GREED = {12 * 6 + 2 * s + 1 for s in range(3)}

def game(job):
    ext, d, fish, extra = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception: return None
    ch = R['champions']; n = len(R['round']); team = {c['id']: c['team'] for c in meta['champions']}
    typ = {c['id']: c['name'] for c in meta['champions']}
    gside = {g['id']: g.get('side', -1) for g in mp['groups']}
    gval = {g['id']: (g['gold'], g['gems']) for g in mp['groups']}
    o = 1 - fish
    def side_lab(g, t):   # where the group is, relative to team t: own, enemy, mid
        s = gside.get(g, -1)
        return 'mid' if s not in (0, 1) else ('own' if s == t else 'enemy')
    out = {'d': d, 'rounds': n, 'fish': fish, **extra}
    w = meta['result'].get('winner'); out['fish_win'] = w == fish
    out['picks_f'] = [typ[c['id']] for c in ch if c['team'] == fish]; out['picks_o'] = [typ[c['id']] for c in ch if c['team'] == o]
    T = {'f': fish, 'o': o}
    for lab, t in T.items():
        for r in C:
            i = min(r, n) - 1
            out[f'{lab}_earned_{r}'] = sum(c['earned'][i] for c in ch if c['team'] == t)
            out[f'{lab}_gems_{r}'] = R['gems'][t][i]
    V = [c for c in ch if c['team'] == fish and typ[c['id']] == 'Vesper Vale']
    out['has_v'] = bool(V)
    fit = tot = 0   # Fish r8's masked priority: share of unit-rounds whose low 20 bits xor the r8 mask to a payload < 2^17
    for k, c in enumerate(sorted((c for c in ch if c['team'] == fish), key=lambda c: c['id'])):
        for i, v in enumerate(c['prio'][:1000]):
            m = MASK.get(k, {}).get(i + 1)
            if m is None or v is None: continue
            tot += 1; fit += ((v & 0xFFFFF) ^ m) < (1 << 17)
    out['r8sig'] = fit / tot if tot else None
    if V:
        v = V[0]
        for r in C:
            i = min(r, n) - 1
            out[f'v_earned_{r}'] = v['earned'][i]; out[f'v_deaths_{r}'] = v['deaths'][i]; out[f'v_kills_{r}'] = v['kills'][i]
            out[f'v_str_{r}'] = v['str'][i]
        gr = None
        for i in range(n):
            L = v['items'][i] or []
            if any(L[k] in GREED for k in range(0, len(L), 2)): gr = i + 1; break
        out['v_greed'] = gr
    OV = [c for c in ch if c['team'] == o and typ[c['id']] == 'Vesper Vale']
    out['o_has_v'] = bool(OV)
    cap = collections.Counter(); kd = collections.Counter(); trib = collections.defaultdict(list)
    for e in ev:
        k = e['k']; r = e['r']
        if k == 'capture':
            t = e['team']; lab = 'f' if t == fish else 'o'; sl = side_lab(e['g'], t)
            go = sum(x[2] for x in e['shares'])
            for c in C:
                if r <= c:
                    cap[(lab, 'gold', 'all', c)] += go; cap[(lab, 'gold', sl, c)] += go; cap[(lab, 'n', sl, c)] += 1
        elif k == 'death':
            vt = team[e['v']]; lab = 'f' if vt == fish else 'o'
            byc = e.get('by') is not None and 'camp' not in e and team.get(e['by']) == 1 - vt
            for c in C:
                if r <= c:
                    kd[(lab, 'deaths', c)] += 1; kd[(lab, 'gemslost', c)] += e.get('gems', 0)
                    if byc: kd[('o' if lab == 'f' else 'f', 'kills', c)] += 1
                    else: kd[(lab, 'campdeaths', c)] += 1
        elif k == 'tribute_end':
            t = team[e['a']]; trib['f' if t == fish else 'o'].append((r, e['gems']))
        elif k == 'lock_place':
            t = team[e['a']]; kd[('f' if t == fish else 'o', 'locks', 0)] += 1
    for (lab, a, sl, c), v in cap.items(): out[f'{lab}_cap{a}_{sl}_{c}'] = v
    for (lab, a, c), v in kd.items(): out[f'{lab}_{a}_{c}' if c else f'{lab}_{a}'] = v
    for lab in 'fo':
        tr = trib[lab]
        out[f'{lab}_trib1'] = tr[0][0] if tr else None
        out[f'{lab}_ntrib'] = len(tr); out[f'{lab}_ntrib100'] = sum(1 for r, g in tr if g >= 100)
        out[f'{lab}_trib_list'] = tr[:12]
    ms = mstats.game((ext, d, fish, {}))
    if ms:
        for k in ('coh5', 'enemy_half', 'prism_maxbag', 'bag_med', 'bag_mean', 'conv', 'assist', 'clear_bodies200', 'coh_r20', 'coh_r60', 'wards', 'recalls', 'crystals', 'casts_champ', 'att_champ', 'att_camp', 'trib_gems', 'caps300'):
            out['fm_' + k] = ms['m'].get(k); out['om_' + k] = ms['o'].get(k)
    return out

def main():
    ext, rows_f, outf = sys.argv[1:4]
    idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(rows_f)); jobs = []
    for g in idx:
        mid = os.path.basename(g['source'])[:-8]
        if mid not in rows: continue
        r = rows[mid]
        jobs.append((ext, g['dir'], r['fish'], {k: v for k, v in r.items() if k != 'fish'} | {'match': mid}))
    with Pool(int(os.environ.get('OMP_NUM_THREADS', '8'))) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    with open(outf, 'w') as fh:
        for x in res: fh.write(json.dumps(x) + '\n')
    print(len(res), 'games ->', outf)

if __name__ == '__main__': main()
