import zipfile, re, json, sys, collections, glob
agg = collections.Counter(); n = 0
for b in sys.argv[1:]:
    for m in json.load(open(b + '/results.json'))['matches']:
        p = m.get('replay')
        if not p: continue
        n += 1
        t = 'ab'[0 if m['order'][0] == 0 else 1]
        o = zipfile.ZipFile(p).read(f'team-{t}.stdout').replace(b'\0', b'').decode('utf-8', 'replace')
        for mm in re.finditer(r'^RS (\d+) (\d+) (\d) (\d) (\d) (\d) (\d) (\d)$', o, re.M):
            path, stay, to, opn, safe, safe_home = map(int, mm.groups()[2:])
            agg[(path, stay, to, min(safe, 1), min(safe_home, 1))] += 1
print(n, 'games; path 1 no danger, 2 step home off avoid, 3 clear option, 4 home-walk option, 5 damaged option, 6 fallback')
print('path stay_lethal to_lethal other_safe other_safe_homeward  count /game')
for k, c in sorted(agg.items()):
    if k[1] or k[2]: print(k, c, round(c / n, 3))
