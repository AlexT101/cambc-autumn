"""Champion deaths in an extract dir: did the victim (or any of its allies) see the killer before the first hit?"""
import sys, json, gzip, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

def one(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    except Exception:
        return None
    rounds = R['round']; r0 = rounds[0]
    ch = {c['id']: c for c in R['champions']}
    names = {c['id']: c['name'] for c in meta['champions']}
    out = []
    # first champion-damage hit per (victim, killer) before death: approximate with attack/cast events targeting victim
    for e in ev:
        if e.get('k') != 'death': continue
        v, k, r = e['v'], e.get('by'), e['r']
        if k is None or k not in ch or ch[k]['team'] == ch[v]['team']: 
            out.append(dict(cause='camp/other', victim=names.get(v), gems=e.get('gems',0))); continue
        i = r - r0
        team = ch[v]['team']
        allies = [c for c in R['champions'] if c['team']==team and c['id']!=v]
        def seen_by(c, j):
            s = c['seenBy'][j] if j < len(c['seenBy']) else []
            return s
        # rounds before death in which victim saw killer (killer's seenBy contains victim)
        W = 10
        vic_saw = [j for j in range(max(0,i-W), i) if v in ch[k]['seenBy'][j]]
        ally_saw = [j for j in range(max(0,i-W), i) if any(a['id'] in ch[k]['seenBy'][j] for a in allies)]
        first_v = min(vic_saw) - i if vic_saw else None
        # allies within 8 at death-1
        j = max(0,i-1)
        vx, vy = ch[v]['x'][j], ch[v]['y'][j]
        near_all = sum(1 for a in allies if a['alive'][j] and max(abs(a['x'][j]-vx), abs(a['y'][j]-vy)) <= 8)
        en = [c for c in R['champions'] if c['team']!=team]
        near_en = sum(1 for c in en if c['alive'][j] and max(abs(c['x'][j]-vx), abs(c['y'][j]-vy)) <= 8)
        out.append(dict(cause='champ', victim=names.get(v), killer=names.get(k), gems=e.get('gems',0), r=r,
                        vic_saw_first=first_v, ally_saw=bool(ally_saw), vic_saw_any=bool(vic_saw), near_all=near_all, near_en=near_en))
    return out

if __name__ == '__main__':
    dirs = [p for a in sys.argv[1:] for p in Path(a).iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, dirs, chunksize=8):
            if o: rows += o
    ch = [x for x in rows if x['cause']=='champ']
    print('deaths', len(rows), 'champ', len(ch), 'games', len(dirs))
    c = collections.Counter()
    for x in ch:
        key = ('saw' if x['vic_saw_any'] else ('ally-saw' if x['ally_saw'] else 'unseen'))
        c[key] += 1; c[key+'_gems'] += x['gems']
    print(c)
    # seen how early
    lead = collections.Counter(x['vic_saw_first'] for x in ch if x['vic_saw_any'])
    print('victim first saw killer, rounds before death:', sorted(lead.items()))
    big = [x for x in ch if x['gems'] >= 100]
    print('big-bag deaths', len(big), collections.Counter(('saw' if x['vic_saw_any'] else 'ally' if x['ally_saw'] else 'unseen') for x in big))
    print('victims', collections.Counter(x['victim'] for x in ch).most_common())
    print('killers', collections.Counter(x['killer'] for x in ch).most_common())
    print('near allies/enemies at death-1 (mean):', sum(x['near_all'] for x in ch)/len(ch), sum(x['near_en'] for x in ch)/len(ch))
    print('outnumbered (en>all+1):', sum(1 for x in ch if x['near_en'] > x['near_all']+1), 'even-ish', sum(1 for x in ch if abs(x['near_en']-x['near_all']-1)<=0))
