"""h-race study read: per side, deaths, gems lost at death, retreat deaths (the body's last turn before death was R),
captures, and the trace side's RACE triggers by previous branch. Usage: race.py BATCH_DIR EXTRACT_DIR"""
import sys, re, json, gzip, zipfile, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
RACE_RE = re.compile(rb'^[\s\0]*RACE (\d+) (\d+) (\S) (-?\d+) (-?\d+) (-?\d+)\s*$', re.M)
INDEX = {}


def init(ix):
    INDEX.update(ix)


def one(f):
    f = Path(f)
    d = INDEX.get(f.name)
    if d is None:
        return None
    try:
        meta = json.loads((d / 'meta.json').read_text())
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
        z = zipfile.ZipFile(f)
    except Exception:
        return None
    names = [t['name'] for t in meta['teams']]
    team = {c['id']: c['team'] for c in meta['champions']}
    cname = {c['id']: c['name'] for c in meta['champions']}
    out = {}
    for t in (0, 1):
        raw = z.read('team-a.stdout' if t == 0 else 'team-b.stdout')
        D = collections.defaultdict(dict)
        for m in D_RE.finditer(raw):
            D[int(m[2])][int(m[1])] = m[3].decode()
        m = collections.Counter()
        m['games'] = 1
        races = collections.defaultdict(list)
        for x in RACE_RE.finditer(raw):
            m['race'] += 1
            m['race_' + x[3].decode()] += 1
            races[int(x[2])].append(int(x[1]))
            if cname.get(int(x[2])) == 'Prism':
                m['race_prism'] += 1
        # a trigger within 3 rounds of the body's last one, its turns between not all retreats: leave, come back, leave
        for h, rs in races.items():
            for a, b in zip(rs, rs[1:]):
                if b - a <= 4 and any(D[h].get(r) not in ('R', 'K', None) for r in range(a + 1, b)):
                    m['race_osc'] += 1
        for e in ev:
            k = e.get('k')
            if k == 'death' and team.get(e['v']) == t and not e.get('linked'):
                v, r = e['v'], e['r']
                m['deaths'] += 1
                m['gems_lost'] += e.get('gems', 0)
                prism = cname[v] == 'Prism'
                if prism:
                    m['prism_deaths'] += 1
                    m['prism_gems_lost'] += e.get('gems', 0)
                turns = [rr for rr in D[v] if rr < r and rr >= r - 70]
                if turns:
                    last = D[v][max(turns)]
                    if last == 'R':
                        m['retreat_deaths'] += 1
                        m['retreat_gems_lost'] += e.get('gems', 0)
                        # the retreat's first turn: was it a race trigger?
                        rr = max(turns)
                        while D[v].get(rr - 1) == 'R':
                            rr -= 1
                        if rr in races.get(v, ()):
                            m['retreat_deaths_raced'] += 1
            elif k == 'capture' and e['team'] == t:
                m['captures'] += 1
                m['cap_gems'] += sum(s[1] for s in e['shares'])
        out[names[t]] = m
    sc = [0, 0]
    return out


if __name__ == '__main__':
    BATCH, AN = Path(sys.argv[1]), Path(sys.argv[2])
    for dd in AN.iterdir():
        if (dd / 'meta.json').exists():
            INDEX[Path(json.loads((dd / 'meta.json').read_text())['source']).name] = dd
    files = sorted(BATCH.glob('*.repl26a'))
    tot = collections.defaultdict(collections.Counter)
    with ProcessPoolExecutor(32, initializer=init, initargs=(INDEX,)) as ex:
        for o in ex.map(one, files, chunksize=8):
            if not o:
                continue
            for k, v in o.items():
                tot[k].update(v)
    for k, m in tot.items():
        g = m['games']
        print(k, f'games {g}', ' '.join(f'{a} {m[a] / g:.3f}' for a in sorted(m) if a != 'games'))
