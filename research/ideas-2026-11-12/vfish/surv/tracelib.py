import json, gzip, os, sys, collections, zipfile
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
class Game:
    def __init__(self, ext, g, repo='/home/ubuntu/cambc-autumn'):
        self.g = g; self.cand = 0 if g['teams'][0].startswith('vfish') else 1
        p = f"{ext}/{g['dir']}"; self.meta = json.load(open(p + '/meta.json'))
        self.typ = {c['id']: c['name'] for c in self.meta['champions']}; self.team = {c['id']: c['team'] for c in self.meta['champions']}
        self.R = json.load(gzip.open(p + '/rounds.json.gz')); self.ch = {c['id']: c for c in self.R['champions']}
        self.ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
        self.map = json.load(open(f"{ext}/maps/{self.meta['map']['hash']}.json"))
        self.win = g['winner'] == self.cand
        self.byr = collections.defaultdict(list)
        for e in self.ev: self.byr[e['r']].append(e)
        src = g['source'] if os.path.isabs(g['source']) else f"{repo}/{g['source']}"
        self.tr = collections.defaultdict(lambda: collections.defaultdict(list))  # handle -> round -> [fields]
        try:
            z = zipfile.ZipFile(src); txt = z.read('team-a.stdout' if self.cand == 0 else 'team-b.stdout').decode('utf8', 'replace')
            for l in txt.split('\n'):
                f = l.split()
                if len(f) >= 3 and f[0] in ('D', 'WH', 'ST', 'TT', 'EB', 'RFWHY', 'RFKEEP', 'RFDROP', 'PZFIX4', 'PZFIX4A', 'LSTEP', 'REVEAL', 'SC', 'MZ'):
                    try: self.tr[int(f[2])][int(f[1])].append(f)
                    except ValueError: pass
                elif len(f) >= 4 and f[0] in ('CT',):
                    try: self.tr[int(f[2])][int(f[1])].append(f)
                    except ValueError: pass
                elif len(f) >= 4 and f[0] == 'CV':
                    try: self.tr[int(f[3])][int(f[2])].append(f)
                    except ValueError: pass
                elif len(f) >= 3 and f[0] == 'SHORTCUT':
                    try: self.tr[int(f[2])][int(f[1])].append(f)
                    except ValueError: pass
        except Exception as e:
            self.tr_err = str(e)
    def pos(self, i, r):
        """position at the END of round r (None if dead)"""
        c = self.ch[i]; ri = r - 1
        if ri < 0 or ri >= len(c['alive']) or not c['alive'][ri]: return None
        return (c['x'][ri], c['y'][ri])
    def spawn_c(self, t):
        s = self.map['spawn'][t]; return ((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2)
    def lines(self, h, r, tag): return [f for f in self.tr[h][r] if f[0] == tag]
    def dec(self, h, r):
        L = self.lines(h, r, 'D'); return L[0][3] if L else '?'
    def deaths(self, maxr=300, ours=True):
        for e in self.ev:
            if e['k'] == 'death' and 'linked' not in e and e['r'] <= maxr and (self.team[e['v']] == self.cand) == ours: yield e
def games(ext):
    idx = json.load(open(ext + '/index.json'))['games']
    for g in idx: yield Game(ext, g)
