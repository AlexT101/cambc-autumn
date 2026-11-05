"""Replay list for decode.mjs: every .repl26a under the given group folders' roots."""
import json, os, sys
out, roots = sys.argv[1], sys.argv[2:]
L = []
for root in roots:
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d)
        gj = os.path.join(p, 'group.json')
        if not os.path.isfile(gj): continue
        files = [f for f in os.listdir(p) if f.endswith('.repl26a')]
        if not files: continue
        g = json.load(open(gj))
        sides = {s['side']: s['teamName'] for s in g['group']['sides']}
        gid = g['group']['id'][:8]
        for f in files:
            n = f.split('-')[0]
            L.append({'key': f'{gid}-{n}', 'replay': os.path.abspath(os.path.join(p, f)), 'teams': [sides['a'], sides['b']],
                      'group': g['group']['id'], 'n': int(n), 'created': g['group']['createdAt']})
json.dump(L, open(out, 'w'))
print(len(L), 'replays')
