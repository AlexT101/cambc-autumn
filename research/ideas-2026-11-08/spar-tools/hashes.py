"""SPARHASH per (map, side) from an ab.py run whose CAND is a patched spar bot: writes hashes.json."""
import json, sys, zipfile, re, os
s = json.load(open(f'/home/ubuntu/cambc-autumn/replays/ab/{sys.argv[1]}/summary.json'))
out = {}
for su in s['suites']:
    r = json.load(open('/home/ubuntu/cambc-autumn/' + su['batch'] + '/results.json'))
    for m in r['matches']:
        side = 'a' if m['order'][0] == 0 else 'b'
        with zipfile.ZipFile(m['replay']) as z: t = z.read(f'team-{side}.stdout').decode('utf-8', 'replace')
        h = re.search(r'SPARHASH (\d+)', t)
        out[os.path.basename(m['map']).replace('.map26a', '') + ':' + side] = int(h[1])
json.dump(out, open(sys.argv[2], 'w'), indent=0); print(len(out), 'unique', len(set(out.values())))
