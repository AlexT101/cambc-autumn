import sys, zipfile, re, glob, collections
import os
root = sys.argv[1]; cls_want = sys.argv[2] if len(sys.argv)>2 else 'oof'; MINR=int(os.environ.get('MINROUND','0'))
st = collections.defaultdict(lambda: [0,0,0,0]); nt=0
for d in glob.glob(root + '/*/'):
    z = glob.glob(d + '*.repl26a')
    if not z: continue
    zf = zipfile.ZipFile(z[0]); side = d.rstrip('/')[-1]
    for line in zf.read(f'team-{side}.stdout').decode(errors='replace').splitlines():
        if not line.startswith('CEN '): continue
        head, _, body = line.partition(' | ')
        try:
            if int(head.split()[1].strip('\x00')) < MINR: continue
        except ValueError: pass
        oof = ' oof1' in head
        m = re.search(r'spent (\d+)', head); spent = int(m.group(1)) if m else 0
        cls = 'oof' if oof else ('heavy' if spent >= 85000 else 'light')
        if cls != cls_want: continue
        nt += 1
        for item in body.split():
            k, _, v = item.rpartition('=')
            try: incl, self_, n = map(int, v.split(":"))
            except ValueError: continue
            s = st[k]; s[0]+=incl; s[1]+=self_; s[2]+=n; s[3]+=1
print('turns', nt)
for k,s in sorted(st.items(), key=lambda kv:-kv[1][1])[:int(os.environ.get("TOP","45"))]:
    print(f'{k:22} self/T {s[1]/nt:7.0f} incl/T {s[0]/nt:7.0f} turns% {100*s[3]/nt:5.1f} calls/T {s[2]/nt:6.2f}')
