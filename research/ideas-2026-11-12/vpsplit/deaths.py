"""Deaths of our champions by round bucket and by champion, split V+P games (BAL rule), paired arms. Usage: deaths.py EXT_ROOT BASE ARM..."""
import sys, json, gzip, glob, os, re, collections
sys.path.insert(0, os.path.dirname(__file__))
from vpmech_lib import split_of
root, base, arms = sys.argv[1], sys.argv[2], sys.argv[3:]
def load(bot):
    out = {}
    for mp in glob.glob(f'{root}/{bot}/*/meta.json'):
        g = os.path.dirname(mp); m = json.load(open(mp))
        k = re.search(r'-k(\d)-ladder', m['source']).group(1); stem = os.path.basename(m['source']).split('-', 1)[1]
        t = [i for i, x in enumerate(m['teams']) if x['name'] == bot][0]
        name = {c['id']: c['name'] for c in m['champions']}; team = {c['id']: c['team'] for c in m['champions']}
        if not {'Vesper Vale', 'Prism'} <= {name[c] for c in name if team[c] == t}: continue
        J = json.load(open(os.path.normpath(os.path.join(g, m['mapFile']))))
        if not split_of(J, t)[0]: continue
        s = collections.Counter()
        for line in gzip.open(f'{g}/events.jsonl.gz', 'rt'):
            e = json.loads(line)
            if e['k'] == 'death' and team.get(e['v']) == t:
                b = 'r<=100' if e['r'] <= 100 else 'r<=200' if e['r'] <= 200 else 'r<=400' if e['r'] <= 400 else 'r>400'
                s[b] += 1; s[name[e['v']]] += 1; s['gemslost'] += e.get('gems', 0)
        out[(k, stem)] = s
    return out
B = load(base)
for arm in arms:
    A = load(arm); ks = [k for k in A if k in B]; n = len(ks)
    keys = sorted(set().union(*[set(A[k]) | set(B[k]) for k in ks]))
    print(arm, n, 'split V+P pairs')
    for x in keys: print(f'  {x}: {sum(B[k][x] for k in ks)/n:.2f} -> {sum(A[k][x] for k in ks)/n:.2f}')
