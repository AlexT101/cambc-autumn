import zipfile, glob, sys, collections
D = sys.argv[1]; bot = sys.argv[2] if len(sys.argv) > 2 else 'fb-inst'
A, An, H, Hn = (collections.Counter() for _ in range(4)); SA, SAn, SH, SHn = (collections.Counter() for _ in range(4)); hdr = collections.Counter()
for f in glob.glob(D + '/*/*.repl26a'):
    z = zipfile.ZipFile(f)
    side = 'a' if f.split('/')[-1].startswith(bot) else 'b'
    last, lasts, lastfbi = {}, {}, {}
    for l in z.read(f'team-{side}.stdout').decode(errors='replace').splitlines():
        p = l.split()
        try:
            if p and p[0] in ('FBL', 'FBS'):
                h = p[1].split('.')[1]; (last if p[0] == 'FBL' else lasts)[(h, int(p[2]))] = tuple(map(int, p[3:7]))
            elif p and p[0] == 'FBI':
                lastfbi[p[1].split('.')[1]] = dict(zip(p[2::2], map(int, p[3::2])))
        except (ValueError, IndexError): pass
    for (h, k), (n, fu, hn, hf) in last.items(): A[k] += fu; An[k] += n; H[k] += hf; Hn[k] += hn
    for (h, k), (n, fu, hn, hf) in lasts.items(): SA[k] += fu; SAn[k] += n; SH[k] += hf; SHn[k] += hn
    for d in lastfbi.values(): hdr.update(d)
print(dict(hdr))
ta, th = sum(A.values()), sum(H.values())
print('line   all%   n_all  per    heavy%  n_heavy per')
for k in sorted(A, key=lambda k: -H[k])[:30]:
    print(f'{k:5d} {100*A[k]/ta:6.2f} {An[k]:8d} {A[k]/max(1,An[k]):6.0f}  {100*H[k]/max(1,th):6.2f} {Hn[k]:8d} {H[k]/max(1,Hn[k]):6.0f}')
print('sub   all%(of loop)  n  per   heavy%  n  per')
for k in sorted(SA, key=lambda k: -SH[k]):
    print(f'{k:5d} {100*SA[k]/ta:6.2f} {SAn[k]:8d} {SA[k]/max(1,SAn[k]):6.0f}  {100*SH[k]/max(1,th):6.2f} {SHn[k]:8d} {SH[k]/max(1,SHn[k]):6.0f}')
